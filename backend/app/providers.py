"""Model factories. Provider and model names come from settings, so switching to a
hosted provider is a .env change rather than a code change."""

import httpx
from langchain.embeddings import init_embeddings
from langchain_core.embeddings import Embeddings
from ollama import ResponseError

from app.config import Settings

# Errors raised by model clients when the model server is down or the model is missing.
MODEL_ERRORS: tuple[type[Exception], ...] = (OSError, httpx.HTTPError, ResponseError)


def build_embeddings(settings: Settings) -> Embeddings:
    kwargs = (
        {"base_url": settings.ollama_base_url} if settings.embedding_provider == "ollama" else {}
    )
    return init_embeddings(settings.embedding_model, provider=settings.embedding_provider, **kwargs)
