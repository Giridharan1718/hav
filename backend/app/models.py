"""ORM models.

Conventions: UUID primary keys, timestamptz audit columns, explicit foreign keys,
named indexes. Private user data stays in user-scoped tables; public scheme content
lives in scheme tables. Sensitive values use EncryptedText/EncryptedDate.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, EncryptedDate, EncryptedText


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _enum(name: str, values: list[str]) -> SAEnum:
    return SAEnum(
        *values,
        name=name,
        native_enum=False,
        length=32,
        create_constraint=True,
        validate_strings=True,
    )


class Role(str, enum.Enum):
    citizen = "citizen"
    reviewer = "reviewer"
    admin = "admin"


class AuthLevel(str, enum.Enum):
    password = "password"
    mfa = "mfa"


class ReviewStatus(str, enum.Enum):
    draft = "draft"
    pending_review = "pending_review"
    source_checked = "source_checked"
    verified = "verified"
    rejected = "rejected"
    superseded = "superseded"


class RuleValidationStatus(str, enum.Enum):
    valid = "valid"
    unverified = "unverified"
    unsupported = "unsupported"


class Scope(str, enum.Enum):
    central = "central"
    state = "state"
    ut = "ut"


class DraftStatus(str, enum.Enum):
    draft = "draft"
    exported = "exported"
    deleted = "deleted"


class DraftFieldSource(str, enum.Enum):
    empty = "empty"
    profile = "profile"
    user = "user"
    assistant = "assistant"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class DeletionStatus(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


class ConsentPurpose(str, enum.Enum):
    required_account = "required_account"
    ai_assistant = "ai_assistant"
    analytics = "analytics"
    voice_processing = "voice_processing"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(_enum("user_role", [r.value for r in Role]), default=Role.citizen.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret_enc: Mapped[str | None] = mapped_column(EncryptedText)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    profile: Mapped[Profile | None] = relationship(
        back_populates="user", uselist=False, passive_deletes=True
    )
    address: Mapped[Address | None] = relationship(
        back_populates="user", uselist=False, passive_deletes=True
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    auth_level: Mapped[str] = mapped_column(_enum("auth_level", ["password", "mfa"]), default="password")
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()


Index("ix_sessions_user_id", Session.user_id)


class PhoneVerification(Base):
    __tablename__ = "phone_verifications"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    phone: Mapped[str] = mapped_column(String(16), nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), default="profile_phone", nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_phone_verifications_user_purpose", "user_id", "purpose"),)


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Index("ix_password_resets_user_id", PasswordReset.user_id)


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(EncryptedDate)
    preferred_language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    phone: Mapped[str | None] = mapped_column(String(16))
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gender: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="profile")


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    line1: Mapped[str | None] = mapped_column(String(200))
    pincode: Mapped[str] = mapped_column(String(6), nullable=False)
    post_office: Mapped[str | None] = mapped_column(String(150))
    district: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(120))
    post_office_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="address")

    __table_args__ = (
        CheckConstraint("pincode ~ '^[1-9][0-9]{5}$'", name="ck_addresses_pincode"),
    )


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    purpose: Mapped[str] = mapped_column(
        _enum("consent_purpose", [p.value for p in ConsentPurpose]), nullable=False
    )
    granted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    document_version: Mapped[str] = mapped_column(String(20), nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "purpose", name="uq_consents_user_purpose"),
        Index("ix_consents_user_id", "user_id"),
    )


class Scheme(Base):
    __tablename__ = "schemes"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    official_name: Mapped[str] = mapped_column(String(300), nullable=False)
    department: Mapped[str] = mapped_column(String(300), nullable=False)
    scope: Mapped[str] = mapped_column(_enum("scheme_scope", [s.value for s in Scope]), nullable=False)
    state_name: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    beneficiary_groups: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb"), nullable=False
    )
    official_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scheme_versions.id", ondelete="SET NULL", use_alter=True)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    versions: Mapped[list[SchemeVersion]] = relationship(
        back_populates="scheme", foreign_keys="SchemeVersion.scheme_id"
    )
    current_version: Mapped[SchemeVersion | None] = relationship(foreign_keys=[current_version_id], post_update=True)


Index("ix_schemes_scope_state", Scheme.scope, Scheme.state_name)


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(String(300))
    publisher: Mapped[str | None] = mapped_column(String(200))
    source_type: Mapped[str] = mapped_column(String(40), default="official_page", nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    byte_size: Mapped[int | None] = mapped_column(Integer)
    policy_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_source_documents_host", "host"),)


class SchemeVersion(Base):
    __tablename__ = "scheme_versions"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    benefit_summary: Mapped[str] = mapped_column(Text, nullable=False)
    eligibility_summary: Mapped[str] = mapped_column(Text, nullable=False)
    required_documents: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb"), nullable=False
    )
    application_steps: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb"), nullable=False
    )
    application_url: Mapped[str] = mapped_column(Text, nullable=False)
    application_mode: Mapped[str | None] = mapped_column(String(160))
    application_url_http_status: Mapped[int | None] = mapped_column(Integer)
    application_url_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline: Mapped[date | None] = mapped_column(Date)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_documents.id", ondelete="SET NULL")
    )
    source_published_at: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    review_status: Mapped[str] = mapped_column(
        _enum("review_status", [s.value for s in ReviewStatus]), default=ReviewStatus.draft.value, nullable=False
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    review_notes: Mapped[str | None] = mapped_column(Text)
    search_text: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', coalesce(search_text, ''))", persisted=True),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    scheme: Mapped[Scheme] = relationship(back_populates="versions", foreign_keys=[scheme_id])
    translations: Mapped[list[SchemeTranslation]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )
    rules: Mapped[list[EligibilityRule]] = relationship(back_populates="version", cascade="all, delete-orphan")
    source_document: Mapped[SourceDocument | None] = relationship()

    __table_args__ = (
        UniqueConstraint("scheme_id", "version_no", name="uq_scheme_versions_scheme_version"),
        CheckConstraint("version_no > 0", name="ck_scheme_versions_version_no"),
        Index("ix_scheme_versions_scheme_id", "scheme_id"),
        Index("ix_scheme_versions_review_status", "review_status"),
        Index("ix_scheme_versions_search_vector", "search_vector", postgresql_using="gin"),
    )


class SchemeTranslation(Base):
    __tablename__ = "scheme_translations"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    scheme_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_versions.id", ondelete="CASCADE"), nullable=False
    )
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    benefit_summary: Mapped[str] = mapped_column(Text, nullable=False)
    eligibility_summary: Mapped[str] = mapped_column(Text, nullable=False)
    required_documents: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb"), nullable=False
    )
    application_steps: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb"), nullable=False
    )
    review_status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    translator: Mapped[str | None] = mapped_column(String(120))
    translated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    version: Mapped[SchemeVersion] = relationship(back_populates="translations")

    __table_args__ = (
        UniqueConstraint("scheme_version_id", "language", name="uq_scheme_translations_version_language"),
    )


class EligibilityRule(Base):
    __tablename__ = "eligibility_rules"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    scheme_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_versions.id", ondelete="CASCADE"), nullable=False
    )
    rule_key: Mapped[str] = mapped_column(String(80), nullable=False)
    field: Mapped[str] = mapped_column(String(60), nullable=False)
    operator: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    validation_status: Mapped[str] = mapped_column(
        _enum("rule_validation_status", [s.value for s in RuleValidationStatus]),
        default=RuleValidationStatus.valid.value,
        nullable=False,
    )
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)

    version: Mapped[SchemeVersion] = relationship(back_populates="rules")

    __table_args__ = (
        UniqueConstraint("scheme_version_id", "rule_key", name="uq_eligibility_rules_version_key"),
    )


class SearchHistory(Base):
    __tablename__ = "search_history"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    query: Mapped[str] = mapped_column(String(300), nullable=False)
    language: Mapped[str | None] = mapped_column(String(8))
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_search_history_created_at", "created_at"),)


class ApplicationDraft(Base):
    __tablename__ = "application_drafts"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    scheme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False)
    scheme_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_versions.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(_enum("draft_status", [s.value for s in DraftStatus]), default="draft")
    last_exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    fields: Mapped[list[DraftField]] = relationship(
        back_populates="draft", cascade="all, delete-orphan", order_by="DraftField.position"
    )
    scheme: Mapped[Scheme] = relationship(foreign_keys=[scheme_id])
    scheme_version: Mapped[SchemeVersion] = relationship(foreign_keys=[scheme_version_id])

    __table_args__ = (Index("ix_application_drafts_user_id", "user_id"),)


class DraftField(Base):
    __tablename__ = "draft_fields"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    draft_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("application_drafts.id", ondelete="CASCADE"), nullable=False
    )
    field_key: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    help_text: Mapped[str | None] = mapped_column(Text)
    value: Mapped[str | None] = mapped_column(Text)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(
        _enum("draft_field_source", [s.value for s in DraftFieldSource]), default="empty", nullable=False
    )
    source_reference: Mapped[str | None] = mapped_column(String(200))
    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    draft: Mapped[ApplicationDraft] = relationship(back_populates="fields")

    __table_args__ = (
        UniqueConstraint("draft_id", "field_key", name="uq_draft_fields_draft_key"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_role: Mapped[str | None] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(20), default="success", nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_audit_events_actor_created", "actor_user_id", "created_at"),
        Index("ix_audit_events_action_created", "action", "created_at"),
    )


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    status: Mapped[str] = mapped_column(_enum("job_status", [s.value for s in JobStatus]), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_background_jobs_status_created", "status", "created_at"),)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    url: Mapped[str] = mapped_column(Text, nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    byte_size: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_documents.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeletionRequest(Base):
    __tablename__ = "deletion_requests"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    execute_after: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        _enum("deletion_status", [s.value for s in DeletionStatus]), default="scheduled", nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_deletion_requests_user_id", "user_id"),)


class PostalDataset(Base):
    __tablename__ = "postal_dataset"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    licence_note: Mapped[str | None] = mapped_column(Text)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PostalOffice(Base):
    __tablename__ = "postal_offices"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    pincode: Mapped[str] = mapped_column(String(6), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    branch_type: Mapped[str | None] = mapped_column(String(40))
    district: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(120), nullable=False)
    delivery_status: Mapped[str | None] = mapped_column(String(30))
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("postal_dataset.id", ondelete="SET NULL"))

    __table_args__ = (
        UniqueConstraint("pincode", "name", "district", name="uq_postal_offices_identity"),
        CheckConstraint("pincode ~ '^[1-9][0-9]{5}$'", name="ck_postal_offices_pincode"),
        Index("ix_postal_offices_pincode", "pincode"),
    )


class PostalLookupCache(Base):
    __tablename__ = "postal_lookup_cache"

    pincode: Mapped[str] = mapped_column(String(6), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String(60), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
