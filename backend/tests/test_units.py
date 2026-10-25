"""Unit tests: pure functions, no database."""

from __future__ import annotations

import uuid
from datetime import date

import pyotp
import pytest

from app.core.errors import ApiError
from app.core.i18n import detect_language, extract_numbers, normalize_digits, normalize_query, t
from app.core.security import (
    decrypt_value,
    encrypt_value,
    generate_otp,
    hash_identifier,
    hash_otp,
    hash_password,
    hash_token,
    mask_phone,
    normalize_phone,
    validate_password_strength,
    verify_password,
    verify_totp,
)
from app.models import EligibilityRule, Scheme, SchemeVersion
from app.services import eligibility
from app.services.assistant import Evidence, LLMAnswer, _validate_llm_answer
from app.services.ingestion import FetchError, _assert_public_host, _validate_url
from app.services.search import build_search_text

# ------------------------------------------------------------------ passwords


def test_password_hash_roundtrip():
    hashed = hash_password("a-long-development-password")
    assert hashed.startswith("$argon2id$")
    assert verify_password("a-long-development-password", hashed)
    assert not verify_password("wrong-password", hashed)


@pytest.mark.parametrize(
    ("password", "code"),
    [
        ("short", "password_too_short"),
        ("password123", "password_too_common"),
        ("aaaaaaaaaaaaaaaa", "password_too_simple"),
    ],
)
def test_password_strength_rejections(password, code):
    with pytest.raises(ValueError) as excinfo:
        validate_password_strength(password)
    assert str(excinfo.value).split(":", 1)[0] == code


def test_password_cannot_contain_email():
    with pytest.raises(ValueError):
        validate_password_strength("citizen-name-password", email="citizen@hva-demo.com")


def test_password_strength_accepts_reasonable_password():
    validate_password_strength("monsoon-river-42", email="citizen@hva-demo.com")


# --------------------------------------------------------------------- tokens


def test_token_hashes_are_not_reversible():
    token = "session-token-value"
    assert hash_token(token) == hash_token(token)
    assert token not in hash_token(token)
    assert len(hash_token(token)) == 64


def test_identifier_hash_is_keyed_and_stable():
    assert hash_identifier("1.2.3.4") == hash_identifier("1.2.3.4")
    assert hash_identifier("1.2.3.4") != hash_identifier("1.2.3.5")
    assert len(hash_identifier("1.2.3.4")) == 64


# --------------------------------------------------------------------- phones


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("9876543210", "+919876543210"),
        ("+91 98765 43210", "+919876543210"),
        ("09876543210", "+919876543210"),
        ("98765-43210", "+919876543210"),
        ("1234567890", None),
        ("abcdefghij", None),
        ("", None),
    ],
)
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


def test_mask_phone_keeps_last_two_digits():
    assert mask_phone("+919876543210") == "+91********10"
    assert mask_phone(None) is None


# ------------------------------------------------------------------------ OTP


def test_otp_hash_is_purpose_scoped():
    code = generate_otp()
    assert len(code) == 6 and code.isdigit()
    assert hash_otp(code, purpose="profile_phone") == hash_otp(code, purpose="profile_phone")
    assert hash_otp(code, purpose="profile_phone") != hash_otp(code, purpose="other")


def test_totp_verification():
    secret = pyotp.random_base32()
    code = pyotp.TOTP(secret).now()
    assert verify_totp(secret, code)
    assert not verify_totp(secret, "000000")
    assert not verify_totp(secret, "12345")


# ------------------------------------------------------------------ encryption


def test_encryption_roundtrip_and_random_ciphertext():
    first = encrypt_value("1994-06-15")
    second = encrypt_value("1994-06-15")
    assert first != second
    assert decrypt_value(first) == "1994-06-15"


# ------------------------------------------------------------------- language


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("मुझे किसान योजना चाहिए", "hi"),
        ("விவசாயி திட்டம் என்ன", "ta"),
        ("I need a farmer scheme", "en"),
        ("12345", "en"),
    ],
)
def test_language_detection(text, language):
    detected, method = detect_language(text)
    assert detected == language
    assert method in {"unicode_script", "default_latin"}


def test_digit_normalisation_and_number_extraction():
    assert normalize_digits("६०००") == "6000"
    assert extract_numbers("₹6,000 and ६०००") == {"6000"}


