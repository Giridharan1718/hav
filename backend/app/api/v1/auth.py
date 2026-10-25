"""Authentication: registration, login, MFA, sessions, phone verification, recovery."""

from __future__ import annotations

from datetime import UTC, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as OrmSession

from app.adapters.notification import send_email, send_otp
from app.core.config import settings
from app.core.errors import ApiError
from app.core.ratelimit import LIMITS, enforce
from app.core.security import (
    generate_otp,
    generate_token,
    hash_identifier,
    hash_otp,
    hash_password,
    hash_token,
    mask_phone,
    new_totp_secret,
    normalize_phone,
    totp_provisioning_uri,
    utcnow,
    validate_password_strength,
    verify_password,
    verify_totp,
)
from app.db import get_db
from app.deps import (
    AuthContext,
    clear_session_cookie,
    client_ip,
    issue_csrf_cookie,
    require_reauth,
    require_user,
    set_session_cookie,
)
from app.models import (
    Consent,
    ConsentPurpose,
    PasswordReset,
    PhoneVerification,
    Profile,
    Role,
    User,
)
from app.models import (
    Session as SessionRow,
)
from app.schemas.api import (
    ChangePasswordRequest,
    LoginOut,
    LoginRequest,
    MeOut,
    MfaCodeRequest,
    MfaVerifyRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    PhoneChallengeRequest,
    PhoneVerifyRequest,
    ReauthRequest,
    RegisterRequest,
    SessionOut,
    UserOut,
)
from app.services import audit

router = APIRouter(prefix="/auth", tags=["auth"])
PRIVACY_DOCUMENT_VERSION = "2026-10-01"
MAX_FAILED_LOGINS = 8
LOCK_MINUTES = 15


def _password_error(exc: ValueError) -> ApiError:
    code = str(exc).split(":", 1)[0]
    messages = {
        "password_too_short": f"Use at least {settings.password_min_length} characters.",
        "password_too_long": "Password is too long.",
        "password_too_common": "Choose a less common password.",
        "password_contains_email": "Do not use your email address inside the password.",
        "password_too_simple": "Use a password with more variety of characters.",
    }
    return ApiError(422, "weak_password", messages.get(code, "Choose a stronger password."))


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        email=user.email,
        role=user.role,
        mfa_enabled=user.mfa_enabled,
        created_at=user.created_at,
    )


def _new_session(
    db: OrmSession,
    *,
    user: User,
    request: Request,
    response: Response,
    auth_level: str = "password",
) -> SessionRow:
    token = generate_token()
    now = utcnow()
    row = SessionRow(
        user_id=user.id,
        token_hash=hash_token(token),
        auth_level=auth_level,
        ip_hash=hash_identifier(client_ip(request)) if client_ip(request) else None,
        user_agent=(request.headers.get("user-agent") or "")[:255] or None,
        expires_at=now + timedelta(minutes=settings.session_ttl_minutes),
        last_seen_at=now,
    )
    db.add(row)
    db.flush()
    set_session_cookie(response, token)
    return row


@router.get("/csrf")
def bootstrap_csrf(response: Response) -> dict[str, str]:
    token = issue_csrf_cookie(response)
    return {"csrf_token": token}


