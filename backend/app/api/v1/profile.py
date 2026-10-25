"""Citizen profile and address management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.adapters import postal
from app.core.errors import ApiError
from app.core.security import normalize_phone
from app.db import get_db
from app.deps import AuthContext, client_ip, require_user
from app.models import Address, Profile
from app.schemas.api import AddressUpdate, ProfileUpdate
from app.services import audit

router = APIRouter(prefix="/me", tags=["profile"])


def _profile_payload(profile: Profile | None, address: Address | None) -> dict:
    return {
        "profile": None
        if profile is None
        else {
            "full_name": profile.full_name,
            "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth else None,
            "preferred_language": profile.preferred_language,
            "phone": profile.phone,
            "phone_verified": profile.phone_verified_at is not None,
            "gender": profile.gender,
            "updated_at": profile.updated_at.isoformat(),
        },
        "address": None
        if address is None
        else {
            "line1": address.line1,
            "pincode": address.pincode,
            "post_office": address.post_office,
            "district": address.district,
            "state": address.state,
            "post_office_confirmed": address.post_office_confirmed,
        },
        "privacy": {
            "date_of_birth_optional": True,
            "phone_optional": True,
            "address_optional": True,
            "note": (
                "Only provide what you are comfortable sharing. Date of birth is used for age-based "
                "eligibility checks, phone is used for contact verification, and address is used to "
                "match state and district restrictions. Questionnaire answers are never stored."
            ),
        },
    }


@router.get("/profile")
def get_profile(auth: AuthContext = Depends(require_user), db: OrmSession = Depends(get_db, scope="function")) -> dict:
    profile = db.scalar(select(Profile).where(Profile.user_id == auth.user.id))
    address = db.scalar(select(Address).where(Address.user_id == auth.user.id))
    return _profile_payload(profile, address)


@router.put("/profile")
def update_profile(
    payload: ProfileUpdate,
    request: Request,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    profile = db.scalar(select(Profile).where(Profile.user_id == auth.user.id))
    if profile is None:
        profile = Profile(user_id=auth.user.id, full_name=payload.full_name)
        db.add(profile)

    if payload.phone:
        phone = normalize_phone(payload.phone)
        if phone is None:
            raise ApiError(422, "invalid_phone", "Enter a valid 10-digit Indian mobile number.")
        if phone != profile.phone:
            profile.phone = phone
            profile.phone_verified_at = None
    else:
        if profile.phone is not None:
            profile.phone = None
            profile.phone_verified_at = None

    profile.full_name = payload.full_name
    profile.date_of_birth = payload.date_of_birth
    profile.preferred_language = payload.preferred_language
    profile.gender = payload.gender
    db.flush()

    address = db.scalar(select(Address).where(Address.user_id == auth.user.id))
    audit.record(
        db,
        actor=auth.user,
        action="profile.updated",
        resource_type="profile",
        resource_id=auth.user.id,
        ip=client_ip(request),
        metadata={"fields": ["full_name", "date_of_birth", "preferred_language", "phone", "gender"]},
    )
    return _profile_payload(profile, address)


@router.put("/address")
def update_address(
    payload: AddressUpdate,
    request: Request,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> dict:
    try:
        result = postal.lookup(db, payload.pincode)
    except ApiError as exc:
        if exc.status_code == 502:
            raise
        raise

    warnings: list[dict[str, str]] = []
    post_office = payload.post_office
    district = payload.district
    state = payload.state
    confirmed = False

    if not result.matches:
        warnings.append(
            {
                "code": "unknown_pincode",
                "message": "This PIN code was not found in the available postal dataset. You can still save your address, but the post office is not confirmed.",
            }
        )
        if payload.post_office_confirmed:
            raise ApiError(422, "post_office_unverified", "A post office cannot be confirmed from an unknown PIN code.")
    else:
        if post_office:
            match = next(
                (item for item in result.matches if item.name.casefold() == post_office.casefold()), None
            )
            if match is None:
                raise ApiError(
                    422,
                    "post_office_not_found",
                    "Select one of the post offices returned for this PIN code.",
                    details=[item.as_dict() for item in result.matches],
                )
            post_office = match.name
            district = match.district
            state = match.state
            confirmed = True
        elif len(result.matches) > 1:
            raise ApiError(
                422,
                "post_office_selection_required",
                "This PIN code covers more than one post office. Choose the correct one.",
                details=[item.as_dict() for item in result.matches],
            )
        else:
            district = district or result.matches[0].district
            state = state or result.matches[0].state
            warnings.append(
                {
                    "code": "post_office_not_selected",
                    "message": "Address saved without confirming a post office. Confirm it to improve eligibility matching.",
                }
            )

    address = db.scalar(select(Address).where(Address.user_id == auth.user.id))
    if address is None:
        address = Address(user_id=auth.user.id, pincode=payload.pincode)
        db.add(address)
    address.line1 = payload.line1
    address.pincode = payload.pincode
    address.post_office = post_office
    address.district = district
    address.state = state
    address.post_office_confirmed = confirmed
    db.flush()

    audit.record(
        db,
        actor=auth.user,
        action="address.updated",
        resource_type="address",
        resource_id=address.id,
        ip=client_ip(request),
        metadata={"post_office_confirmed": confirmed, "pincode_known": bool(result.matches)},
    )
    profile = db.scalar(select(Profile).where(Profile.user_id == auth.user.id))
    payload_out = _profile_payload(profile, address)
    payload_out["lookup"] = result.as_dict()
    payload_out["warnings"] = warnings
    return payload_out


@router.delete("/profile", status_code=204)
def delete_profile(
    request: Request,
    auth: AuthContext = Depends(require_user),
    db: OrmSession = Depends(get_db, scope="function"),
) -> Response:
    profile = db.scalar(select(Profile).where(Profile.user_id == auth.user.id))
    address = db.scalar(select(Address).where(Address.user_id == auth.user.id))
    if address is not None:
        db.delete(address)
    if profile is not None:
        db.delete(profile)
    db.flush()
    audit.record(
        db, actor=auth.user, action="profile.deleted", resource_type="profile", resource_id=auth.user.id,
        ip=client_ip(request),
    )
    return Response(status_code=204)
