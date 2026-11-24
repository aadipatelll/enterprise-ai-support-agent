"""Ticket persistence. Converts database failures into TicketStoreError."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ticket_server.models import Base, Priority, Status, Ticket, TicketRecord, utc_now


class TicketNotFoundError(Exception):
    pass


class TicketStoreError(Exception):
    pass


def create_ticket_engine(database_url: str, **kwargs: object) -> Engine:
    engine = create_engine(database_url, pool_pre_ping=True, **kwargs)
    Base.metadata.create_all(engine)
    return engine


class TicketRepository:
    def __init__(self, engine: Engine) -> None:
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    @contextmanager
    def _transaction(self) -> Iterator[Session]:
        try:
            with self._session_factory.begin() as session:
                yield session
        except SQLAlchemyError as exc:
            raise TicketStoreError("Ticket database is unavailable") from exc

    def create(
        self, title: str, description: str, priority: Priority, requester: str | None
    ) -> Ticket:
        with self._transaction() as session:
            record = TicketRecord(
                title=title,
                description=description,
                priority=priority,
                status="open",
                requester=requester,
                notes=[],
            )
            session.add(record)
            session.flush()
            return Ticket.model_validate(record)

    def get(self, ticket_id: int) -> Ticket:
        with self._transaction() as session:
            return Ticket.model_validate(self._load(session, ticket_id))

    def update(
        self,
        ticket_id: int,
        status: Status | None = None,
        priority: Priority | None = None,
        note: str | None = None,
    ) -> Ticket:
        with self._transaction() as session:
            record = self._load(session, ticket_id)
            if status is not None:
                record.status = status
            if priority is not None:
                record.priority = priority
            if note is not None:
                record.notes = [*record.notes, f"[{utc_now():%Y-%m-%d %H:%M} UTC] {note}"]
            session.flush()
            return Ticket.model_validate(record)

    @staticmethod
    def _load(session: Session, ticket_id: int) -> TicketRecord:
        record = session.get(TicketRecord, ticket_id)
        if record is None:
            raise TicketNotFoundError(f"Ticket {ticket_id} does not exist")
        return record
