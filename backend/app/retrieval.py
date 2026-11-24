"""Vector similarity search over stored chunks."""

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.db import DocumentChunk
from app.exceptions import DatabaseError


@dataclass(frozen=True)
class RetrievedChunk:
    title: str
    section: str
    source: str
    content: str
    score: float  # cosine similarity, higher is more relevant


class Retriever(Protocol):
    def search(self, query_vector: list[float], top_k: int) -> list[RetrievedChunk]: ...


class PgVectorRetriever:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def search(self, query_vector: list[float], top_k: int) -> list[RetrievedChunk]:
        distance = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
        statement = select(DocumentChunk, distance).order_by(distance).limit(top_k)
        try:
            with self._session_factory() as session:
                rows = session.execute(statement).all()
        except SQLAlchemyError as exc:
            raise DatabaseError(
                "Could not search documents. Is the database running and ingestion done?"
            ) from exc
        return [to_retrieved_chunk(chunk, distance) for chunk, distance in rows]


def to_retrieved_chunk(chunk: DocumentChunk, distance: float) -> RetrievedChunk:
    return RetrievedChunk(
        title=chunk.title,
        section=chunk.section,
        source=chunk.source,
        content=chunk.content,
        score=round(1 - float(distance), 4),
    )
