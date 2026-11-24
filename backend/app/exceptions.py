"""Domain errors that callers (CLI, API) translate into user-facing messages."""


class SupportAgentError(Exception):
    """Base class for all expected application errors."""


class ModelUnavailableError(SupportAgentError):
    """The LLM or embedding model could not be reached."""


class DatabaseError(SupportAgentError):
    """A database operation failed."""


class IngestionError(SupportAgentError):
    """Documents could not be turned into stored chunks."""


class TicketServiceError(SupportAgentError):
    """The ticket MCP server is unreachable or rejected the request."""


class TicketNotFoundError(SupportAgentError):
    """The requested ticket does not exist."""


class DocumentNotFoundError(SupportAgentError):
    """The requested source document does not exist."""