def test_query_expansion_cross_language():
    assert "farmer" in normalize_query("किसान")
    assert "scholarship" in normalize_query("scholership")
    assert "pension" in normalize_query("पेंशन")
    assert normalize_query("   ") == ""
    # Generic scheme vocabulary must not turn an unrelated question into a catalogue match.
    generic = normalize_query("बालिका बचत योजना")
    assert "scheme" not in generic and "योजना" not in generic
    assert "girl" in generic
    assert normalize_query("योजना") == ""
    assert normalize_query("sarkari yojana") == ""


def test_translation_catalog_has_core_strings():
    for language in ("en", "hi", "ta"):
        assert t(language, "no_match")
        assert t(language, "uncertainty")
        assert t(language, "benefit")


# ----------------------------------------------------------------- eligibility


def _version(rules: list[EligibilityRule], *, review_status: str = "verified") -> SchemeVersion:
    scheme = Scheme(
        id=uuid.uuid4(),
        slug="test-scheme",
        official_name="Test Scheme",
        department="Test Department",
        scope="central",
        category="Test",
        beneficiary_groups=[],
        official_url="https://example.gov.in/",
        is_published=True,
    )
    version = SchemeVersion(
        id=uuid.uuid4(),
        scheme=scheme,
        version_no=1,
        benefit_summary="Benefit",
        eligibility_summary="Criteria",
        application_url="https://example.gov.in/",
        review_status=review_status,
        search_text="",
    )
    version.rules = rules
    return version


def _rule(key: str, field: str, operator: str, value, status: str = "valid") -> EligibilityRule:
    return EligibilityRule(
        id=uuid.uuid4(),
        scheme_version_id=uuid.uuid4(),
        rule_key=key,
        field=field,
        operator=operator,
        value=value,
        description=f"{field} {operator}",
        validation_status=status,
    )


def test_eligibility_eligible():
    version = _version([_rule("age", "age", "gte", 18), _rule("state", "state", "in", ["Delhi"])])
    result = eligibility.evaluate(version, {"age": 30, "state": "Delhi"})
    assert result["outcome"] == eligibility.OUTCOME_ELIGIBLE
    assert all(rule["status"] == "met" for rule in result["rules"])


def test_eligibility_not_eligible():
    version = _version([_rule("age", "age", "gte", 18)])
    result = eligibility.evaluate(version, {"age": 15})
    assert result["outcome"] == eligibility.OUTCOME_NOT_ELIGIBLE
    assert result["reasons"][0]["code"] == "criterion_not_met"


def test_eligibility_insufficient_information():
    version = _version([_rule("age", "age", "gte", 18), _rule("income", "annual_income_inr", "lte", 100000)])
    result = eligibility.evaluate(version, {"age": 30})
    assert result["outcome"] == eligibility.OUTCOME_INSUFFICIENT
    assert [item["key"] for item in result["missing_fields"]] == ["annual_income_inr"]


def test_eligibility_cannot_evaluate_for_unsupported_rule():
    version = _version([_rule("secc", "is_bpl", "requires_entitlement_list", True, status="unsupported")])
    result = eligibility.evaluate(version, {})
    assert result["outcome"] == eligibility.OUTCOME_CANNOT
    assert result["reasons"][0]["code"] == "rule_not_validated"


def test_eligibility_rejects_unrelated_personal_fields():
    version = _version([_rule("age", "age", "gte", 18)])
    with pytest.raises(ApiError) as excinfo:
        eligibility.evaluate(version, {"age": 30, "annual_income_inr": 200000})
    assert excinfo.value.status_code == 422


def test_eligibility_validates_choice_and_range():
    version = _version([_rule("state", "state", "in", ["Delhi"])])
    with pytest.raises(ApiError):
        eligibility.evaluate(version, {"state": "Atlantis"})
    age_version = _version([_rule("age", "age", "lte", 120)])
    with pytest.raises(ApiError):
        eligibility.evaluate(age_version, {"age": 500})


def test_build_questions_localises_labels_and_excludes_unsupported():
    version = _version([_rule("age", "age", "gte", 18)])
    questions = eligibility.build_questions(version, "hi")
    assert questions["fields"][0]["key"] == "age"
    assert questions["fields"][0]["label"] == "आयु"
    unsupported = _version([_rule("secc", "is_bpl", "requires_entitlement_list", True, status="unsupported")])
    assert eligibility.build_questions(unsupported, "en")["fields"] == []


def test_eligibility_does_not_use_model_output():
    # The module exposes no provider hook at all; evaluation is a pure function.
    assert not hasattr(eligibility, "llm")
    assert not hasattr(eligibility, "provider")


