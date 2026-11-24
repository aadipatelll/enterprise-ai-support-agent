from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.exceptions import DatabaseError, ModelUnavailableError, TicketNotFoundError
from app.main import Services, create_app
from app.rag import AnswerService
from app.schemas import AskResponse, Ticket, TicketCreate, TicketUpdate
from tests.conftest import PTO_CHUNK, FakeEmbeddings, StaticRetriever

NOW = datetime(2026, 11, 24, tzinfo=UTC)


class InMemoryTicketClient:
    def __init__(self) -> None:
        self.tickets: dict[int, Ticket] = {}

    async def create_ticket(self, data: TicketCreate) -> Ticket:
        ticket = Ticket(
            id=len(self.tickets) + 1,
            status="open",
            notes=[],
            created_at=NOW,
            updated_at=NOW,
            **data.model_dump(),
        )
        self.tickets[ticket.id] = ticket
        return ticket

    async def update_ticket(self, ticket_id: int, data: TicketUpdate) -> Ticket:
        ticket = await self.get_ticket_status(ticket_id)
        changes = data.model_dump(exclude_none=True, exclude={"note"})
        self.tickets[ticket_id] = ticket.model_copy(update=changes)
        return self.tickets[ticket_id]

    async def get_ticket_status(self, ticket_id: int) -> Ticket:
        if ticket_id not in self.tickets:
            raise TicketNotFoundError(f"NOT_FOUND: Ticket {ticket_id} does not exist")
        return self.tickets[ticket_id]


class FailingAnswerer:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def ask(self, question: str) -> AskResponse:
        raise self.error


def make_client(answer: str = "Up to 5 days [1].", answerer: object | None = None) -> TestClient:
    service = answerer or AnswerService(
        FakeEmbeddings(),
        StaticRetriever([PTO_CHUNK]),
        FakeListChatModel(responses=[answer]),
        top_k=4,
        min_score=0.5,
        prompt_version="v1",
    )
    return TestClient(create_app(Services(answerer=service, tickets=InMemoryTicketClient())))


def test_health() -> None:
    assert make_client().get("/health").json() == {"status": "ok"}


def test_ask_returns_answer_with_citations() -> None:
    response = make_client().post("/ask", json={"question": "How many PTO days carry over?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answered"] is True
    assert body["citations"][0]["source"] == "hr-pto-policy.md"
    assert body["citations"][0]["section"] == "Carryover"


def test_ask_without_answer_suggests_ticket() -> None:
    response = make_client(answer="INSUFFICIENT_CONTEXT").post(
        "/ask", json={"question": "Who won the office chili contest?"}
    )

    body = response.json()
    assert body["answered"] is False
    assert body["suggested_ticket"]["title"] == "Who won the office chili contest?"


@pytest.mark.parametrize("question", ["", "  ", "x" * 1001])
def test_ask_validates_question(question: str) -> None:
    assert make_client().post("/ask", json={"question": question}).status_code == 422


@pytest.mark.parametrize("error", [ModelUnavailableError("Ollama down"), DatabaseError("db down")])
def test_ask_dependency_failures_return_503(error: Exception) -> None:
    client = make_client(answerer=FailingAnswerer(error))

    response = client.post("/ask", json={"question": "Any question?"})

    assert response.status_code == 503
    assert response.json()["detail"] == str(error)


def test_ticket_lifecycle() -> None:
    client = make_client()

    created = client.post(
        "/tickets", json={"title": "Printer jam", "description": "BOS-3 is jammed"}
    )
    assert created.status_code == 201
    ticket_id = created.json()["id"]

    updated = client.patch(f"/tickets/{ticket_id}", json={"status": "resolved"})
    assert updated.json()["status"] == "resolved"

    fetched = client.get(f"/tickets/{ticket_id}")
    assert fetched.json()["status"] == "resolved"


def test_unknown_ticket_returns_404() -> None:
    assert make_client().get("/tickets/99").status_code == 404


def test_create_ticket_validates_priority() -> None:
    response = make_client().post(
        "/tickets", json={"title": "Printer jam", "description": "x", "priority": "asap"}
    )

    assert response.status_code == 422
