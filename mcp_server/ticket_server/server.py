"""MCP tool definitions. Expected failures become ToolErrors with a stable prefix
(NOT_FOUND / UNAVAILABLE / INVALID) so clients can map them to the right response."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from ticket_server.models import Priority, Status, Ticket
from ticket_server.repository import TicketNotFoundError, TicketRepository, TicketStoreError

Title = Annotated[str, Field(min_length=3, max_length=200)]
Description = Annotated[str, Field(min_length=1, max_length=5000)]
TicketId = Annotated[int, Field(gt=0)]


@contextmanager
def tool_errors() -> Iterator[None]:
    try:
        yield
    except TicketNotFoundError as exc:
        raise ToolError(f"NOT_FOUND: {exc}") from exc
    except TicketStoreError as exc:
        raise ToolError(f"UNAVAILABLE: {exc}") from exc


def create_server(repository: TicketRepository) -> MCPServer:
    server = MCPServer(
        "support-tickets",
        instructions="Create, update, and look up IT/HR support tickets.",
    )

    @server.tool()
    def create_ticket(
        title: Title,
        description: Description,
        priority: Priority = "medium",
        requester: str | None = None,
    ) -> Ticket:
        """Open a new support ticket and return it, including its ID."""
        with tool_errors():
            return repository.create(title, description, priority, requester)

    @server.tool()
    def update_ticket(
        ticket_id: TicketId,
        status: Status | None = None,
        priority: Priority | None = None,
        note: str | None = None,
    ) -> Ticket:
        """Change a ticket's status or priority, or append a note."""
        if status is None and priority is None and not note:
            raise ToolError("INVALID: provide at least one of status, priority, or note")
        with tool_errors():
            return repository.update(ticket_id, status=status, priority=priority, note=note)

    @server.tool()
    def get_ticket_status(ticket_id: TicketId) -> Ticket:
        """Look up a ticket by ID."""
        with tool_errors():
            return repository.get(ticket_id)

    return server
