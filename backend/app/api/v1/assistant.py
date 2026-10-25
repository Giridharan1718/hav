"""Multilingual assistant endpoints."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.adapters import transcription as transcription_adapter
from app.adapters.llm import LLMProvider, get_llm_provider
from app.core.config import settings
from app.core.errors import ApiError
from app.core.ratelimit import LIMITS, enforce
from app.db import get_db
from app.deps import (
    AuthContext,
    client_ip,
    get_optional_auth,
    require_consent_active,
    require_user,
)
from app.models import AuditEvent, ConsentPurpose
from app.schemas.api import AssistantOut, AssistantRequest, TranscriptionRequest
from app.services import assistant, audit

logger = logging.getLogger("hva.assistant")
router = APIRouter(prefix="/assistant", tags=["assistant"])


def _messages_today(db: OrmSession, user_id) -> int:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(
                AuditEvent.actor_user_id == user_id,
                AuditEvent.action == "assistant.message",
                AuditEvent.created_at >= start,
            )
        )
        or 0
    )


@router.post("/messages", response_model=AssistantOut)
def send_message(
    payload: AssistantRequest,
    request: Request,
    db: OrmSession = Depends(get_db, scope="function"),
    provider: LLMProvider | None = Depends(get_llm_provider),
    auth: AuthContext | None = Depends(get_optional_auth),
) -> dict:
    enforce(LIMITS["assistant"], scope="assistant", request=request)
    if auth is not None and _messages_today(db, auth.user.id) >= settings.assistant_daily_limit:
        # A signed-in quota protects the (costly) language provider from one account.
        # Anonymous use is bounded by the per-IP limit above instead.
        raise ApiError(
            429,
            "daily_limit_reached",
            "You have reached today's assistant message limit. Please try again tomorrow.",
            headers={"Retry-After": "3600"},
        )
    # Optional AI-assistant consent controls two things: using the saved language
    # preference, and sending the question/evidence to an external language model.
    # Without it, signed-in and anonymous callers get the deterministic composer.
    ai_consent = auth is not None and require_consent_active(
        db, auth.user.id, ConsentPurpose.ai_assistant.value
    )
    preferred_language = None
    if ai_consent and auth.user.profile is not None:
        preferred_language = auth.user.profile.preferred_language
    effective_provider = provider if ai_consent else None
    result = assistant.answer(
        db,
        message=payload.message,
        language=payload.language,
        preferred_language=preferred_language,
        scheme_slug=payload.scheme_slug,
        eligibility_inputs=payload.eligibility_inputs,
        provider=effective_provider,
    )
    if auth is not None:
        audit.record(
            db,
            actor=auth.user,
            action="assistant.message",
            resource_type="assistant",
            ip=client_ip(request),
            metadata={
                "language": result["language"],
                "provider": result["provider"],
                "citations": len(result["citations"]),
                "fallback_used": result["fallback_used"],
            },
        )
    return result


@router.post("/transcribe")
def transcribe(
    payload: TranscriptionRequest,
    request: Request,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict[str, str]:
    if not payload.consent_voice_processing:
        raise ApiError(403, "voice_consent_required", "Voice processing consent is required for audio input.")
    if not require_consent_active(db, auth.user.id, ConsentPurpose.voice_processing.value):
        raise ApiError(403, "voice_consent_required", "Grant voice processing consent in privacy settings first.")
    if not transcription_adapter.available():
        raise ApiError(
            503,
            "transcription_unavailable",
            "Speech input is not configured in this environment. Please type your question instead.",
        )
    try:
        text = transcription_adapter.transcribe(payload.audio_base64, language=payload.language)
    except transcription_adapter.ProviderError as exc:
        code = str(exc)
        raise ApiError(
            502 if "provider" in code else 422,
            code,
            "The speech service could not process this audio. Please type your question instead.",
        ) from exc
    audit.record(
        db,
        actor=auth.user,
        action="assistant.transcribed",
        resource_type="assistant",
        ip=client_ip(request),
        metadata={"language": payload.language, "characters": len(text)},
    )
    return {"text": text, "language": payload.language or "", "provider": "http"}
