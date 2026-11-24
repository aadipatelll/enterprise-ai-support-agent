"""Compare chunk sizes, top-k values, and prompt versions on eval/questions.json.

Usage (from the repo root, with the backend venv active and Ollama running):
    python eval/run_eval.py --chunk-sizes 300 800 --top-ks 2 4 --prompts v1 v2

The index for each chunk size is built in memory with exact cosine search (the same
metric pgvector uses), so running an evaluation never touches the app's database.
Results are written to eval/results/results.md and eval/results/details.json.
"""

import argparse
import itertools
import json
import math
import sys
import time
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from app.config import Settings, get_settings
from app.exceptions import SupportAgentError
from app.ingestion.chunking import Chunk, chunk_documents
from app.ingestion.loader import SourceDocument, load_documents
from app.ingestion.pipeline import embed_chunks
from app.prompts import PROMPT_VERSIONS
from app.providers import build_chat_model, build_embeddings
from app.rag import AnswerService
from app.retrieval import RetrievedChunk
from app.schemas import AskResponse

EVAL_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = EVAL_DIR / "questions.json"
RESULTS_DIR = EVAL_DIR / "results"


@dataclass(frozen=True)
class Question:
    id: str
    question: str
    expected_answer: str
    expected_sources: tuple[str, ...]
    key_facts: tuple[str, ...]  # each fact may list alternatives separated by "|"
    answerable: bool


@dataclass(frozen=True)
class EvalConfig:
    chunk_size: int
    top_k: int
    prompt_version: str


@dataclass(frozen=True)
class QuestionResult:
    question_id: str
    answer: str
    retrieved_sources: list[str]
    retrieval_hit: bool | None  # None for unanswerable questions
    correct: bool
    cited_expected_source: bool | None  # None unless an answerable question was answered
    latency_seconds: float


@dataclass(frozen=True)
class ConfigReport:
    config: EvalConfig
    retrieval_hit_rate: float
    answer_accuracy: float
    abstention_accuracy: float | None
    citation_accuracy: float | None
    mean_latency_seconds: float
    results: list[QuestionResult]


def load_questions(path: Path = QUESTIONS_PATH) -> list[Question]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        Question(
            id=item["id"],
            question=item["question"],
            expected_answer=item["expected_answer"],
            expected_sources=tuple(item["expected_sources"]),
            key_facts=tuple(item["key_facts"]),
            answerable=item["answerable"],
        )
        for item in raw
    ]


# --- Scoring -------------------------------------------------------------------------


def normalize(text: str) -> str:
    return text.lower().replace(",", "")


def fact_present(fact: str, answer: str) -> bool:
    """True if any "|"-separated alternative of the fact appears in the answer."""
    return any(normalize(option.strip()) in normalize(answer) for option in fact.split("|"))


def is_correct(question: Question, response: AskResponse) -> bool:
    if not question.answerable:
        return not response.answered
    return response.answered and all(fact_present(f, response.answer) for f in question.key_facts)


def cited_expected_source(question: Question, response: AskResponse) -> bool | None:
    if not (question.answerable and response.answered):
        return None
    return any(citation.source in question.expected_sources for citation in response.citations)


def rate(values: Iterable[bool | None]) -> float | None:
    scored = [value for value in values if value is not None]
    return sum(scored) / len(scored) if scored else None


# --- In-memory index -----------------------------------------------------------------


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    norm = math.hypot(*a) * math.hypot(*b)
    return sum(x * y for x, y in zip(a, b, strict=True)) / norm if norm else 0.0


class InMemoryRetriever:
    """Exact cosine search over pre-embedded chunks; implements the Retriever protocol."""

    def __init__(self, chunks: Sequence[Chunk], vectors: Sequence[list[float]]) -> None:
        self._items = list(zip(chunks, vectors, strict=True))

    def search(self, query_vector: list[float], top_k: int) -> list[RetrievedChunk]:
        scored = [(cosine_similarity(query_vector, vector), chunk) for chunk, vector in self._items]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            RetrievedChunk(
                title=chunk.title,
                section=chunk.section,
                source=chunk.source,
                content=chunk.content,
                score=round(score, 4),
            )
            for score, chunk in scored[:top_k]
        ]


class QueryCachingEmbeddings(Embeddings):
    """Embeds each question once, however many configurations reuse it."""

    def __init__(self, inner: Embeddings) -> None:
        self._inner = inner
        self._cache: dict[str, list[float]] = {}

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._inner.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        if text not in self._cache:
            self._cache[text] = self._inner.embed_query(text)
        return self._cache[text]


# --- Running -------------------------------------------------------------------------


def evaluate_question(service: AnswerService, question: Question) -> QuestionResult:
    retrieved = [chunk.source for chunk in service.retrieve(question.question)]
    started = time.perf_counter()
    response = service.ask(question.question)
    latency = time.perf_counter() - started
    hit = any(s in question.expected_sources for s in retrieved) if question.answerable else None
    return QuestionResult(
        question_id=question.id,
        answer=response.answer,
        retrieved_sources=retrieved,
        retrieval_hit=hit,
        correct=is_correct(question, response),
        cited_expected_source=cited_expected_source(question, response),
        latency_seconds=round(latency, 3),
    )


