"""Private application-draft endpoints (creation, editing, export)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session as OrmSession

from app.core.errors import ApiError
from app.core.ratelimit import LIMITS, enforce
from app.db import get_db
from app.deps import AuthContext, client_ip, require_user
from app.schemas.api import DraftCreate, DraftExportOut, DraftExportRequest, DraftOut, DraftUpdate
from app.services import audit, drafts

router = APIRouter(prefix="/drafts", tags=["drafts"])


def _draft_id(raw: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError as exc:
        raise ApiError(404, "draft_not_found", "No draft matches this request.") from exc


@router.post("", status_code=201, response_model=DraftOut)
def create_draft(
    payload: DraftCreate,
    request: Request,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    draft = drafts.create_draft(
        db,
        user=auth.user,
        scheme_slug=payload.scheme_slug,
        language=payload.language,
        reuse_profile=payload.reuse_profile,
    )
    audit.record(
        db,
        actor=auth.user,
        action="draft.created",
        resource_type="application_draft",
        resource_id=draft.id,
        ip=client_ip(request),
        metadata={"scheme": payload.scheme_slug, "reuse_profile": payload.reuse_profile},
    )
    return drafts.serialize(draft, language=payload.language)


@router.get("")
def list_drafts(
    auth: AuthContext = Depends(require_user), db: OrmSession = Depends(get_db, scope="function")
) -> dict:
    return {"drafts": drafts.list_drafts(db, auth.user.id)}


@router.get("/{draft_id}", response_model=DraftOut)
def get_draft(
    draft_id: str,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    draft = drafts.get_draft(db, draft_id=_draft_id(draft_id), user_id=auth.user.id)
    return drafts.serialize(draft)


@router.patch("/{draft_id}", response_model=DraftOut)
def update_draft(
    draft_id: str,
    payload: DraftUpdate,
    request: Request,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    draft = drafts.update_draft(
        db,
        draft_id=_draft_id(draft_id),
        user_id=auth.user.id,
        updates=[item.model_dump() for item in payload.fields],
        remove=payload.remove,
        confirm=payload.confirm,
    )
    audit.record(
        db,
        actor=auth.user,
        action="draft.updated",
        resource_type="application_draft",
        resource_id=draft.id,
        ip=client_ip(request),
        metadata={"updated": len(payload.fields), "removed": len(payload.remove)},
    )
    return drafts.serialize(draft)


@router.delete("/{draft_id}", status_code=204)
def delete_draft(
    draft_id: str,
    request: Request,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> Response:
    parsed = _draft_id(draft_id)
    drafts.delete_draft(db, draft_id=parsed, user_id=auth.user.id)
    audit.record(
        db, actor=auth.user, action="draft.deleted", resource_type="application_draft",
        resource_id=parsed, ip=client_ip(request),
    )
    return Response(status_code=204)


@router.post("/{draft_id}/export", response_model=DraftExportOut)
def export_draft(
    draft_id: str,
    payload: DraftExportRequest,
    request: Request,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    enforce(LIMITS["draft_export"], scope="draft_export", request=request, identity=str(auth.user.id))
    parsed = _draft_id(draft_id)
    result = drafts.export_draft(
        db, draft_id=parsed, user_id=auth.user.id, fmt=payload.format, language=payload.language
    )
    audit.record(
        db,
        actor=auth.user,
        action="draft.exported",
        resource_type="application_draft",
        resource_id=parsed,
        ip=client_ip(request),
        metadata={"format": payload.format, "submitted": False},
    )
    return result
