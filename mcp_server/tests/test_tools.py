"""Exercise each tool through a real in-process MCP client against SQLite."""

from typing import Any
from unittest.mock import MagicMock

import anyio
import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import StaticPool

from ticket_server.repository import TicketRepository, TicketStoreError, create_ticket_engine
from ticket_server.server import create_server


@pytest.fixture
def server() -> MCPServer:
    engine = create_ticket_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    return create_server(TicketRepository(engine))


def call(server: MCPServer, tool: str, arguments: dict[str, Any]) -> CallToolResult:
    async def run() -> CallToolResult:
        async with Client(server) as client:
            return await client.call_tool(tool, arguments)

    return anyio.run(run)


def error_text(result: CallToolResult) -> str:
    assert result.is_error
    return result.content[0].text


def create(server: MCPServer, **overrides: Any) -> dict[str, Any]:
    arguments = {"title": "VPN keeps dropping", "description": "Disconnects hourly"} | overrides
    result = call(server, "create_ticket", arguments)
    assert not result.is_error
    return result.structured_content


def test_server_lists_the_three_ticket_tools(server: MCPServer) -> None:
    async def names() -> set[str]:
        async with Client(server) as client:
            return {tool.name for tool in (await client.list_tools()).tools}

    assert anyio.run(names) == {"create_ticket", "update_ticket", "get_ticket_status"}


def test_create_ticket_returns_open_ticket(server: MCPServer) -> None:
    ticket = create(server, priority="high", requester="sam@corvane.example")

    assert ticket["id"] == 1
    assert ticket["status"] == "open"
    assert ticket["priority"] == "high"
    assert ticket["requester"] == "sam@corvane.example"


def test_create_ticket_defaults_to_medium_priority(server: MCPServer) -> None:
    assert create(server)["priority"] == "medium"


def test_create_ticket_rejects_short_title(server: MCPServer) -> None:
    result = call(server, "create_ticket", {"title": "Hi", "description": "x"})

    assert result.is_error


def test_get_ticket_status_returns_ticket(server: MCPServer) -> None:
    ticket_id = create(server)["id"]

    result = call(server, "get_ticket_status", {"ticket_id": ticket_id})

    assert result.structured_content["title"] == "VPN keeps dropping"


def test_get_ticket_status_unknown_id(server: MCPServer) -> None:
    result = call(server, "get_ticket_status", {"ticket_id": 999})

    assert "NOT_FOUND" in error_text(result)


def test_update_ticket_changes_status_and_appends_note(server: MCPServer) -> None:
    ticket_id = create(server)["id"]

    result = call(
        server,
        "update_ticket",
        {"ticket_id": ticket_id, "status": "in_progress", "note": "Assigned to Network team"},
    )

    ticket = result.structured_content
    assert ticket["status"] == "in_progress"
    assert ticket["notes"][0].endswith("Assigned to Network team")


def test_update_ticket_requires_a_change(server: MCPServer) -> None:
    ticket_id = create(server)["id"]

    result = call(server, "update_ticket", {"ticket_id": ticket_id})

    assert "INVALID" in error_text(result)


def test_update_ticket_rejects_unknown_status(server: MCPServer) -> None:
    ticket_id = create(server)["id"]

    result = call(server, "update_ticket", {"ticket_id": ticket_id, "status": "lost"})

    assert result.is_error


def test_update_ticket_unknown_id(server: MCPServer) -> None:
    result = call(server, "update_ticket", {"ticket_id": 42, "priority": "low"})

    assert "NOT_FOUND" in error_text(result)


def test_database_failure_is_reported_as_unavailable() -> None:
    repository = MagicMock(spec=TicketRepository)
    repository.get.side_effect = TicketStoreError("Ticket database is unavailable")

    result = call(create_server(repository), "get_ticket_status", {"ticket_id": 1})

    assert "UNAVAILABLE" in error_text(result)


def test_repository_wraps_sqlalchemy_errors() -> None:
    engine = MagicMock()
    engine.connect.side_effect = OperationalError("SELECT", {}, Exception("db down"))
    repository = TicketRepository(engine)

    with pytest.raises(TicketStoreError):
        repository.get(1)
