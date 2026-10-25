"""Translation adapter.

Default behaviour is the curated catalogue: reviewed translations stored in
``scheme_translations``. No machine translation is applied silently. An HTTP
translation provider can be configured with a simple documented contract
(POST {"text", "source", "target"} -> {"translation"}); its output is marked as
machine-translated and not presented as reviewed content.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings

logger = logging.getLogger("hva.translation")


class TranslationProvider(ABC):
    name: str
    reviewed: bool = False

    @abstractmethod
    def translate(self, text: str, *, source: str, target: str) -> str | None: ...


class HttpTranslationProvider(TranslationProvider):
    name = "http"

    def translate(self, text: str, *, source: str, target: str) -> str | None:
        try:
            response = httpx.post(
                settings.translation_http_url,
                json={"text": text, "source": source, "target": target},
                headers={"Authorization": f"Bearer {settings.translation_http_token}"},
                timeout=15,
            )
            response.raise_for_status()
            value = response.json().get("translation")
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("translation provider failure: %s", type(exc).__name__)
            return None
        if not isinstance(value, str) or not value.strip():
            return None
        return value.strip()


def get_translation_provider() -> TranslationProvider | None:
    if settings.translation_provider == "http" and settings.translation_http_url:
        return HttpTranslationProvider()
    return None
