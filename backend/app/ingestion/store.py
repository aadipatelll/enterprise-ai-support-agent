"""Persistence for embedded chunks."""

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.db import DocumentChunk
from app.exceptions import DatabaseError
from app.ingestion.chunking import Chunk


class ChunkStore(Protocol):
    def replace_all(self, chunks: Sequence[Chunk], vectors: Sequence[list[float]]) -> None: ...


class PgVectorChunkStore:
    """Replaces the whole index in one transaction, so re-ingestion is idempotent
    and a failed run never leaves a half-written index."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def replace_all(self, chunks: Sequence[Chunk], vectors: Sequence[list[float]]) -> None:
        rows = [
            DocumentChunk(
                title=chunk.title,
                section=chunk.section,
                source=chunk.source,
                content=chunk.content,
                embedding=vector,
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        try:
            with self._session_factory.begin() as session:
                session.execute(delete(DocumentChunk))
                session.add_all(rows)
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Failed to store chunks: {exc}") from exc
