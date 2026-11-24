"""Domain errors that callers (CLI, API) translate into user-facing messages."""


class SupportAgentError(Exception):
    """Base class for all expected application errors."""


class ModelUnavailableError(SupportAgentError):
    """The LLM or embedding model could not be reached."""


class DatabaseError(SupportAgentError):
    """A database operation failed."""


class IngestionError(SupportAgentError):
    """Documents could not be turned into stored chunks."""
