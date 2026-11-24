"""Serve source documents so the UI can open a citation."""

import re
from pathlib import Path

from app.exceptions import DocumentNotFoundError
from app.ingestion.loader import SourceDocument, parse_document

# Only plain file names like "hr-pto-policy.md": blocks path traversal.
_SAFE_SOURCE = re.compile(r"[a-z0-9][a-z0-9-]*\.md")


def read_document(docs_dir: Path, source: str) -> SourceDocument:
    path = docs_dir / source
    if not _SAFE_SOURCE.fullmatch(source) or not path.is_file():
        raise DocumentNotFoundError(f"Document {source!r} not found")
    return parse_document(source, path.read_text(encoding="utf-8"))
