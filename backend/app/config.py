"""Application settings loaded from environment variables and the repo-level .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://support:change-me@localhost:5432/support_agent"

    llm_provider: str = "ollama"
    llm_model: str = "llama3.1:8b"
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = Field(default=768, gt=0)
    ollama_base_url: str = "http://localhost:11434"

    chunk_size: int = Field(default=800, gt=0)
    chunk_overlap: int = Field(default=100, ge=0)
    docs_dir: Path = REPO_ROOT / "data" / "docs"

    top_k: int = Field(default=4, gt=0)
    min_relevance_score: float = Field(default=0.55, ge=-1, le=1)
    prompt_version: str = "v1"

    mcp_server_url: str = "http://localhost:8001/mcp"
    cors_origins: list[str] = ["http://localhost:5173"]

    @model_validator(mode="after")
    def _overlap_smaller_than_chunk(self) -> Self:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
