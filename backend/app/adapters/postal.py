"""Postal lookup adapters.

The local source reads the seeded postal dataset in PostgreSQL. The HTTP source is a
config-gated adapter for an authorized postal API and is disabled unless
HVA_POSTAL_SOURCE=http with a URL configured; no vendor API is assumed.

A correctly formatted PIN code is never assumed to be a valid postal location.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError
from app.models import PostalDataset, PostalLookupCache, PostalOffice

logger = logging.getLogger("hva.postal")


@dataclass
class PostalMatch:
    name: str
    district: str
    state: str
    branch_type: str | None = None
    delivery_status: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "district": self.district,
            "state": self.state,
            "branch_type": self.branch_type,
            "delivery_status": self.delivery_status,
        }


@dataclass
class PostalResult:
    pincode: str
    matches: list[PostalMatch]
    source: str
    source_url: str | None
    retrieved_at: datetime | None
    is_sample: bool
    cached: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "pincode": self.pincode,
            "matches": [match.as_dict() for match in self.matches],
            "ambiguous": len(self.matches) > 1,
            "source": {
                "name": self.source,
                "url": self.source_url,
                "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None,
                "is_sample": self.is_sample,
                "cached": self.cached,
            },
        }


def _local_lookup(db: Session, pincode: str) -> PostalResult:
    offices = db.scalars(
        select(PostalOffice).where(PostalOffice.pincode == pincode).order_by(PostalOffice.name)
    ).all()
    dataset = db.scalar(select(PostalDataset).order_by(PostalDataset.retrieved_at.desc()).limit(1))
    return PostalResult(
        pincode=pincode,
        matches=[
            PostalMatch(
                name=office.name,
                district=office.district,
                state=office.state,
                branch_type=office.branch_type,
                delivery_status=office.delivery_status,
            )
            for office in offices
        ],
        source=dataset.name if dataset else "local postal dataset",
        source_url=dataset.source_url if dataset else None,
        retrieved_at=dataset.retrieved_at if dataset else None,
        is_sample=dataset.is_sample if dataset else True,
    )


def _http_lookup(db: Session, pincode: str) -> PostalResult:
    cached = db.get(PostalLookupCache, pincode)
    now = datetime.now(UTC)
    if cached is not None:
        expires = cached.expires_at if cached.expires_at.tzinfo else cached.expires_at.replace(tzinfo=UTC)
        if expires > now:
            payload = cached.payload
            return PostalResult(
                pincode=pincode,
                matches=[PostalMatch(**item) for item in payload["matches"]],
                source=payload["source"],
                source_url=payload.get("source_url"),
                retrieved_at=datetime.fromisoformat(payload["retrieved_at"]) if payload.get("retrieved_at") else None,
                is_sample=False,
                cached=True,
            )
    try:
        response = httpx.get(
            f"{settings.postal_http_url.rstrip('/')}/{pincode}",
            headers={"Authorization": f"Bearer {settings.postal_http_token}"},
            timeout=10,
        )
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("postal provider failure: %s", type(exc).__name__)
        raise ApiError(502, "postal_provider_error", "The postal provider is unavailable right now.") from exc

    records = body.get("post_offices") or body.get("matches") or []
    matches = [
        PostalMatch(
            name=str(item.get("name", "")).strip(),
            district=str(item.get("district", "")).strip(),
            state=str(item.get("state", "")).strip(),
            branch_type=item.get("branch_type"),
            delivery_status=item.get("delivery_status"),
        )
        for item in records
        if item.get("name") and item.get("district") and item.get("state")
    ]
    fetched_at = now
    payload = {
        "matches": [match.as_dict() for match in matches],
        "source": body.get("source", "authorized postal API"),
        "source_url": body.get("source_url"),
        "retrieved_at": fetched_at.isoformat(),
    }
    if cached is None:
        db.add(
            PostalLookupCache(
                pincode=pincode,
                payload=payload,
                source=payload["source"],
                fetched_at=fetched_at,
                expires_at=fetched_at + timedelta(hours=settings.postal_cache_ttl_hours),
            )
        )
    else:
        cached.payload = payload
        cached.fetched_at = fetched_at
        cached.expires_at = fetched_at + timedelta(hours=settings.postal_cache_ttl_hours)
    return PostalResult(
        pincode=pincode,
        matches=matches,
        source=payload["source"],
        source_url=payload["source_url"],
        retrieved_at=fetched_at,
        is_sample=False,
    )


def lookup(db: Session, pincode: str) -> PostalResult:
    if settings.postal_source == "http":
        if not settings.postal_http_url:
            raise ApiError(502, "postal_provider_error", "The postal provider is not configured.")
        return _http_lookup(db, pincode)
    return _local_lookup(db, pincode)
