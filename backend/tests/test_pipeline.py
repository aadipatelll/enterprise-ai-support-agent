from unittest.mock import MagicMock

import httpx
import pytest
from langchain_core.embeddings import Embeddings

from app.exceptions import IngestionError, ModelUnavailableError
from app.ingestion.loader import SourceDocument
from app.ingestion.pipeline import ingest
from tests.conftest import EMBEDDING_DIM, InMemoryChunkStore


def run_ingest(
    documents: list[SourceDocument], embeddings: Embeddings, store: InMemoryChunkStore
) -> object:
    return ingest(
        documents,
        embeddings,
        store,
        chunk_size=500,
        chunk_overlap=50,
        embedding_dim=EMBEDDING_DIM,
    )


def test_ingest_stores_one_vector_per_chunk(
    sample_document: SourceDocument, fake_embeddings: Embeddings, store: InMemoryChunkStore
) -> None:
    report = run_ingest([sample_document], fake_embeddings, store)

    assert report.documents == 1
    assert report.chunks == len(store.chunks) == len(store.vectors) == 3
    assert all(len(vector) == EMBEDDING_DIM for vector in store.vectors)


def test_ingest_with_no_documents_raises(
    fake_embeddings: Embeddings, store: InMemoryChunkStore
) -> None:
    with pytest.raises(IngestionError, match="No chunks"):
        run_ingest([], fake_embeddings, store)


def test_unreachable_model_raises_model_unavailable(
    sample_document: SourceDocument, store: InMemoryChunkStore
) -> None:
    embeddings = MagicMock(spec=Embeddings)
    embeddings.embed_documents.side_effect = httpx.ConnectError("connection refused")

    with pytest.raises(ModelUnavailableError):
        run_ingest([sample_document], embeddings, store)
    assert store.chunks == []


def test_dimension_mismatch_raises(
    sample_document: SourceDocument, store: InMemoryChunkStore
) -> None:
    embeddings = MagicMock(spec=Embeddings)
    embeddings.embed_documents.return_value = [[0.1, 0.2]] * 3

    with pytest.raises(IngestionError, match="EMBEDDING_DIM"):
        run_ingest([sample_document], embeddings, store)
