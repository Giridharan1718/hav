"""Application configuration.

All secrets arrive through the environment (never source code). Development runs may
use derived development-only keys; production refuses to start without strong
explicit keys. Provider adapters that are not configured stay visibly disabled.
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_SECRET = "development-only-secret-key-not-for-production-use"

# Official portals the ingestion pipeline may fetch and the catalogue may cite. Hosts
# are matched after lowercasing and stripping a leading "www.".
DEFAULT_APPROVED_INGEST_HOSTS = [
    "pmkisan.gov.in",
    "pmjay.gov.in",
    "scholarships.gov.in",
    "socialjustice.gov.in",
    "pmayg.dord.gov.in",
    "nsap.dord.gov.in",
    "nrega.nic.in",
    "pfrda.org.in",
    "indiapost.gov.in",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HVA_",
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        # lists are comma-separated in the environment, not JSON
        enable_decoding=False,
    )

    env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    app_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    cors_origins: list[str] = ["http://localhost:3000"]

    database_url: str = "postgresql+psycopg://hva:hva@localhost:55432/hva"

    secret_key: str = ""
    encryption_key: str = ""

    session_cookie_name: str = "hva_session"
    csrf_cookie_name: str = "hva_csrf"
    cookie_secure: bool | None = None
    session_ttl_minutes: int = 720
    session_last_seen_interval_seconds: int = 60
    mfa_challenge_ttl_minutes: int = 5

    password_min_length: int = 10
    otp_ttl_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60
    password_reset_ttl_minutes: int = 30

    # provider selection: adapters are only "on" when explicitly configured
    sms_provider: Literal["disabled", "mock", "http"] = "mock"
    sms_http_url: str = ""
    sms_http_token: str = ""
    email_provider: Literal["disabled", "outbox", "smtp"] = "outbox"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@hva.local"

    llm_provider: Literal["disabled", "openai_compatible"] = "disabled"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: int = 20

    translation_provider: Literal["catalog", "http"] = "catalog"
    translation_http_url: str = ""
    translation_http_token: str = ""

    transcription_provider: Literal["disabled", "http"] = "disabled"
    transcription_http_url: str = ""
    transcription_http_token: str = ""

    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = ""

    approved_ingest_hosts: list[str] = DEFAULT_APPROVED_INGEST_HOSTS
    ingestion_max_bytes: int = 2_000_000
    ingestion_timeout_seconds: int = 10

    postal_source: Literal["local", "http"] = "local"
    postal_http_url: str = ""
    postal_http_token: str = ""
    postal_cache_ttl_hours: int = 168

    max_request_bytes: int = 1_000_000
    assistant_daily_limit: int = 100

    @field_validator("cors_origins", "approved_ingest_hosts", mode="before")
    @classmethod
    def _split_list(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _apply_environment_rules(self) -> Settings:
        if self.env == "production":
            if len(self.secret_key) < 32 or self.secret_key == DEVELOPMENT_SECRET:
                raise ValueError("HVA_SECRET_KEY must be an explicit 32+ character secret in production")
            if not self.encryption_key:
                raise ValueError("HVA_ENCRYPTION_KEY must be set in production")
            if self.sms_provider == "mock":
                raise ValueError("mock SMS adapter must not be enabled in production")
            if self.cookie_secure is False:
                raise ValueError("insecure cookies are not permitted in production")
        if not self.secret_key:
            object.__setattr__(self, "secret_key", DEVELOPMENT_SECRET)
        if not self.encryption_key:
            digest = hashlib.sha256(f"{self.secret_key}|encryption".encode()).digest()
            object.__setattr__(self, "encryption_key", base64.urlsafe_b64encode(digest).decode())
        if self.cookie_secure is None:
            object.__setattr__(self, "cookie_secure", self.env == "production")
        return self

    def features(self) -> dict[str, object]:
        """Report which capabilities are genuinely configured (never optimistic)."""
        return {
            "sms": {"provider": self.sms_provider, "configured": self.sms_provider in {"mock", "http"}},
            "email": {"provider": self.email_provider, "configured": self.email_provider != "disabled"},
            "assistant": {
                "provider": self.llm_provider,
                "configured": self.llm_provider != "disabled",
                "fallback": "grounded_template_composer",
            },
            "translation": {
                "provider": self.translation_provider,
                "configured": self.translation_provider == "catalog" or bool(self.translation_http_url),
            },
            "transcription": {
                "provider": self.transcription_provider,
                "configured": self.transcription_provider == "http" and bool(self.transcription_http_url),
            },
            "oidc": {
                "enabled": bool(self.oidc_issuer and self.oidc_client_id),
                "issuer": self.oidc_issuer or None,
            },
            "postal_source": self.postal_source,
            "mfa": True,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
