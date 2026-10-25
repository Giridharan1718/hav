"""Personal-data export and account deletion.

Deletion is scheduled with a 30-day retention window while all personal content
(profile, address, drafts, consents, sessions, phone challenges, password resets and
search history) is removed or anonymised immediately, so the request takes effect for
future processing at once. Audit rows retain no personal data.
"""

from __future__ import annotations

import secrets
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Address,
    ApplicationDraft,
    AuditEvent,
    Consent,
    DeletionRequest,
    PasswordReset,
    PhoneVerification,
    Profile,
    SearchHistory,
    User,
)
from app.models import (
    Session as SessionRow,
)
from app.services.drafts import serialize as serialize_draft

DELETE_RETENTION_DAYS = 30


def export_user_data(db: Session, user: User) -> dict[str, Any]:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    address = db.scalar(select(Address).where(Address.user_id == user.id))
    consents = db.scalars(select(Consent).where(Consent.user_id == user.id)).all()
    drafts = db.scalars(
        select(ApplicationDraft)
        .options(
            selectinload(ApplicationDraft.fields),
            selectinload(ApplicationDraft.scheme),
            selectinload(ApplicationDraft.scheme_version),
        )
        .where(ApplicationDraft.user_id == user.id)
    ).all()
    sessions = db.scalars(
        select(SessionRow).where(SessionRow.user_id == user.id).order_by(SessionRow.created_at.desc())
    ).all()
    audit = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.actor_user_id == user.id)
        .order_by(AuditEvent.created_at.desc())
        .limit(500)
    ).all()
    deletion = db.scalars(
        select(DeletionRequest).where(DeletionRequest.user_id == user.id).order_by(DeletionRequest.requested_at.desc())
    ).first()
    search_history = db.scalars(
        select(SearchHistory)
        .where(SearchHistory.user_id == user.id)
        .order_by(SearchHistory.created_at.desc())
        .limit(500)
    ).all()

    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "notice": (
            "This export contains the personal data HVA holds about you. Questionnaire answers used for "
            "eligibility checks are not stored. Draft exports you generated are included below."
        ),
        "account": {
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "mfa_enabled": user.mfa_enabled,
        },
        "profile": None
        if profile is None
        else {
            "full_name": profile.full_name,
            "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth else None,
            "preferred_language": profile.preferred_language,
            "phone": profile.phone,
            "phone_verified": profile.phone_verified_at is not None,
            "gender": profile.gender,
            "updated_at": profile.updated_at.isoformat(),
        },
        "address": None
        if address is None
        else {
            "line1": address.line1,
            "pincode": address.pincode,
            "post_office": address.post_office,
            "district": address.district,
            "state": address.state,
            "post_office_confirmed": address.post_office_confirmed,
        },
        "consents": [
            {
                "purpose": item.purpose,
                "granted": item.granted,
                "document_version": item.document_version,
                "granted_at": item.granted_at.isoformat() if item.granted_at else None,
                "withdrawn_at": item.withdrawn_at.isoformat() if item.withdrawn_at else None,
            }
            for item in consents
        ],
        "drafts": [serialize_draft(draft) for draft in drafts],
        "search_history": [
            {
                "query": item.query,
                "language": item.language,
                "filters": item.filters,
                "result_count": item.result_count,
                "created_at": item.created_at.isoformat(),
            }
            for item in search_history
        ],
        "sessions": [
            {
                "created_at": item.created_at.isoformat(),
                "last_seen_at": item.last_seen_at.isoformat(),
                "expires_at": item.expires_at.isoformat(),
                "revoked": item.revoked_at is not None,
                "auth_level": item.auth_level,
            }
            for item in sessions
        ],
        "activity": [
            {
                "action": item.action,
                "resource_type": item.resource_type,
                "outcome": item.outcome,
                "created_at": item.created_at.isoformat(),
            }
            for item in audit
        ],
        "deletion_request": None
        if deletion is None
        else {
            "status": deletion.status,
            "requested_at": deletion.requested_at.isoformat(),
            "execute_after": deletion.execute_after.isoformat(),
        },
    }


def request_deletion(db: Session, user: User) -> DeletionRequest:
    now = datetime.now(UTC)
    # Immediate effect on future processing.
    db.execute(delete(Profile).where(Profile.user_id == user.id))
    db.execute(delete(Address).where(Address.user_id == user.id))
    db.execute(delete(ApplicationDraft).where(ApplicationDraft.user_id == user.id))
    db.execute(delete(SearchHistory).where(SearchHistory.user_id == user.id))
    db.execute(delete(Consent).where(Consent.user_id == user.id))
    db.execute(delete(PhoneVerification).where(PhoneVerification.user_id == user.id))
    db.execute(delete(PasswordReset).where(PasswordReset.user_id == user.id))
    db.execute(delete(SessionRow).where(SessionRow.user_id == user.id))

    user.email = f"deleted+{user.id}@invalid.local"
    user.password_hash = "!" + secrets.token_urlsafe(48)
    user.mfa_secret_enc = None
    user.mfa_enabled = False
    user.is_active = False
    user.deleted_at = now

    request = DeletionRequest(
        user_id=user.id,
        execute_after=date.today() + timedelta(days=DELETE_RETENTION_DAYS),
        status="scheduled",
    )
    db.add(request)
    db.flush()
    return request


def get_deletion_request(db: Session, user_id) -> DeletionRequest | None:
    return db.scalars(
        select(DeletionRequest).where(DeletionRequest.user_id == user_id).order_by(DeletionRequest.requested_at.desc())
    ).first()


def purge_expired_accounts(db: Session) -> int:
    """Hard-delete accounts whose retention window has elapsed. Used by the job worker."""
    now = date.today()
    requests = db.scalars(
        select(DeletionRequest).where(
            DeletionRequest.status == "scheduled", DeletionRequest.execute_after <= now
        )
    ).all()
    purged = 0
    for request in requests:
        user = db.get(User, request.user_id)
        if user is not None:
            db.execute(delete(SearchHistory).where(SearchHistory.user_id == user.id))
            db.execute(
                delete(AuditEvent).where(
                    AuditEvent.actor_user_id == user.id, AuditEvent.resource_type == "user"
                )
            )
            db.delete(user)
        request.status = "completed"
        request.completed_at = datetime.now(UTC)
        purged += 1
    db.flush()
    return purged
