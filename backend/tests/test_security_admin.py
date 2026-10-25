"""Privacy, administration, ingestion, assistant and security-control tests."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta

import pyotp
from conftest import PASSWORD, create_user, csrf
from fastapi.testclient import TestClient

from app.adapters.llm import get_llm_provider
from app.jobs import worker
from app.main import app
from app.models import (
    AuditEvent,
    BackgroundJob,
    Consent,
    DeletionRequest,
    DraftField,
    IngestionRun,
    Profile,
    ReviewStatus,
    Scheme,
    SchemeVersion,
    SearchHistory,
    SourceDocument,
    User,
)
from app.models import (
    Session as SessionRow,
)
from app.services import ingestion


def _login(db, *, role: str = "citizen", email: str = "session.user@hva-demo.com", mfa: bool = False):
    user = create_user(db, email=email, role=role, mfa=mfa)
    client = TestClient(app)
    client.get("/api/v1/auth/csrf")
    response = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}, headers=csrf(client)
    )
    assert response.status_code == 200, response.text
    if mfa:
        token = response.json()["mfa_token"]
        code = pyotp.TOTP(user.mfa_secret_enc).now()
        verified = client.post(
            "/api/v1/auth/mfa/verify",
            json={"mfa_token": token, "code": code},
            headers=csrf(client),
        )
        assert verified.status_code == 200, verified.text
    return client, user


# --------------------------------------------------------------------- privacy


def test_consent_withdrawal_and_required_consent(db):
    client, user = _login(db)
    listed = client.get("/api/v1/me/consents")
    assert listed.status_code == 200
    assert {item["purpose"] for item in listed.json()["consents"]} == {
        "required_account",
        "ai_assistant",
        "analytics",
        "voice_processing",
    }

    grant = client.put("/api/v1/me/consents/analytics", json={"granted": True}, headers=csrf(client))
    assert grant.status_code == 200
    row = db.query(Consent).filter(Consent.user_id == user.id, Consent.purpose == "analytics").one()
    assert row.granted is True and row.granted_at is not None

    withdraw = client.put("/api/v1/me/consents/analytics", json={"granted": False}, headers=csrf(client))
    assert withdraw.status_code == 200
    db.refresh(row)
    assert row.granted is False and row.withdrawn_at is not None

    required = client.put(
        "/api/v1/me/consents/required_account", json={"granted": False}, headers=csrf(client)
    )
    assert required.status_code == 409
    assert client.put(
        "/api/v1/me/consents/not_a_purpose", json={"granted": True}, headers=csrf(client)
    ).status_code == 404


def test_data_export_requires_password_and_omits_secrets(db, seeded_catalogue):
    client, user = _login(db)
    client.put("/api/v1/me/consents/analytics", json={"granted": True}, headers=csrf(client))
    searched = client.get("/api/v1/schemes", params={"query": "farmer", "language": "en"})
    assert searched.status_code == 200

    wrong = client.post(
        "/api/v1/me/export", json={"password": "wrong-password"}, headers=csrf(client)
    )
    assert wrong.status_code == 403

    exported = client.post(
        "/api/v1/me/export", json={"password": PASSWORD}, headers=csrf(client)
    )
    assert exported.status_code == 200, exported.text
    body = exported.json()
    assert body["account"]["email"] == user.email
    assert any("farmer" in item["query"] for item in body["search_history"])
    serialized = json.dumps(body)
    assert "password_hash" not in serialized
    assert "$argon2" not in serialized
    assert "code_hash" not in serialized


def test_account_deletion_removes_personal_data_and_sessions(db, seeded_catalogue):
    client, user = _login(db, email="deleting.user@hva-demo.com")
    client.put("/api/v1/me/consents/analytics", json={"granted": True}, headers=csrf(client))
    searched = client.get("/api/v1/schemes", params={"query": "farmer", "language": "en"})
    assert searched.status_code == 200
    assert db.query(SearchHistory).filter(SearchHistory.user_id == user.id).count() == 1
    draft = client.post("/api/v1/drafts", json={"scheme_slug": "pm-kisan"}, headers=csrf(client))
    assert draft.status_code == 201

    bad = client.post(
        "/api/v1/me/deletion",
        json={"password": PASSWORD, "confirmation": "delete"},
        headers=csrf(client),
    )
    assert bad.status_code == 422
    wrong_password = client.post(
        "/api/v1/me/deletion",
        json={"password": "not-it", "confirmation": "DELETE"},
        headers=csrf(client),
    )
    assert wrong_password.status_code == 403

    response = client.post(
        "/api/v1/me/deletion",
        json={"password": PASSWORD, "confirmation": "DELETE"},
        headers=csrf(client),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "scheduled"

    db.expire_all()
    stored = db.get(User, user.id)
    assert stored.deleted_at is not None
    assert stored.is_active is False
    assert stored.email.startswith("deleted+")
    assert stored.mfa_secret_enc is None
    assert db.query(Profile).filter(Profile.user_id == user.id).count() == 0
    assert db.query(DraftField).count() == 0
    assert db.query(Consent).filter(Consent.user_id == user.id).count() == 0
    assert db.query(SearchHistory).filter(SearchHistory.user_id == user.id).count() == 0
    assert db.query(SessionRow).filter(SessionRow.user_id == user.id).count() == 0
    assert db.query(DeletionRequest).filter(DeletionRequest.user_id == user.id).count() == 1

    assert client.get("/api/v1/auth/me").status_code == 401
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "deleting.user@hva-demo.com", "password": PASSWORD},
        headers=csrf(client),
    )
    assert login.status_code == 401
    assert db.query(AuditEvent).filter(AuditEvent.action == "privacy.deletion_requested").count() == 1


def test_worker_purges_accounts_after_retention(db):
    user = create_user(db, email="purge.after.retention@hva-demo.com")
    user_id = user.id
    request = DeletionRequest(
        user_id=user_id,
        execute_after=date.today() - timedelta(days=1),
        status="scheduled",
    )
    db.add(request)
    db.commit()
    request_id = request.id

    results = worker.tick()

    db.expire_all()
    assert db.get(User, user_id) is None
    assert db.get(DeletionRequest, request_id) is None
    assert "deletion_purge:purged=1" in results


# ------------------------------------------------------------------------ admin


def test_anonymous_and_citizen_cannot_reach_admin(client, db):
    assert client.get("/api/v1/admin/review/queue").status_code == 401
    cit, _ = _login(db, email="plain.citizen@hva-demo.com")
    response = cit.get("/api/v1/admin/review/queue")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_reviewer_without_mfa_is_blocked(db):
    reviewer, _ = _login(db, role="reviewer", email="reviewer.no.mfa@hva-demo.com")
    response = reviewer.get("/api/v1/admin/review/queue")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "mfa_enrollment_required"


def test_review_approval_publishes_and_audits(db, seeded_catalogue):
    client, reviewer = _login(db, role="reviewer", email="reviewer.mfa@hva-demo.com", mfa=True)
    queue = client.get("/api/v1/admin/review/queue")
    assert queue.status_code == 200
    items = queue.json()["items"]
    assert len(items) == 8
    target = next(item for item in items if item["scheme_slug"] == "pm-kisan")

    approved = client.post(
        f"/api/v1/admin/schemes/{target['version_id']}/review",
        json={"decision": "approve", "notes": "Checked official page and rules."},
        headers=csrf(client),
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["review_status"] == "verified"
    assert approved.json()["published"] is True

    db.expire_all()
    version = db.get(SchemeVersion, target["version_id"])
    assert version.review_status == ReviewStatus.verified.value
    assert version.reviewer_id == reviewer.id
    assert version.verified_at is not None
    scheme = db.query(Scheme).filter(Scheme.slug == "pm-kisan").one()
    assert scheme.current_version_id == version.id
    events = db.query(AuditEvent).filter(AuditEvent.action == "scheme_version.approved").all()
    assert len(events) == 1
    assert events[0].actor_user_id == reviewer.id


def test_rejection_requires_reason_and_unpublishes(db, seeded_catalogue):
    client, _ = _login(db, role="admin", email="admin.mfa@hva-demo.com", mfa=True)
    version = (
        db.query(SchemeVersion)
        .join(Scheme, Scheme.id == SchemeVersion.scheme_id)
        .filter(Scheme.slug == "pm-kisan")
        .one()
    )
    missing_notes = client.post(
        f"/api/v1/admin/schemes/{version.id}/review",
        json={"decision": "reject"},
        headers=csrf(client),
    )
    assert missing_notes.status_code == 422

    rejected = client.post(
        f"/api/v1/admin/schemes/{version.id}/review",
        json={"decision": "reject", "notes": "Source did not match the transcribed rules."},
        headers=csrf(client),
    )
    assert rejected.status_code == 200
    db.expire_all()
    scheme = db.query(Scheme).filter(Scheme.slug == "pm-kisan").one()
    assert db.get(SchemeVersion, version.id).review_status == ReviewStatus.rejected.value
    assert scheme.is_published is False


def test_admin_overview_reports_numeric_published_count(db, seeded_catalogue):
    client, _ = _login(db, role="reviewer", email="reviewer.overview@hva-demo.com", mfa=True)
    overview = client.get("/api/v1/admin/overview")
    assert overview.status_code == 200
    count = overview.json()["counts"]["published_schemes"]
    assert isinstance(count, int) and not isinstance(count, bool)
    assert count == 8


# ------------------------------------------------------------------- ingestion


def test_ingestion_rejects_unapproved_hosts(db, seeded_catalogue):
    client, _ = _login(db, role="reviewer", email="reviewer.ingest@hva-demo.com", mfa=True)
    for url, code in (
        ("http://pmkisan.gov.in/", "source_not_permitted"),
        ("https://evil.example.com/", "source_host_not_approved"),
        ("https://127.0.0.1/", "source_not_permitted"),
        ("https://pmkisan.gov.in:8443/", "source_not_permitted"),
    ):
        response = client.post("/api/v1/admin/ingestion", json={"url": url}, headers=csrf(client))
        assert response.status_code == 422, (url, response.text)
        assert response.json()["error"]["code"] == code

    assert db.query(BackgroundJob).count() == 0


def test_ingestion_worker_records_source_document(db, seeded_catalogue, monkeypatch):
    client, reviewer = _login(db, role="reviewer", email="reviewer.worker@hva-demo.com", mfa=True)
    queued = client.post(
        "/api/v1/admin/ingestion",
        json={"url": "https://pmkisan.gov.in/"},
        headers=csrf(client),
    )
    assert queued.status_code == 202, queued.text

    def fake_fetch(url: str):
        return ingestion.FetchedDocument(
            url=url,
            final_url=url,
            host="pmkisan.gov.in",
            status_code=200,
            content_type="text/html",
            text="<html><title>PM-KISAN</title></html>",
            content_hash="a" * 64,
            byte_size=40,
            retrieved_at=datetime.now(UTC),
            title="PM-KISAN",
        )

    monkeypatch.setattr(ingestion, "fetch_document", fake_fetch)
    results = ingestion.run_queue(db, limit=5)
    db.commit()
    assert results == ["ingestion:succeeded"]

    run = db.query(IngestionRun).one()
    assert run.status == "succeeded"
    assert run.content_hash == "a" * 64
    assert db.query(SourceDocument).filter(SourceDocument.content_hash == "a" * 64).count() == 1
    job = db.query(BackgroundJob).one()
    assert job.status == "succeeded" and job.attempts == 1


# ------------------------------------------------------------------- assistant


def test_assistant_uses_catalogue_only(client, seeded_catalogue):
    response = client.post(
        "/api/v1/assistant/messages",
        json={"message": "I am a farmer looking for income support", "language": "en"},
        headers=csrf(client),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "grounded_template"
    assert body["fallback_used"] is False
    assert body["citations"], "answers must cite records"
    assert any("PM-KISAN" in scheme["name"] for scheme in body["schemes"])
    assert "pmkisan.gov.in" in body["answer"]


def test_assistant_answers_hindi_and_flags_missing_translation(client, seeded_catalogue):
    response = client.post(
        "/api/v1/assistant/messages",
        json={"message": "किसान योजना क्या है?", "language": "hi"},
        headers=csrf(client),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "hi"
    assert "योजना" in body["answer"]

    untranslated = client.post(
        "/api/v1/assistant/messages",
        json={"message": "pension", "scheme_slug": "atal-pension-yojana", "language": "hi"},
        headers=csrf(client),
    )
    notices = [notice["code"] for notice in untranslated.json()["notices"]]
    assert "translation_unavailable" in notices


def test_assistant_scheme_focus_excludes_unrelated_matches(client, seeded_catalogue):
    unscoped = client.post(
        "/api/v1/assistant/messages",
        json={"message": "I am a farmer looking for income support", "language": "en"},
        headers=csrf(client),
    )
    assert unscoped.status_code == 200, unscoped.text
    assert any(scheme["slug"] == "pm-kisan" for scheme in unscoped.json()["schemes"])

    focused = client.post(
        "/api/v1/assistant/messages",
        json={
            "message": "I am a farmer looking for income support",
            "scheme_slug": "atal-pension-yojana",
            "language": "en",
        },
        headers=csrf(client),
    )
    assert focused.status_code == 200, focused.text
    body = focused.json()
    assert [scheme["slug"] for scheme in body["schemes"]] == ["atal-pension-yojana"]
    assert {citation["scheme_slug"] for citation in body["citations"]} == {"atal-pension-yojana"}
    assert "PM-KISAN" not in body["answer"]
    assert body["missing_information"] == list(dict.fromkeys(body["missing_information"]))


def test_assistant_personalisation_requires_consent(db, seeded_catalogue):
    client, _ = _login(db, email="assistant.personalisation@hva-demo.com")
    updated = client.put(
        "/api/v1/me/profile",
        json={"full_name": "Test Citizen", "preferred_language": "hi"},
        headers=csrf(client),
    )
    assert updated.status_code == 200, updated.text

    without_consent = client.post(
        "/api/v1/assistant/messages",
        json={"message": "What is PM-KISAN?"},
        headers=csrf(client),
    )
    assert without_consent.status_code == 200, without_consent.text
    assert without_consent.json()["language"] == "en"

    granted = client.put(
        "/api/v1/me/consents/ai_assistant", json={"granted": True}, headers=csrf(client)
    )
    assert granted.status_code == 200

    with_consent = client.post(
        "/api/v1/assistant/messages",
        json={"message": "What is PM-KISAN?"},
        headers=csrf(client),
    )
    assert with_consent.status_code == 200, with_consent.text
    assert with_consent.json()["language"] == "hi"
    # Script-detectable Hindi keeps the question's language even with a Hindi profile.
    hindi = client.post(
        "/api/v1/assistant/messages",
        json={"message": "पीएम किसान क्या है?"},
        headers=csrf(client),
    )
    assert hindi.json()["language"] == "hi"


def test_assistant_provider_requires_ai_consent(db, seeded_catalogue):
    calls: list[str] = []

    class _StubProvider:
        name = "consent-stub"

        def generate(self, *, system, user, schema):
            calls.append(user)
            return schema(
                answer="PM-KISAN provides 6000 per year to eligible farmer families.",
                citations=["pm-kisan"],
            )

    client, _ = _login(db, email="assistant.no-consent@hva-demo.com")
    app.dependency_overrides[get_llm_provider] = lambda: _StubProvider()
    try:
        response = client.post(
            "/api/v1/assistant/messages",
            json={"message": "PM-KISAN amount", "scheme_slug": "pm-kisan", "language": "en"},
            headers=csrf(client),
        )
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)
    assert response.status_code == 200, response.text
    assert response.json()["provider"] == "grounded_template"
    assert calls == []


def test_assistant_daily_quota_applies_to_signed_in_users(db, seeded_catalogue, monkeypatch):
    from app.core.config import settings

    client, _ = _login(db, email="assistant.quota@hva-demo.com")
    monkeypatch.setattr(settings, "assistant_daily_limit", 1)
    first = client.post(
        "/api/v1/assistant/messages",
        json={"message": "What is PM-KISAN?", "language": "en"},
        headers=csrf(client),
    )
    assert first.status_code == 200, first.text
    second = client.post(
        "/api/v1/assistant/messages",
        json={"message": "What is PM-KISAN?", "language": "en"},
        headers=csrf(client),
    )
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "daily_limit_reached"


def test_assistant_no_match_does_not_invent_scheme(client, seeded_catalogue):
    response = client.post(
        "/api/v1/assistant/messages",
        json={"message": "quantum astrophysics telescope grant", "language": "en"},
        headers=csrf(client),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["citations"] == []
    assert "No scheme" in body["answer"]


class _FabricatingProvider:
    name = "fabricating-stub"

    def generate(self, *, system, user, schema):
        return schema(answer="PM-KISAN guarantees 99999 rupees to everyone.", citations=["pm-kisan"])


class _GroundedProvider:
    name = "grounded-stub"

    def generate(self, *, system, user, schema):
        return schema(
            answer="PM-KISAN provides 6000 per year to eligible farmer families. Aadhaar card is required.",
            citations=["pm-kisan"],
        )


def test_assistant_rejects_fabricated_provider_output(db, seeded_catalogue):
    client, _ = _login(db, email="assistant.fabricated@hva-demo.com")
    client.put("/api/v1/me/consents/ai_assistant", json={"granted": True}, headers=csrf(client))
    app.dependency_overrides[get_llm_provider] = lambda: _FabricatingProvider()
    try:
        response = client.post(
            "/api/v1/assistant/messages",
            json={"message": "PM-KISAN amount", "scheme_slug": "pm-kisan", "language": "en"},
            headers=csrf(client),
        )
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)
    assert response.status_code == 200
    body = response.json()
    assert body["fallback_used"] is True
    assert body["provider"] == "grounded_template"
    assert "99999" not in body["answer"]
    assert "assistant_output_rejected" in [notice["code"] for notice in body["notices"]]


def test_assistant_accepts_grounded_provider_output(db, seeded_catalogue):
    client, _ = _login(db, email="assistant.grounded@hva-demo.com")
    client.put("/api/v1/me/consents/ai_assistant", json={"granted": True}, headers=csrf(client))
    app.dependency_overrides[get_llm_provider] = lambda: _GroundedProvider()
    try:
        response = client.post(
            "/api/v1/assistant/messages",
            json={"message": "PM-KISAN amount", "scheme_slug": "pm-kisan", "language": "en"},
            headers=csrf(client),
        )
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)
    body = response.json()
    assert body["provider"] == "grounded-stub"
    assert body["fallback_used"] is False
    assert "99999" not in body["answer"]


def test_transcription_requires_consent_and_provider(db):
    anonymous = TestClient(app)
    anonymous.get("/api/v1/auth/csrf")
    assert anonymous.post(
        "/api/v1/assistant/transcribe",
        json={"audio_base64": "A" * 40, "consent_voice_processing": True},
        headers=csrf(anonymous),
    ).status_code == 401

    client, _ = _login(db, email="voice.user@hva-demo.com")
    no_consent = client.post(
        "/api/v1/assistant/transcribe",
        json={"audio_base64": "A" * 40, "consent_voice_processing": True},
        headers=csrf(client),
    )
    assert no_consent.status_code == 403

    client.put("/api/v1/me/consents/voice_processing", json={"granted": True}, headers=csrf(client))
    unavailable = client.post(
        "/api/v1/assistant/transcribe",
        json={"audio_base64": "A" * 40, "consent_voice_processing": True},
        headers=csrf(client),
    )
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "transcription_unavailable"


# -------------------------------------------------------------------- controls


def test_security_headers_present(client):
    response = client.get("/api/v1/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "referrer-policy" in response.headers
    assert response.headers["x-request-id"]

    # Early middleware rejections must carry the same headers as normal responses.
    rejected = client.post("/api/v1/assistant/messages", json={"message": "no csrf"})
    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "csrf_failed"
    assert rejected.headers["x-content-type-options"] == "nosniff"
    assert rejected.headers["x-frame-options"] == "DENY"
    assert rejected.headers["x-request-id"]


def test_oversized_request_is_rejected(client):
    response = client.post(
        "/api/v1/assistant/messages",
        content=b"x" * 1_100_000,
        headers={**csrf(client), "Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_draft_values_are_returned_as_data_not_markup(db, seeded_catalogue):
    client, _ = _login(db, email="xss.user@hva-demo.com")
    created = client.post("/api/v1/drafts", json={"scheme_slug": "pm-kisan"}, headers=csrf(client))
    draft_id = created.json()["id"]
    payload = "<script>alert(1)</script>"
    updated = client.patch(
        f"/api/v1/drafts/{draft_id}",
        json={"fields": [{"key": "full_name", "value": payload}], "remove": [], "confirm": []},
        headers=csrf(client),
    )
    assert updated.status_code == 200
    assert updated.headers["content-type"].startswith("application/json")
    field = next(item for item in updated.json()["fields"] if item["key"] == "full_name")
    assert field["value"] == payload


def test_audit_metadata_has_no_credentials(db):
    client, user = _login(db, email="audit.user@hva-demo.com")
    client.put("/api/v1/me/consents/analytics", json={"granted": True}, headers=csrf(client))
    rows = db.query(AuditEvent).all()
    assert rows, "security-relevant actions should be audited"
    serialized = json.dumps([row.event_metadata for row in rows])
    for secret in (user.email, PASSWORD, "argon2", "code_hash", "token_hash"):
        assert secret not in serialized
    forbidden_keys = {"password", "password_hash", "otp", "code", "token", "new_password"}
    for row in rows:
        assert not (forbidden_keys & set(row.event_metadata.keys()))


def test_health_reports_disabled_capabilities_honestly(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert body["features"]["transcription"]["configured"] is False
    assert body["features"]["assistant"]["provider"] == "disabled"
    assert body["features"]["oidc"]["enabled"] is False
    assert body["languages"] == ["en", "hi", "ta"]


def test_invalid_uuid_paths_return_not_found_not_server_error(db):
    client, _ = _login(db, email="uuid.user@hva-demo.com")
    assert client.get("/api/v1/drafts/not-a-uuid").status_code == 404
    assert client.delete("/api/v1/auth/sessions/not-a-uuid", headers=csrf(client)).status_code == 404
