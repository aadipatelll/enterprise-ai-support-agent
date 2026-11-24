"""Model factories. Provider and model names come from settings, so switching to a
hosted provider is a .env change rather than a code change."""

from typing import Any

import httpx
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from ollama import ResponseError

from app.config import Settings

# Errors raised by model clients when the model server is down or the model is missing.
MODEL_ERRORS: tuple[type[Exception], ...] = (OSError, httpx.HTTPError, ResponseError)


def _ollama_kwargs(provider: str, settings: Settings) -> dict[str, Any]:
    return {"base_url": settings.ollama_base_url} if provider == "ollama" else {}


def build_embeddings(settings: Settings) -> Embeddings:
    return init_embeddings(
        settings.embedding_model,
        provider=settings.embedding_provider,
        **_ollama_kwargs(settings.embedding_provider, settings),
    )


def build_chat_model(settings: Settings) -> BaseChatModel:
    return init_chat_model(
        settings.llm_model,
        model_provider=settings.llm_provider,
        temperature=0,
        **_ollama_kwargs(settings.llm_provider, settings),
    )
