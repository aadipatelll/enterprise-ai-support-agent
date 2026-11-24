import zlib
from collections.abc import Sequence

import pytest
from langchain_core.embeddings import Embeddings

from app.ingestion.chunking import Chunk
from app.ingestion.loader import SourceDocument
from app.retrieval import RetrievedChunk

EMBEDDING_DIM = 8

PTO_CHUNK = RetrievedChunk(
    title="Paid Time Off Policy",
    section="Carryover",
    source="hr-pto-policy.md",
    content="Up to 5 unused PTO days carry over into the next calendar year.",
    score=0.82,
)
VPN_CHUNK = RetrievedChunk(
    title="VPN Access",
    section="Limits",
    source="it-vpn-access.md",
    content="VPN sessions disconnect after 12 hours.",
    score=0.61,
)


class StaticRetriever:
    """Returns fixed results and records the requested top_k."""

    def __init__(self, results: list[RetrievedChunk]) -> None:
        self.results = results
        self.requested_top_k: int | None = None

    def search(self, query_vector: list[float], top_k: int) -> list[RetrievedChunk]:
        self.requested_top_k = top_k
        return self.results[:top_k]


class FakeEmbeddings(Embeddings):
    """Deterministic bag-of-words hashing embeddings: no model server needed,
    and texts sharing words get similar vectors."""

    def __init__(self, size: int = EMBEDDING_DIM) -> None:
        self.size = size

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        vector = [0.0] * self.size
        for word in text.lower().split():
            vector[zlib.crc32(word.encode()) % self.size] += 1.0
        return vector


class InMemoryChunkStore:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self.vectors: list[list[float]] = []

    def replace_all(self, chunks: Sequence[Chunk], vectors: Sequence[list[float]]) -> None:
        self.chunks = list(chunks)
        self.vectors = list(vectors)


@pytest.fixture
def fake_embeddings() -> FakeEmbeddings:
    return FakeEmbeddings()


@pytest.fixture
def store() -> InMemoryChunkStore:
    return InMemoryChunkStore()


@pytest.fixture
def sample_document() -> SourceDocument:
    text = (
        "# VPN Access\n\n"
        "Owner: IT\n\n"
        "## Installing the Client\n\n"
        "Install GlobalProtect from Self Service.\n\n"
        "## Limits\n\n"
        "Sessions disconnect after 12 hours.\n"
    )
    return SourceDocument(source="it-vpn-access.md", title="VPN Access", text=text)
