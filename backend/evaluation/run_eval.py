"""Reproducible retrieval and source-attribution evaluation.

    cd backend
    python -m evaluation.run_eval

Runs against the currently configured database. Metrics are measured, never assumed:
- recall@5: share of expected records found in the top five results
- precision@5: share of the returned top five that were expected
- MRR@5: reciprocal rank of the first expected result
- source attribution: every returned record must carry an official URL whose host is
  on the approved source list, with a stored source document
- link verification: share of returned records whose recorded link check succeeded
  (a failed check is flagged, not counted as verified)
- negative controls: unsupported queries must return no catalogue records

Writes a markdown report with the actual numbers and the sample size.
"""

from __future__ import annotations

import json
import statistics
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from app.core.config import settings
from app.db import SessionLocal
from app.models import Scheme, SchemeVersion
from app.services import search

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "dataset.json"
REPORT = ROOT.parents[1] / "docs" / "evaluation" / "results.md"


def _host(url: str | None) -> str:
    host = (urlsplit(url or "").hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _approved(url: str | None, approved: list[str]) -> bool:
    host = _host(url)
    return bool(host) and host in {_host(f"https://{item}") for item in approved}


def main() -> None:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = payload["cases"]
    results: list[dict] = []
    by_language: dict[str, list[dict]] = defaultdict(list)
    latencies: list[float] = []

    with SessionLocal() as db:
        for case in cases:
            started = time.perf_counter()
            response = search.search_schemes(
                db,
                query=case["query"],
                language=case["language"],
                page_size=5,
                sort="relevance",
            )
            latencies.append((time.perf_counter() - started) * 1000)
            returned = [item["slug"] for item in response["items"]]
            expected = case["expected"]
            hits = [slug for slug in returned if slug in expected]
            recall = (len(hits) / len(expected)) if expected else (1.0 if not returned else 0.0)
            precision = (len(hits) / len(returned)) if returned else 0.0
            reciprocal = 0.0
            for index, slug in enumerate(returned, start=1):
                if slug in expected:
                    reciprocal = 1.0 / index
                    break
            if not expected:
                precision = 1.0 if not returned else 0.0

            attribution_ok = True
            link_ok = True
            for item in response["items"]:
                scheme = db.query(Scheme).filter(Scheme.slug == item["slug"]).one()
                version = db.get(SchemeVersion, scheme.current_version_id)
                host_ok = _approved(scheme.official_url, settings.approved_ingest_hosts)
                source_present = version is not None and version.source_document is not None
                attribution_ok = attribution_ok and host_ok and source_present
                link_ok = link_ok and bool(source_present and version.source_document.http_status == 200)

            row = {
                **case,
                "returned": returned,
                "recall": recall,
                "precision": precision,
                "reciprocal": reciprocal,
                "attribution": attribution_ok,
                "links_verified": link_ok,
                "latency_ms": latencies[-1],
            }
            results.append(row)
            by_language[case["language"]].append(row)

    def average(rows: list[dict], key: str) -> float:
        return statistics.fmean(row[key] for row in rows) if rows else 0.0

    summary = {
        language: {
            "n": len(rows),
            "recall@5": average(rows, "recall"),
            "precision@5": average(rows, "precision"),
            "mrr@5": average(rows, "reciprocal"),
            "attribution": sum(row["attribution"] for row in rows) / len(rows),
            "links_verified": sum(row["links_verified"] for row in rows) / len(rows),
        }
        for language, rows in by_language.items()
    }
    overall = {
        "n": len(results),
        "recall@5": average(results, "recall"),
        "precision@5": average(results, "precision"),
        "mrr@5": average(results, "reciprocal"),
        "attribution": sum(row["attribution"] for row in results) / len(results),
        "links_verified": sum(row["links_verified"] for row in results) / len(results),
        "p50_latency_ms": statistics.median(latencies),
        "negative_controls": sum(1 for row in results if not row["expected"]),
        "negative_control_passes": sum(1 for row in results if not row["expected"] and not row["returned"]),
    }
    negative_failures = [
        row for row in results if not row["expected"] and row["returned"]
    ]

    lines = [
        "# Retrieval and source evaluation",
        "",
        f"Measured at: {datetime.now(UTC).isoformat()}",
        f"Dataset: `backend/evaluation/dataset.json` (version {payload['version']})",
        f"Sample size: {overall['n']} queries — "
        + ", ".join(f"{language}: {info['n']}" for language, info in sorted(summary.items())),
        "",
        "## Method",
        "",
        "1. Each query is sent through the same search service the API uses, with the query",
        "   language as the content-language filter and a top-five cut-off.",
        "2. A result is a hit only if its slug is in the reviewer-defined expected list.",
        "3. recall@5 is macro-averaged over expected records; precision@5 is the share of",
        "   returned records that were expected; negative controls count as a pass when the",
        "   service returns no record at all.",
        "4. Every returned record is checked for an official URL on the approved source list",
        "   and for a stored source document. A link counts as verified only when the",
        "   recorded HTTP check returned 200.",
        "",
        "The catalogue is the development dataset in this repository (8 schemes, 4 with",
        "development Hindi/Tamil translations). These numbers describe this dataset only.",
        "",
        "## Summary",
        "",
        "| Slice | Queries | recall@5 | precision@5 | MRR@5 | attribution | links verified |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for language, info in sorted(summary.items()):
        lines.append(
            f"| {language} | {info['n']} | {info['recall@5']:.2f} | {info['precision@5']:.2f} | "
            f"{info['mrr@5']:.2f} | {info['attribution'] * 100:.0f}% | {info['links_verified'] * 100:.0f}% |"
        )
    lines.append(
        f"| overall | {overall['n']} | {overall['recall@5']:.2f} | {overall['precision@5']:.2f} | "
        f"{overall['mrr@5']:.2f} | {overall['attribution'] * 100:.0f}% | {overall['links_verified'] * 100:.0f}% |"
    )
    lines += [
        "",
        f"Median search latency: {overall['p50_latency_ms']:.1f} ms (single process, local database).",
        f"Negative controls: {overall['negative_control_passes']}/{overall['negative_controls']} returned no records.",
        "",
        "## Per-query results",
        "",
        "| ID | Language | Query | Expected | Returned (top 5) | recall | precision |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in results:
        lines.append(
            f"| {row['id']} | {row['language']} | {row['query']} | "
            f"{', '.join(row['expected']) or '—'} | {', '.join(row['returned']) or '—'} | "
            f"{row['recall']:.2f} | {row['precision']:.2f} |"
        )
    lines += [
        "",
        "## Known limitations surfaced by this evaluation",
        "",
        "- Hindi and Tamil retrieval only covers the four schemes with development",
        "  translations; `hi-06` and `ta-05` are negative controls for that gap, not",
        "  evidence that the schemes do not exist.",
        "- Translations in the catalogue are marked `draft` and were not reviewed by a",
        "  professional translator. Translation quality has not been measured against a",
        "  reference corpus.",
        "- Ranking uses PostgreSQL full-text search with the `simple` configuration plus a",
        "  keyword fallback. There is no learned ranker and no semantic retrieval.",
        "- Two seeded official links (PM-JAY and PM-KISAN) could not be reached from the",
        "  build environment and are flagged unverified; see",
        "  `docs/evaluation/links.md`.",
    ]
    if negative_failures:
        lines += ["", "## Negative-control failures", ""]
        for row in negative_failures:
            lines.append(f"- {row['id']} returned {', '.join(row['returned'])}")
    else:
        lines += ["", "## Negative-control failures", "", "None."]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"evaluated {overall['n']} queries")
    print(json.dumps(overall, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"report written to {REPORT}")


if __name__ == "__main__":
    main()
