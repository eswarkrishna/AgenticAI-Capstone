"""Runtime configuration loaded from environment / `.env`."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CLAUDE_SONNET_MODEL = "claude-3-5-sonnet-latest"
DEFAULT_PARSE_MODEL = "gpt-4o"


class Settings(BaseSettings):
    """Application settings. Secrets stay in the environment, never in source."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    langsmith_api_key: str = ""
    parse_model: str = DEFAULT_PARSE_MODEL
    score_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    chroma_dir: Path = Path("data/chroma")
    sqlite_path: Path = Path("data/tracking.db")
    top_k: int = Field(default=5, ge=1)

    @model_validator(mode="after")
    def use_claude_for_parse_when_anthropic_configured(self) -> Settings:
        """If an Anthropic key is present and PARSE_MODEL was not set, parse with Claude Sonnet."""
        if self.anthropic_api_key and os.getenv("PARSE_MODEL") is None:
            self.parse_model = CLAUDE_SONNET_MODEL
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
