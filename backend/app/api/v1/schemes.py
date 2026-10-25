"""Scheme catalogue, evidence detail and deterministic eligibility endpoints."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.core.errors import ApiError
from app.core.i18n import SUPPORTED_LANGUAGES
from app.core.ratelimit import LIMITS, enforce
from app.db import get_db
from app.deps import AuthContext, get_optional_auth, require_consent_active
from app.models import Scheme, SearchHistory
from app.schemas.api import (
    EligibilityOut,
    EligibilityRequest,
    QuestionsOut,
    SchemeDetailOut,
    SchemeSearchOut,
)
from app.services import eligibility, search

router = APIRouter(prefix="/schemes", tags=["schemes"])


def _language(value: str | None, auth: AuthContext | None, default: str = "en") -> tuple[str, bool]:
    if value:
        if value not in SUPPORTED_LANGUAGES:
            raise ApiError(422, "unsupported_language", "Supported languages are English, Hindi and Tamil.")
        return value, True
    if auth is not None:
        profile = auth.user.profile
        if profile is not None and profile.preferred_language in SUPPORTED_LANGUAGES:
            return profile.preferred_language, False
    return default, False


@router.get("", response_model=SchemeSearchOut)
def search_schemes(
    request: Request,
    query: str | None = Query(default=None, max_length=200),
    language: str | None = Query(default=None, max_length=8),
    state: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=60),
    beneficiary: str | None = Query(default=None, max_length=60),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    sort: Literal["relevance", "name", "updated"] = "relevance",
    auth: AuthContext | None = Depends(get_optional_auth),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    enforce(LIMITS["search"], scope="scheme_search", request=request)
    language_code, explicit = _language(language, auth)
    result = search.search_schemes(
        db,
        query=query,
        language=language_code,
        language_explicit=explicit,
        state=state,
        category=category,
        beneficiary=beneficiary,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    if auth is not None and query and require_consent_active(db, auth.user.id, "analytics"):
        db.add(
            SearchHistory(
                user_id=auth.user.id,
                query=result["normalized_query"][:300] or query[:300],
                language=language_code,
                filters={"state": state, "category": category, "beneficiary": beneficiary},
                result_count=result["total"],
            )
        )
    return result


@router.get("/meta/categories")
def categories(db: OrmSession = Depends(get_db, scope="function")) -> dict:
    return {
        "categories": search.list_categories(db),
        "published_schemes": search.count_published(db),
        "languages": list(SUPPORTED_LANGUAGES),
    }


@router.get("/{slug}", response_model=SchemeDetailOut)
def scheme_detail(
    slug: str,
    language: str | None = Query(default=None, max_length=8),
    auth: AuthContext | None = Depends(get_optional_auth),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    language_code, _ = _language(language, auth)
    return search.get_scheme(db, slug, language=language_code)


@router.get("/{slug}/eligibility/questions", response_model=QuestionsOut)
def eligibility_questions(
    slug: str,
    language: str | None = Query(default=None, max_length=8),
    auth: AuthContext | None = Depends(get_optional_auth),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    language_code, _ = _language(language, auth)
    scheme = db.scalar(select(Scheme).where(Scheme.slug == slug, Scheme.is_published.is_(True)))
    if scheme is None:
        raise ApiError(404, "scheme_not_found", "No published scheme matches this address.")
    version = search.load_version(db, scheme)
    payload = eligibility.build_questions(version, language_code)

    prefill: dict[str, object] = {}
    if auth is not None:
        from app.models import Address, Profile

        profile = db.scalar(select(Profile).where(Profile.user_id == auth.user.id))
        address = db.scalar(select(Address).where(Address.user_id == auth.user.id))
        available = {item["key"] for item in payload["fields"]}
        if profile and profile.date_of_birth and "age" in available:
            today = date.today()
            dob = profile.date_of_birth
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            prefill["age"] = age
        if address:
            if address.state and "state" in available:
                prefill["state"] = address.state
            if address.district and "district" in available:
                prefill["district"] = address.district
        if prefill:
            prefill["_note"] = (
                "Values copied from your profile are suggestions only. Confirm or change them before "
                "evaluating; they are not saved."
            )
    payload["prefill"] = prefill
    return payload


@router.post("/{slug}/eligibility/evaluate", response_model=EligibilityOut)
def evaluate_eligibility(
    slug: str,
    payload: EligibilityRequest,
    auth: AuthContext | None = Depends(get_optional_auth),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    language_code = payload.language or _language(None, auth)[0]
    scheme = db.scalar(select(Scheme).where(Scheme.slug == slug, Scheme.is_published.is_(True)))
    if scheme is None:
        raise ApiError(404, "scheme_not_found", "No published scheme matches this address.")
    version = search.load_version(db, scheme)
    if not version.rules:
        raise ApiError(
            409,
            "eligibility_unavailable",
            "This scheme does not yet have documented, machine-checkable criteria. Read the official eligibility summary instead.",
        )
    return eligibility.evaluate(version, payload.inputs, language=language_code)


@router.get("/{slug}/checklist")
def document_checklist(
    slug: str,
    language: str | None = Query(default=None, max_length=8),
    auth: AuthContext | None = Depends(get_optional_auth),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    language_code, _ = _language(language, auth)
    detail = search.get_scheme(db, slug, language=language_code)
    documents = []
    for index, item in enumerate(detail["documents"]):
        if isinstance(item, dict):
            documents.append(
                {
                    "key": item.get("key") or f"document_{index + 1}",
                    "name": item.get("name") or "Document",
                    "note": item.get("note"),
                    "required": bool(item.get("required", True)),
                    "source_reference": item.get("source_reference"),
                }
            )
        else:
            documents.append(
                {"key": f"document_{index + 1}", "name": str(item), "note": None, "required": True,
                 "source_reference": None}
            )
    return {
        "scheme": {"slug": detail["slug"], "name": detail["name"], "version_no": detail["version"]["version_no"]},
        "documents": documents,
        "translation_available": detail["translation_available"],
        "language": detail["language"],
        "note": (
            "This checklist is transcribed from the recorded official source. Requirements can change; "
            "confirm on the official portal before applying."
        ),
        "source": detail["source"],
        "disclaimer": detail["disclaimer"],
    }
