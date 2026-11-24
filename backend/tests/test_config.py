import pytest
from pydantic import ValidationError

from app.config import Settings


def test_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValidationError, match="chunk_overlap"):
        Settings(chunk_size=100, chunk_overlap=100, _env_file=None)


def test_settings_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "some-hosted-model")
    monkeypatch.setenv("CHUNK_SIZE", "1200")

    settings = Settings(_env_file=None)

    assert settings.llm_model == "some-hosted-model"
    assert settings.chunk_size == 1200
