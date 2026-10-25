# Testing and evaluation

How the build is verified, what the tests actually cover, and the measured evaluation
results. Numbers below are the real output of the commands on this machine at the
recorded date; they are not aspirational targets.

## Commands

```bash
# Backend — lint, tests (needs PostgreSQL), evaluation, dependency audit
cd backend
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m pytest
.venv/Scripts/python -m evaluation.run_eval
.venv/Scripts/python -m pip_audit --skip-editable

# Frontend — typecheck, unit tests, production build, dependency audit
cd frontend
npx tsc --noEmit
npm test
npm run build
npm audit --audit-level=high

# Container stack (Docker daemon required)
docker compose up --build

# Secret scan (not installed on the verification machine)
gitleaks detect --source . --no-git
```

## Test inventory

| Suite | File | Focus |
| --- | --- | --- |
| Unit | `backend/tests/test_units.py` | Validation, normalization, language detection, eligibility rules, grounding validation, consent transitions, security primitives |
| Integration (auth) | `backend/tests/test_auth_flows.py` | Registration, login/logout, session revocation and expiry, CSRF, cross-origin rejection, password reset, OTP limits, MFA login, mass-assignment rejection |
| Integration (catalogue) | `backend/tests/test_catalogue_flow.py` | Search, scheme detail, eligibility evaluation, checklist, draft lifecycle with provenance, profile-reuse permission, export |
| Security / admin / assistant | `backend/tests/test_security_admin.py` | Consent withdrawal, export/deletion including search history, admin authorization + MFA, ingestion host allowlist, assistant grounding and prompt-injection rejection, scheme-scoped evidence, headers, request-size limit, XSS, audit hygiene |
| Frontend unit | `frontend/tests/lib.test.ts` | Translation fallback, language-query handling, API error mapping, field-issue mapping, server-side cookie safety |

## Final measured results (2026-10-23; backend and frontend rerun 2026-10-25)

| Check | Command | Actual result |
| --- | --- | --- |
| Backend lint | `.venv/Scripts/python -m ruff check .` | PASS, `All checks passed!` |
| Backend tests (real PostgreSQL) | `.venv/Scripts/python -m pytest` | PASS, **110 passed, 0 failed** in 32.68 s (final clean rerun) |
| Frontend typecheck | `npx tsc --noEmit` | PASS, exit 0, no diagnostics |
| Frontend unit tests | `npm test` | PASS, **12 passed** (Vitest 5.0.5) |
| Frontend production build | `npm run build` | PASS, Next.js 15.5.28, 17/17 pages generated |
| Retrieval evaluation | `.venv/Scripts/python -m evaluation.run_eval` | recall@5 1.00, precision@5 0.71, MRR@5 0.81, attribution 100%, negative controls 5/5, median 5.8 ms |
| Backend dependency audit | `.venv/Scripts/python -m pip_audit --skip-editable` | PASS, no known vulnerabilities (local editable package skipped) |
| Frontend dependency audit | `npm audit --audit-level=high` | PASS, 0 vulnerabilities |
| Docker Compose build + run | `docker compose up --build` (temporary host-port override) | PASS: db healthy, migrations+seed exit 0, API healthy, worker running, web running; 17/17 HTTP probe against the containerised stack |
| End-to-end browser journey | manual, see [verification-report.md](verification-report.md) | Citizen, consent, search, eligibility, assistant, draft/export, deletion and reviewer-approval paths exercised |
| Secret scan | `gitleaks detect` | **BLOCKED**, gitleaks not installed |
| GitHub Actions workflow | runner | **NOT TESTED**, no runner available |

