"""Purpose-specific consent management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.core.errors import ApiError
from app.core.security import utcnow
from app.db import get_db
from app.deps import AuthContext, client_ip, require_user
from app.models import Consent, ConsentPurpose
from app.schemas.api import ConsentUpdate
from app.services import audit

router = APIRouter(tags=["consent"])
PRIVACY_DOCUMENT_VERSION = "2026-10-01"

PURPOSE_CATALOG = [
    {
        "purpose": ConsentPurpose.required_account.value,
        "required": True,
        "title": "Account operation and security",
        "description": (
            "Creating and securing your account, signing you in, and sending essential service "
            "messages. This processing is necessary for the account and cannot be withdrawn while "
            "the account exists. Deleting your account removes it."
        ),
    },
    {
        "purpose": ConsentPurpose.ai_assistant.value,
        "required": False,
        "title": "Personalised assistant",
        "description": (
            "Allows the assistant to answer in your saved language preference and to send your "
            "question plus the retrieved catalogue evidence to the configured language-model "
            "provider. Messages are not stored, eligibility answers are not stored, and your "
            "profile is never sent to a provider. Off by default: without this consent the "
            "deterministic catalogue composer is used and the language is detected from your "
            "message."
        ),
    },
    {
        "purpose": ConsentPurpose.analytics.value,
        "required": False,
        "title": "Search analytics",
        "description": (
            "Stores the search terms you use so the catalogue and synonyms can be improved. Off by "
            "default; you can withdraw this at any time."
        ),
    },
    {
        "purpose": ConsentPurpose.voice_processing.value,
        "required": False,
        "title": "Voice input",
        "description": (
            "Sends recorded audio to the configured speech provider when you choose to use voice "
            "input. Off by default. Voice input is unavailable until a provider is configured."
        ),
    },
]


@router.get("/consents/catalog")
def consent_catalog() -> dict:
    return {
        "document_version": PRIVACY_DOCUMENT_VERSION,
        "purposes": PURPOSE_CATALOG,
        "note": (
            "Consent is recorded per purpose. Withdrawal takes effect for future processing. "
            "Questionnaire answers used for eligibility checks are never stored."
        ),
    }


@router.get("/me/consents")
def list_consents(
    auth: AuthContext = Depends(require_user), db: OrmSession = Depends(get_db, scope="function")
) -> dict:
    rows = db.scalars(select(Consent).where(Consent.user_id == auth.user.id)).all()
    by_purpose = {row.purpose: row for row in rows}
    return {
        "document_version": PRIVACY_DOCUMENT_VERSION,
        "consents": [
            {
                "purpose": item["purpose"],
                "required": item["required"],
                "title": item["title"],
                "description": item["description"],
                "granted": bool(by_purpose.get(item["purpose"]) and by_purpose[item["purpose"]].granted),
                "updated_at": (
                    by_purpose[item["purpose"]].updated_at.isoformat()
                    if by_purpose.get(item["purpose"])
                    else None
                ),
            }
            for item in PURPOSE_CATALOG
        ],
    }


@router.put("/me/consents/{purpose}")
def update_consent(
    purpose: str,
    payload: ConsentUpdate,
    request: Request,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    if purpose not in {item.value for item in ConsentPurpose}:
        raise ApiError(404, "purpose_not_found", "No such consent purpose.")
    if purpose == ConsentPurpose.required_account.value and not payload.granted:
        raise ApiError(
            409,
            "required_consent",
            "Account operation consent cannot be withdrawn while the account exists. You can request account deletion instead.",
        )
    row = db.scalar(select(Consent).where(Consent.user_id == auth.user.id, Consent.purpose == purpose))
    now = utcnow()
    if row is None:
        row = Consent(
            user_id=auth.user.id,
            purpose=purpose,
            granted=payload.granted,
            document_version=PRIVACY_DOCUMENT_VERSION,
        )
        db.add(row)
    row.granted = payload.granted
    row.document_version = PRIVACY_DOCUMENT_VERSION
    if payload.granted:
        row.granted_at = now
        row.withdrawn_at = None
    else:
        row.withdrawn_at = now
    db.flush()
    audit.record(
        db,
        actor=auth.user,
        action="consent.updated",
        resource_type="consent",
        resource_id=purpose,
        ip=client_ip(request),
        metadata={"granted": payload.granted},
    )
    return {"purpose": purpose, "granted": payload.granted, "document_version": PRIVACY_DOCUMENT_VERSION}
