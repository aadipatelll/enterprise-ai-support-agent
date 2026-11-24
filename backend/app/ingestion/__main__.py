"""CLI: python -m app.ingestion [--chunk-size N] [--chunk-overlap N] [--docs-dir PATH]"""

import argparse
import sys
from pathlib import Path

from app.config import Settings, get_settings
from app.db import create_db_engine, create_session_factory, init_db
from app.exceptions import SupportAgentError
from app.ingestion.loader import load_documents
from app.ingestion.pipeline import IngestionReport, ingest
from app.ingestion.store import PgVectorChunkStore
from app.providers import build_embeddings


def parse_args(settings: Settings) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embed markdown documents into pgvector.")
    parser.add_argument("--docs-dir", type=Path, default=settings.docs_dir)
    parser.add_argument("--chunk-size", type=int, default=settings.chunk_size)
    parser.add_argument("--chunk-overlap", type=int, default=settings.chunk_overlap)
    return parser.parse_args()


def run(settings: Settings, args: argparse.Namespace) -> IngestionReport:
    engine = create_db_engine(settings.database_url)
    init_db(engine)
    return ingest(
        load_documents(args.docs_dir),
        build_embeddings(settings),
        PgVectorChunkStore(create_session_factory(engine)),
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        embedding_dim=settings.embedding_dim,
    )


def main() -> int:
    settings = get_settings()
    args = parse_args(settings)
    try:
        report = run(settings, args)
    except (SupportAgentError, FileNotFoundError, ValueError) as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1
    print(f"Ingested {report.chunks} chunks from {report.documents} documents.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
