"""FastAPI application. Run with: uvicorn app.main:create_app --factory"""

from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.db import create_db_engine, create_session_factory
from app.exceptions import (
    DatabaseError,
    ModelUnavailableError,
    SupportAgentError,
    TicketNotFoundError,
    TicketServiceError,
)
from app.providers import build_chat_model, build_embeddings
from app.rag import AnswerService
from app.retrieval import PgVectorRetriever
from app.schemas import AskRequest, AskResponse, Ticket, TicketCreate, TicketUpdate
from app.tickets import McpTicketClient, TicketClient

_ERROR_STATUS: dict[type[SupportAgentError], int] = {
    ModelUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
    DatabaseError: status.HTTP_503_SERVICE_UNAVAILABLE,
    TicketServiceError: status.HTTP_502_BAD_GATEWAY,
    TicketNotFoundError: status.HTTP_404_NOT_FOUND,
}


class Answerer(Protocol):
    def ask(self, question: str) -> AskResponse: ...


@dataclass(frozen=True)
class Services:
    answerer: Answerer
    tickets: TicketClient


def build_services(settings: Settings) -> Services:
    session_factory = create_session_factory(create_db_engine(settings.database_url))
    answerer = AnswerService(
        build_embeddings(settings),
        PgVectorRetriever(session_factory),
        build_chat_model(settings),
        top_k=settings.top_k,
        min_score=settings.min_relevance_score,
        prompt_version=settings.prompt_version,
    )
    return Services(answerer=answerer, tickets=McpTicketClient(settings.mcp_server_url))


def get_services(request: Request) -> Services:
    return request.app.state.services


ServicesDep = Annotated[Services, Depends(get_services)]


async def handle_app_error(_: Request, exc: Exception) -> JSONResponse:
    code = _ERROR_STATUS.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    return JSONResponse(status_code=code, content={"detail": str(exc)})


def create_app(services: Services | None = None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Enterprise AI Support Agent", version="0.1.0")
    app.state.services = services or build_services(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type"],
    )
    app.add_exception_handler(SupportAgentError, handle_app_error)
    register_routes(app)
    return app


def register_routes(app: FastAPI) -> None:
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ask")
    def ask(body: AskRequest, services: ServicesDep) -> AskResponse:
        return services.answerer.ask(body.question)

    @app.post("/tickets", status_code=status.HTTP_201_CREATED)
    async def create_ticket(body: TicketCreate, services: ServicesDep) -> Ticket:
        return await services.tickets.create_ticket(body)

    @app.get("/tickets/{ticket_id}")
    async def get_ticket(ticket_id: int, services: ServicesDep) -> Ticket:
        return await services.tickets.get_ticket_status(ticket_id)

    @app.patch("/tickets/{ticket_id}")
    async def update_ticket(ticket_id: int, body: TicketUpdate, services: ServicesDep) -> Ticket:
        return await services.tickets.update_ticket(ticket_id, body)
