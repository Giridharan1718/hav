"""Seed the development database.

    cd backend
    python -m seed.seed                 # seed + check source links
    python -m seed.seed --skip-link-check

Creates synthetic accounts (passwords printed once), a curated scheme catalogue with
provenance, unreviewed Hindi/Tamil translations, eligibility rules, and a small,
clearly-labelled postal sample. Nothing here is production content.
"""

from __future__ import annotations

import argparse
import hashlib
import secrets
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlsplit

import httpx
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import hash_password, validate_password_strength
from app.db import SessionLocal
from app.models import (
    Address,
    Consent,
    EligibilityRule,
    PostalDataset,
    PostalOffice,
    Profile,
    Role,
    Scheme,
    SchemeTranslation,
    SchemeVersion,
    SourceDocument,
    User,
)
from app.services.search import build_search_text
from seed import catalogue

USER_AGENT = "HVA-Catalogue-Seed/0.1 (development; automated link check)"
MAX_SAMPLE_BYTES = 400_000


def probe(url: str) -> tuple[int | None, str | None, int | None]:
    """Fetch a page for link verification only; returns (status, hash, byte size)."""
    try:
        with httpx.Client(follow_redirects=True, timeout=20, headers={"User-Agent": USER_AGENT}) as client:
            with client.stream("GET", url) as response:
                buffer = bytearray()
                for chunk in response.iter_bytes():
                    buffer.extend(chunk)
                    if len(buffer) >= MAX_SAMPLE_BYTES:
                        break
                return response.status_code, hashlib.sha256(bytes(buffer)).hexdigest(), len(buffer)
    except httpx.HTTPError:
        return None, None, None


def _random_password() -> str:
    return secrets.token_urlsafe(12)


def ensure_user(db, *, email: str, role: str, full_name: str, password: str) -> bool:
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        return False
    validate_password_strength(password, email=email)
    user = User(email=email, password_hash=hash_password(password), role=role, is_active=True)
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id, full_name=full_name, preferred_language="en"))
    now = datetime.now(UTC)
    db.add(
        Consent(
            user_id=user.id,
            purpose="required_account",
            granted=True,
            document_version="2026-10-01",
            granted_at=now,
        )
    )
    db.flush()
    return True


def seed_postal(db) -> None:
    if db.scalar(select(func.count()).select_from(PostalOffice)):
        return
    dataset = PostalDataset(
        name="Development sample: India Post PIN directory (curated subset)",
        source_url="https://www.indiapost.gov.in/",
        licence_note=(
            "Curated development sample containing widely known GPO PIN codes only. This is not the "
            "complete India Post directory. Obtain the authoritative dataset from India Post / "
            "data.gov.in and confirm reuse terms before production use."
        ),
        is_sample=True,
        record_count=len(catalogue.PINCODES),
        retrieved_at=datetime.now(UTC),
        refreshed_at=datetime.now(UTC),
    )
    db.add(dataset)
    db.flush()
    for item in catalogue.PINCODES:
        db.add(
            PostalOffice(
                pincode=item["pincode"],
                name=item["name"],
                branch_type=item["branch_type"],
                district=item["district"],
                state=item["state"],
                delivery_status=item["delivery_status"],
                dataset_id=dataset.id,
            )
        )
    db.flush()
    print(f"postal: seeded {len(catalogue.PINCODES)} post offices (sample dataset)")


