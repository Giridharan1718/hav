"""Private application-preparation drafts.

Every proposed value records where it came from (profile, user edit, assistant
suggestion or empty) and whether the citizen confirmed it. Nothing is ever submitted
externally; export produces a document the citizen can review and carry themselves.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.core.i18n import SUPPORTED_LANGUAGES
from app.models import Address, ApplicationDraft, DraftField, Profile, Scheme, SchemeVersion, User
from app.services import eligibility, search

EXPORT_DISCLAIMER = (
    "This document was prepared by HVA, an independent assistance platform. It is a draft, "
    "not an official application. No application has been submitted. Verify every field and "
    "attach the required documents on the official portal."
)

CORE_FIELDS: list[dict[str, str]] = [
    {"key": "full_name", "label": "Full name", "help": "As it appears on your identity document."},
    {"key": "date_of_birth", "label": "Date of birth", "help": "Some schemes require age verification."},
    {"key": "phone", "label": "Phone number", "help": "Used by the department to contact you."},
    {"key": "address", "label": "Address", "help": "Complete postal address including PIN code."},
]

PROFILE_SOURCES = {
    "full_name": "profiles.full_name",
    "date_of_birth": "profiles.date_of_birth",
    "phone": "profiles.phone",
    "state": "addresses.state",
    "district": "addresses.district",
    "pincode": "addresses.pincode",
    "post_office": "addresses.post_office",
}


def _profile_values(db: Session, user_id) -> dict[str, str]:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    address = db.scalar(select(Address).where(Address.user_id == user_id))
    values: dict[str, str] = {}
    if profile:
        values["full_name"] = profile.full_name
        if profile.date_of_birth:
            values["date_of_birth"] = profile.date_of_birth.isoformat()
        if profile.phone:
            values["phone"] = profile.phone
    if address:
        values["state"] = address.state or ""
        values["district"] = address.district or ""
        values["pincode"] = address.pincode
        values["post_office"] = address.post_office or ""
        parts = [part for part in (address.line1, address.post_office, address.district, address.state, address.pincode) if part]
        values["address"] = ", ".join(parts)
    return {key: value for key, value in values.items() if value}


def _build_field_rows(
    db: Session, user_id, version: SchemeVersion, *, reuse_profile: bool
) -> list[DraftField]:
    # Stored personal data is only read when the citizen opted in for this draft.
    profile_values = _profile_values(db, user_id) if reuse_profile else {}
    rows: list[DraftField] = []
    position = 0
    for item in CORE_FIELDS:
        value = profile_values.get(item["key"])
        rows.append(
            DraftField(
                field_key=item["key"],
                label=item["label"],
                help_text=item["help"],
                value=value,
                required=True,
                source="profile" if value else "empty",
                source_reference=PROFILE_SOURCES.get(item["key"]) if value else None,
                user_confirmed=False,
                position=position,
            )
        )
        position += 1
    seen = {row.field_key for row in rows}
    for rule in sorted(version.rules, key=lambda item: item.rule_key):
        if rule.field in seen or rule.field not in eligibility.FIELD_SPECS:
            continue
        seen.add(rule.field)
        spec = eligibility.FIELD_SPECS[rule.field]
        value = profile_values.get(rule.field)
        rows.append(
            DraftField(
                field_key=rule.field,
                label=spec.label["en"],
                help_text=f"{rule.description} ({spec.purpose['en']})",
                value=value,
                required=rule.validation_status == "valid",
                source="profile" if value else "empty",
                source_reference=PROFILE_SOURCES.get(rule.field) if value else None,
                user_confirmed=False,
                position=position,
            )
        )
        position += 1
    return rows


def serialize(draft: ApplicationDraft, *, language: str = "en") -> dict[str, Any]:
    fields = []
    for item in sorted(draft.fields, key=lambda row: row.position):
        fields.append(
            {
                "key": item.field_key,
                "label": item.label,
                "help_text": item.help_text,
                "value": item.value,
                "required": item.required,
                "source": item.source,
                "source_reference": item.source_reference,
                "user_confirmed": item.user_confirmed,
                "status": "confirmed" if item.user_confirmed else ("proposed" if item.value else "missing"),
            }
        )
    missing_required = [item["key"] for item in fields if item["required"] and not item["value"]]
    unconfirmed = [item["key"] for item in fields if item["value"] and not item["user_confirmed"]]
    return {
        "id": str(draft.id),
        "scheme": {
            "slug": draft.scheme.slug if draft.scheme else None,
            "title": draft.title,
            "version_no": draft.scheme_version.version_no if draft.scheme_version else None,
        },
        "scheme_slug": draft.scheme.slug if draft.scheme else None,
        "status": draft.status,
        "fields": fields,
        "missing_required": missing_required,
        "unconfirmed": unconfirmed,
        "ready_to_export": not missing_required and not unconfirmed,
        "created_at": draft.created_at.isoformat(),
        "updated_at": draft.updated_at.isoformat(),
        "last_exported_at": draft.last_exported_at.isoformat() if draft.last_exported_at else None,
        "language": language,
        "disclaimer": EXPORT_DISCLAIMER,
    }


def _load_owned(db: Session, draft_id, user_id) -> ApplicationDraft:
    draft = db.scalar(
        select(ApplicationDraft)
        .options(
            selectinload(ApplicationDraft.fields),
            selectinload(ApplicationDraft.scheme),
            selectinload(ApplicationDraft.scheme_version),
        )
        .where(ApplicationDraft.id == draft_id, ApplicationDraft.user_id == user_id, ApplicationDraft.status != "deleted")
    )
    if draft is None:
        raise ApiError(404, "draft_not_found", "No draft matches this request.")
    return draft


def create_draft(
    db: Session,
    *,
    user: User,
    scheme_slug: str,
    language: str = "en",
    reuse_profile: bool = False,
) -> ApplicationDraft:
    scheme = db.scalar(select(Scheme).where(Scheme.slug == scheme_slug, Scheme.is_published.is_(True)))
    if scheme is None:
        raise ApiError(404, "scheme_not_found", "No published scheme matches this address.")
    version = search.load_version(db, scheme)
    draft = ApplicationDraft(
        user_id=user.id,
        scheme_id=scheme.id,
        scheme_version_id=version.id,
        title=scheme.official_name,
        status="draft",
    )
    draft.fields = _build_field_rows(db, user.id, version, reuse_profile=reuse_profile)
    db.add(draft)
    db.flush()
    return draft


def list_drafts(db: Session, user_id) -> list[dict[str, Any]]:
    drafts = db.scalars(
        select(ApplicationDraft)
        .options(
            selectinload(ApplicationDraft.fields),
            selectinload(ApplicationDraft.scheme),
            selectinload(ApplicationDraft.scheme_version),
        )
        .where(ApplicationDraft.user_id == user_id, ApplicationDraft.status != "deleted")
        .order_by(ApplicationDraft.updated_at.desc())
    ).all()
    result = []
    for draft in drafts:
        payload = serialize(draft)
        result.append(
            {
                "id": payload["id"],
                "title": draft.title,
                "status": draft.status,
                "field_count": len(payload["fields"]),
                "missing_required": len(payload["missing_required"]),
                "updated_at": payload["updated_at"],
            }
        )
    return result


def get_draft(db: Session, *, draft_id, user_id) -> ApplicationDraft:
    return _load_owned(db, draft_id, user_id)


def update_draft(
    db: Session,
    *,
    draft_id,
    user_id,
    updates: list[dict[str, Any]],
    remove: list[str],
    confirm: list[str],
) -> ApplicationDraft:
    draft = _load_owned(db, draft_id, user_id)
    by_key = {field.field_key: field for field in draft.fields}
    for item in updates:
        key = item["key"]
        field = by_key.get(key)
        if field is None:
            raise ApiError(422, "validation_error", "Unknown draft field.", details=[{"field": key, "issue": "not in draft"}])
        value = (item.get("value") or "").strip()
        if len(value) > 500:
            raise ApiError(422, "validation_error", "Draft values must be under 500 characters.")
        field.value = value or None
        if value:
            field.source = "user"
            field.source_reference = None
        else:
            field.source = "empty"
        field.user_confirmed = bool(item.get("confirmed")) and bool(value)
    for key in remove:
        field = by_key.get(key)
        if field is None:
            raise ApiError(422, "validation_error", "Unknown draft field.", details=[{"field": key, "issue": "not in draft"}])
        field.value = None
        field.source = "empty"
        field.source_reference = None
        field.user_confirmed = False
    for key in confirm:
        field = by_key.get(key)
        if field is None:
            raise ApiError(422, "validation_error", "Unknown draft field.", details=[{"field": key, "issue": "not in draft"}])
        if not field.value:
            raise ApiError(422, "validation_error", "A field without a value cannot be confirmed.")
        field.user_confirmed = True
        if field.source == "empty":
            field.source = "user"
    draft.updated_at = datetime.now(UTC)
    db.flush()
    return draft


def delete_draft(db: Session, *, draft_id, user_id) -> None:
    draft = _load_owned(db, draft_id, user_id)
    db.delete(draft)
    db.flush()


def export_draft(
    db: Session, *, draft_id, user_id, fmt: str = "json", language: str = "en"
) -> dict[str, Any]:
    draft = _load_owned(db, draft_id, user_id)
    language = language if language in SUPPORTED_LANGUAGES else "en"
    payload = serialize(draft, language=language)
    confirmed = [field for field in payload["fields"] if field["user_confirmed"]]
    proposed = [field for field in payload["fields"] if field["value"] and not field["user_confirmed"]]
    empty = [field for field in payload["fields"] if not field["value"]]

    if fmt == "text":
        lines = [
            "HVA application preparation draft",
            "==============================",
            f"Scheme: {draft.title}",
            f"Exported: {datetime.now(UTC).isoformat()}",
            "",
            "Confirmed by you:",
            *[f"- {field['label']}: {field['value']}" for field in confirmed],
            "",
            "Proposed but not confirmed (review before use):",
            *[f"- {field['label']}: {field['value']}" for field in proposed],
            "",
            "Still missing:",
            *[f"- {field['label']}" for field in empty],
            "",
            EXPORT_DISCLAIMER,
        ]
        document: Any = "\n".join(lines)
    else:
        document = {
            "scheme": draft.title,
            "exported_at": datetime.now(UTC).isoformat(),
            "submitted": False,
            "confirmed_fields": confirmed,
            "proposed_fields": proposed,
            "missing_fields": empty,
            "disclaimer": EXPORT_DISCLAIMER,
        }

    draft.status = "exported"
    draft.last_exported_at = datetime.now(UTC)
    db.flush()
    return {
        "format": fmt,
        "document": document,
        "submitted": False,
        "disclaimer": EXPORT_DISCLAIMER,
        "draft": serialize(draft, language=language),
    }
