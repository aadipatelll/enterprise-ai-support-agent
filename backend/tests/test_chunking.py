import pytest

from app.ingestion.chunking import DEFAULT_SECTION, chunk_document, chunk_documents
from app.ingestion.loader import SourceDocument


def test_splits_on_section_headings(sample_document: SourceDocument) -> None:
    chunks = chunk_document(sample_document, chunk_size=500, chunk_overlap=50)

    assert [chunk.section for chunk in chunks] == [
        DEFAULT_SECTION,
        "Installing the Client",
        "Limits",
    ]
    assert chunks[2].content == "Sessions disconnect after 12 hours."


def test_chunks_carry_document_metadata(sample_document: SourceDocument) -> None:
    chunks = chunk_document(sample_document, chunk_size=500, chunk_overlap=50)

    assert all(chunk.title == "VPN Access" for chunk in chunks)
    assert all(chunk.source == "it-vpn-access.md" for chunk in chunks)


def test_embedding_text_includes_heading_path(sample_document: SourceDocument) -> None:
    chunk = chunk_document(sample_document, chunk_size=500, chunk_overlap=50)[-1]

    assert chunk.embedding_text.startswith("VPN Access > Limits\n")


def test_long_section_is_split_by_size_with_overlap() -> None:
    body = " ".join(f"word{i}" for i in range(200))
    document = SourceDocument("long.md", "Long", f"# Long\n\n## Body\n\n{body}\n")

    chunks = chunk_document(document, chunk_size=100, chunk_overlap=30)

    assert len(chunks) > 1
    assert all(len(chunk.content) <= 100 for chunk in chunks)
    assert all(chunk.section == "Body" for chunk in chunks)
    last_word_of_first = chunks[0].content.split()[-1]
    assert last_word_of_first in chunks[1].content


def test_empty_sections_are_skipped() -> None:
    document = SourceDocument(
        "empty.md", "Empty", "# Empty\n\n## Nothing\n\n## Something\n\nText.\n"
    )

    chunks = chunk_document(document, chunk_size=200, chunk_overlap=0)

    assert [chunk.section for chunk in chunks] == ["Something"]


def test_overlap_must_be_smaller_than_chunk_size(sample_document: SourceDocument) -> None:
    with pytest.raises(ValueError, match="chunk_overlap"):
        chunk_document(sample_document, chunk_size=100, chunk_overlap=100)


def test_chunk_documents_flattens_all_documents(sample_document: SourceDocument) -> None:
    chunks = chunk_documents([sample_document, sample_document], chunk_size=500, chunk_overlap=0)

    assert len(chunks) == 6
