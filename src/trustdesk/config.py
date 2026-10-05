"""Settings, overridable with environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    ollama_host: str = field(default_factory=lambda: _env("OLLAMA_HOST", "http://localhost:11434"))
    llm_model: str = field(default_factory=lambda: _env("TRUSTDESK_LLM", "qwen3:8b"))
    embed_model: str = field(default_factory=lambda: _env("TRUSTDESK_EMBED", "nomic-embed-text"))
    db_path: Path = field(default_factory=lambda: Path(_env("TRUSTDESK_DB", ".trustdesk/index.db")))
    num_ctx: int = field(default_factory=lambda: int(_env("TRUSTDESK_NUM_CTX", "8192")))
    top_k: int = field(default_factory=lambda: int(_env("TRUSTDESK_TOP_K", "6")))
    chunk_chars: int = 900
    min_quote_chars: int = 20


settings = Settings()
