from pathlib import Path

import pytest

from app.config import REPO_ROOT
from app.ingestion.loader import load_documents, parse_document

DOCS_DIR = REPO_ROOT / "data" / "docs"


def test_title_comes_from_first_h1() -> None:
    document = parse_document("a.md", "intro\n# Expense Policy\n## Limits\n")

    assert document.title == "Expense Policy"


def test_title_falls_back_to_file_name() -> None:
    assert parse_document("travel-policy.md", "no heading").title == "Travel Policy"


def test_load_documents_reads_markdown_sorted(tmp_path: Path) -> None:
    (tmp_path / "b.md").write_text("# B", encoding="utf-8")
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")

    documents = load_documents(tmp_path)

    assert [document.source for document in documents] == ["a.md", "b.md"]


def test_load_documents_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_documents(tmp_path / "missing")


def test_sample_corpus_meets_spec() -> None:
    documents = load_documents(DOCS_DIR)

    assert len(documents) == 30
    for document in documents:
        sections = document.text.count("\n## ")
        assert 150 <= len(document.text.split()) <= 250, document.source
        assert 2 <= sections <= 4, document.source
