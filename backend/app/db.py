"""Database engine, session factory and encrypted column types."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import Text, TypeDecorator

from app.core.config import settings
from app.core.security import decrypt_value, encrypt_value


class Base(DeclarativeBase):
    pass


class EncryptedText(TypeDecorator[str]):
    """Authenticated encryption at rest for selected highly sensitive fields.

    Stored as ciphertext text; key material lives outside the database.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Any) -> str | None:
        return None if value is None else encrypt_value(value)

    def process_result_value(self, value: str | None, dialect: Any) -> str | None:
        return None if value is None else decrypt_value(value)


class EncryptedDate(TypeDecorator[date]):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: date | None, dialect: Any) -> str | None:
        return None if value is None else encrypt_value(value.isoformat())

    def process_result_value(self, value: str | None, dialect: Any) -> date | None:
        return None if value is None else date.fromisoformat(decrypt_value(value))


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
