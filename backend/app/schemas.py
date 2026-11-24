"""Request and response models for the REST API."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

Priority = Literal["low", "medium", "high"]
Status = Literal["open", "in_progress", "resolved", "closed"]


class AskRequest(BaseModel):
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=3, max_length=1000)
    ]


class Citation(BaseModel):
    id: int = Field(description="Matches the [n] marker in the answer text")
    title: str
    section: str
    source: str
    score: float


class TicketDraft(BaseModel):
    title: str
    description: str


class AskResponse(BaseModel):
    answer: str
    answered: bool
    citations: list[Citation]
    suggested_ticket: TicketDraft | None = None


class Document(BaseModel):
    source: str
    title: str
    text: str


class TicketCreate(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]
    description: Annotated[str, StringConstraints(min_length=1, max_length=5000)]
    priority: Priority = "medium"
    requester: str | None = None


class TicketUpdate(BaseModel):
    status: Status | None = None
    priority: Priority | None = None
    note: Annotated[str, StringConstraints(max_length=2000)] | None = None


class Ticket(BaseModel):
    id: int
    title: str
    description: str
    priority: Priority
    status: Status
    requester: str | None
    notes: list[str]
    created_at: datetime
    updated_at: datetime
