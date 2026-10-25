"""Health and capability reporting (no secrets, no optimistic claims)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session as OrmSession

from app.core.config import settings
from app.db import get_db
from app.models import PostalDataset, Scheme
from app.schemas.api import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health(db: OrmSession = Depends(get_db, scope="function")) -> dict:
    database = "ok"
    try:
        db.execute(text("select 1"))
    except Exception:  # noqa: BLE001 - health must still answer
        database = "unavailable"
    return {
        "status": "ok" if database == "ok" else "degraded",
        "environment": settings.env,
        "database": database,
        "features": settings.features(),
        "languages": ["en", "hi", "ta"],
        "time": datetime.now(UTC),
    }


@router.get("/health/catalogue")
def catalogue_health(db: OrmSession = Depends(get_db, scope="function")) -> dict:
    published = db.scalar(select(func.count()).select_from(Scheme).where(Scheme.is_published.is_(True))) or 0
    dataset = db.scalar(select(PostalDataset).order_by(PostalDataset.retrieved_at.desc()).limit(1))
    return {
        "published_schemes": published,
        "postal_dataset": None
        if dataset is None
        else {
            "name": dataset.name,
            "is_sample": dataset.is_sample,
            "record_count": dataset.record_count,
            "retrieved_at": dataset.retrieved_at.isoformat() if dataset.retrieved_at else None,
            "source_url": dataset.source_url,
        },
        "note": "Counts describe this environment's database, not production coverage.",
    }
