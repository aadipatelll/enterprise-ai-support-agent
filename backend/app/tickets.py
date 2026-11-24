"""MCP client for the ticket server. The API never touches the tickets table directly;
every ticket operation goes through the MCP tools."""

from typing import Any, Protocol

import httpx2
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.shared.exceptions import MCPError
from mcp_types import CallToolResult, TextContent

from app.exceptions import TicketNotFoundError, TicketServiceError
from app.schemas import Ticket, TicketCreate, TicketUpdate

# The ticket server prefixes "not found" tool errors with this marker.
NOT_FOUND_MARKER = "NOT_FOUND"
_CONNECTION_ERRORS = (OSError, httpx2.HTTPError, MCPError)


class TicketClient(Protocol):
    async def create_ticket(self, data: TicketCreate) -> Ticket: ...

    async def update_ticket(self, ticket_id: int, data: TicketUpdate) -> Ticket: ...

    async def get_ticket_status(self, ticket_id: int) -> Ticket: ...


class McpTicketClient:
    def __init__(self, server: str | MCPServer) -> None:
        """`server` is the Streamable HTTP URL, or an in-process MCPServer in tests."""
        self._server = server

    async def create_ticket(self, data: TicketCreate) -> Ticket:
        return await self._call("create_ticket", data.model_dump(exclude_none=True))

    async def update_ticket(self, ticket_id: int, data: TicketUpdate) -> Ticket:
        arguments = {"ticket_id": ticket_id, **data.model_dump(exclude_none=True)}
        return await self._call("update_ticket", arguments)

    async def get_ticket_status(self, ticket_id: int) -> Ticket:
        return await self._call("get_ticket_status", {"ticket_id": ticket_id})

    async def _call(self, tool: str, arguments: dict[str, Any]) -> Ticket:
        try:
            # "legacy" = the classic initialize handshake. MCP 2.3's newer protocol
            # negotiation drops the connection over Streamable HTTP.
            async with Client(self._server, mode="legacy") as client:
                result = await client.call_tool(tool, arguments)
        except* _CONNECTION_ERRORS as group:
            raise TicketServiceError(
                f"Ticket service is unavailable: {group.exceptions[0]}"
            ) from None
        return parse_result(result)


def parse_result(result: CallToolResult) -> Ticket:
    if result.is_error:
        message = " ".join(item.text for item in result.content if isinstance(item, TextContent))
        if NOT_FOUND_MARKER in message:
            raise TicketNotFoundError(message)
        raise TicketServiceError(message or "Ticket service returned an error")
    return Ticket.model_validate(result.structured_content)
