"""Protected review, audit and ingestion administration.

Every route here requires an MFA-satisfied reviewer or administrator session, and each
state change writes an audit event.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.core.config import settings
from app.core.errors import ApiError
from app.core.ratelimit import LIMITS, enforce
from app.db import get_db
from app.deps import AuthContext, client_ip, require_privileged_mfa
from app.models import (
    AuditEvent,
    BackgroundJob,
    EligibilityRule,
    IngestionRun,
    ReviewStatus,
    Scheme,
    SchemeVersion,
)
from app.schemas.api import IngestionRequest, ReviewDecision
from app.services import audit, ingestion, search

router = APIRouter(prefix="/admin", tags=["admin"])


def _version_id(raw: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError as exc:
        raise ApiError(404, "version_not_found", "No scheme version matches this request.") from exc


@router.get("/review/queue")
def review_queue(
    auth: AuthContext = Depends(require_privileged_mfa),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    rows = db.execute(
        select(SchemeVersion, Scheme)
        .join(Scheme, Scheme.id == SchemeVersion.scheme_id)
        .where(
            SchemeVersion.review_status.in_(
                [ReviewStatus.draft.value, ReviewStatus.pending_review.value, ReviewStatus.source_checked.value]
            )
        )
        .order_by(SchemeVersion.created_at.desc())
        .limit(100)
    ).all()
    return {
        "items": [
            {
                "version_id": str(version.id),
                "scheme_slug": scheme.slug,
                "scheme_name": scheme.official_name,
                "department": scheme.department,
                "version_no": version.version_no,
                "review_status": version.review_status,
                "retrieved_at": version.retrieved_at.isoformat() if version.retrieved_at else None,
                "source_document_id": str(version.source_document_id) if version.source_document_id else None,
                "application_url": version.application_url,
                "rule_count": db.scalar(
                    select(EligibilityRule.id)
                    .where(EligibilityRule.scheme_version_id == version.id)
                    .limit(1)
                )
                is not None,
            }
            for version, scheme in rows
        ],
        "count": len(rows),
        "note": (
            "Approving a version records you as the reviewer, marks its rules valid and publishes it. "
            "Only approve after checking the recorded source document."
        ),
    }


@router.post("/schemes/{version_id}/review")
def review_version(
    version_id: str,
    payload: ReviewDecision,
    request: Request,
    auth: AuthContext = Depends(require_privileged_mfa),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    enforce(LIMITS["admin_write"], scope="admin_review", request=request, identity=str(auth.user.id))
    version = db.get(SchemeVersion, _version_id(version_id))
    if version is None:
        raise ApiError(404, "version_not_found", "No scheme version matches this request.")
    scheme = db.get(Scheme, version.scheme_id)
    if scheme is None:
        raise ApiError(404, "scheme_not_found", "The scheme for this version no longer exists.")
    previous = version.review_status
    now = datetime.now(UTC)

    if payload.decision == "approve":
        version.review_status = ReviewStatus.verified.value
        version.verified_at = now
        version.reviewer_id = auth.user.id
        version.review_notes = payload.notes or "Approved after source review."
        rules = db.scalars(
            select(EligibilityRule).where(EligibilityRule.scheme_version_id == version.id)
        ).all()
        for rule in rules:
            if rule.validation_status == "unverified":
                rule.validation_status = "valid"
        others = db.scalars(
            select(SchemeVersion).where(
                SchemeVersion.scheme_id == scheme.id,
                SchemeVersion.id != version.id,
                SchemeVersion.review_status.in_([ReviewStatus.verified.value, ReviewStatus.source_checked.value]),
            )
        ).all()
        for other in others:
            other.review_status = ReviewStatus.superseded.value
        scheme.current_version_id = version.id
        scheme.is_published = True
        outcome = "approved"
    else:
        version.review_status = ReviewStatus.rejected.value
        version.reviewer_id = auth.user.id
        version.review_notes = payload.notes
        if scheme.current_version_id == version.id:
            scheme.is_published = False
        outcome = "rejected"

    db.flush()
    audit.record(
        db,
        actor=auth.user,
        action=f"scheme_version.{outcome}",
        resource_type="scheme_version",
        resource_id=version.id,
        ip=client_ip(request),
        metadata={
            "scheme": scheme.slug,
            "previous_status": previous,
            "new_status": version.review_status,
            "notes_recorded": bool(version.review_notes),
        },
    )
    return {
        "status": "ok",
        "decision": payload.decision,
        "version_id": str(version.id),
        "scheme_slug": scheme.slug,
        "review_status": version.review_status,
        "published": scheme.is_published,
    }


@router.get("/audit")
def audit_log(
    limit: int = Query(default=50, ge=1, le=200),
    action: str | None = Query(default=None, max_length=80),
    auth: AuthContext = Depends(require_privileged_mfa),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    rows = db.scalars(stmt).all()
    return {
        "items": [
            {
                "id": str(row.id),
                "action": row.action,
                "actor_role": row.actor_role,
                "actor_id": str(row.actor_user_id) if row.actor_user_id else None,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "outcome": row.outcome,
                "created_at": row.created_at.isoformat(),
                "metadata": row.event_metadata,
            }
            for row in rows
        ],
        "limit": limit,
    }


@router.post("/ingestion", status_code=202)
def start_ingestion(
    payload: IngestionRequest,
    request: Request,
    auth: AuthContext = Depends(require_privileged_mfa),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    enforce(LIMITS["admin_write"], scope="admin_ingestion", request=request, identity=str(auth.user.id))
    run, job = ingestion.queue_ingestion(db, user_id=auth.user.id, url=payload.url)
    audit.record(
        db,
        actor=auth.user,
        action="ingestion.queued",
        resource_type="ingestion_run",
        resource_id=run.id,
        ip=client_ip(request),
        metadata={"host": run.host},
    )
    return {
        "status": "queued",
        "run_id": str(run.id),
        "job_id": str(job.id),
        "host": run.host,
        "approved_hosts": list(settings.approved_ingest_hosts),
        "note": (
            "The worker records the source document hash and retrieval time. Structured scheme facts "
            "are entered and reviewed separately; this platform does not auto-generate eligibility rules."
        ),
    }


@router.get("/ingestion/runs")
def ingestion_runs(
    auth: AuthContext = Depends(require_privileged_mfa), db: OrmSession = Depends(get_db, scope="function")
) -> dict:
    rows = db.scalars(select(IngestionRun).order_by(IngestionRun.created_at.desc()).limit(50)).all()
    return {
        "items": [
            {
                "id": str(row.id),
                "url": row.url,
                "host": row.host,
                "status": row.status,
                "http_status": row.http_status,
                "content_hash": row.content_hash,
                "byte_size": row.byte_size,
                "error": row.error,
                "created_at": row.created_at.isoformat(),
                "finished_at": row.finished_at.isoformat() if row.finished_at else None,
            }
            for row in rows
        ]
    }


@router.get("/jobs")
def background_jobs(
    auth: AuthContext = Depends(require_privileged_mfa), db: OrmSession = Depends(get_db, scope="function")
) -> dict:
    rows = db.scalars(select(BackgroundJob).order_by(BackgroundJob.created_at.desc()).limit(50)).all()
    return {
        "items": [
            {
                "id": str(row.id),
                "kind": row.kind,
                "status": row.status,
                "attempts": row.attempts,
                "last_error": row.last_error,
                "created_at": row.created_at.isoformat(),
                "finished_at": row.finished_at.isoformat() if row.finished_at else None,
            }
            for row in rows
        ],
        "worker_note": "Run `python -m app.jobs.worker --once` to process queued jobs.",
    }


@router.get("/overview")
def overview(
    auth: AuthContext = Depends(require_privileged_mfa), db: OrmSession = Depends(get_db, scope="function")
) -> dict:
    now = datetime.now(UTC)
    return {
        "reviewer": {"email": auth.user.email, "role": auth.user.role, "mfa_satisfied": auth.is_mfa},
        "counts": {
            "published_schemes": search.count_published(db),
            "pending_versions": len(
                db.scalars(
                    select(SchemeVersion).where(
                        SchemeVersion.review_status.in_(
                            [ReviewStatus.pending_review.value, ReviewStatus.source_checked.value]
                        )
                    )
                ).all()
            ),
            "failed_jobs_24h": len(
                db.scalars(
                    select(BackgroundJob).where(
                        BackgroundJob.status == "failed", BackgroundJob.created_at > now - timedelta(hours=24)
                    )
                ).all()
            ),
        },
        "integrity_note": (
            "Review status 'source_checked' means only the source link was checked automatically. "
            "Only 'verified' indicates human content review."
        ),
    }
