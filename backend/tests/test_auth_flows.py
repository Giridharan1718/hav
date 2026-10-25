"""Authentication, session, MFA, recovery and phone verification tests."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import pyotp
from conftest import PASSWORD, create_user, csrf
from fastapi.testclient import TestClient

from app.adapters.notification import outbox
from app.main import app
from app.models import PhoneVerification, User
from app.models import Session as SessionRow

REGISTER = {
    "email": "new.person@hva-demo.com",
    "password": "monsoon-river-42",
    "full_name": "Asha Kumari",
    "preferred_language": "hi",
    "accept_privacy_notice": True,
    "consent_ai_assistant": True,
    "consent_analytics": False,
    "consent_voice_processing": False,
}


def test_registration_creates_citizen_and_session(client, db):
    response = client.post("/api/v1/auth/register", json=REGISTER, headers=csrf(client))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "registered"
    assert body["user"]["role"] == "citizen"
    assert "password" not in response.text.lower()

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["profile"]["full_name"] == "Asha Kumari"
    assert me.json()["user"]["email"] == REGISTER["email"]

    stored = db.query(User).filter(User.email == REGISTER["email"]).one()
    assert stored.password_hash.startswith("$argon2id$")
    assert "monsoon-river-42" not in stored.password_hash


def test_registration_rejects_role_mass_assignment(client):
    payload = {**REGISTER, "role": "admin"}
    response = client.post("/api/v1/auth/register", json=payload, headers=csrf(client))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_registration_requires_privacy_notice(client):
    payload = {**REGISTER, "accept_privacy_notice": False}
    response = client.post("/api/v1/auth/register", json=payload, headers=csrf(client))
    assert response.status_code == 422


def test_registration_rejects_weak_password(client):
    payload = {**REGISTER, "email": "weak@hva-demo.com", "password": "password123"}
    response = client.post("/api/v1/auth/register", json=payload, headers=csrf(client))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "weak_password"


def test_duplicate_registration_is_generic(client, user):
    payload = {**REGISTER, "email": user.email}
    response = client.post("/api/v1/auth/register", json=payload, headers=csrf(client))
    assert response.status_code == 409
    assert response.json()["error"]["message"] == "Unable to create an account with these details."


def test_login_logout_revokes_session(client, user, db):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": PASSWORD},
        headers=csrf(client),
    )
    assert login.status_code == 200, login.text
    assert client.get("/api/v1/auth/me").status_code == 200

    logout = client.post("/api/v1/auth/logout", headers=csrf(client))
    assert logout.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    rows = db.query(SessionRow).filter(SessionRow.user_id == user.id).all()
    assert rows and all(row.revoked_at is not None for row in rows)


def test_login_failure_is_generic_and_locks_after_repeated_attempts(client, user):
    for _ in range(8):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "definitely-wrong-password"},
            headers=csrf(client),
        )
        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Email or password is incorrect."
    locked = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": PASSWORD},
        headers=csrf(client),
    )
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "account_locked"


def test_unknown_account_does_not_reveal_existence(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@hva-demo.com", "password": "whatever-password"},
        headers=csrf(client),
    )
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Email or password is incorrect."


def test_csrf_is_required_for_mutations(client):
    response = client.post("/api/v1/auth/register", json=REGISTER)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


def test_cross_origin_mutation_is_rejected(client):
    headers = {**csrf(client), "Origin": "https://evil.example"}
    response = client.post("/api/v1/auth/register", json=REGISTER, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "cross_origin_denied"


def test_expired_session_is_rejected(logged_in, db, user):
    assert logged_in.get("/api/v1/auth/me").status_code == 200
    row = db.query(SessionRow).filter(SessionRow.user_id == user.id).one()
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    assert logged_in.get("/api/v1/auth/me").status_code == 401


def test_session_listing_and_cross_device_revocation(db, user):
    first = TestClient(app)
    first.get("/api/v1/auth/csrf")
    assert first.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}, headers=csrf(first)
    ).status_code == 200

    second = TestClient(app)
    second.get("/api/v1/auth/csrf")
    assert second.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}, headers=csrf(second)
    ).status_code == 200

    sessions = first.get("/api/v1/auth/sessions").json()
    assert len(sessions) == 2
    assert sum(1 for item in sessions if item["current"]) == 1

    assert first.delete("/api/v1/auth/sessions", headers=csrf(first)).status_code == 204
    assert second.get("/api/v1/auth/me").status_code == 401
    assert first.get("/api/v1/auth/me").status_code == 200


def test_password_change_requires_current_password(logged_in, user):
    wrong = logged_in.post(
        "/api/v1/auth/password/change",
        json={"current_password": "not-the-password", "new_password": "new-river-monsoon-77"},
        headers=csrf(logged_in),
    )
    assert wrong.status_code == 403
    assert wrong.json()["error"]["code"] == "reauth_failed"

    changed = logged_in.post(
        "/api/v1/auth/password/change",
        json={"current_password": PASSWORD, "new_password": "new-river-monsoon-77"},
        headers=csrf(logged_in),
    )
    assert changed.status_code == 204

    fresh = TestClient(app)
    fresh.get("/api/v1/auth/csrf")
    old = fresh.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}, headers=csrf(fresh)
    )
    assert old.status_code == 401
    new = fresh.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "new-river-monsoon-77"},
        headers=csrf(fresh),
    )
    assert new.status_code == 200


def test_password_reset_outbox_flow(client, user):
    outbox.clear()
    request = client.post(
        "/api/v1/auth/password/reset/request",
        json={"email": user.email},
        headers=csrf(client),
    )
    assert request.status_code == 202
    assert "If that email is registered" in request.json()["message"]
    assert outbox.messages, "development outbox should contain the reset message"
    token = re.search(r"token=([A-Za-z0-9_\-]+)", outbox.messages[-1]["body"])
    assert token, outbox.messages[-1]["body"]
    value = token.group(1)

    confirm = client.post(
        "/api/v1/auth/password/reset/confirm",
        json={"token": value, "new_password": "reset-river-monsoon-88"},
        headers=csrf(client),
    )
    assert confirm.status_code == 204

    reuse = client.post(
        "/api/v1/auth/password/reset/confirm",
        json={"token": value, "new_password": "another-river-monsoon-99"},
        headers=csrf(client),
    )
    assert reuse.status_code == 400

    login = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "reset-river-monsoon-88"},
        headers=csrf(client),
    )
    assert login.status_code == 200


def test_password_reset_for_unknown_account_is_generic(client):
    response = client.post(
        "/api/v1/auth/password/reset/request",
        json={"email": "missing@hva-demo.com"},
        headers=csrf(client),
    )
    assert response.status_code == 202
    assert "If that email is registered" in response.json()["message"]


def test_phone_challenge_and_verification(logged_in, db, user):
    updated = logged_in.put(
        "/api/v1/me/profile",
        json={"full_name": "Test Citizen", "preferred_language": "en", "phone": "9876543210"},
        headers=csrf(logged_in),
    )
    assert updated.status_code == 200, updated.text

    challenge = logged_in.post(
        "/api/v1/auth/phone/challenge", json={"phone": "9876543210"}, headers=csrf(logged_in)
    )
    assert challenge.status_code == 200, challenge.text
    code = challenge.json()["dev_code"]
    assert code and challenge.json()["delivery"] == "mock"

    stored = db.query(PhoneVerification).filter(PhoneVerification.user_id == user.id).one()
    assert stored.code_hash != code
    assert len(stored.code_hash) == 64

    cooldown = logged_in.post(
        "/api/v1/auth/phone/challenge", json={"phone": "9876543210"}, headers=csrf(logged_in)
    )
    assert cooldown.status_code == 429
    assert cooldown.json()["error"]["code"] == "otp_resend_cooldown"

    wrong = logged_in.post(
        "/api/v1/auth/phone/verify", json={"code": "000000"}, headers=csrf(logged_in)
    )
    assert wrong.status_code == 400
    assert wrong.json()["error"]["code"] == "invalid_otp"

    verified = logged_in.post(
        "/api/v1/auth/phone/verify", json={"code": code}, headers=csrf(logged_in)
    )
    assert verified.status_code == 200
    me = logged_in.get("/api/v1/auth/me").json()
    assert me["profile"]["phone_verified"] is True


def test_otp_attempt_limit(logged_in, db, user):
    logged_in.put(
        "/api/v1/me/profile",
        json={"full_name": "Test Citizen", "preferred_language": "en", "phone": "9876543211"},
        headers=csrf(logged_in),
    )
    challenge = logged_in.post(
        "/api/v1/auth/phone/challenge", json={"phone": "9876543211"}, headers=csrf(logged_in)
    )
    assert challenge.status_code == 200
    for _ in range(5):
        response = logged_in.post(
            "/api/v1/auth/phone/verify", json={"code": "000001"}, headers=csrf(logged_in)
        )
        assert response.status_code == 400
    blocked = logged_in.post(
        "/api/v1/auth/phone/verify", json={"code": "000001"}, headers=csrf(logged_in)
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "otp_attempts_exceeded"


def test_mfa_login_for_privileged_account(db):
    reviewer = create_user(db, email="reviewer.integration@hva-demo.com", role="reviewer", mfa=True)
    client = TestClient(app)
    client.get("/api/v1/auth/csrf")

    login = client.post(
        "/api/v1/auth/login",
        json={"email": reviewer.email, "password": PASSWORD},
        headers=csrf(client),
    )
    assert login.status_code == 200
    body = login.json()
    assert body["mfa_required"] is True and body["mfa_token"]
    assert client.get("/api/v1/auth/me").status_code == 401

    wrong = client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": body["mfa_token"], "code": "000000"},
        headers=csrf(client),
    )
    assert wrong.status_code == 401

    code = pyotp.TOTP(reviewer.mfa_secret_enc).now()
    verified = client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": body["mfa_token"], "code": code},
        headers=csrf(client),
    )
    assert verified.status_code == 200, verified.text
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["permissions"]["mfa_satisfied"] is True
    assert me.json()["user"]["role"] == "reviewer"

    replay = client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": body["mfa_token"], "code": code},
        headers=csrf(client),
    )
    assert replay.status_code == 401


def test_me_never_exposes_secrets(logged_in, user):
    body = logged_in.get("/api/v1/auth/me").json()
    serialized = str(body)
    assert "password_hash" not in serialized
    assert "$argon2" not in serialized
    assert "mfa_secret" not in serialized
    assert user.email not in serialized or body["user"]["email"] == user.email
