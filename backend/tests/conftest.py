"""Test configuration.

Integration tests run against a real PostgreSQL database (HVA_TEST_DATABASE_URL) and
exercise the Alembic migration chain. No test replaces database behaviour with an
in-memory imitation.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.environ.get(
    "HVA_TEST_DATABASE_URL", "postgresql+psycopg://hva:hva@127.0.0.1:55432/hva_test"
)

os.environ.setdefault("HVA_ENV", "test")
os.environ["HVA_DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("HVA_SECRET_KEY", "test-secret-key-that-is-long-enough-for-the-suite")
os.environ.setdefault("HVA_LOG_LEVEL", "WARNING")
os.environ.setdefault("HVA_SMS_PROVIDER", "mock")
os.environ.setdefault("HVA_EMAIL_PROVIDER", "outbox")
os.environ.setdefault("HVA_COOKIE_SECURE", "false")

from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.core.ratelimit import limiter  # noqa: E402
from app.core.security import hash_password, new_totp_secret  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Consent, Profile, Role, User  # noqa: E402

PASSWORD = "correct-horse-battery-42"


@pytest.fixture(scope="session", autouse=True)
def migrate_database():
    os.chdir(BACKEND_ROOT)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(config, "head")
    yield


@pytest.fixture(autouse=True)
def clean_state(migrate_database):
    limiter.reset()
    with engine.begin() as connection:
        tables = ", ".join(f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables))
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        test_client.get("/api/v1/auth/csrf")
        yield test_client


def csrf(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get("hva_csrf", "")}


def create_user(
    db,
    *,
    email: str = "citizen@hva-demo.com",
    password: str = PASSWORD,
    role: str = Role.citizen.value,
    full_name: str = "Test Citizen",
    mfa: bool = False,
    verified_phone: bool = False,
) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
        mfa_enabled=mfa,
        mfa_secret_enc=new_totp_secret() if mfa else None,
    )
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id, full_name=full_name, preferred_language="en"))
    db.add(
        Consent(
            user_id=user.id,
            purpose="required_account",
            granted=True,
            document_version="2026-10-01",
        )
    )
    db.commit()
    if verified_phone:
        profile = db.query(Profile).filter(Profile.user_id == user.id).one()
        profile.phone_verified_at = profile.created_at
        db.commit()
    return user


@pytest.fixture
def user(db) -> User:
    return create_user(db)


@pytest.fixture
def logged_in(client, user) -> TestClient:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": PASSWORD},
        headers=csrf(client),
    )
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
def seeded_catalogue(db):
    from seed import catalogue
    from seed.seed import seed_scheme

    for item in catalogue.SCHEMES:
        seed_scheme(db, item, check_links=False)
    db.commit()
    return catalogue


@pytest.fixture
def published_scheme(db, seeded_catalogue):
    from app.models import ReviewStatus, Scheme, SchemeVersion

    scheme = db.query(Scheme).filter(Scheme.slug == "pm-kisan").one()
    version = db.get(SchemeVersion, scheme.current_version_id)
    version.review_status = ReviewStatus.verified.value
    source = version.source_document
    source.http_status = 200
    db.commit()
    return scheme
