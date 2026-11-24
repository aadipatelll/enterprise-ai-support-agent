"""Read markdown files from disk into SourceDocument objects."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceDocument:
    source: str
    title: str
    text: str


def parse_document(source: str, text: str) -> SourceDocument:
    """Use the first level-1 heading as the title, falling back to the file name."""
    title = next(
        (line[2:].strip() for line in text.splitlines() if line.startswith("# ")),
        Path(source).stem.replace("-", " ").title(),
    )
    return SourceDocument(source=source, title=title, text=text)


def load_documents(docs_dir: Path) -> list[SourceDocument]:
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"Documents directory not found: {docs_dir}")
    return [
        parse_document(path.name, path.read_text(encoding="utf-8"))
        for path in sorted(docs_dir.glob("*.md"))
    ]
