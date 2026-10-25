"""Typed request and response contracts for the versioned API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from app.core.i18n import SUPPORTED_LANGUAGES

Language = Literal["en", "hi", "ta"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ErrorDetail(BaseModel):
    field: str | None = None
    issue: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | list[dict[str, Any]] | None = None
    request_id: str | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody


# --------------------------------------------------------------------------- auth


class RegisterRequest(Strict):
    email: EmailStr
    password: SecretStr = Field(min_length=10, max_length=200)
    full_name: str = Field(min_length=2, max_length=200)
    preferred_language: Language = "en"
    accept_privacy_notice: bool
    consent_ai_assistant: bool = False
    consent_analytics: bool = False
    consent_voice_processing: bool = False

    @field_validator("full_name")
    @classmethod
    def _name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if sum(char.isalpha() for char in cleaned) < 2:
            raise ValueError("Enter your name using letters.")
        if any(ord(char) < 32 for char in cleaned):
            raise ValueError("Name contains unsupported characters.")
        return cleaned

    @model_validator(mode="after")
    def _privacy(self) -> RegisterRequest:
        if not self.accept_privacy_notice:
            raise ValueError("The privacy notice must be accepted to create an account.")
        return self


class LoginRequest(Strict):
    # Plain string: login must not reject an existing stored account because a
    # stricter address validator was introduced later.
    email: str = Field(min_length=3, max_length=320)
    password: SecretStr = Field(min_length=1, max_length=200)


class MfaVerifyRequest(Strict):
    mfa_token: str = Field(min_length=10, max_length=200)
    code: str = Field(pattern=r"^\d{6}$")


class MfaCodeRequest(Strict):
    code: str = Field(pattern=r"^\d{6}$")


class ReauthRequest(Strict):
    password: SecretStr = Field(min_length=1, max_length=200)


class ChangePasswordRequest(Strict):
    current_password: SecretStr = Field(min_length=1, max_length=200)
    new_password: SecretStr = Field(min_length=10, max_length=200)


class PasswordResetRequest(Strict):
    email: str = Field(min_length=3, max_length=320)


class PasswordResetConfirm(Strict):
    token: str = Field(min_length=10, max_length=200)
    new_password: SecretStr = Field(min_length=10, max_length=200)


class PhoneChallengeRequest(Strict):
    phone: str = Field(min_length=6, max_length=20)


class PhoneVerifyRequest(Strict):
    code: str = Field(pattern=r"^\d{6}$")


class SessionOut(BaseModel):
    id: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    auth_level: str
    current: bool = False


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    mfa_enabled: bool
    created_at: datetime


class ProfileOut(BaseModel):
    full_name: str
    date_of_birth: date | None = None
    preferred_language: str
    phone: str | None = None
    phone_masked: str | None = None
    phone_verified: bool = False
    gender: str | None = None
    updated_at: datetime | None = None


class AddressOut(BaseModel):
    line1: str | None = None
    pincode: str
    post_office: str | None = None
    district: str | None = None
    state: str | None = None
    post_office_confirmed: bool = False


class ConsentOut(BaseModel):
    purpose: str
    granted: bool
    document_version: str
    granted_at: datetime | None = None
    withdrawn_at: datetime | None = None


class MeOut(BaseModel):
    user: UserOut
    profile: ProfileOut | None = None
    address: AddressOut | None = None
    consents: list[ConsentOut] = []
    permissions: dict[str, bool] = {}


class LoginOut(BaseModel):
    status: str
    mfa_required: bool = False
    mfa_token: str | None = None
    user: UserOut | None = None


# ------------------------------------------------------------------------ profile


class ProfileUpdate(Strict):
    full_name: str = Field(min_length=2, max_length=200)
    date_of_birth: date | None = None
    preferred_language: Language = "en"
    phone: str | None = Field(default=None, max_length=20)
    gender: Literal["female", "male", "other", "prefer_not_to_say"] | None = None

    @field_validator("full_name")
    @classmethod
    def _name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if sum(char.isalpha() for char in cleaned) < 2:
            raise ValueError("Enter your name using letters.")
        return cleaned

    @field_validator("date_of_birth")
    @classmethod
    def _dob(cls, value: date | None) -> date | None:
        if value is None:
            return None
        if value > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        if value.year < 1900:
            raise ValueError("Date of birth is out of range.")
        age = date.today().year - value.year - ((date.today().month, date.today().day) < (value.month, value.day))
        if age > 120:
            raise ValueError("Date of birth is out of range.")
        return value


class AddressUpdate(Strict):
    line1: str | None = Field(default=None, max_length=200)
    pincode: str = Field(pattern=r"^[1-9][0-9]{5}$")
    post_office: str | None = Field(default=None, max_length=150)
    district: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    post_office_confirmed: bool = False


class ConsentUpdate(Strict):
    granted: bool


# ------------------------------------------------------------------------ schemes


class SearchMatch(BaseModel):
    terms: list[str] = []
    reason: str


class SourceStatus(BaseModel):
    code: str
    label: str
    verified: bool


class SchemeCard(BaseModel):
    slug: str
    name: str
    department: str
    scope: str
    state: str | None = None
    category: str
    beneficiary_groups: list[str] = []
    summary: str
    summary_language: str
    translation_available: bool
    available_languages: list[str] = []
    official_url: str
    source_status: SourceStatus
    version_no: int
    verified_at: str | None = None
    retrieved_at: str | None = None
    deadline: str | None = None
    match: SearchMatch


class SchemeSearchOut(BaseModel):
    model_config = ConfigDict(extra="allow")
    items: list[SchemeCard]
    page: int
    page_size: int
    total: int
    pages: int
    query: str
    normalized_query: str
    language: str
    language_detected: tuple[str, str] | None = None
    sort: str
    filters: dict[str, str | None]
    disclaimer: str


class RuleOut(BaseModel):
    rule_key: str
    field: str
    description: str
    source_reference: str | None = None
    validation_status: str | None = None


class SchemeDetailOut(BaseModel):
    slug: str
    name: str
    department: str
    scope: str
    state: str | None = None
    category: str
    beneficiary_groups: list[str] = []
    official_url: str
    application_url: str
    application_mode: str | None = None
    deadline: str | None = None
    benefit_summary: str
    eligibility_summary: str
    documents: list[dict[str, Any]] | list[str] = []
    application_steps: list[str] = []
    language: str
    requested_language: str
    translation_available: bool
    available_languages: list[str] = []
    version: dict[str, Any]
    application_link: dict[str, Any]
    source: dict[str, Any]
    eligibility: dict[str, Any]
    disclaimer: str


class FieldOut(BaseModel):
    key: str
    type: str
    label: str
    purpose: str
    choices: list[str] | None = None
    minimum: float | None = None
    maximum: float | None = None
    sensitive: bool = False


class QuestionsOut(BaseModel):
    scheme: dict[str, Any]
    fields: list[FieldOut]
    rules: list[RuleOut]
    prefill: dict[str, Any] = {}
    disclaimer: str


class EligibilityRequest(Strict):
    inputs: dict[str, Any] = Field(default_factory=dict)
    language: Language | None = None


class EligibilityOut(BaseModel):
    outcome: str
    scheme: dict[str, Any]
    rules: list[dict[str, Any]]
    missing_fields: list[FieldOut] = []
    reasons: list[dict[str, Any]] = []
    disclaimer: str
    evaluated_at: str
    language: str


# --------------------------------------------------------------------- assistant


class AssistantRequest(Strict):
    message: str = Field(min_length=1, max_length=1000)
    language: Language | None = None
    scheme_slug: str | None = Field(default=None, max_length=120)
    eligibility_inputs: dict[str, Any] | None = None


class AssistantOut(BaseModel):
    answer: str
    language: str
    detected_language: str
    detection_method: str
    provider: str
    fallback_used: bool
    notices: list[dict[str, str]] = []
    citations: list[dict[str, Any]] = []
    schemes: list[dict[str, Any]] = []
    missing_information: list[str] = []
    eligibility: dict[str, Any] | None = None
    disclaimer: str


class TranscriptionRequest(Strict):
    audio_base64: str = Field(min_length=16, max_length=8_000_000)
    language: Language | None = None
    consent_voice_processing: bool


# ------------------------------------------------------------------------- drafts


class DraftCreate(Strict):
    scheme_slug: str = Field(min_length=2, max_length=120)
    language: Language = "en"
    # Profile reuse is opt-in per draft: stored personal data is read only when the
    # citizen explicitly asks for it in the draft-preparation dialog.
    reuse_profile: bool = False


class DraftFieldUpdate(Strict):
    key: str = Field(min_length=1, max_length=80)
    value: str | None = Field(default=None, max_length=500)
    confirmed: bool = False


class DraftUpdate(Strict):
    fields: list[DraftFieldUpdate] = Field(default_factory=list, max_length=60)
    remove: list[str] = Field(default_factory=list, max_length=60)
    confirm: list[str] = Field(default_factory=list, max_length=60)


class DraftExportRequest(Strict):
    format: Literal["json", "text"] = "json"
    confirm: bool
    language: Language = "en"

    @model_validator(mode="after")
    def _confirm(self) -> DraftExportRequest:
        if not self.confirm:
            raise ValueError("Export requires explicit confirmation.")
        return self


class DraftOut(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    scheme: dict[str, Any]
    scheme_slug: str | None
    status: str
    fields: list[dict[str, Any]]
    missing_required: list[str]
    unconfirmed: list[str]
    ready_to_export: bool
    created_at: str
    updated_at: str
    last_exported_at: str | None = None
    language: str
    disclaimer: str


class DraftExportOut(BaseModel):
    format: str
    document: Any
    submitted: bool
    disclaimer: str
    draft: DraftOut


# ------------------------------------------------------------------------ privacy


class DeletionRequestIn(Strict):
    password: SecretStr = Field(min_length=1, max_length=200)
    confirmation: Literal["DELETE"]


# -------------------------------------------------------------------------- admin


class ReviewDecision(Strict):
    decision: Literal["approve", "reject"]
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _notes(self) -> ReviewDecision:
        if self.decision == "reject" and (not self.notes or len(self.notes.strip()) < 5):
            raise ValueError("A rejection needs a short reason.")
        return self


class IngestionRequest(Strict):
    url: str = Field(min_length=10, max_length=2000)


class HealthOut(BaseModel):
    status: str
    environment: str
    database: str
    features: dict[str, Any]
    languages: list[str]
    time: datetime


def normalise_language(value: str | None, default: str = "en") -> str:
    if value in SUPPORTED_LANGUAGES:
        return value
    return default