@router.post("/register", status_code=201, response_model=LoginOut)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: OrmSession = Depends(get_db, scope="function"),
) -> LoginOut:
    enforce(LIMITS["register"], scope="register", request=request)
    try:
        validate_password_strength(payload.password.get_secret_value(), email=str(payload.email))
    except ValueError as exc:
        raise _password_error(exc) from exc

    email = str(payload.email).strip().lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        # Generic response limits account enumeration.
        raise ApiError(409, "registration_failed", "Unable to create an account with these details.")

    user = User(
        email=email,
        password_hash=hash_password(payload.password.get_secret_value()),
        role=Role.citizen.value,
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(
        Profile(
            user_id=user.id,
            full_name=payload.full_name,
            preferred_language=payload.preferred_language,
        )
    )
    now = utcnow()
    consents = {
        ConsentPurpose.required_account.value: True,
        ConsentPurpose.ai_assistant.value: payload.consent_ai_assistant,
        ConsentPurpose.analytics.value: payload.consent_analytics,
        ConsentPurpose.voice_processing.value: payload.consent_voice_processing,
    }
    for purpose, granted in consents.items():
        db.add(
            Consent(
                user_id=user.id,
                purpose=purpose,
                granted=granted,
                document_version=PRIVACY_DOCUMENT_VERSION,
                granted_at=now if granted else None,
                withdrawn_at=None if granted else now,
            )
        )
    _new_session(db, user=user, request=request, response=response)
    user.last_login_at = now
    audit.record(
        db,
        actor=user,
        action="user.registered",
        resource_type="user",
        resource_id=user.id,
        ip=client_ip(request),
        metadata={"language": payload.preferred_language},
    )
    return LoginOut(status="registered", user=_user_out(user))


@router.post("/login", response_model=LoginOut)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: OrmSession = Depends(get_db, scope="function"),
) -> LoginOut:
    email = str(payload.email).strip().lower()
    enforce(LIMITS["login"], scope="login", request=request, identity=hash_identifier(email))
    user = db.scalar(select(User).where(User.email == email))
    now = utcnow()
    if user is None or user.deleted_at is not None or not user.is_active:
        audit.record(
            db,
            actor=None,
            action="auth.login_failed",
            resource_type="session",
            outcome="denied",
            ip=client_ip(request),
        )
        raise ApiError(401, "invalid_credentials", "Email or password is incorrect.")
    locked_until = user.locked_until
    if locked_until and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=UTC)
    if locked_until and locked_until > now:
        raise ApiError(429, "account_locked", "Too many failed attempts. Try again later.")

    if not verify_password(payload.password.get_secret_value(), user.password_hash):
        user.failed_logins += 1
        if user.failed_logins >= MAX_FAILED_LOGINS:
            user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            user.failed_logins = 0
        audit.record(
            db,
            actor=None,
            action="auth.login_failed",
            resource_type="session",
            outcome="denied",
            ip=client_ip(request),
        )
        # Commit security counters and the audit entry: raising would otherwise roll
        # them back with the request transaction, silently disabling lockout.
        db.commit()
        raise ApiError(401, "invalid_credentials", "Email or password is incorrect.")

    user.failed_logins = 0
    user.locked_until = None
    user.last_login_at = now

    if user.role in {Role.reviewer.value, Role.admin.value} and user.mfa_enabled:
        challenge = generate_token()
        db.add(
            SessionRow(
                user_id=user.id,
                token_hash=hash_token(challenge),
                auth_level="password",
                ip_hash=hash_identifier(client_ip(request)) if client_ip(request) else None,
                user_agent=(request.headers.get("user-agent") or "")[:255] or None,
                expires_at=now + timedelta(minutes=settings.mfa_challenge_ttl_minutes),
                last_seen_at=now,
            )
        )
        db.flush()
        audit.record(
            db,
            actor=user,
            action="auth.mfa_challenge",
            resource_type="session",
            ip=client_ip(request),
        )
        return LoginOut(status="mfa_required", mfa_required=True, mfa_token=challenge)

    _new_session(db, user=user, request=request, response=response)
    audit.record(
        db,
        actor=user,
        action="auth.login",
        resource_type="session",
        ip=client_ip(request),
        metadata={"auth_level": "password"},
    )
    return LoginOut(status="ok", user=_user_out(user))


@router.post("/mfa/verify", response_model=LoginOut)
def verify_mfa(
    payload: MfaVerifyRequest,
    request: Request,
    response: Response,
    db: OrmSession = Depends(get_db, scope="function"),
) -> LoginOut:
    enforce(LIMITS["mfa"], scope="mfa_verify", request=request)
    now = utcnow()
    row = db.scalar(
        select(SessionRow)
        .where(SessionRow.token_hash == hash_token(payload.mfa_token))
        .where(SessionRow.revoked_at.is_(None))
        .where(SessionRow.expires_at > now)
    )
    if row is None:
        raise ApiError(401, "mfa_challenge_invalid", "The verification window expired. Sign in again.")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active or not user.mfa_enabled or not user.mfa_secret_enc:
        raise ApiError(401, "mfa_challenge_invalid", "The verification window expired. Sign in again.")
    if not verify_totp(user.mfa_secret_enc, payload.code):
        audit.record(
            db,
            actor=user,
            action="auth.mfa_failed",
            resource_type="session",
            outcome="denied",
            ip=client_ip(request),
        )
        raise ApiError(401, "invalid_mfa_code", "That code is not valid. Try the current code.")
    row.revoked_at = now  # single use
    _new_session(db, user=user, request=request, response=response, auth_level="mfa")
    audit.record(
        db, actor=user, action="auth.login", resource_type="session", ip=client_ip(request),
        metadata={"auth_level": "mfa"},
    )
    return LoginOut(status="ok", user=_user_out(user))


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> Response:
    auth.session.revoked_at = utcnow()
    clear_session_cookie(response)
    audit.record(db, actor=auth.user, action="auth.logout", resource_type="session", ip=client_ip(request))
    response.status_code = 204
    return response


