"""McpTicketClient against an in-process stub MCP server (real protocol, no network)."""

from typing import Any

import anyio
import pytest
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from app.exceptions import TicketNotFoundError, TicketServiceError
from app.schemas import Ticket, TicketCreate, TicketUpdate
from app.tickets import McpTicketClient


def ticket_payload(ticket_id: int, **overrides: Any) -> dict[str, Any]:
    return {
        "id": ticket_id,
        "title": "VPN keeps dropping",
        "description": "Disconnects hourly",
        "priority": "medium",
        "status": "open",
        "requester": None,
        "notes": [],
        "created_at": "2026-11-24T10:00:00Z",
        "updated_at": "2026-11-24T10:00:00Z",
    } | overrides


@pytest.fixture
def stub_server() -> MCPServer:
    server = MCPServer("stub-tickets")

    @server.tool()
    def create_ticket(title: str, description: str, priority: str = "medium") -> dict[str, Any]:
        return ticket_payload(7, title=title, description=description, priority=priority)

    @server.tool()
    def update_ticket(ticket_id: int, status: str | None = None) -> dict[str, Any]:
        return ticket_payload(ticket_id, status=status or "open")

    @server.tool()
    def get_ticket_status(ticket_id: int) -> dict[str, Any]:
        if ticket_id == 404:
            raise ToolError("NOT_FOUND: Ticket 404 does not exist")
        if ticket_id == 500:
            raise ToolError("UNAVAILABLE: Ticket database is unavailable")
        return ticket_payload(ticket_id)

    return server


def test_create_ticket(stub_server: MCPServer) -> None:
    client = McpTicketClient(stub_server)
    data = TicketCreate(title="Laptop broken", description="Screen cracked", priority="high")

    ticket: Ticket = anyio.run(client.create_ticket, data)

    assert (ticket.id, ticket.title, ticket.priority) == (7, "Laptop broken", "high")


def test_update_ticket(stub_server: MCPServer) -> None:
    client = McpTicketClient(stub_server)

    ticket = anyio.run(client.update_ticket, 3, TicketUpdate(status="resolved"))

    assert (ticket.id, ticket.status) == (3, "resolved")


def test_get_ticket_status(stub_server: MCPServer) -> None:
    assert anyio.run(McpTicketClient(stub_server).get_ticket_status, 12).id == 12


def test_not_found_tool_error_maps_to_ticket_not_found(stub_server: MCPServer) -> None:
    with pytest.raises(TicketNotFoundError):
        anyio.run(McpTicketClient(stub_server).get_ticket_status, 404)


def test_other_tool_errors_map_to_service_error(stub_server: MCPServer) -> None:
    with pytest.raises(TicketServiceError, match="UNAVAILABLE"):
        anyio.run(McpTicketClient(stub_server).get_ticket_status, 500)


def test_unreachable_server_raises_service_error() -> None:
    client = McpTicketClient("http://127.0.0.1:9/mcp")

    with pytest.raises(TicketServiceError, match="unavailable"):
        anyio.run(client.get_ticket_status, 1)
