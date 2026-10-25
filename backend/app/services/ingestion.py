"""Authorized-source ingestion.

Two things happen here: a policy-checked fetch (https only, hostname allowlist,
public-IP resolution checks, manual redirect validation, content-type and size
limits, hashing) and a persisted ingestion run that records provenance. Structured
scheme facts are *not* extracted automatically; a reviewer transcribes and validates
them, so the system cannot invent eligibility criteria from a webpage.
"""

from __future__ import annotations

import hashlib
import ipaddress
import logging
import re
import socket
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError
from app.models import BackgroundJob, IngestionRun, SourceDocument

logger = logging.getLogger("hva.ingestion")

ALLOWED_CONTENT_TYPES = {"text/html", "text/plain", "application/xhtml+xml"}
MAX_REDIRECTS = 3
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


class FetchError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass
class FetchedDocument:
    url: str
    final_url: str
    host: str
    status_code: int
    content_type: str
    text: str
    content_hash: str
    byte_size: int
    retrieved_at: datetime
    title: str | None


def _validate_url(raw: str) -> tuple[str, str]:
    try:
        parts = urlsplit(raw.strip())
    except ValueError as exc:
        raise FetchError("source_not_permitted", "The source URL is not valid.") from exc
    if parts.scheme != "https":
        raise FetchError("source_not_permitted", "Only https sources are permitted.")
    if parts.username or parts.password:
        raise FetchError("source_not_permitted", "Credentials are not permitted in source URLs.")
    if parts.port not in (None, 443):
        raise FetchError("source_not_permitted", "Only the default https port is permitted.")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        raise FetchError("source_not_permitted", "The source URL has no hostname.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise FetchError("source_not_permitted", "IP-address sources are not permitted.")
    if host not in set(settings.approved_ingest_hosts):
        raise FetchError(
            "source_host_not_approved",
            "This host is not on the approved source list. An administrator must approve it first.",
        )
    normalized = urlunsplit(("https", host, parts.path or "/", parts.query, ""))
    return normalized, host


def _assert_public_host(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FetchError("source_unresolvable", "The approved source host could not be resolved.") from exc
    for info in infos:
        address = info[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as exc:
            raise FetchError("source_not_permitted", "The source resolved to an invalid address.") from exc
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise FetchError("source_not_permitted", "The source resolved to a non-public address.")


def fetch_document(url: str) -> FetchedDocument:
    current, host = _validate_url(url)
    retrieved_at = datetime.now(UTC)
    headers = {
        "User-Agent": "HVA-Ingestion/0.1 (independent scheme assistance; contact: operator)",
        "Accept": "text/html, text/plain;q=0.9",
    }
    try:
        with httpx.Client(
            timeout=settings.ingestion_timeout_seconds,
            follow_redirects=False,
            headers=headers,
        ) as client:
            for _ in range(MAX_REDIRECTS + 1):
                _assert_public_host(host)
                with client.stream("GET", current) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise FetchError("redirect_invalid", "The source redirect had no destination.")
                        current, host = _validate_url(urljoin(current, location))
                        continue
                    if response.status_code != 200:
                        raise FetchError(
                            "source_http_error",
                            f"The source returned HTTP {response.status_code}.",
                            status_code=502,
                        )
                    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                    if content_type not in ALLOWED_CONTENT_TYPES:
                        raise FetchError(
                            "source_content_type_rejected",
                            "Only HTML or plain-text official pages may be ingested.",
                        )
                    buffer = bytearray()
                    for chunk in response.iter_bytes():
                        buffer.extend(chunk)
                        if len(buffer) > settings.ingestion_max_bytes:
                            raise FetchError(
                                "source_too_large", "The source page exceeds the ingestion size limit."
                            )
                    body = bytes(buffer)
                    text_value = body.decode(response.encoding or "utf-8", errors="replace")
                    title_match = TITLE_RE.search(text_value)
                    title = (
                        re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", title_match.group(1))).strip()[:300]
                        if title_match
                        else None
                    )
                    return FetchedDocument(
                        url=url,
                        final_url=current,
                        host=host,
                        status_code=response.status_code,
                        content_type=content_type,
                        text=text_value,
                        content_hash=hashlib.sha256(body).hexdigest(),
                        byte_size=len(body),
                        retrieved_at=retrieved_at,
                        title=title,
                    )
            raise FetchError("too_many_redirects", "The source redirected too many times.")
    except httpx.HTTPError as exc:
        logger.warning("ingestion fetch failure: %s", type(exc).__name__)
        raise FetchError("source_unreachable", "The source could not be reached.", status_code=502) from exc


def queue_ingestion(db: Session, *, user_id, url: str) -> tuple[IngestionRun, BackgroundJob]:
    try:
        normalized, host = _validate_url(url)
    except FetchError as exc:
        raise ApiError(exc.status_code, exc.code, exc.message) from exc
    run = IngestionRun(requested_by=user_id, url=normalized, host=host, status="queued")
    db.add(run)
    db.flush()
    job = BackgroundJob(
        kind="ingestion",
        payload={"run_id": str(run.id), "url": normalized},
        requested_by=user_id,
        status="queued",
    )
    db.add(job)
    db.flush()
    return run, job


def _process_ingestion(db: Session, job: BackgroundJob) -> None:
    run_id = job.payload.get("run_id")
    run = db.get(IngestionRun, run_id) if run_id else None
    if run is None:
        raise FetchError("run_missing", "The ingestion run record no longer exists.")
    try:
        document = fetch_document(job.payload.get("url", run.url))
    except FetchError as exc:
        run.status = "failed"
        run.error = exc.code
        run.finished_at = datetime.now(UTC)
        raise
    source = SourceDocument(
        url=document.final_url,
        host=document.host,
        title=document.title,
        publisher=document.host,
        source_type="official_page",
        http_status=document.status_code,
        content_hash=document.content_hash,
        byte_size=document.byte_size,
        policy_approved=True,
        retrieved_at=document.retrieved_at,
    )
    db.add(source)
    db.flush()
    run.status = "succeeded"
    run.http_status = document.status_code
    run.content_hash = document.content_hash
    run.byte_size = document.byte_size
    run.source_document_id = source.id
    run.finished_at = datetime.now(UTC)


def process_job(db: Session, job: BackgroundJob) -> None:
    job.status = "running"
    job.started_at = datetime.now(UTC)
    job.attempts += 1
    db.flush()
    try:
        if job.kind == "ingestion":
            _process_ingestion(db, job)
        elif job.kind == "deletion_purge":
            from app.services import privacy

            privacy.purge_expired_accounts(db)
        else:
            raise FetchError("unsupported_job", f"Unsupported job kind: {job.kind}")
        job.status = "succeeded"
        job.finished_at = datetime.now(UTC)
    except FetchError as exc:
        job.status = "failed"
        job.last_error = exc.code
        job.finished_at = datetime.now(UTC)
    except Exception as exc:  # noqa: BLE001 - recorded, not exposed
        logger.exception("job failed: %s", job.kind)
        job.status = "failed"
        job.last_error = type(exc).__name__
        job.finished_at = datetime.now(UTC)


def run_queue(db: Session, limit: int = 10) -> list[str]:
    jobs = db.scalars(
        select(BackgroundJob).where(BackgroundJob.status == "queued").order_by(BackgroundJob.created_at).limit(limit)
    ).all()
    results: list[str] = []
    for job in jobs:
        process_job(db, job)
        results.append(f"{job.kind}:{job.status}")
    return results
