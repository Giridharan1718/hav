"""Personal-data export and account deletion requests (reauthentication required)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session as OrmSession

from app.core.ratelimit import LIMITS, enforce
from app.db import get_db
from app.deps import (
    AuthContext,
    clear_session_cookie,
    client_ip,
    require_reauth,
    require_user,
)
from app.schemas.api import DeletionRequestIn, ReauthRequest
from app.services import audit, privacy

router = APIRouter(prefix="/me", tags=["privacy"])


@router.post("/export")
def export_data(
    payload: ReauthRequest,
    request: Request,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    enforce(LIMITS["data_export"], scope="data_export", request=request, identity=str(auth.user.id))
    require_reauth(payload.password.get_secret_value(), auth)
    data = privacy.export_user_data(db, auth.user)
    audit.record(
        db, actor=auth.user, action="privacy.exported", resource_type="user", resource_id=auth.user.id,
        ip=client_ip(request),
    )
    return data


@router.post("/deletion")
def request_deletion(
    payload: DeletionRequestIn,
    request: Request,
    response: Response,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    require_reauth(payload.password.get_secret_value(), auth)
    record = privacy.request_deletion(db, auth.user)
    audit.record(
        db,
        actor=None,
        action="privacy.deletion_requested",
        resource_type="user",
        resource_id=auth.user.id,
        ip=client_ip(request),
        metadata={"retention_days": privacy.DELETE_RETENTION_DAYS},
    )
    clear_session_cookie(response)
    return {
        "status": "scheduled",
        "requested_at": record.requested_at.isoformat(),
        "execute_after": record.execute_after.isoformat(),
        "message": (
            "Your profile, address, drafts, consents, search history and sessions have been removed "
            "and all sessions were signed out. Remaining records are scheduled for permanent deletion "
            f"after the {privacy.DELETE_RETENTION_DAYS}-day retention window. You can contact support "
            "to cancel before then."
        ),
    }


@router.get("/deletion")
def deletion_status(
    auth: AuthContext = Depends(require_user), db: OrmSession = Depends(get_db, scope="function")
) -> dict:
    record = privacy.get_deletion_request(db, auth.user.id)
    if record is None:
        return {"status": "none"}
    return {
        "status": record.status,
        "requested_at": record.requested_at.isoformat(),
        "execute_after": record.execute_after.isoformat(),
        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
    }
