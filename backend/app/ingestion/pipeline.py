"""Ingestion pipeline: documents -> chunks -> vectors -> store."""

from dataclasses import dataclass

from langchain_core.embeddings import Embeddings

from app.exceptions import IngestionError, ModelUnavailableError
from app.ingestion.chunking import Chunk, chunk_documents
from app.ingestion.loader import SourceDocument
from app.ingestion.store import ChunkStore
from app.providers import MODEL_ERRORS


@dataclass(frozen=True)
class IngestionReport:
    documents: int
    chunks: int


def embed_chunks(
    chunks: list[Chunk], embeddings: Embeddings, expected_dim: int
) -> list[list[float]]:
    try:
        vectors = embeddings.embed_documents([chunk.embedding_text for chunk in chunks])
    except MODEL_ERRORS as exc:
        raise ModelUnavailableError(f"Embedding model is unavailable: {exc}") from exc

    if any(len(vector) != expected_dim for vector in vectors):
        raise IngestionError(
            f"Embedding size does not match EMBEDDING_DIM={expected_dim}; "
            "update .env to match the embedding model."
        )
    return vectors


def ingest(
    documents: list[SourceDocument],
    embeddings: Embeddings,
    store: ChunkStore,
    *,
    chunk_size: int,
    chunk_overlap: int,
    embedding_dim: int,
) -> IngestionReport:
    chunks = chunk_documents(documents, chunk_size, chunk_overlap)
    if not chunks:
        raise IngestionError("No chunks were produced; is the documents directory empty?")

    vectors = embed_chunks(chunks, embeddings, embedding_dim)
    store.replace_all(chunks, vectors)
    return IngestionReport(documents=len(documents), chunks=len(chunks))
