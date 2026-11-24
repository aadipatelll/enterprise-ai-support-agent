"""Versioned answer prompts. The evaluation script compares versions side by side."""

from langchain_core.prompts import ChatPromptTemplate

from app.retrieval import RetrievedChunk

NO_ANSWER_TOKEN = "INSUFFICIENT_CONTEXT"

_SYSTEM_PROMPTS = {
    "v1": (
        "You are an internal IT and HR support assistant for Corvane Labs. "
        "Answer the employee's question using only the numbered sources below. "
        "Cite sources inline with their number, like [1]. "
        f"If the sources do not contain the answer, reply with exactly {NO_ANSWER_TOKEN}."
    ),
    "v2": (
        "You are a careful support assistant for Corvane Labs employees.\n"
        "Rules:\n"
        "1. Use only facts stated in the numbered sources. Never use outside knowledge.\n"
        "2. Answer in at most three sentences, quoting exact numbers, limits, and deadlines.\n"
        "3. After every sentence, cite the supporting source number in brackets, like [2].\n"
        f"4. If no source answers the question, reply with exactly {NO_ANSWER_TOKEN} "
        "and nothing else."
    ),
}

_HUMAN_TEMPLATE = "Sources:\n{context}\n\nQuestion: {question}"

PROMPT_VERSIONS = tuple(_SYSTEM_PROMPTS)


def build_prompt(version: str) -> ChatPromptTemplate:
    if version not in _SYSTEM_PROMPTS:
        raise ValueError(f"Unknown prompt version {version!r}; choose from {PROMPT_VERSIONS}")
    return ChatPromptTemplate.from_messages(
        [("system", _SYSTEM_PROMPTS[version]), ("human", _HUMAN_TEMPLATE)]
    )


def format_context(chunks: list[RetrievedChunk]) -> str:
    return "\n\n".join(
        f"[{number}] {chunk.title} > {chunk.section} ({chunk.source})\n{chunk.content}"
        for number, chunk in enumerate(chunks, start=1)
    )