def summarize(
    config: EvalConfig, questions: list[Question], results: list[QuestionResult]
) -> ConfigReport:
    answerable_ids = {q.id for q in questions if q.answerable}
    return ConfigReport(
        config=config,
        retrieval_hit_rate=rate(r.retrieval_hit for r in results) or 0.0,
        answer_accuracy=rate(r.correct for r in results) or 0.0,
        abstention_accuracy=rate(r.correct for r in results if r.question_id not in answerable_ids),
        citation_accuracy=rate(r.cited_expected_source for r in results),
        mean_latency_seconds=sum(r.latency_seconds for r in results) / len(results),
        results=results,
    )


def run_evaluation(
    documents: list[SourceDocument],
    questions: list[Question],
    configs: list[EvalConfig],
    embeddings: Embeddings,
    llm: BaseChatModel,
    *,
    chunk_overlap: int,
    min_score: float,
    embedding_dim: int,
) -> list[ConfigReport]:
    embeddings = QueryCachingEmbeddings(embeddings)
    reports: list[ConfigReport] = []
    for chunk_size, group in itertools.groupby(configs, key=lambda c: c.chunk_size):
        chunks = chunk_documents(documents, chunk_size, min(chunk_overlap, chunk_size // 4))
        retriever = InMemoryRetriever(chunks, embed_chunks(chunks, embeddings, embedding_dim))
        for config in group:
            print(f"Evaluating {config} ...", file=sys.stderr)
            service = AnswerService(
                embeddings,
                retriever,
                llm,
                top_k=config.top_k,
                min_score=min_score,
                prompt_version=config.prompt_version,
            )
            results = [evaluate_question(service, question) for question in questions]
            reports.append(summarize(config, questions, results))
    return reports


def build_configs(
    chunk_sizes: list[int], top_ks: list[int], prompts: list[str]
) -> list[EvalConfig]:
    return [
        EvalConfig(chunk_size, top_k, prompt)
        for chunk_size, top_k, prompt in itertools.product(sorted(chunk_sizes), top_ks, prompts)
    ]


# --- Reporting -----------------------------------------------------------------------


def percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def render_markdown(reports: list[ConfigReport], settings: Settings, question_count: int) -> str:
    header = [
        "# Evaluation results",
        "",
        f"Generated by `eval/run_eval.py` on {datetime.now(UTC):%Y-%m-%d %H:%M} UTC.",
        f"LLM: `{settings.llm_provider}:{settings.llm_model}` · "
        f"Embeddings: `{settings.embedding_provider}:{settings.embedding_model}` · "
        f"Min relevance score: {settings.min_relevance_score} · Questions: {question_count}",
        "",
        "| Chunk size | Top-k | Prompt | Retrieval hit@k | Answer accuracy "
        "| Correct abstentions | Citation accuracy | Mean latency (s) |",
        "|---:|---:|:---|---:|---:|---:|---:|---:|",
    ]
    rows = [
        f"| {r.config.chunk_size} | {r.config.top_k} | {r.config.prompt_version} "
        f"| {percent(r.retrieval_hit_rate)} | {percent(r.answer_accuracy)} "
        f"| {percent(r.abstention_accuracy)} | {percent(r.citation_accuracy)} "
        f"| {r.mean_latency_seconds:.2f} |"
        for r in reports
    ]
    return "\n".join([*header, *rows, ""])


def write_reports(reports: list[ConfigReport], markdown: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.md").write_text(markdown, encoding="utf-8")
    details = [asdict(report) for report in reports]
    (out_dir / "details.json").write_text(json.dumps(details, indent=2), encoding="utf-8")


def parse_args(settings: Settings) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chunk-sizes", type=int, nargs="+", default=[300, 800])
    parser.add_argument("--top-ks", type=int, nargs="+", default=[2, 4])
    parser.add_argument("--prompts", nargs="+", choices=PROMPT_VERSIONS, default=["v1", "v2"])
    parser.add_argument("--limit", type=int, help="Only use the first N questions")
    parser.add_argument("--out-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--docs-dir", type=Path, default=settings.docs_dir)
    return parser.parse_args()


def main() -> int:
    settings = get_settings()
    args = parse_args(settings)
    questions = load_questions()[: args.limit]
    try:
        reports = run_evaluation(
            load_documents(args.docs_dir),
            questions,
            build_configs(args.chunk_sizes, args.top_ks, args.prompts),
            build_embeddings(settings),
            build_chat_model(settings),
            chunk_overlap=settings.chunk_overlap,
            min_score=settings.min_relevance_score,
            embedding_dim=settings.embedding_dim,
        )
    except SupportAgentError as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        return 1
    markdown = render_markdown(reports, settings, len(questions))
    write_reports(reports, markdown, args.out_dir)
    print(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
