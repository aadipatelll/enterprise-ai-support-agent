import os
from unittest.mock import MagicMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.config import get_settings
from app.db import DocumentChunk, create_db_engine, create_session_factory, init_db
from app.exceptions import DatabaseError
from app.ingestion.chunking import Chunk
from app.ingestion.store import PgVectorChunkStore

CHUNK = Chunk(title="T", section="S", source="t.md", content="text")


def test_database_failure_is_wrapped() -> None:
    session_factory = MagicMock()
    session_factory.begin.side_effect = OperationalError("INSERT", {}, Exception("db down"))
    store = PgVectorChunkStore(session_factory)

    with pytest.raises(DatabaseError, match="Failed to store chunks"):
        store.replace_all([CHUNK], [[0.0] * get_settings().embedding_dim])


def test_mismatched_chunks_and_vectors_rejected() -> None:
    store = PgVectorChunkStore(MagicMock())

    with pytest.raises(ValueError):
        store.replace_all([CHUNK, CHUNK], [[0.0]])


@pytest.mark.integration
@pytest.mark.skipif("TEST_DATABASE_URL" not in os.environ, reason="TEST_DATABASE_URL not set")
def test_replace_all_is_idempotent_against_postgres() -> None:
    engine = create_db_engine(os.environ["TEST_DATABASE_URL"])
    init_db(engine)
    session_factory = create_session_factory(engine)
    store = PgVectorChunkStore(session_factory)
    vector = [0.1] * get_settings().embedding_dim

    store.replace_all([CHUNK, CHUNK], [vector, vector])
    store.replace_all([CHUNK], [vector])

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(DocumentChunk)) == 1
