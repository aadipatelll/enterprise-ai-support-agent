"""Section-aware chunking: split on markdown headings first, then by size."""

from dataclasses import dataclass

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.ingestion.loader import SourceDocument

DEFAULT_SECTION = "Overview"
_HEADERS = [("#", "title"), ("##", "section")]


@dataclass(frozen=True)
class Chunk:
    title: str
    section: str
    source: str
    content: str

    @property
    def embedding_text(self) -> str:
        """Prefix the heading path so each vector carries its document context."""
        return f"{self.title} > {self.section}\n{self.content}"


def chunk_document(document: SourceDocument, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    sections = MarkdownHeaderTextSplitter(headers_to_split_on=_HEADERS).split_text(document.text)
    size_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return [
        Chunk(
            title=document.title,
            section=section.metadata.get("section", DEFAULT_SECTION),
            source=document.source,
            content=piece,
        )
        for section in sections
        for piece in size_splitter.split_text(section.page_content)
        if piece.strip()
    ]


def chunk_documents(
    documents: list[SourceDocument], chunk_size: int, chunk_overlap: int
) -> list[Chunk]:
    return [
        chunk
        for document in documents
        for chunk in chunk_document(document, chunk_size, chunk_overlap)
    ]