@router.get("/me", response_model=MeOut)
def me(auth: AuthContext = Depends(require_user), db: OrmSession = Depends(get_db, scope="function")) -> MeOut:
    profile = db.scalar(select(Profile).where(Profile.user_id == auth.user.id))
    from app.models import Address

    address = db.scalar(select(Address).where(Address.user_id == auth.user.id))
    consents = db.scalars(select(Consent).where(Consent.user_id == auth.user.id)).all()
    payload = MeOut(
        user=_user_out(auth.user),
        profile=None
        if profile is None
        else {
            "full_name": profile.full_name,
            "date_of_birth": profile.date_of_birth,
            "preferred_language": profile.preferred_language,
            "phone": profile.phone,
            "phone_masked": mask_phone(profile.phone),
            "phone_verified": profile.phone_verified_at is not None,
            "gender": profile.gender,
            "updated_at": profile.updated_at,
        },
        address=None
        if address is None
        else {
            "line1": address.line1,
            "pincode": address.pincode,
            "post_office": address.post_office,
            "district": address.district,
            "state": address.state,
            "post_office_confirmed": address.post_office_confirmed,
        },
        consents=[
            {
                "purpose": item.purpose,
                "granted": item.granted,
                "document_version": item.document_version,
                "granted_at": item.granted_at,
                "withdrawn_at": item.withdrawn_at,
            }
            for item in consents
        ],
        permissions={
            "reviewer": auth.user.role in {Role.reviewer.value, Role.admin.value},
            "admin": auth.user.role == Role.admin.value,
            "mfa_satisfied": auth.is_mfa,
        },
    )
    return payload


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    auth: AuthContext = Depends(require_user), db: OrmSession = Depends(get_db, scope="function")
) -> list[SessionOut]:
    rows = db.scalars(
        select(SessionRow)
        .where(SessionRow.user_id == auth.user.id, SessionRow.revoked_at.is_(None), SessionRow.expires_at > utcnow())
        .order_by(SessionRow.created_at.desc())
    ).all()
    return [
        SessionOut(
            id=str(row.id),
            created_at=row.created_at,
            last_seen_at=row.last_seen_at,
            expires_at=row.expires_at,
            auth_level=row.auth_level,
            current=row.id == auth.session.id,
        )
        for row in rows
    ]


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_session(
    session_id: str,
    request: Request,
    response: Response,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> Response:
    try:
        parsed_id = UUID(session_id)
    except ValueError as exc:
        raise ApiError(404, "session_not_found", "No session matches this request.") from exc
    row = db.get(SessionRow, parsed_id)
    if row is None or row.user_id != auth.user.id:
        raise ApiError(404, "session_not_found", "No session matches this request.")
    row.revoked_at = utcnow()
    if row.id == auth.session.id:
        clear_session_cookie(response)
    audit.record(db, actor=auth.user, action="auth.session_revoked", resource_type="session", resource_id=row.id, ip=client_ip(request))
    response.status_code = 204
    return response


@router.delete("/sessions", status_code=204)
def revoke_other_sessions(
    request: Request,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> Response:
    others = db.scalars(
        select(SessionRow).where(
            SessionRow.user_id == auth.user.id,
            SessionRow.id != auth.session.id,
            SessionRow.revoked_at.is_(None),
        )
    ).all()
    now = utcnow()
    for row in others:
        row.revoked_at = now
    audit.record(
        db, actor=auth.user, action="auth.other_sessions_revoked", resource_type="session",
        metadata={"count": len(others)}, ip=client_ip(request),
    )
    return Response(status_code=204)


@router.post("/password/change", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> Response:
    require_reauth(payload.current_password.get_secret_value(), auth)
    try:
        validate_password_strength(payload.new_password.get_secret_value(), email=auth.user.email)
    except ValueError as exc:
        raise _password_error(exc) from exc
    auth.user.password_hash = hash_password(payload.new_password.get_secret_value())
    others = db.scalars(
        select(SessionRow).where(
            SessionRow.user_id == auth.user.id,
            SessionRow.id != auth.session.id,
            SessionRow.revoked_at.is_(None),
        )
    ).all()
    for row in others:
        row.revoked_at = utcnow()
    audit.record(db, actor=auth.user, action="auth.password_changed", resource_type="user", resource_id=auth.user.id, ip=client_ip(request))
    return Response(status_code=204)


@router.post("/password/reset/request", status_code=202)
def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict[str, str]:
    email = str(payload.email).strip().lower()
    enforce(LIMITS["password_reset_request"], scope="reset_request", request=request, identity=hash_identifier(email))
    user = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
    if user is not None:
        token = generate_token()
        db.add(
            PasswordReset(
                user_id=user.id,
                token_hash=hash_token(token),
                expires_at=utcnow() + timedelta(minutes=settings.password_reset_ttl_minutes),
            )
        )
        try:
            send_email(
                email,
                "Reset your HVA password",
                (
                    "Use this link to reset your password:\n\n"
                    f"{settings.app_base_url}/reset-password?token={token}\n\n"
                    f"This link expires in {settings.password_reset_ttl_minutes} minutes. "
                    "If you did not request it, ignore this message."
                ),
            )
        except ApiError:
            # Delivery problems must not reveal whether the account exists.
            audit.record(db, actor=None, action="auth.reset_email_failed", resource_type="password_reset", outcome="error")
        audit.record(db, actor=user, action="auth.password_reset_requested", resource_type="password_reset", ip=client_ip(request))
    return {"status": "accepted", "message": "If that email is registered, a reset link has been sent."}


@router.post("/password/reset/confirm", status_code=204)
def confirm_password_reset(
    payload: PasswordResetConfirm,
    request: Request,
    db: OrmSession = Depends(get_db, scope="function"),
) -> Response:
    enforce(LIMITS["password_reset_confirm"], scope="reset_confirm", request=request)
    now = utcnow()
    row = db.scalar(
        select(PasswordReset)
        .where(PasswordReset.token_hash == hash_token(payload.token))
        .where(PasswordReset.used_at.is_(None))
        .where(PasswordReset.expires_at > now)
    )
    if row is None:
        raise ApiError(400, "reset_token_invalid", "This reset link is invalid or has expired.")
    user = db.get(User, row.user_id)
    if user is None or user.deleted_at is not None:
        raise ApiError(400, "reset_token_invalid", "This reset link is invalid or has expired.")
    try:
        validate_password_strength(payload.new_password.get_secret_value(), email=user.email)
    except ValueError as exc:
        raise _password_error(exc) from exc
    user.password_hash = hash_password(payload.new_password.get_secret_value())
    user.failed_logins = 0
    user.locked_until = None
    row.used_at = now
    db.execute(delete(SessionRow).where(SessionRow.user_id == user.id))
    audit.record(db, actor=user, action="auth.password_reset_completed", resource_type="user", resource_id=user.id, ip=client_ip(request))
    return Response(status_code=204)


@router.post("/phone/challenge")
def phone_challenge(
    payload: PhoneChallengeRequest,
    request: Request,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict[str, object]:
    enforce(LIMITS["phone_challenge"], scope="phone_challenge", request=request, identity=str(auth.user.id))
    phone = normalize_phone(payload.phone)
    if phone is None:
        raise ApiError(422, "invalid_phone", "Enter a valid 10-digit Indian mobile number.")
    last = db.scalar(
        select(PhoneVerification)
        .where(PhoneVerification.user_id == auth.user.id, PhoneVerification.purpose == "profile_phone")
        .order_by(PhoneVerification.sent_at.desc())
    )
    if last is not None:
        sent_at = last.sent_at if last.sent_at.tzinfo else last.sent_at.replace(tzinfo=UTC)
        elapsed = (utcnow() - sent_at).total_seconds()
        if elapsed < settings.otp_resend_cooldown_seconds:
            raise ApiError(
                429, "otp_resend_cooldown",
                f"Wait {int(settings.otp_resend_cooldown_seconds - elapsed) + 1} seconds before requesting a new code.",
                headers={"Retry-After": str(int(settings.otp_resend_cooldown_seconds - elapsed) + 1)},
            )
    code = generate_otp()
    db.add(
        PhoneVerification(
            user_id=auth.user.id,
            phone=phone,
            purpose="profile_phone",
            code_hash=hash_otp(code, purpose="profile_phone"),
            expires_at=utcnow() + timedelta(minutes=settings.otp_ttl_minutes),
        )
    )
    delivery = send_otp(phone, code, purpose="profile_phone")
    audit.record(db, actor=auth.user, action="phone.challenge_sent", resource_type="phone_verification", ip=client_ip(request))
    return {
        "status": "sent",
        "phone_masked": mask_phone(phone),
        "expires_in_seconds": settings.otp_ttl_minutes * 60,
        "delivery": delivery.provider,
        # Development-only convenience; never present in production.
        "dev_code": delivery.dev_code if settings.env != "production" else None,
    }


@router.post("/phone/verify")
def phone_verify(
    payload: PhoneVerifyRequest,
    request: Request,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict[str, object]:
    enforce(LIMITS["phone_verify"], scope="phone_verify", request=request, identity=str(auth.user.id))
    now = utcnow()
    row = db.scalar(
        select(PhoneVerification)
        .where(
            PhoneVerification.user_id == auth.user.id,
            PhoneVerification.purpose == "profile_phone",
            PhoneVerification.consumed_at.is_(None),
        )
        .order_by(PhoneVerification.sent_at.desc())
    )
    if row is None or (row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)) <= now:
        raise ApiError(400, "otp_expired", "That verification code has expired. Request a new one.")
    if row.attempts >= settings.otp_max_attempts:
        raise ApiError(429, "otp_attempts_exceeded", "Too many attempts. Request a new code.")
    if hash_otp(payload.code, purpose="profile_phone") != row.code_hash:
        row.attempts += 1
        audit.record(
            db, actor=auth.user, action="phone.verify_failed", resource_type="phone_verification",
            outcome="denied", ip=client_ip(request),
        )
        db.commit()
        raise ApiError(400, "invalid_otp", "That code is not correct.")
    profile = db.scalar(select(Profile).where(Profile.user_id == auth.user.id))
    if profile is None:
        raise ApiError(409, "profile_missing", "Complete your profile before verifying a phone number.")
    profile.phone = row.phone
    profile.phone_verified_at = now
    row.consumed_at = now
    audit.record(db, actor=auth.user, action="phone.verified", resource_type="phone_verification", ip=client_ip(request))
    return {"status": "verified", "phone_masked": mask_phone(row.phone)}


@router.post("/mfa/setup")
def mfa_setup(
    auth: AuthContext = Depends(require_user), db: OrmSession = Depends(get_db, scope="function")
) -> dict[str, str]:
    if auth.user.mfa_enabled:
        raise ApiError(409, "mfa_already_enabled", "Multifactor authentication is already enabled.")
    secret = new_totp_secret()
    auth.user.mfa_secret_enc = secret
    db.flush()
    return {
        "secret": secret,
        "provisioning_uri": totp_provisioning_uri(secret, account_name=auth.user.email),
        "instructions": "Add this secret to an authenticator app, then confirm with a 6-digit code.",
    }


@router.post("/mfa/confirm")
def mfa_confirm(
    payload: MfaCodeRequest,
    request: Request,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict[str, str]:
    if not auth.user.mfa_secret_enc:
        raise ApiError(409, "mfa_not_started", "Start multifactor setup first.")
    if not verify_totp(auth.user.mfa_secret_enc, payload.code):
        raise ApiError(401, "invalid_mfa_code", "That code is not valid. Try the current code.")
    auth.user.mfa_enabled = True
    auth.session.auth_level = "mfa"
    audit.record(db, actor=auth.user, action="auth.mfa_enabled", resource_type="user", resource_id=auth.user.id, ip=client_ip(request))
    return {"status": "enabled"}


@router.post("/reauth")
def reauth_probe(payload: ReauthRequest, auth: AuthContext = Depends(require_user)) -> dict[str, str]:
    require_reauth(payload.password.get_secret_value(), auth)
    return {"status": "confirmed"}

