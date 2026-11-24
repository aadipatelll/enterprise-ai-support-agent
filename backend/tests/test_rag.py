from unittest.mock import MagicMock

import httpx
import pytest
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.exceptions import ModelUnavailableError
from app.prompts import NO_ANSWER_TOKEN
from app.rag import NO_ANSWER_MESSAGE, AnswerService, cite
from app.retrieval import RetrievedChunk
from tests.conftest import PTO_CHUNK, VPN_CHUNK, FakeEmbeddings, StaticRetriever

QUESTION = "How many PTO days carry over?"


def make_service(
    results: list[RetrievedChunk],
    llm: BaseChatModel,
    embeddings: Embeddings | None = None,
    min_score: float = 0.5,
) -> AnswerService:
    return AnswerService(
        embeddings or FakeEmbeddings(),
        StaticRetriever(results),
        llm,
        top_k=4,
        min_score=min_score,
        prompt_version="v1",
    )


def test_answer_includes_cited_sources() -> None:
    llm = FakeListChatModel(responses=["Up to 5 days carry over [1]."])

    response = make_service([PTO_CHUNK, VPN_CHUNK], llm).ask(QUESTION)

    assert response.answered
    assert response.answer == "Up to 5 days carry over [1]."
    assert [c.source for c in response.citations] == ["hr-pto-policy.md"]
    assert response.citations[0].id == 1
    assert response.suggested_ticket is None


def test_low_relevance_skips_llm_and_suggests_ticket() -> None:
    llm = MagicMock(spec=BaseChatModel)

    response = make_service([VPN_CHUNK], llm, min_score=0.7).ask(QUESTION)

    assert not response.answered
    assert response.answer == NO_ANSWER_MESSAGE
    assert response.citations == []
    assert response.suggested_ticket is not None
    assert QUESTION in response.suggested_ticket.description
    llm.invoke.assert_not_called()


def test_empty_index_returns_no_answer() -> None:
    response = make_service([], FakeListChatModel(responses=["unused"])).ask(QUESTION)

    assert not response.answered


def test_model_saying_insufficient_context_returns_no_answer() -> None:
    llm = FakeListChatModel(responses=[NO_ANSWER_TOKEN])

    response = make_service([PTO_CHUNK], llm).ask("What is the CEO's favourite colour?")

    assert not response.answered
    assert response.suggested_ticket is not None


def test_retrieve_uses_configured_top_k() -> None:
    service = make_service([PTO_CHUNK, VPN_CHUNK], FakeListChatModel(responses=["x"]))

    assert service.retrieve(QUESTION) == [PTO_CHUNK, VPN_CHUNK]


def test_unreachable_embedding_model_raises() -> None:
    embeddings = MagicMock(spec=Embeddings)
    embeddings.embed_query.side_effect = httpx.ConnectError("refused")
    service = make_service([PTO_CHUNK], FakeListChatModel(responses=["x"]), embeddings)

    with pytest.raises(ModelUnavailableError, match="Embedding model"):
        service.ask(QUESTION)


def test_unreachable_llm_raises() -> None:
    llm = MagicMock(spec=BaseChatModel)
    llm.invoke.side_effect = ConnectionError("Ollama is not running")

    with pytest.raises(ModelUnavailableError, match="Language model"):
        make_service([PTO_CHUNK], llm).ask(QUESTION)


def test_cite_falls_back_to_all_sources_when_answer_has_no_markers() -> None:
    citations = cite("Five days carry over.", [PTO_CHUNK, VPN_CHUNK])

    assert [c.id for c in citations] == [1, 2]


def test_cite_ignores_out_of_range_and_duplicate_markers() -> None:
    citations = cite("See [2], [2] and [9].", [PTO_CHUNK, VPN_CHUNK])

    assert [(c.id, c.source) for c in citations] == [(2, "it-vpn-access.md")]