def seed_scheme(db, item: dict, *, check_links: bool) -> str:
    existing = db.scalar(select(Scheme).where(Scheme.slug == item["slug"]))
    if existing is not None:
        return "skipped"

    official_status = official_hash = None
    official_bytes = None
    application_status = None
    checked_at = datetime.now(UTC) if check_links else None
    if check_links:
        official_status, official_hash, official_bytes = probe(item["official_url"])
        if item["application_url"] != item["official_url"]:
            application_status, _, _ = probe(item["application_url"])
        else:
            application_status = official_status

    source = SourceDocument(
        url=item["official_url"],
        host=urlsplit(item["official_url"]).hostname or "",
        title=item["name"],
        publisher=item["department"],
        source_type="link_check",
        http_status=official_status,
        content_hash=official_hash,
        byte_size=official_bytes,
        policy_approved=True,
        retrieved_at=checked_at,
    )
    db.add(source)
    db.flush()

    scheme = Scheme(
        slug=item["slug"],
        official_name=item["name"],
        department=item["department"],
        scope=item["scope"],
        state_name=item.get("state_name"),
        category=item["category"],
        beneficiary_groups=item["beneficiary_groups"],
        official_url=item["official_url"],
        is_published=True,
    )
    db.add(scheme)
    db.flush()

    review_status = (
        catalogue.SOURCE_CHECKED if official_status == 200 else catalogue.PENDING_REVIEW
    )
    version = SchemeVersion(
        scheme_id=scheme.id,
        version_no=1,
        benefit_summary=item["benefit"],
        eligibility_summary=item["eligibility"],
        required_documents=item["documents"],
        application_steps=item["steps"],
        application_url=item["application_url"],
        application_mode=item["application_mode"],
        application_url_http_status=application_status,
        application_url_checked_at=checked_at,
        source_document_id=source.id,
        retrieved_at=checked_at,
        content_hash=official_hash,
        effective_from=date.today() - timedelta(days=30),
        review_status=review_status,
        review_notes=(
            catalogue.REVIEW_NOTE_VERIFIED_LINK
            if review_status == catalogue.SOURCE_CHECKED
            else catalogue.REVIEW_NOTE_PENDING_LINK
        ),
        search_text="",
    )
    db.add(version)
    db.flush()

    for rule in item["rules"]:
        db.add(
            EligibilityRule(
                scheme_version_id=version.id,
                rule_key=rule["key"],
                field=rule["field"],
                operator=rule["operator"],
                value=rule["value"],
                description=rule["description"],
                source_reference=item["official_url"],
                validation_status=rule.get("validation_status", "valid"),
                effective_from=version.effective_from,
            )
        )

    for language, payload in item.get("translations", {}).items():
        documents = [
            {
                "key": original["key"],
                "name": translated,
                "note": original.get("note"),
                "required": original.get("required", True),
            }
            for original, translated in zip(item["documents"], payload["documents"], strict=False)
        ]
        db.add(
            SchemeTranslation(
                scheme_version_id=version.id,
                language=language,
                benefit_summary=payload["benefit"],
                eligibility_summary=payload["eligibility"],
                required_documents=documents,
                application_steps=payload["steps"],
                review_status="draft",
                translator="HVA development translation (unreviewed)",
                translated_at=datetime.now(UTC),
            )
        )
    db.flush()
    db.refresh(version)
    scheme.current_version_id = version.id
    version.search_text = build_search_text(scheme, version)
    db.flush()
    return "seeded"


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed HVA development data")
    parser.add_argument("--skip-link-check", action="store_true", help="do not fetch official pages")
    parser.add_argument("--reviewer-password", default=None)
    parser.add_argument("--admin-password", default=None)
    parser.add_argument("--citizen-password", default=None)
    args = parser.parse_args()

    check_links = not args.skip_link_check
    reviewer_password = args.reviewer_password or _random_password()
    admin_password = args.admin_password or _random_password()
    citizen_password = args.citizen_password or _random_password()

    with SessionLocal() as db:
        created_reviewer = ensure_user(
            db, email="reviewer@hva.test", role=Role.reviewer.value,
            full_name="Demo Reviewer", password=reviewer_password,
        )
        created_admin = ensure_user(
            db, email="admin@hva.test", role=Role.admin.value,
            full_name="Demo Administrator", password=admin_password,
        )
        created_citizen = ensure_user(
            db, email="citizen@hva.test", role=Role.citizen.value,
            full_name="Demo Citizen", password=citizen_password,
        )
        if created_citizen:
            citizen = db.scalar(select(User).where(User.email == "citizen@hva.test"))
            profile = db.scalar(select(Profile).where(Profile.user_id == citizen.id))
            profile.date_of_birth = date(1994, 6, 15)
            db.add(
                Address(
                    user_id=citizen.id,
                    line1="12 Example Marg",
                    pincode="110001",
                    post_office="New Delhi GPO",
                    district="New Delhi",
                    state="Delhi",
                    post_office_confirmed=True,
                )
            )
        db.flush()

        seed_postal(db)

        results: dict[str, int] = {"seeded": 0, "skipped": 0}
        for item in catalogue.SCHEMES:
            outcome = seed_scheme(db, item, check_links=check_links)
            results[outcome] += 1
            print(f"scheme {item['slug']}: {outcome}")
        db.commit()

    print("\nseed complete:", results)
    print("source links checked:", check_links)
    print("provider configuration:", settings.features())
    if created_reviewer:
        print(f"\nreviewer login: reviewer@hva.test / {reviewer_password}")
    if created_admin:
        print(f"admin login:    admin@hva.test / {admin_password}")
    if created_citizen:
        print(f"citizen login:  citizen@hva.test / {citizen_password}")
    print("\nReviewer/admin accounts must enrol TOTP MFA at /settings/security before reviewing.")


if __name__ == "__main__":
    main()
