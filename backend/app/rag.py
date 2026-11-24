"""Retrieval-augmented answering with citations and a no-guess fallback."""

import re

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser

from app.exceptions import ModelUnavailableError
from app.prompts import NO_ANSWER_TOKEN, build_prompt, format_context
from app.providers import MODEL_ERRORS
from app.retrieval import RetrievedChunk, Retriever
from app.schemas import AskResponse, Citation, TicketDraft

NO_ANSWER_MESSAGE = (
    "I couldn't find this in the company documents, so I won't guess. "
    "Would you like me to open a support ticket so the right team can help?"
)
_CITATION_MARKER = re.compile(r"\[(\d+)\]")


class AnswerService:
    def __init__(
        self,
        embeddings: Embeddings,
        retriever: Retriever,
        llm: BaseChatModel,
        *,
        top_k: int,
        min_score: float,
        prompt_version: str,
    ) -> None:
        self._embeddings = embeddings
        self._retriever = retriever
        self._chain = build_prompt(prompt_version) | llm | StrOutputParser()
        self._top_k = top_k
        self._min_score = min_score

    def retrieve(self, question: str) -> list[RetrievedChunk]:
        try:
            query_vector = self._embeddings.embed_query(question)
        except MODEL_ERRORS as exc:
            raise ModelUnavailableError(f"Embedding model is unavailable: {exc}") from exc
        return self._retriever.search(query_vector, self._top_k)

    def ask(self, question: str) -> AskResponse:
        relevant = [chunk for chunk in self.retrieve(question) if chunk.score >= self._min_score]
        if not relevant:
            return no_answer(question)

        answer = self._generate(question, relevant)
        if NO_ANSWER_TOKEN in answer:
            return no_answer(question)
        return AskResponse(answer=answer, answered=True, citations=cite(answer, relevant))

    def _generate(self, question: str, chunks: list[RetrievedChunk]) -> str:
        try:
            answer = self._chain.invoke({"question": question, "context": format_context(chunks)})
        except MODEL_ERRORS as exc:
            raise ModelUnavailableError(f"Language model is unavailable: {exc}") from exc
        return answer.strip()


def cite(answer: str, chunks: list[RetrievedChunk]) -> list[Citation]:
    """Return the sources the answer cites; fall back to all context if it cites none."""
    cited = {int(number) for number in _CITATION_MARKER.findall(answer)}
    numbers = sorted(n for n in cited if 1 <= n <= len(chunks)) or range(1, len(chunks) + 1)
    return [to_citation(number, chunks[number - 1]) for number in numbers]


def to_citation(number: int, chunk: RetrievedChunk) -> Citation:
    return Citation(
        id=number,
        title=chunk.title,
        section=chunk.section,
        source=chunk.source,
        score=chunk.score,
    )


def no_answer(question: str) -> AskResponse:
    draft = TicketDraft(
        title=question if len(question) <= 80 else f"{question[:77]}...",
        description=f"The knowledge base could not answer this employee question:\n\n{question}",
    )
    return AskResponse(
        answer=NO_ANSWER_MESSAGE, answered=False, citations=[], suggested_ticket=draft
    )
