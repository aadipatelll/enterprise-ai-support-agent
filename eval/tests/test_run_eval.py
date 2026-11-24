import json
import zlib
from pathlib import Path

import pytest
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.config import REPO_ROOT, Settings
from app.ingestion.chunking import Chunk
from app.ingestion.loader import SourceDocument, load_documents
from app.schemas import AskResponse, Citation
from run_eval import (
    EvalConfig,
    InMemoryRetriever,
    Question,
    build_configs,
    cited_expected_source,
    fact_present,
    is_correct,
    load_questions,
    render_markdown,
    run_evaluation,
    write_reports,
)

DOCS_DIR = REPO_ROOT / "data" / "docs"
DIM = 16

PTO_QUESTION = Question(
    id="q1",
    question="How many PTO days carry over?",
    expected_answer="Up to 5 days, used by March 31.",
    expected_sources=("hr-pto-policy.md",),
    key_facts=("5|five", "march 31"),
    answerable=True,
)
UNANSWERABLE = Question("q2", "Stock ticker?", "n/a", (), (), answerable=False)


class HashEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        vector = [0.0] * DIM
        for word in text.lower().split():
            vector[zlib.crc32(word.encode()) % DIM] += 1.0
        return vector


def response(answer: str, answered: bool = True, sources: tuple[str, ...] = ()) -> AskResponse:
    citations = [
        Citation(id=i, title="T", section="S", source=source, score=0.9)
        for i, source in enumerate(sources, start=1)
    ]
    return AskResponse(answer=answer, answered=answered, citations=citations)


# --- Dataset ---------------------------------------------------------------------------


def test_dataset_has_30_unique_questions_with_both_kinds() -> None:
    questions = load_questions()

    assert len(questions) == 30
    assert len({q.id for q in questions}) == 30
    assert any(not q.answerable for q in questions)


def test_answerable_questions_match_the_corpus() -> None:
    """Every key fact must actually appear in one of its expected source documents."""
    corpus = {doc.source: doc.text for doc in load_documents(DOCS_DIR)}
    for question in load_questions():
        if not question.answerable:
            assert not question.expected_sources and not question.key_facts, question.id
            continue
        assert question.expected_sources and question.key_facts, question.id
        texts = [corpus[source] for source in question.expected_sources]
        for fact in question.key_facts:
            assert any(fact_present(fact, text) for text in texts), (question.id, fact)


# --- Scoring ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fact", "answer", "expected"),
    [
        ("$5000|5000", "The limit is $5,000 per month.", True),
        ("three years|3 years", "Every 3 years.", True),
        ("march 31", "Use them by March 31 [1].", True),
        ("16 weeks", "Eight weeks.", False),
    ],
)
def test_fact_present(fact: str, answer: str, expected: bool) -> None:
    assert fact_present(fact, answer) is expected


def test_correct_answer_needs_every_key_fact() -> None:
    assert is_correct(PTO_QUESTION, response("5 days, by March 31 [1]."))
    assert not is_correct(PTO_QUESTION, response("5 days [1]."))
    assert not is_correct(PTO_QUESTION, response("No answer", answered=False))


def test_unanswerable_question_is_correct_only_when_declined() -> None:
    assert is_correct(UNANSWERABLE, response("No answer", answered=False))
    assert not is_correct(UNANSWERABLE, response("CRVN"))


def test_citation_scoring() -> None:
    assert cited_expected_source(PTO_QUESTION, response("x", sources=("hr-pto-policy.md",)))
    assert not cited_expected_source(PTO_QUESTION, response("x", sources=("it-vpn-access.md",)))
    assert cited_expected_source(PTO_QUESTION, response("x", answered=False)) is None


# --- Retrieval and the full run -------------------------------------------------------------


def test_in_memory_retriever_ranks_by_cosine_similarity() -> None:
    chunks = [Chunk("A", "S", "a.md", "a"), Chunk("B", "S", "b.md", "b")]
    retriever = InMemoryRetriever(chunks, [[1.0, 0.0], [0.6, 0.8]])

    results = retriever.search([0.0, 1.0], top_k=2)

    assert [r.source for r in results] == ["b.md", "a.md"]
    assert results[0].score == pytest.approx(0.8)


def test_build_configs_is_full_grid_grouped_by_chunk_size() -> None:
    configs = build_configs([800, 300], [2, 4], ["v1", "v2"])

    assert len(configs) == 8
    assert configs[0] == EvalConfig(300, 2, "v1")
    assert [c.chunk_size for c in configs] == [300] * 4 + [800] * 4


def test_run_evaluation_end_to_end(tmp_path: Path) -> None:
    documents = [
        SourceDocument(
            "hr-pto-policy.md",
            "Paid Time Off Policy",
            "# Paid Time Off Policy\n\n## Carryover\n\n"
            "Up to 5 unused PTO days carry over and must be used by March 31.\n",
        )
    ]
    llm = FakeListChatModel(responses=["5 days carry over, used by March 31 [1].", "CRVN"])
    configs = [EvalConfig(200, 2, "v1")]

    [report] = run_evaluation(
        documents,
        [PTO_QUESTION, UNANSWERABLE],
        configs,
        HashEmbeddings(),
        llm,
        chunk_overlap=20,
        min_score=0.0,
        embedding_dim=DIM,
    )

    assert report.retrieval_hit_rate == 1.0
    assert report.citation_accuracy == 1.0
    assert report.abstention_accuracy == 0.0  # the fake LLM guessed "CRVN"
    assert report.answer_accuracy == 0.5

    settings = Settings(_env_file=None)
    markdown = render_markdown([report], settings, question_count=2)
    write_reports([report], markdown, tmp_path)

    assert "| 200 | 2 | v1 | 100% | 50% | 0% | 100% |" in markdown
    details = json.loads((tmp_path / "details.json").read_text(encoding="utf-8"))
    assert details[0]["results"][0]["question_id"] == "q1"
