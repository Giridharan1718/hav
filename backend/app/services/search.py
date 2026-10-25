"""Scheme catalogue retrieval: keyword search, filters and provenance-rich detail.

Ranking uses PostgreSQL full-text search with the ``simple`` configuration (it splits
on whitespace/punctuation, which works for Indic scripts as well as English) plus a
substring fallback. Result explanations only state which query terms matched where;
they do not invent relevance claims.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.core.i18n import SUPPORTED_LANGUAGES, detect_language, normalize_query
from app.models import EligibilityRule, Scheme, SchemeTranslation, SchemeVersion

REVIEW_LABELS = {
    "draft": {
        "en": "Draft — not for public use",
        "hi": "मसौदा — सार्वजनिक उपयोग के लिए नहीं",
        "ta": "வரைவு — பொதுப் பயன்பாட்டுக்கு அல்ல",
    },
    "pending_review": {
        "en": "Awaiting content review",
        "hi": "सामग्री समीक्षा प्रतीक्षित",
        "ta": "உள்ளடக்க மதிப்பாய்வு நிலுவையில்",
    },
    "source_checked": {
        "en": "Official source link checked automatically; content review pending",
        "hi": "आधिकारिक स्रोत लिंक स्वतः जाँचा गया; सामग्री समीक्षा प्रतीक्षित",
        "ta": "அதிகாரப்பூர்வ மூல இணைப்பு தானாகச் சரிபார்க்கப்பட்டது; உள்ளடக்க மதிப்பாய்வு நிலுவையில்",
    },
    "verified": {
        "en": "Reviewed by a content reviewer",
        "hi": "सामग्री समीक्षक द्वारा जाँचा गया",
        "ta": "உள்ளடக்க மதிப்பாய்வாளரால் சரிபார்க்கப்பட்டது",
    },
    "rejected": {
        "en": "Rejected in review",
        "hi": "समीक्षा में अस्वीकृत",
        "ta": "மதிப்பாய்வில் நிராகரிக்கப்பட்டது",
    },
    "superseded": {
        "en": "Superseded by a newer version",
        "hi": "नए संस्करण द्वारा प्रतिस्थापित",
        "ta": "புதிய பதிப்பால் மாற்றப்பட்டது",
    },
}

DISCLAIMER = (
    "HVA is an independent assistance platform. It is not a government website and it does "
    "not certify identity or grant benefits. Always confirm details on the official portal."
)


def build_search_text(scheme: Scheme, version: SchemeVersion) -> str:
    translations = [
        f"{item.benefit_summary} {item.eligibility_summary}" for item in version.translations
    ]
    parts = [
        scheme.official_name,
        scheme.department,
        scheme.category,
        " ".join(scheme.beneficiary_groups),
        version.benefit_summary,
        version.eligibility_summary,
        " ".join(str(document.get("name", "")) for document in version.required_documents),
        " ".join(str(step) for step in version.application_steps),
        *translations,
    ]
    return re.sub(r"\s+", " ", " ".join(part for part in parts if part)).strip()


def _ts_query(normalized: str):
    tokens = [token for token in re.findall(r"[0-9a-zA-Z\u0900-\u097F\u0B80-\u0BFF]+", normalized) if token]
    if not tokens:
        return None
    expression = " | ".join(tokens[:24])
    return func.to_tsquery("simple", expression)


def _apply_filters(stmt, *, language: str, state: str | None, category: str | None, beneficiary: str | None):
    if state:
        stmt = stmt.where(
            or_(
                Scheme.scope == "central",
                func.lower(Scheme.state_name) == state.lower(),
            )
        )
    if category:
        stmt = stmt.where(func.lower(Scheme.category) == category.lower())
    if beneficiary:
        stmt = stmt.where(func.jsonb_exists(Scheme.beneficiary_groups, beneficiary))
    if language and language != "en" and language in SUPPORTED_LANGUAGES:
        stmt = stmt.where(
            select(SchemeTranslation.id)
            .where(
                SchemeTranslation.scheme_version_id == Scheme.current_version_id,
                SchemeTranslation.language == language,
            )
            .exists()
        )
    return stmt


def _review_status(version: SchemeVersion) -> dict[str, Any]:
    return {
        "code": version.review_status,
        "label": REVIEW_LABELS.get(version.review_status, {}).get("en", version.review_status),
        "verified": version.review_status == "verified",
    }


def _translation(version: SchemeVersion, language: str) -> SchemeTranslation | None:
    for item in version.translations:
        if item.language == language:
            return item
    return None


def serialise_card(
    scheme: Scheme, version: SchemeVersion, *, language: str, matched_terms: list[str], match_reason: str
) -> dict[str, Any]:
    translation = _translation(version, language)
    available = sorted({item.language for item in version.translations} | {"en"})
    return {
        "slug": scheme.slug,
        "name": scheme.official_name,
        "department": scheme.department,
        "scope": scheme.scope,
        "state": scheme.state_name,
        "category": scheme.category,
        "beneficiary_groups": scheme.beneficiary_groups,
        "summary": translation.benefit_summary if translation else version.benefit_summary,
        "summary_language": language if translation else "en",
        "translation_available": translation is not None or language == "en",
        "available_languages": available,
        "official_url": scheme.official_url,
        "source_status": _review_status(version),
        "version_no": version.version_no,
        "verified_at": version.verified_at.isoformat() if version.verified_at else None,
        "retrieved_at": version.retrieved_at.isoformat() if version.retrieved_at else None,
        "deadline": version.deadline.isoformat() if version.deadline else None,
        "match": {"terms": matched_terms, "reason": match_reason},
    }


def search_schemes(
    db: Session,
    *,
    query: str | None,
    language: str = "en",
    language_explicit: bool = False,
    state: str | None = None,
    category: str | None = None,
    beneficiary: str | None = None,
    page: int = 1,
    page_size: int = 10,
    sort: str = "relevance",
) -> dict[str, Any]:
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    normalized = normalize_query(query or "")
    tsquery = _ts_query(normalized) if normalized else None

    base = (
        select(Scheme, SchemeVersion)
        .join(SchemeVersion, Scheme.current_version_id == SchemeVersion.id)
        .where(Scheme.is_published.is_(True))
    )
    base = _apply_filters(
        base, language=language, state=state, category=category, beneficiary=beneficiary
    )

    rank = func.ts_rank_cd(SchemeVersion.search_vector, tsquery) if tsquery is not None else None
    if normalized:
        conditions = [SchemeVersion.search_vector.op("@@")(tsquery)]
        like = f"%{normalized}%"
        conditions.append(func.lower(SchemeVersion.search_text).like(like))
        # also allow individual token matches (helps with spelling variation)
        for token in normalized.split(" ")[:8]:
            if len(token) > 2:
                conditions.append(func.lower(SchemeVersion.search_text).like(f"%{token}%"))
        base = base.where(or_(*conditions))

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    if sort == "name":
        ordering = (Scheme.official_name.asc(), Scheme.slug.asc())
    elif sort == "updated":
        ordering = (SchemeVersion.verified_at.desc().nullslast(), Scheme.slug.asc())
    else:
        sort = "relevance"
        if rank is not None:
            ordering = (rank.desc().nullslast(), Scheme.slug.asc())
        else:
            ordering = (Scheme.official_name.asc(), Scheme.slug.asc())

    stmt = base.order_by(*ordering).offset((page - 1) * page_size).limit(page_size)
    if rank is not None:
        stmt = stmt.add_columns(
            rank.label("rank"),
            SchemeVersion.search_vector.op("@@")(tsquery).label("text_matched"),
        )
    rows = db.execute(stmt).all()

    items: list[dict[str, Any]] = []
    for row in rows:
        scheme, version = row[0], row[1]
        haystack = (version.search_text or "").lower()
        terms = [token for token in normalized.split(" ") if token and token in haystack][:6]
        reason = "full_text" if rank is not None and bool(row[3]) else ("keyword" if normalized else "browse")
        items.append(
            serialise_card(
                scheme, version, language=language, matched_terms=terms or normalized.split(" ")[:3], match_reason=reason
            )
        )

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
        "query": query or "",
        "normalized_query": normalized,
        "language": language,
        "language_detected": None if language_explicit else detect_language(query or ""),
        "sort": sort,
        "filters": {"state": state, "category": category, "beneficiary": beneficiary},
        "disclaimer": DISCLAIMER,
    }


def get_version(db: Session, scheme: Scheme) -> SchemeVersion | None:
    if scheme.current_version_id:
        return db.get(SchemeVersion, scheme.current_version_id)
    return None


def load_version(db: Session, scheme: Scheme) -> SchemeVersion:
    version = db.scalar(
        select(SchemeVersion)
        .options(
            selectinload(SchemeVersion.translations),
            selectinload(SchemeVersion.rules),
            selectinload(SchemeVersion.source_document),
        )
        .where(SchemeVersion.id == scheme.current_version_id)
    )
    if version is None:
        raise ApiError(404, "scheme_unavailable", "This scheme is not available yet.")
    return version


def get_scheme(db: Session, slug: str, *, language: str = "en") -> dict[str, Any]:
    scheme = db.scalar(select(Scheme).where(Scheme.slug == slug, Scheme.is_published.is_(True)))
    if scheme is None:
        raise ApiError(404, "scheme_not_found", "No published scheme matches this address.")
    version = load_version(db, scheme)
    translation = _translation(version, language)
    available = sorted({item.language for item in version.translations} | {"en"})
    source = version.source_document
    documents = translation.required_documents if translation else version.required_documents
    steps = translation.application_steps if translation else version.application_steps
    rules = (
        db.scalars(
            select(EligibilityRule)
            .where(EligibilityRule.scheme_version_id == version.id)
            .order_by(EligibilityRule.rule_key)
        ).all()
    )
    return {
        "slug": scheme.slug,
        "name": scheme.official_name,
        "department": scheme.department,
        "scope": scheme.scope,
        "state": scheme.state_name,
        "category": scheme.category,
        "beneficiary_groups": scheme.beneficiary_groups,
        "official_url": scheme.official_url,
        "application_url": version.application_url,
        "application_mode": version.application_mode,
        "deadline": version.deadline.isoformat() if version.deadline else None,
        "benefit_summary": translation.benefit_summary if translation else version.benefit_summary,
        "eligibility_summary": translation.eligibility_summary if translation else version.eligibility_summary,
        "documents": documents,
        "application_steps": steps,
        "language": language if translation else "en",
        "requested_language": language,
        "translation_available": translation is not None or language == "en",
        "available_languages": available,
        "version": {
            "version_no": version.version_no,
            "review_status": version.review_status,
            "review_label": REVIEW_LABELS.get(version.review_status, {}).get("en", version.review_status),
            "verified": version.review_status == "verified",
            "verified_at": version.verified_at.isoformat() if version.verified_at else None,
            "retrieved_at": version.retrieved_at.isoformat() if version.retrieved_at else None,
            "source_published_at": version.source_published_at.isoformat() if version.source_published_at else None,
            "content_hash": version.content_hash,
            "effective_from": version.effective_from.isoformat() if version.effective_from else None,
            "effective_to": version.effective_to.isoformat() if version.effective_to else None,
            "review_notes": version.review_notes,
        },
        "application_link": {
            "url": version.application_url,
            "http_status": version.application_url_http_status,
            "checked_at": (
                version.application_url_checked_at.isoformat()
                if version.application_url_checked_at
                else None
            ),
            "verified": version.application_url_http_status == 200,
        },
        "source": {
            "url": source.url if source else None,
            "host": source.host if source else None,
            "title": source.title if source else None,
            "publisher": source.publisher if source else None,
            "http_status": source.http_status if source else None,
            "retrieved_at": source.retrieved_at.isoformat() if source and source.retrieved_at else None,
            "content_hash": source.content_hash if source else None,
            "link_verified": bool(source and source.http_status == 200),
        },
        "eligibility": {
            "rules": [
                {
                    "rule_key": rule.rule_key,
                    "field": rule.field,
                    "description": rule.description,
                    "source_reference": rule.source_reference,
                    "validation_status": rule.validation_status,
                }
                for rule in rules
            ],
            "required_fields": [
                rule.field for rule in rules if rule.validation_status == "valid"
            ],
            "evaluable": all(rule.validation_status == "valid" for rule in rules) and bool(rules),
        },
        "disclaimer": DISCLAIMER,
    }


def list_categories(db: Session) -> list[str]:
    return sorted(
        {
            value
            for value in db.scalars(select(Scheme.category).where(Scheme.is_published.is_(True))).all()
            if value
        }
    )


def count_published(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Scheme).where(Scheme.is_published.is_(True))) or 0
