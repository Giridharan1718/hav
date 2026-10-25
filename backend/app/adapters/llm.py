"""Language-model adapter.

Only an OpenAI-compatible /chat/completions client (a documented contract) is
implemented, and it is enabled only when HVA_LLM_PROVIDER=openai_compatible with a
base URL, API key and model configured. The default is a deterministic, local
grounded composer in ``app/services/assistant.py``; it is never presented as an LLM.

Model output is treated as untrusted: callers must validate it against a schema and
against retrieved evidence before showing it.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.errors import ApiError

logger = logging.getLogger("hva.llm")

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class ProviderError(Exception):
    """Raised when the provider is unavailable or returns unusable output."""


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, *, system: str, user: str, schema: type[SchemaT]) -> SchemaT: ...


class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compatible"

    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def generate(self, *, system: str, user: str, schema: type[SchemaT]) -> SchemaT:
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise ProviderError("provider_unavailable") from exc
        try:
            data = json.loads(content)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ProviderError("provider_invalid_output") from exc


class DisabledProvider(LLMProvider):
    name = "disabled"

    def generate(self, *, system: str, user: str, schema: type[SchemaT]) -> SchemaT:
        raise ApiError(503, "assistant_provider_unavailable", "The assistant provider is not configured.")


def get_llm_provider() -> LLMProvider | None:
    if settings.llm_provider == "disabled":
        return None
    if not (settings.llm_base_url and settings.llm_api_key and settings.llm_model):
        logger.warning("LLM provider selected but incomplete configuration; treating as disabled")
        return None
    return OpenAICompatibleProvider(
        settings.llm_base_url, settings.llm_api_key, settings.llm_model, settings.llm_timeout_seconds
    )
