"""Run the ticket MCP server over Streamable HTTP: python -m ticket_server"""

import os

from mcp.server.transport_security import TransportSecuritySettings

from ticket_server.repository import TicketRepository, create_ticket_engine
from ticket_server.server import create_server

DEFAULT_DATABASE_URL = "postgresql+psycopg://support:change-me@localhost:5432/support_agent"
DEFAULT_ALLOWED_HOSTS = "localhost:*,127.0.0.1:*,mcp_server:*"


def main() -> None:
    engine = create_ticket_engine(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))
    server = create_server(TicketRepository(engine))
    allowed_hosts = os.environ.get("MCP_ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS).split(",")
    server.run(
        "streamable-http",
        host=os.environ.get("MCP_HOST", "127.0.0.1"),
        port=int(os.environ.get("MCP_PORT", "8001")),
        # Each tool call is independent, so no server-side session state is needed.
        stateless_http=True,
        transport_security=TransportSecuritySettings(allowed_hosts=allowed_hosts),
    )


if __name__ == "__main__":
    main()
