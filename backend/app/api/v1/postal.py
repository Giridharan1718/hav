"""PIN-code postal lookup with explicit invalid/unknown/ambiguous distinctions."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session as OrmSession

from app.adapters import postal
from app.core.errors import ApiError
from app.core.ratelimit import LIMITS, enforce
from app.db import get_db

router = APIRouter(prefix="/postal", tags=["postal"])
PIN_RE = re.compile(r"^[1-9][0-9]{5}$")


@router.get("/{pincode}")
def lookup_pincode(
    pincode: str,
    request: Request,
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    enforce(LIMITS["postal"], scope="postal", request=request)
    trimmed = pincode.strip()
    if not PIN_RE.match(trimmed):
        raise ApiError(
            422,
            "invalid_pincode_format",
            "Enter a six-digit Indian PIN code. It cannot start with zero.",
        )
    result = postal.lookup(db, trimmed)
    payload = result.as_dict()
    if not result.matches:
        raise ApiError(
            404,
            "unknown_pincode",
            "This PIN code is not in the available postal dataset. Check the digits, or enter your address without post-office confirmation.",
            details={"pincode": trimmed, "source": payload["source"]},
        )
    if payload["ambiguous"]:
        payload["message"] = "This PIN code covers multiple post offices. Select the one that serves your address."
    return payload
