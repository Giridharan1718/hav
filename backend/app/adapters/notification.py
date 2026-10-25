"""SMS and email delivery adapters.

Contracts:
- HTTP SMS gateway: POST JSON {"to": "+91...", "message": "..."} with
  ``Authorization: Bearer <token>`` and a 2xx response. This is a bring-your-own
  gateway contract, not a claim about any specific vendor API.
- SMTP email uses the standard SMTP protocol via the Python standard library.

The mock SMS adapter exists for development and is rejected by configuration when
HVA_ENV=production. The outbox email adapter writes development mail to
backend/.dev-outbox and is likewise a development-only path.
"""

from __future__ import annotations

import logging
import secrets
import smtplib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.errors import ApiError

logger = logging.getLogger("hva.notification")
OUTBOX_DIR = Path(__file__).resolve().parents[2] / ".dev-outbox"


@dataclass
class DeliveryResult:
    provider: str
    delivered: bool
    dev_code: str | None = None
    reference: str | None = None


@dataclass
class Outbox:
    messages: list[dict[str, str]] = field(default_factory=list)

    def clear(self) -> None:
        self.messages.clear()


outbox = Outbox()


def send_otp(phone: str, code: str, *, purpose: str) -> DeliveryResult:
    provider = settings.sms_provider
    if provider == "disabled":
        raise ApiError(503, "sms_unavailable", "Phone verification is not configured.")
    if provider == "mock":
        if settings.env == "production":  # defence in depth; settings also refuses to boot
            raise ApiError(503, "sms_unavailable", "Phone verification is not configured.")
        OUTBOX_DIR.mkdir(exist_ok=True)
        with (OUTBOX_DIR / "sms.log").open("a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now(UTC).isoformat()} {purpose} {phone[-4:]} {code}\n")
        return DeliveryResult(provider="mock", delivered=True, dev_code=code)
    if provider == "http":
        if not settings.sms_http_url:
            raise ApiError(503, "sms_unavailable", "Phone verification is not configured.")
        try:
            response = httpx.post(
                settings.sms_http_url,
                json={"to": phone, "message": f"Your HVA verification code is {code}. It expires in {settings.otp_ttl_minutes} minutes."},
                headers={"Authorization": f"Bearer {settings.sms_http_token}"},
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("sms provider failure: %s", type(exc).__name__)
            raise ApiError(502, "sms_provider_error", "The SMS provider could not deliver the code.") from exc
        return DeliveryResult(provider="http", delivered=True, reference=response.headers.get("x-message-id"))
    raise ApiError(503, "sms_unavailable", "Phone verification is not configured.")


def send_email(to: str, subject: str, body: str) -> None:
    provider = settings.email_provider
    if provider == "disabled":
        raise ApiError(503, "email_unavailable", "Email delivery is not configured.")
    if provider == "outbox":
        OUTBOX_DIR.mkdir(exist_ok=True)
        name = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-{secrets.token_hex(4)}.txt"
        (OUTBOX_DIR / name).write_text(f"To: {to}\nSubject: {subject}\n\n{body}\n", encoding="utf-8")
        outbox.messages.append({"to": to, "subject": subject, "body": body, "file": name})
        return
    if provider == "smtp":
        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as client:
                client.starttls()
                if settings.smtp_username:
                    client.login(settings.smtp_username, settings.smtp_password)
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            logger.warning("smtp failure: %s", type(exc).__name__)
            raise ApiError(503, "email_provider_error", "Email delivery is currently unavailable.") from exc
        return
    raise ApiError(503, "email_unavailable", "Email delivery is not configured.")
