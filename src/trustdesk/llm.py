"""LLM clients: Ollama (JSON-schema constrained output) and a FakeLLM for tests."""
from __future__ import annotations

from collections.abc import Callable
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from .config import settings


class Citation(BaseModel):
    source: str = Field(description="Source id like S1")
    quote: str = Field(description="Exact words copied from that source")


class DraftAnswer(BaseModel):
    status: Literal["answered", "insufficient_evidence"]
    answer: Literal["Yes", "No", "Partial", "N/A"] | None = None
    explanation: str = ""
    citations: list[Citation] = Field(default_factory=list)


class LLM(Protocol):
    name: str

    def draft(self, system: str, user: str) -> DraftAnswer: ...


class OllamaLLM:
    def __init__(self, model: str | None = None, host: str | None = None):
        from ollama import Client

        self.model = model or settings.llm_model
        self.client = Client(host=host or settings.ollama_host)
        self.name = f"ollama:{self.model}"

    def draft(self, system: str, user: str) -> DraftAnswer:
        kwargs = dict(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            format=DraftAnswer.model_json_schema(),
            options={"temperature": 0, "num_ctx": settings.num_ctx},
        )
        try:
            resp = self.client.chat(**kwargs, think=False)  # qwen3: skip slow reasoning traces
        except TypeError:  # older ollama client without `think`
            resp = self.client.chat(**kwargs)
        return DraftAnswer.model_validate_json(resp.message.content)


class FakeLLM:
    """Test double: `responder(question, sources_text) -> DraftAnswer`."""

    name = "fake"

    def __init__(self, responder: Callable[[str, str], DraftAnswer]):
        self.responder = responder

    def draft(self, system: str, user: str) -> DraftAnswer:
        sources, _, question = user.partition("QUESTION:\n<<<\n")
        return self.responder(question.removesuffix("\n>>>"), sources)
