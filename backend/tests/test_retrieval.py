import os
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import OperationalError

from app.config import get_settings
from app.db import DocumentChunk, create_db_engine, create_session_factory, init_db
from app.exceptions import DatabaseError
from app.ingestion.chunking import Chunk
from app.ingestion.store import PgVectorChunkStore
from app.retrieval import PgVectorRetriever


def session_factory_returning(rows: list[tuple[DocumentChunk, float]]) -> MagicMock:
    session = MagicMock()
    session.execute.return_value.all.return_value = rows
    factory = MagicMock()
    factory.return_value.__enter__.return_value = session
    return factory


def test_search_converts_distance_to_similarity_score() -> None:
    row = DocumentChunk(title="T", section="S", source="t.md", content="text", embedding=[0.0])
    retriever = PgVectorRetriever(session_factory_returning([(row, 0.25)]))

    [result] = retriever.search([0.1, 0.2], top_k=3)

    assert result.score == 0.75
    assert (result.title, result.section, result.source) == ("T", "S", "t.md")


def test_search_empty_index_returns_empty_list() -> None:
    assert PgVectorRetriever(session_factory_returning([])).search([0.1], top_k=3) == []


def test_database_failure_is_wrapped() -> None:
    factory = MagicMock(side_effect=OperationalError("SELECT", {}, Exception("db down")))

    with pytest.raises(DatabaseError):
        PgVectorRetriever(factory).search([0.1], top_k=3)


@pytest.mark.integration
@pytest.mark.skipif("TEST_DATABASE_URL" not in os.environ, reason="TEST_DATABASE_URL not set")
def test_search_orders_by_similarity_against_postgres() -> None:
    dim = get_settings().embedding_dim
    engine = create_db_engine(os.environ["TEST_DATABASE_URL"])
    init_db(engine)
    session_factory = create_session_factory(engine)
    near, far = [1.0] + [0.0] * (dim - 1), [0.0, 1.0] + [0.0] * (dim - 2)
    chunks = [Chunk("Far", "S", "far.md", "far"), Chunk("Near", "S", "near.md", "near")]
    PgVectorChunkStore(session_factory).replace_all(chunks, [far, near])

    results = PgVectorRetriever(session_factory).search(near, top_k=2)

    assert [r.source for r in results] == ["near.md", "far.md"]
    assert results[0].score == pytest.approx(1.0)
