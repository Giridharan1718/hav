"""Speech-to-text adapter.

No provider is configured in this build. The endpoint reports a structured
``transcription_unavailable`` error instead of pretending audio was processed, and
voice input is only offered in the UI when the feature report says it is available.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("hva.transcription")


class ProviderError(Exception):
    pass


def available() -> bool:
    return settings.transcription_provider == "http" and bool(settings.transcription_http_url)


def transcribe(audio_base64: str, *, language: str | None = None) -> str:
    if not available():
        raise ProviderError("transcription_unavailable")
    try:
        response = httpx.post(
            settings.transcription_http_url,
            json={"audio_base64": audio_base64, "language": language},
            headers={"Authorization": f"Bearer {settings.transcription_http_token}"},
            timeout=30,
        )
        response.raise_for_status()
        text = response.json().get("text")
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("transcription provider failure: %s", type(exc).__name__)
        raise ProviderError("transcription_provider_error") from exc
    if not isinstance(text, str) or not text.strip():
        raise ProviderError("transcription_empty")
    return text.strip()