# --------------------------------------------------------------------- search


def test_search_text_includes_translations_and_documents():
    from app.models import SchemeTranslation

    version = _version([_rule("age", "age", "gte", 18)])
    version.required_documents = [{"key": "aadhaar", "name": "Aadhaar card"}]
    version.application_steps = ["Apply online"]
    version.translations = [
        SchemeTranslation(
            id=uuid.uuid4(),
            scheme_version_id=uuid.uuid4(),
            language="hi",
            benefit_summary="लाभ",
            eligibility_summary="पात्रता",
            required_documents=[],
            application_steps=[],
            review_status="draft",
        )
    ]
    text = build_search_text(version.scheme, version)
    assert "Aadhaar card" in text
    assert "लाभ" in text
    assert "Apply online" in text


# -------------------------------------------------------------------- URL rules


def test_source_url_requires_https_and_allowlist():
    with pytest.raises(FetchError):
        _validate_url("http://pmkisan.gov.in/")
    with pytest.raises(FetchError):
        _validate_url("https://evil.example.com/")
    with pytest.raises(FetchError):
        _validate_url("https://pmkisan.gov.in@evil.example.com/")
    with pytest.raises(FetchError):
        _validate_url("https://pmkisan.gov.in:8443/")
    with pytest.raises(FetchError):
        _validate_url("https://127.0.0.1/")
    normalized, host = _validate_url("https://pmkisan.gov.in/scheme?x=1#fragment")
    assert host == "pmkisan.gov.in"
    assert normalized == "https://pmkisan.gov.in/scheme?x=1"


def test_private_addresses_are_rejected():
    with pytest.raises(FetchError):
        _assert_public_host("127.0.0.1")
    with pytest.raises(FetchError):
        _assert_public_host("localhost")


# ------------------------------------------------------- assistant grounding


def _evidence() -> list[Evidence]:
    detail = {
        "department": "Ministry",
        "scope": "central",
        "state": None,
        "deadline": None,
        "official_url": "https://pmkisan.gov.in/",
        "application_url": "https://pmkisan.gov.in/",
        "version": {"review_status": "verified", "verified": True, "retrieved_at": None},
        "source": {"url": "https://pmkisan.gov.in/"},
        "translation_available": True,
    }
    return [
        Evidence(
            slug="pm-kisan",
            name="PM-KISAN",
            detail=detail,
            documents=["Aadhaar card"],
            steps=["Apply online"],
            benefit="Income support of ₹6,000 per year.",
            eligibility_text="Landholding farmer families.",
            translation=True,
        )
    ]


def test_grounding_accepts_evidence_backed_answer():
    answer = LLMAnswer(answer="PM-KISAN provides 6000 per year. Aadhaar card is required.", citations=["pm-kisan"])
    assert _validate_llm_answer(answer, _evidence()) == []


def test_grounding_rejects_unknown_citation_and_number():
    evidence = _evidence()
    unknown = LLMAnswer(answer="PM-KISAN provides 6000.", citations=["other-scheme"])
    assert "unknown_citation" in _validate_llm_answer(unknown, evidence)
    invented = LLMAnswer(answer="PM-KISAN provides 99999 per year.", citations=["pm-kisan"])
    assert any(item.startswith("unsupported_number") for item in _validate_llm_answer(invented, evidence))


def test_grounding_rejects_invented_url_and_missing_scheme_name():
    evidence = _evidence()
    url = LLMAnswer(answer="PM-KISAN pays 6000. See https://fake-scheme.example/", citations=["pm-kisan"])
    assert "unsupported_url" in _validate_llm_answer(url, evidence)
    unnamed = LLMAnswer(answer="A scheme pays 6000 per year.", citations=["pm-kisan"])
    assert "scheme_not_named" in _validate_llm_answer(unnamed, evidence)


def test_eligibility_language_fallback():
    version = _version([_rule("age", "age", "gte", 18)])
    result = eligibility.evaluate(version, {"age": 20}, language="xx")  # type: ignore[arg-type]
    assert result["language"] == "en"


def test_rule_effective_window():
    rule = _rule("age", "age", "gte", 18)
    rule.effective_to = date(2000, 1, 1)
    version = _version([rule])
    result = eligibility.evaluate(version, {"age": 20})
    assert result["rules"][0]["status"] == "not_applicable"
    assert result["outcome"] == eligibility.OUTCOME_ELIGIBLE
