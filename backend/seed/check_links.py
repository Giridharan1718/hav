"""Re-check official source links and record the result.

    cd backend
    python -m seed.check_links [--markdown ../docs/evaluation/links.md]

Records HTTP status, retrieval time and a content hash for the official page and the
application page. A successful check only moves a version from ``pending_review`` to
``source_checked``; it never marks content as human-verified.
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import UTC, datetime

import httpx
from sqlalchemy import select

from app.db import SessionLocal
from app.models import ReviewStatus, Scheme, SchemeVersion, SourceDocument

USER_AGENT = "HVA-LinkCheck/0.1 (automated source availability check)"
MAX_SAMPLE_BYTES = 400_000


def probe(url: str) -> tuple[int | None, str | None, int | None]:
    try:
        with httpx.Client(follow_redirects=True, timeout=40, headers={"User-Agent": USER_AGENT}) as client:
            with client.stream("GET", url) as response:
                buffer = bytearray()
                for chunk in response.iter_bytes():
                    buffer.extend(chunk)
                    if len(buffer) >= MAX_SAMPLE_BYTES:
                        break
                return response.status_code, hashlib.sha256(bytes(buffer)).hexdigest(), len(buffer)
    except httpx.HTTPError as exc:
        print(f"  check failed for {url}: {type(exc).__name__}")
        return None, None, None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", default=None, help="write a markdown report to this path")
    args = parser.parse_args()

    rows: list[tuple[str, str, str, str, str]] = []
    with SessionLocal() as db:
        schemes = db.scalars(select(Scheme).order_by(Scheme.slug)).all()
        for scheme in schemes:
            version = db.get(SchemeVersion, scheme.current_version_id) if scheme.current_version_id else None
            if version is None:
                continue
            print(f"checking {scheme.slug}")
            status, digest, size = probe(scheme.official_url)
            app_status = status if version.application_url == scheme.official_url else probe(version.application_url)[0]
            now = datetime.now(UTC)
            source = db.get(SourceDocument, version.source_document_id) if version.source_document_id else None
            if source is not None:
                source.http_status = status
                source.content_hash = digest
                source.byte_size = size
                source.retrieved_at = now
            version.application_url_http_status = app_status
            version.application_url_checked_at = now
            if status == 200 and version.review_status == ReviewStatus.pending_review.value:
                version.review_status = ReviewStatus.source_checked.value
            rows.append(
                (
                    scheme.slug,
                    scheme.official_url,
                    str(status) if status else "unavailable",
                    str(app_status) if app_status else "unavailable",
                    version.review_status,
                )
            )
            print(f"  official={status} application={app_status} status={version.review_status}")
        db.commit()

    if args.markdown:
        lines = [
            "# Official source link check",
            "",
            f"Checked at: {datetime.now(UTC).isoformat()}",
            "",
            "| Scheme | Official source | Official HTTP | Application HTTP | Review status |",
            "| --- | --- | --- | --- | --- |",
        ]
        for slug, url, status, app_status, review in rows:
            lines.append(f"| {slug} | {url} | {status} | {app_status} | {review} |")
        lines += [
            "",
            "`unavailable` means the page could not be fetched from the checking environment; it is",
            "displayed as unverified, never as working. A successful check is not a content review",
            "and does not produce the `verified` state.",
            "",
        ]
        from pathlib import Path

        path = Path(args.markdown)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