The 17-check live HTTP probe and the containerised rerun are stored under
[`docs/verification/evidence/`](verification/evidence/). Pytest emits two
non-blocking deprecation warnings (Starlette's TestClient/httpx recommendation and
Alembic's missing `path_separator`); they are visible in the captured output and were
not suppressed.

## Security controls exercised by tests

CSRF required for mutations; cross-origin mutation rejected; expired session rejected;
cross-device session revocation; generic login failure and account-enumeration
resistance; mass-assignment (role) rejection; per-object authorization (foreign draft →
404); OTP attempt limit; MFA gate for reviewer/admin; admin route denial for citizen and
anonymous; ingestion host-allowlist rejection; oversized request → 413; security headers
present; draft values returned as data not markup (XSS); audit metadata free of
credentials; `GET /me` never exposes secrets; grounding rejects fabricated provider
output (unknown citation, unsupported number, foreign URL).

## Evaluation (reproducible)

`backend/evaluation/dataset.json` holds 26 reviewer-labelled multilingual queries
(14 English, 7 Hindi, 5 Tamil) over the seeded catalogue, including negative controls
for topics the catalogue does not cover. `python -m evaluation.run_eval` runs them
through the same search service the API uses, at a top-five cut-off, and writes
`docs/evaluation/results.md`.

Metrics are macro-averaged per slice: `recall@5` (expected records found in the top
five), `precision@5` (share of returned records that were expected), `MRR@5`, source
attribution (official URL on the approved list + a stored source document), link
verification (recorded HTTP check returned 200), and negative-control passes (an
unsupported query must return nothing).

Key measured results (see `docs/evaluation/results.md` for the full per-query table):

- recall@5 = 1.00 across all three languages; precision@5 ≈ 0.71; MRR@5 ≈ 0.81.
- Source attribution 100% of returned records; link verification ≈ 58% (two seeded
  official pages were unreachable from the build environment and are flagged, not
  counted as verified).
- All 5 negative controls returned no records (no fabricated schemes).
- Median search latency ≈ 6 ms (single process, local database).

These numbers describe the small development catalogue (a handful of schemes, partial
Hindi/Tamil coverage) and this dataset only. They are not claims about production
retrieval quality.

## Browser end-to-end

A manual browser walkthrough was performed against the local frontend and API on
2026-10-23. It covered registration, Hindi profile and consents, mock phone
verification, PIN-code address lookup, search, scheme detail, eligibility, the
scheme-scoped assistant, draft create/edit/confirm/export, consent withdrawal and
re-grant, account deletion, administrator MFA login, ingestion-host rejection, and
reviewer approval of a disposable scheme. The approval was confirmed in PostgreSQL
(`review_status=verified`, `schemes.is_published=true`,
`scheme_version.approved` audit event). Details are recorded in
[`docs/verification/evidence/browser-e2e.md`](verification/evidence/browser-e2e.md).

There is no automated Playwright/Cypress suite. The manual walkthrough is evidence
that the rendered UI works; it is not a substitute for a repeatable browser test suite.

## Accessibility

Reviewed manually: semantic landmarks, labelled inputs, visible focus, keyboard
navigation, `aria-live` for async status, sufficient contrast, responsive layout.
**Not** audited with a screen reader or an automated axe scan; this is a documented
gap, not a pass.

## Performance

Search and eligibility are measured in the evaluation run (median ≈ 6 ms locally).
There is no load or soak test; horizontal scaling is blocked by the single-process rate
limiter (see [limitations.md](limitations.md)).

## What is NOT verified here

- No automated browser end-to-end suite (Playwright/Cypress). The manual walkthrough
  above is the only UI-level evidence.
- No real SMS, SMTP, LLM, translation-HTTP, transcription or OIDC provider was
  exercised — only the deterministic adapters and their structured-failure paths.
- A secret scan was not executed: `gitleaks` is not installed on this machine.
- CI (`.github/workflows/ci.yml`) was authored but not executed on GitHub Actions.
- No load/soak test, automated accessibility audit, backup/restore drill, TLS/HSTS
  deployment check, monitoring validation, penetration test or external audit.
- Docker Compose was built and exercised only on the local Docker daemon with a
  temporary host-port override; it was not tested on a production host.
