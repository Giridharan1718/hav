"""Postal lookup, search, eligibility and draft flows."""

from __future__ import annotations

from datetime import date

import pytest
from conftest import PASSWORD, create_user, csrf
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models import ApplicationDraft, PostalOffice


@pytest.fixture
def postal(db):
    from seed.seed import seed_postal

    seed_postal(db)
    db.commit()
    return db


def test_pincode_format_validation(client, postal):
    for value in ("012345", "12345", "ABCDEF", "000000"):
        response = client.get(f"/api/v1/postal/{value}")
        assert response.status_code == 422, value
        assert response.json()["error"]["code"] == "invalid_pincode_format"


def test_unknown_pincode_is_not_treated_as_valid(client, postal):
    response = client.get("/api/v1/postal/999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "unknown_pincode"
    assert response.json()["error"]["details"]["source"]["is_sample"] is True


def test_known_pincode_returns_source_provenance(client, postal):
    response = client.get("/api/v1/postal/110001")
    assert response.status_code == 200
    body = response.json()
    assert body["matches"][0]["name"] == "New Delhi GPO"
    assert body["ambiguous"] is False
    assert body["source"]["is_sample"] is True
    assert body["source"]["url"] == "https://www.indiapost.gov.in/"


def test_ambiguous_pincode_requires_selection(client, postal, db):
    db.add(
        PostalOffice(
            pincode="110001",
            name="Example Extension PO",
            district="New Delhi",
            state="Delhi",
            branch_type="Branch Post Office",
            delivery_status="Delivery",
        )
    )
    db.commit()
    response = client.get("/api/v1/postal/110001")
    assert response.status_code == 200
    assert response.json()["ambiguous"] is True
    assert len(response.json()["matches"]) == 2


def test_postal_provider_failure_is_distinct(client, postal, monkeypatch):
    monkeypatch.setattr(settings, "postal_source", "http")
    monkeypatch.setattr(settings, "postal_http_url", "")
    response = client.get("/api/v1/postal/110001")
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "postal_provider_error"


def test_address_save_requires_post_office_when_ambiguous(logged_in, postal, db):
    db.add(
        PostalOffice(
            pincode="110001",
            name="Example Extension PO",
            district="New Delhi",
            state="Delhi",
        )
    )
    db.commit()
    response = logged_in.put(
        "/api/v1/me/address",
        json={"pincode": "110001", "post_office_confirmed": False},
        headers=csrf(logged_in),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "post_office_selection_required"


def test_address_confirms_selected_post_office(logged_in, postal):
    response = logged_in.put(
        "/api/v1/me/address",
        json={"pincode": "110001", "post_office": "New Delhi GPO", "line1": "12 Example Marg"},
        headers=csrf(logged_in),
    )
    assert response.status_code == 200, response.text
    address = response.json()["address"]
    assert address["post_office"] == "New Delhi GPO"
    assert address["district"] == "New Delhi"
    assert address["state"] == "Delhi"
    assert address["post_office_confirmed"] is True


def test_unknown_pincode_allows_manual_address_with_warning(logged_in, postal):
    response = logged_in.put(
        "/api/v1/me/address",
        json={"pincode": "999999", "district": "Somewhere", "state": "Delhi"},
        headers=csrf(logged_in),
    )
    assert response.status_code == 200
    assert response.json()["address"]["post_office_confirmed"] is False
    codes = [item["code"] for item in response.json()["warnings"]]
    assert "unknown_pincode" in codes


def test_search_finds_farmer_scheme(client, seeded_catalogue):
    response = client.get("/api/v1/schemes", params={"query": "farmer income support"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] > 0
    slugs = [item["slug"] for item in body["items"]]
    assert "pm-kisan" in slugs
    item = next(item for item in body["items"] if item["slug"] == "pm-kisan")
    assert item["source_status"]["code"] in {"source_checked", "pending_review"}
    assert item["match"]["reason"] in {"full_text", "keyword"}


def test_search_filters_category_and_beneficiary(client, seeded_catalogue):
    education = client.get("/api/v1/schemes", params={"category": "Education"}).json()
    assert [item["slug"] for item in education["items"]] == ["post-matric-scholarship-sc"]
    students = client.get("/api/v1/schemes", params={"beneficiary": "student"}).json()
    assert "post-matric-scholarship-sc" in [item["slug"] for item in students["items"]]
    pensions = client.get("/api/v1/schemes", params={"category": "Pension"}).json()
    assert {"atal-pension-yojana", "nsap-old-age-pension"} <= {item["slug"] for item in pensions["items"]}


def test_language_filter_only_returns_available_translations(client, seeded_catalogue):
    response = client.get("/api/v1/schemes", params={"language": "hi"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    assert all(item["translation_available"] for item in body["items"])
    assert {item["slug"] for item in body["items"]} == {
        "pm-kisan",
        "post-matric-scholarship-sc",
        "mgnrega-job-card",
        "nsap-old-age-pension",
    }


def test_pagination_is_stable(client, seeded_catalogue):
    response = client.get("/api/v1/schemes", params={"page_size": 3, "sort": "name"}).json()
    assert len(response["items"]) == 3
    assert response["total"] == 8
    assert response["pages"] == 3
    assert [item["name"] for item in response["items"]] == sorted(
        item["name"] for item in response["items"]
    )


def test_search_injection_attempt_is_parameterised(client, seeded_catalogue):
    response = client.get("/api/v1/schemes", params={"query": "' OR 1=1; DROP TABLE schemes; --"})
    assert response.status_code == 200
    assert "schemes" in [item["slug"] for item in response.json()["items"]] or response.json()["total"] >= 0
    assert client.get("/api/v1/schemes").status_code == 200


def test_scheme_detail_evidence_flags(client, seeded_catalogue):
    detail = client.get("/api/v1/schemes/pm-kisan").json()
    assert detail["source"]["url"] == "https://pmkisan.gov.in/"
    assert detail["source"]["link_verified"] is False
    assert detail["application_link"]["verified"] is False
    assert detail["version"]["review_status"] == "pending_review"
    assert detail["translation_available"] is True
    assert client.get("/api/v1/schemes/no-such-scheme").status_code == 404


def test_document_checklist(client, seeded_catalogue):
    response = client.get("/api/v1/schemes/pm-kisan/checklist")
    assert response.status_code == 200
    body = response.json()
    assert body["documents"][0]["name"] == "Aadhaar card"
    assert body["scheme"]["version_no"] == 1


def test_eligibility_questions_and_profile_prefill(logged_in, seeded_catalogue, postal):
    profile = logged_in.put(
        "/api/v1/me/profile",
        json={
            "full_name": "Test Citizen",
            "date_of_birth": "1994-06-15",
            "preferred_language": "en",
        },
        headers=csrf(logged_in),
    )
    assert profile.status_code == 200, profile.text
    logged_in.put(
        "/api/v1/me/address",
        json={"pincode": "110001", "post_office": "New Delhi GPO"},
        headers=csrf(logged_in),
    )
    response = logged_in.get("/api/v1/schemes/pm-kisan/eligibility/questions")
    assert response.status_code == 200
    body = response.json()
    keys = {field["key"] for field in body["fields"]}
    assert {"age", "occupation", "landholding_acres", "is_income_tax_payer"} == keys
    today = date.today()
    expected_age = today.year - 1994 - ((today.month, today.day) < (6, 15))
    assert body["prefill"]["age"] == expected_age
    # Only fields this scheme actually needs may be suggested: this scheme has no
    # state rule, so the saved state must not be copied into the questionnaire.
    assert "state" not in body["prefill"]
    assert "_note" in body["prefill"]
    assert body["scheme"]["verified"] is False


def test_eligibility_outcomes(client, seeded_catalogue):
    eligible = client.post(
        "/api/v1/schemes/pm-kisan/eligibility/evaluate",
        json={
            "inputs": {
                "age": 34,
                "occupation": "farmer",
                "landholding_acres": 2.5,
                "is_income_tax_payer": False,
            }
        },
        headers=csrf(client),
    )
    assert eligible.status_code == 200
    assert eligible.json()["outcome"] == "eligible"

    not_eligible = client.post(
        "/api/v1/schemes/pm-kisan/eligibility/evaluate",
        json={
            "inputs": {
                "age": 34,
                "occupation": "farmer",
                "landholding_acres": 2.5,
                "is_income_tax_payer": True,
            }
        },
        headers=csrf(client),
    )
    assert not_eligible.json()["outcome"] == "not_eligible"

    insufficient = client.post(
        "/api/v1/schemes/pm-kisan/eligibility/evaluate",
        json={"inputs": {"age": 34}},
        headers=csrf(client),
    )
    assert insufficient.json()["outcome"] == "insufficient_information"

    cannot = client.post(
        "/api/v1/schemes/ayushman-bharat-pmjay/eligibility/evaluate",
        json={"inputs": {}},
        headers=csrf(client),
    )
    assert cannot.status_code == 200
    assert cannot.json()["outcome"] == "cannot_evaluate"


def test_eligibility_rejects_unrequested_fields_and_bad_values(client, seeded_catalogue):
    extra = client.post(
        "/api/v1/schemes/pm-kisan/eligibility/evaluate",
        json={"inputs": {"age": 30, "annual_income_inr": 500000}},
        headers=csrf(client),
    )
    assert extra.status_code == 422
    assert extra.json()["error"]["details"][0]["field"] == "annual_income_inr"

    invalid = client.post(
        "/api/v1/schemes/pm-kisan/eligibility/evaluate",
        json={"inputs": {"age": 30, "occupation": "astronaut"}},
        headers=csrf(client),
    )
    assert invalid.status_code == 422


def test_draft_requires_authentication(client, seeded_catalogue):
    response = client.post(
        "/api/v1/drafts", json={"scheme_slug": "pm-kisan"}, headers=csrf(client)
    )
    assert response.status_code == 401


def test_draft_does_not_reuse_profile_without_permission(logged_in, seeded_catalogue):
    created = logged_in.post(
        "/api/v1/drafts", json={"scheme_slug": "pm-kisan"}, headers=csrf(logged_in)
    )
    assert created.status_code == 201, created.text
    full_name = next(field for field in created.json()["fields"] if field["key"] == "full_name")
    # The citizen did not ask HVA to reuse stored personal data, so it must start empty.
    assert full_name["value"] is None
    assert full_name["source"] == "empty"


def test_draft_lifecycle_and_provenance(logged_in, seeded_catalogue):
    created = logged_in.post(
        "/api/v1/drafts",
        json={"scheme_slug": "pm-kisan", "reuse_profile": True},
        headers=csrf(logged_in),
    )
    assert created.status_code == 201, created.text
    draft = created.json()
    assert draft["scheme"]["slug"] == "pm-kisan"
    full_name = next(field for field in draft["fields"] if field["key"] == "full_name")
    assert full_name["source"] == "profile"
    assert full_name["value"] == "Test Citizen"
    assert full_name["user_confirmed"] is False
    assert draft["ready_to_export"] is False
    draft_id = draft["id"]

    updated = logged_in.patch(
        f"/api/v1/drafts/{draft_id}",
        json={
            "fields": [{"key": "full_name", "value": "Test Citizen", "confirmed": True}],
            "remove": ["phone"],
            "confirm": ["full_name"],
        },
        headers=csrf(logged_in),
    )
    assert updated.status_code == 200, updated.text
    fields = {field["key"]: field for field in updated.json()["fields"]}
    assert fields["full_name"]["user_confirmed"] is True
    assert fields["full_name"]["source"] == "user"
    assert fields["phone"]["value"] is None
    assert fields["phone"]["source"] == "empty"

    unconfirmed_export = logged_in.post(
        f"/api/v1/drafts/{draft_id}/export",
        json={"format": "text", "confirm": False},
        headers=csrf(logged_in),
    )
    assert unconfirmed_export.status_code == 422

    exported = logged_in.post(
        f"/api/v1/drafts/{draft_id}/export",
        json={"format": "text", "confirm": True},
        headers=csrf(logged_in),
    )
    assert exported.status_code == 200, exported.text
    assert exported.json()["submitted"] is False
    assert "not an official application" in exported.json()["disclaimer"]
    assert "Confirmed by you" in exported.json()["document"]
    assert exported.json()["draft"]["status"] == "exported"


def test_draft_ownership_is_enforced(db, seeded_catalogue, user):
    owner = TestClient(app)
    owner.get("/api/v1/auth/csrf")
    owner.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}, headers=csrf(owner)
    )
    created = owner.post(
        "/api/v1/drafts", json={"scheme_slug": "pm-kisan"}, headers=csrf(owner)
    )
    draft_id = created.json()["id"]

    other = create_user(db, email="other.person@hva-demo.com")
    client = TestClient(app)
    client.get("/api/v1/auth/csrf")
    client.post(
        "/api/v1/auth/login", json={"email": other.email, "password": PASSWORD}, headers=csrf(client)
    )
    assert client.get(f"/api/v1/drafts/{draft_id}").status_code == 404
    assert client.patch(
        f"/api/v1/drafts/{draft_id}",
        json={"fields": [], "remove": [], "confirm": []},
        headers=csrf(client),
    ).status_code == 404
    assert client.delete(f"/api/v1/drafts/{draft_id}", headers=csrf(client)).status_code == 404
    assert db.query(ApplicationDraft).filter(ApplicationDraft.id == draft_id).count() == 1
