"""Request dependencies: database session, authentication, authorization, CSRF bootstrap."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.core.config import settings
from app.core.errors import ApiError
from app.core.security import hash_identifier, hash_token, verify_password
from app.db import get_db
from app.models import Role, User
from app.models import Session as SessionRow


@dataclass
class AuthContext:
    user: User
    session: SessionRow

    @property
    def is_mfa(self) -> bool:
        return self.session.auth_level == "mfa"

    @property
    def is_privileged(self) -> bool:
        return self.user.role in {Role.reviewer.value, Role.admin.value}


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _load_session(db: OrmSession, token: str) -> tuple[SessionRow, User] | None:
    now = datetime.now(UTC)
    row = db.scalar(
        select(SessionRow)
        .where(SessionRow.token_hash == hash_token(token))
        .where(SessionRow.revoked_at.is_(None))
        .where(SessionRow.expires_at > now)
    )
    if row is None:
        return None
    user = db.get(User, row.user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        return None
    idle_limit = timedelta(minutes=settings.session_ttl_minutes)
    last_seen = row.last_seen_at
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=UTC)
    if now - last_seen > idle_limit:
        row.revoked_at = now
        db.flush()
        return None
    if (now - last_seen).total_seconds() > settings.session_last_seen_interval_seconds:
        row.last_seen_at = now
        db.flush()
    return row, user


def get_optional_auth(
    request: Request, db: OrmSession = Depends(get_db, scope="function")
) -> AuthContext | None:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    loaded = _load_session(db, token)
    if loaded is None:
        return None
    session_row, user = loaded
    return AuthContext(user=user, session=session_row)


def require_user(auth: AuthContext | None = Depends(get_optional_auth)) -> AuthContext:
    if auth is None:
        raise ApiError(401, "unauthenticated", "Please sign in to continue.")
    return auth


def require_role(*roles: Role):
    allowed = {role.value for role in roles}

    def dependency(auth: AuthContext = Depends(require_user)) -> AuthContext:
        if auth.user.role not in allowed:
            raise ApiError(403, "forbidden", "You do not have access to this resource.")
        return auth

    return dependency


def require_privileged_mfa(auth: AuthContext = Depends(require_role(Role.reviewer, Role.admin))) -> AuthContext:
    """Administrative operations require an MFA-satisfied session."""
    if not auth.user.mfa_enabled:
        raise ApiError(403, "mfa_enrollment_required", "Enable multifactor authentication first.")
    if not auth.is_mfa:
        raise ApiError(403, "mfa_required", "Reauthenticate with multifactor authentication.")
    return auth


def require_reauth(password: str, auth: AuthContext) -> None:
    if not verify_password(password, auth.user.password_hash):
        raise ApiError(403, "reauth_failed", "Password confirmation failed.")


def require_consent_active(db: OrmSession, user_id, purpose: str) -> bool:
    from app.models import Consent

    consent = db.scalar(select(Consent).where(Consent.user_id == user_id, Consent.purpose == purpose))
    return bool(consent and consent.granted)


def issue_csrf_cookie(response: Response) -> str:
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        settings.csrf_cookie_name,
        token,
        httponly=False,
        secure=bool(settings.cookie_secure),
        samesite="lax",
        path="/",
        max_age=settings.session_ttl_minutes * 60,
    )
    return token


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        secure=bool(settings.cookie_secure),
        samesite="lax",
        path="/",
        max_age=settings.session_ttl_minutes * 60,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")


def ip_hash_for(request: Request) -> str | None:
    ip = client_ip(request)
    return hash_identifier(ip) if ip else None
