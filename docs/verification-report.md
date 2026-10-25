# HVA — Verification Report

**Report date:** 2026-10-25
**Verification runs:** 2026-10-23 (local API/UI) and 2026-10-23 (Docker Compose); final backend and frontend regression run 2026-10-25
**Scope:** the repository at `C:\Users\girid\Downloads\HVA`, the local PostgreSQL service, the local API/UI, and a locally built Docker Compose stack.
**Status vocabulary:** PASS, FAIL, BLOCKED, NOT TESTED only. A PASS means the stated check was executed on this machine and the result was inspected. It does not mean production-ready.

## 1. Environment

| Item | Value |
| --- | --- |
| Backend | Python 3.12.10, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16.4 |
| Frontend | Next.js 15.5.28, React 19, TypeScript, Vitest 5.0.5 |
| Database | local portable PostgreSQL at `127.0.0.1:55432`; test database `hva_test` |
| Local API | `http://127.0.0.1:8010` |
| Local web | `http://localhost:3000` |
| Docker | Docker 29.9.2, Compose v5.6.1; stack built and run with a temporary host-port override |
| Repository | Git repository initialised by the environment; verification was performed on the working tree, then the verified snapshot was committed for delivery |

Older phase reports under `docs/verification/` are retained as historical records. Some
contain pre-fix counts, stale port numbers or superseded claims (for example, the
earlier Docker report's `55433` port experiment and the earlier 109-test reports). This
file is the authoritative verification report; `docs/testing.md` and
`docs/production-readiness.md` were updated to match it.

**Repository integrity note.** During final delivery, an external process emptied
`frontend/lib` and `frontend/tests` and replaced the verified `next.config.ts` /
`tsconfig.json` with unverified variants. The missing `lib` files, `next.config.ts`,
`next-env.d.ts`, `tsconfig.json` and `components/useRequireAuth.ts` were recovered
byte-for-byte from the verified Docker build-cache layer (snapshot 27). The 12-test
`frontend/tests/lib.test.ts` was reconstructed from the recorded test source and the
exact strings in `lib/strings.ts`. The restored tree was re-verified: `tsc --noEmit`
exit 0, Vitest 12/12, `npm run build` generated 17/17 pages, and `docker build frontend`
exited 0. The unverified `next.config.js` / `jsconfig.json` variants were removed.

## 2. Requirements matrix

### 2.1 Environment and delivery

| Requirement ID | Feature | Implementation status | Exact verification command/test | Actual result | Evidence/log location | Remaining defect/blocker |
| --- | --- | --- | --- | --- | --- | --- |
| ENV-01 | Repository, manifests, dependencies, frontend/backend/database/env/tests inspected before edits | PASS | Manual inspection plus baseline `ruff`, `pytest`, `tsc`, `npm test`, `npm run build` | All baseline checks executed; defects recorded and fixed | `docs/verification/baseline.md`; this report §3 | None |
| ENV-02 | Backend reproducible on a clean local environment | PASS | `cd backend; .venv/Scripts/python -m ruff check .; .venv/Scripts/python -m pytest` | Ruff exit 0; pytest 110 passed, 0 failed (final run) | `docs/verification/evidence/pytest-110.txt`, `ruff.txt` | CI runner not executed |
| ENV-03 | Frontend reproducible on a clean local environment | PASS | `cd frontend; npx tsc --noEmit; npm test; npm run build` | Typecheck exit 0; Vitest 12 passed; Next.js build generated 17/17 pages | `docs/verification/evidence/tsc.txt`, `vitest-12.txt`, `next-build.txt` | No automated browser suite |

### 2.2 Authentication and account security

| Requirement ID | Feature | Implementation status | Exact verification command/test | Actual result | Evidence/log location | Remaining defect/blocker |
| --- | --- | --- | --- | --- | --- | --- |
| AUTH-01 | Registration requires privacy notice, enforces password policy, creates citizen session | PASS | `pytest tests/test_auth_flows.py -k "registration"`; browser registration | Tests pass; browser registration succeeded with Hindi preference | `backend/tests/test_auth_flows.py`; `docs/verification/evidence/browser-e2e.md` | None |
| AUTH-02 | Login, logout, session expiry, cross-device revocation, generic failures, lockout | PASS | `pytest tests/test_auth_flows.py -k "login or session or expired"` | All selected tests pass; old credentials rejected after deletion | `backend/tests/test_auth_flows.py`; browser E2E | None |
| AUTH-03 | TOTP MFA mandatory for reviewer/admin routes | PASS | `pytest tests/test_security_admin.py -k "mfa or reviewer_without_mfa"`; browser admin login | Tests pass; reviewer/admin login required MFA and succeeded | `backend/tests/test_security_admin.py`; browser E2E | None |
| AUTH-04 | Password reset and phone OTP flows with mock/outbox adapters | PASS | `pytest tests/test_auth_flows.py -k "password_reset or otp or phone"` | Tests pass; browser mock phone verification succeeded | `backend/tests/test_auth_flows.py`; browser E2E | Real SMS/email providers BLOCKED (EXT-01/02) |
| AUTH-05 | CSRF, Origin validation, request-size limit, login rate limiting | PASS | `pytest tests/test_auth_flows.py tests/test_security_admin.py -k "csrf or origin or oversized or lock"`; live CSRF rejection | All selected tests pass; a live CSRF rejection returned 403 with the security headers | `docs/verification/evidence/live-api-probe.txt` | Rate limiter is in-memory (SEC-09) |

### 2.3 Profile, consent and personalisation

| Requirement ID | Feature | Implementation status | Exact verification command/test | Actual result | Evidence/log location | Remaining defect/blocker |
| --- | --- | --- | --- | --- | --- | --- |
| PROF-01 | Profile read/update with saved language | PASS | `pytest tests/test_catalogue_flow.py -k "profile or prefill"`; browser profile save | Tests pass; browser saved Hindi profile | `backend/tests/test_catalogue_flow.py`; browser E2E | None |
| PROF-02 | Phone verification with mock OTP | PASS | `pytest tests/test_auth_flows.py -k "phone_challenge or otp_attempt"`; browser verification | Tests pass; browser phone verified | `backend/tests/test_auth_flows.py`; browser E2E | Real SMS provider BLOCKED (EXT-01) |
| PROF-03 | PIN-code post-office lookup and address confirmation | PASS | `pytest tests/test_catalogue_flow.py -k "pincode or post_office or address"`; browser lookup | Tests pass; browser found and confirmed a post office | `backend/tests/test_catalogue_flow.py`; browser E2E | Authoritative India Post data BLOCKED (EXT-07) |
| CONS-01 | Purpose-specific consent grant/withdraw; required consent cannot be withdrawn | PASS | `pytest tests/test_security_admin.py::test_consent_withdrawal_and_required_consent`; browser consent settings | Test passes; UI shows “Ends only with account deletion” and no Withdraw button for required consent | `backend/tests/test_security_admin.py`; browser E2E | None |
| CONS-02 | AI-assistant consent gates saved-language personalisation and external provider use | PASS | `pytest tests/test_security_admin.py::test_assistant_personalisation_requires_consent tests/test_security_admin.py::test_assistant_provider_requires_ai_consent`; live probe | Tests pass; live probe: consent off → `language=en`, consent on → `language=hi`; provider remains deterministic | `docs/verification/evidence/live-api-probe.txt` | No real LLM provider (EXT-03) |

### 2.4 Catalogue, search and source evidence

| Requirement ID | Feature | Implementation status | Exact verification command/test | Actual result | Evidence/log location | Remaining defect/blocker |
| --- | --- | --- | --- | --- | --- | --- |
| CAT-01 | Search, filters, pagination and parameterised queries | PASS | `pytest tests/test_catalogue_flow.py -k "search or pagination or injection"`; browser search | Tests pass; browser `scholarship` search returned the expected record | `backend/tests/test_catalogue_flow.py`; browser E2E | None |
| CAT-02 | English/Hindi/Tamil search and translation fallback | PASS | `pytest tests/test_units.py -k "language or query_expansion" tests/test_catalogue_flow.py -k "language_filter"`; evaluation | Tests pass; recall@5 1.00 across en/hi/ta; missing translations flagged | `docs/verification/evidence/evaluation.txt` | Professional Hindi/Tamil review BLOCKED (EXT-08) |
| CAT-03 | Scheme detail shows official source, retrieval time and review status | PASS | `pytest tests/test_catalogue_flow.py -k "scheme_detail or evidence"`; browser detail page | Tests pass; browser detail page displayed source and “Awaiting content review” | `backend/tests/test_catalogue_flow.py`; browser E2E | Some source links unreachable from build machine |
| CAT-04 | Source-link checks recorded and unverified links flagged | PASS | `python -m evaluation.run_eval`; `seed.check_links` output | 58% of returned records have a recorded HTTP 200; others remain flagged, not counted as verified | `docs/verification/evidence/evaluation.txt`; `docs/evaluation/results.md` | Re-check links from a networked production host |

### 2.5 Deterministic eligibility

| Requirement ID | Feature | Implementation status | Exact verification command/test | Actual result | Evidence/log location | Remaining defect/blocker |
| --- | --- | --- | --- | --- | --- | --- |
| ELIG-01 | Deterministic eligibility outcomes (eligible / not eligible / insufficient information) | PASS | `pytest tests/test_units.py -k "eligibility"`; browser questionnaire | Tests pass; browser result `eligible` with all four rules met | `backend/tests/test_units.py`; browser E2E | None |
| ELIG-02 | Localised questions, profile prefill, value validation and unsupported-rule refusal | PASS | `pytest tests/test_units.py -k "eligibility_questions or eligibility_validates or unsupported_rule"` | All selected tests pass | `backend/tests/test_units.py` | None |
| ELIG-03 | Sensitive answers evaluated in-request and not persisted; model output cannot decide eligibility | PASS | `pytest tests/test_units.py::test_eligibility_does_not_use_model_output tests/test_units.py::test_eligibility_rejects_unrelated_personal_fields` | Both tests pass | `backend/tests/test_units.py` | None |

### 2.6 Assistant

| Requirement ID | Feature | Implementation status | Exact verification command/test | Actual result | Evidence/log location | Remaining defect/blocker |
| --- | --- | --- | --- | --- | --- | --- |
| AST-01 | Grounded answers with citations; no invented scheme/number/URL | PASS | `pytest tests/test_security_admin.py -k "assistant or grounding"`; browser assistant | Tests pass; browser answer cited the selected scheme; grounding rejects fabricated output | `backend/tests/test_security_admin.py`; browser E2E | Deterministic composer is less fluent than an LLM |
| AST-02 | Hindi/Tamil answers and explicit missing-translation flag | PASS | `pytest tests/test_security_admin.py::test_assistant_answers_hindi_and_flags_missing_translation`; browser Hindi answer | Test passes; browser answer body was Devanagari | `backend/tests/test_security_admin.py`; browser E2E | Translation quality unreviewed |
| AST-03 | Scheme-scoped assistant uses only the selected scheme's record | PASS | `pytest tests/test_security_admin.py::test_assistant_scheme_focus_excludes_unrelated_matches`; browser scheme-scoped assistant | Test passes; the browser answer cited the selected scheme only; the regression test also verifies missing labels are deduplicated | `backend/tests/test_security_admin.py`; `docs/verification/evidence/browser-e2e.md` | None |
| AST-04 | Assistant consent and saved-language gating; explicit request language wins | PASS | `pytest tests/test_security_admin.py -k "personalisation or provider_requires"`; live probe; browser | Tests pass; live probe confirms consent gating; browser defaults to saved Hindi with consent | `docs/verification/evidence/live-api-probe.txt`; browser E2E | None |
| AST-05 | Speech transcription | BLOCKED | `pytest tests/test_security_admin.py::test_transcription_requires_consent_and_provider`; `/assistant/transcribe` | Test passes for the disabled path; endpoint returns structured 503 when no provider is configured | `backend/tests/test_security_admin.py` | No speech provider credentials (EXT-05) |

### 2.7 Drafts

| Requirement ID | Feature | Implementation status | Exact verification command/test | Actual result | Evidence/log location | Remaining defect/blocker |
| --- | --- | --- | --- | --- | --- | --- |
| DRF-01 | Draft create/prefill/edit/confirm/save with per-field provenance | PASS | `pytest tests/test_catalogue_flow.py::test_draft_lifecycle_and_provenance`; browser draft flow | Test passes; browser draft saved and exported | `backend/tests/test_catalogue_flow.py`; browser E2E | None |
| DRF-02 | Draft ownership enforced; draft values rendered as data not markup | PASS | `pytest tests/test_catalogue_flow.py -k "draft_ownership or draft_values"` | Both tests pass; foreign draft returns 404; XSS payload not executed | `backend/tests/test_catalogue_flow.py` | None |
| DRF-03 | Draft export | PASS | Browser export; `pytest tests/test_catalogue_flow.py::test_draft_lifecycle_and_provenance` | Downloaded 755-byte `.txt` with expected fields | `docs/verification/evidence/browser-e2e.md` | None |

### 2.8 Privacy and retention

| Requirement ID | Feature | Implementation status | Exact verification command/test | Actual result | Evidence/log location | Remaining defect/blocker |
| --- | --- | --- | --- | --- | --- | --- |
| PRV-01 | Data export requires reauthentication, includes search history, omits secrets | PASS | `pytest tests/test_security_admin.py -k "export"`; live export probe | Test passes and asserts password/hash/token fields are absent; the live export contained the recorded search history | `backend/tests/test_security_admin.py`; `docs/verification/evidence/live-api-probe.txt` | None |
| PRV-02 | Account deletion immediately removes profile/address/drafts/consents/search history/sessions and anonymises the account | PASS | `pytest tests/test_security_admin.py::test_account_deletion_removes_personal_data_and_sessions`; browser deletion; live probe | Test passes; browser deletion signed out the user and old credentials failed; live probe confirmed zero linked search rows | `docs/verification/evidence/live-api-probe.txt`; browser E2E | 30-day retention is deliberate |
| PRV-03 | Scheduled hard purge after retention window | PASS | `pytest tests/test_security_admin.py::test_worker_purges_accounts_after_retention`; worker run | New regression test passes; worker tick purges expired scheduled accounts and reports `deletion_purge:purged=1` | `backend/app/jobs/worker.py`; `backend/tests/test_security_admin.py`; `docs/verification/evidence/pytest-110.txt` | Production worker must run continuously |
| PRV-04 | Privacy notice and UI copy match actual export/deletion behaviour | PASS | Browser privacy/consent pages; `pytest tests/test_security_admin.py -k "consent"` | Copy mentions search history and required-consent retention; tests pass | `frontend/app/privacy/page.tsx`; `frontend/components/ConsentSettings.tsx`; browser E2E | Legal review BLOCKED (EXT-09) |

### 2.9 Administration and audit

| Requirement ID | Feature | Implementation status | Exact verification command/test | Actual result | Evidence/log location | Remaining defect/blocker |
| --- | --- | --- | --- | --- | --- | --- |
| ADM-01 | Admin overview returns numeric published-scheme count | PASS | `pytest tests/test_security_admin.py::test_admin_overview_reports_numeric_published_count`; live probe | Test passes; live overview `published_schemes=8` (int) matches catalogue | `docs/verification/evidence/live-api-probe.txt` | None |
| ADM-02 | Reviewer approval publishes the version and writes an audit event | PASS | `pytest tests/test_security_admin.py::test_review_approval_publishes_and_audits`; browser approval of disposable scheme | Test passes; browser approval set `review_status=verified`, `is_published=true`; audit `scheme_version.approved` with actor and notes | `docs/verification/evidence/browser-e2e.md` | Needs a real content-review rota in production |
| ADM-03 | Rejection requires a reason and unpublishes the version | PASS | `pytest tests/test_security_admin.py::test_rejection_requires_reason_and_unpublishes` | Test passes | `backend/tests/test_security_admin.py` | Not exercised in the browser |
| ADM-04 | Ingestion accepts only approved HTTPS hosts; SSRF/private-address protections | PASS | `pytest tests/test_security_admin.py -k "ingestion or source_url or private_addresses"`; browser ingestion form | Tests pass; browser unauthorised host returned 422 | `backend/tests/test_security_admin.py`; browser E2E | Real ingestion worker needs a production source allowlist |
| ADM-05 | Audit metadata excludes passwords, OTPs, tokens and questionnaire answers | PASS | `pytest tests/test_security_admin.py::test_audit_metadata_has_no_credentials` | Test passes | `backend/tests/test_security_admin.py` | None |

### 2.10 Security controls

| Requirement ID | Feature | Implementation status | Exact verification command/test | Actual result | Evidence/log location | Remaining defect/blocker |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Argon2id passwords, encrypted sensitive fields, hashed opaque tokens | PASS | `pytest tests/test_units.py -k "password_hash or encryption or token_hash or identifier_hash"` | All selected tests pass | `backend/tests/test_units.py` | Development keys are local only |
| SEC-02 | Security headers, CSRF and Origin validation on success and early rejection paths | PASS | `pytest tests/test_security_admin.py -k "headers or csrf or cross_origin"`; live probe | Tests pass; live 403 includes `x-content-type-options`, `x-frame-options`, referrer, permissions and CORP headers | `docs/verification/evidence/live-api-probe.txt` | CSP still allows inline/eval (SEC-08) |
| SEC-03 | Role/object authorization, mass-assignment rejection, no secret exposure | PASS | `pytest tests/test_security_admin.py -k "admin or ownership or mass_assignment or me_never"` | All selected tests pass | `backend/tests/test_security_admin.py` | None |
| SEC-04 | Request-size limits and per-route rate limiting | PASS | `pytest tests/test_auth_flows.py -k "oversized or lock"`; code review of limiter | Tests pass; limits are enforced in the single process | `backend/tests/test_auth_flows.py`; `backend/app/core/ratelimit.py` | In-memory limiter (SEC-09) |
| SEC-05 | Dependency vulnerability scans | PASS | `pip-audit --skip-editable`; `npm audit --audit-level=high` | pip-audit exit 0, no known vulnerabilities; npm audit 0 vulnerabilities | `docs/verification/evidence/pip-audit.txt`, `npm-audit.txt` | Local editable package skipped |
| SEC-06 | Secret scan | BLOCKED | `gitleaks detect --source . --no-git` | `gitleaks` is not installed; command not executed | `docs/verification/evidence/unexecuted-checks.md` | Install gitleaks or run CI secret-scan job |
| SEC-07 | External penetration test / WAF | NOT TESTED | Independent assessment | Not commissioned | — | Commission before public launch |
| SEC-08 | Content-Security-Policy without `unsafe-inline`/`unsafe-eval` | FAIL | Review of `frontend/next.config.ts` | CSP still permits inline/eval for the Next.js bootstrap; documented as a known gap | `docs/security.md`; `docs/limitations.md` | Requires nonce-based CSP work |
| SEC-09 | Shared rate-limit store for horizontal scaling | FAIL | Code review of `app/core/ratelimit.py` | Limiter is in-memory and per-process; no Redis/shared store | `backend/app/core/ratelimit.py` | Add shared store before scaling |

### 2.11 Infrastructure and quality gates

| Requirement ID | Feature | Implementation status | Exact verification command/test | Actual result | Evidence/log location | Remaining defect/blocker |
| --- | --- | --- | --- | --- | --- | --- |
| INF-01 | Backend lint | PASS | `.venv/Scripts/python -m ruff check .` | `All checks passed!`, exit 0 | `docs/verification/evidence/ruff.txt` | None |
| INF-02 | Backend test suite on real PostgreSQL | PASS | `.venv/Scripts/python -m pytest` | 110 passed, 0 failed | `docs/verification/evidence/pytest-110.txt` | CI execution not tested |
| INF-03 | Frontend typecheck | PASS | `npx tsc --noEmit` | Exit 0, no diagnostics | `docs/verification/evidence/tsc.txt` | None |
| INF-04 | Frontend unit tests | PASS | `npm test` | 12 passed (Vitest 5.0.5) | `docs/verification/evidence/vitest-12.txt` | No component/E2E tests |
| INF-05 | Frontend production build | PASS | `npm run build` | Next.js 15.5.28, 17/17 pages generated | `docs/verification/evidence/next-build.txt` | Deployment-host build not tested |
| INF-06 | Docker Compose build and run | PASS | `docker compose -p hva-probe -f docker-compose.yml -f <temp-override> up --build -d` | db healthy; migrate exit 0; API healthy; worker/web running; 17/17 HTTP probe; web search returned the scholarship record; clean `down -v` | `docs/verification/evidence/docker-compose.md`, `compose-probe.txt`, `compose-ps.txt` | Tested with dev secrets/mock adapters and a temporary host-port override |
| INF-07 | GitHub Actions CI execution | NOT TESTED | Push/run `.github/workflows/ci.yml` | Workflow authored; no runner available; not executed | `.github/workflows/ci.yml`; `unexecuted-checks.md` | Run on GitHub Actions |
| INF-08 | Retrieval/link evaluation | PASS | `.venv/Scripts/python -m evaluation.run_eval` | 26 queries; recall@5 1.00; precision@5 0.71; MRR@5 0.81; attribution 100%; negative controls 5/5; median 5.8 ms | `docs/verification/evidence/evaluation.txt`; `docs/evaluation/results.md` | Small development catalogue only |
| INF-09 | Load / soak test | NOT TESTED | Load generator | None run | — | Add shared rate-limit store and test beyond one instance |
| INF-10 | Automated accessibility audit | NOT TESTED | axe/screen-reader run | Manual review only | `docs/testing.md` | Run axe and a screen-reader pass |
| INF-11 | Backup and restore drill | NOT TESTED | Backup/restore procedure | No automation or drill | `docs/operations.md` | Configure encrypted backups and record a restore |
| INF-12 | TLS/HSTS/secure cookies in deployment | NOT TESTED | Deployed HTTPS check | No deployed environment | — | Verify at the reverse proxy |
| INF-13 | Monitoring and alerting | NOT TESTED | Log/metrics integration | Structured logs only | `docs/operations.md` | Wire logs to a managed store and add alerts |

### 2.12 External integrations and approvals

| Requirement ID | Feature | Implementation status | Exact verification command/test | Actual result | Evidence/log location | Remaining defect/blocker |
| --- | --- | --- | --- | --- | --- | --- |
| EXT-01 | Real SMS/OTP gateway | BLOCKED | Provider contract/delivery test | Mock adapter only; no credentials | `docs/adapters.md` | Funded gateway and approved sender |
| EXT-02 | Real SMTP email | BLOCKED | Password-reset delivery test | Outbox adapter only; no credentials | `docs/adapters.md` | SMTP relay with SPF/DKIM |
| EXT-03 | External LLM provider | BLOCKED | Configured provider test | Disabled; deterministic composer used | `docs/adapters.md` | API key, DPA, spending cap |
| EXT-04 | HTTP translation provider | BLOCKED | Provider quality/terms test | Catalogue mode only | `docs/adapters.md` | Vendor contract and review |
| EXT-05 | Speech-to-text provider | BLOCKED | Audio transcription test | Disabled; structured 503 | `docs/adapters.md` | Provider contract and audio evaluation |
| EXT-06 | OIDC/SSO | BLOCKED | Authorization-code flow test | Not implemented; flags only | `docs/adapters.md` | Implement flow with JWKS validation or remove flags |
| EXT-07 | Authoritative India Post dataset | BLOCKED | Dataset import and provenance check | Small seeded sample only | `docs/adapters.md` | Obtain data and reuse permission |
| EXT-08 | Professional Hindi/Tamil review | BLOCKED | Qualified reviewer sign-off | Four catalogue entries remain development translations; marked draft/unreviewed | `docs/verification/localization-report.md` | Engage qualified reviewers |
| EXT-09 | DPDP/legal and provider-contract review | BLOCKED | Counsel review | Not performed | `docs/privacy.md`; `docs/production-readiness.md` | Legal review before launch |
| EXT-10 | Grievance/support channel | BLOCKED | Published monitored channel | Not published | `docs/production-readiness.md` | Publish before launch |

### 2.13 Documentation

| Requirement ID | Feature | Implementation status | Exact verification command/test | Actual result | Evidence/log location | Remaining defect/blocker |
| --- | --- | --- | --- | --- | --- | --- |
| DOC-01 | API/architecture/limitations/privacy docs match implementation | PASS | Manual cross-check of endpoints, deletion path, links and copy | `total_pages` → `pages`; deletion path fixed; broken link fixed; privacy/AI-consent/search-history wording corrected | `docs/api.md`, `docs/architecture.md`, `docs/limitations.md`, `docs/privacy.md` | Docs must be maintained with code |
| DOC-02 | Honest production-readiness checklist and verification report | PASS | This report and `docs/production-readiness.md` | Gates split into PASS/FAIL/BLOCKED/NOT TESTED; Docker and dependency scans updated with evidence | `docs/production-readiness.md`; this report | None |
| DOC-03 | CI workflow authored | PASS | Review `.github/workflows/ci.yml` | Backend, frontend and secret-scan jobs defined; not executed | `.github/workflows/ci.yml` | Execution is INF-07 |

## 3. Defects found and fixed during verification

| # | Defect | Root cause | Fix | Regression evidence |
| --- | --- | --- | --- | --- |
| 1 | Search history and other committed writes could be invisible to the next request | `Depends(get_db)` closed the session after the response was sent, so commits could race the client | Changed every `Depends(get_db)` to `Depends(get_db, scope="function")` (49 occurrences) so the session commits before the response | Live probe: registration → consented search → export included the search row; full suite |
| 2 | Data export omitted search history; deletion left search-history rows | Privacy service did not include/delete `SearchHistory` | Added export section and deletion/purge deletes; updated copy/docstring | `test_data_export_requires_password_and_omits_secrets`; `test_account_deletion_removes_personal_data_and_sessions`; live probe |
| 3 | AI consent did not gate saved-language personalisation or external provider use | Assistant service always used the saved language/provider | Added `preferred_language` and consent checks; provider use requires AI consent | `test_assistant_personalisation_requires_consent`; `test_assistant_provider_requires_ai_consent`; live probe |
| 4 | Scheme-scoped assistant could cite unrelated search matches | Evidence collection used the whole search result set | Restricted evidence/citations to the requested `scheme_slug` | `test_assistant_scheme_focus_excludes_unrelated_matches`; browser scheme-scoped answer |
| 5 | Missing-information labels repeated (e.g. “Age” twice) | Labels appended without de-duplication | De-duplicated while preserving order | Same scheme-scope test asserts no duplicate labels |
| 6 | Admin overview `published_schemes` was a string/bool-like value | Count serialised inconsistently | Returned an integer under `counts` | `test_admin_overview_reports_numeric_published_count`; live probe |
| 7 | Security headers missing on early CSRF/413 rejections | Headers added only in the normal response path | Middleware applies headers to early rejections too | Live probe checks a 403 CSRF rejection for all headers |
| 8 | `?language=` links were ignored | Frontend language hook did not read the query string | Added `languageFromQuery`; hook honours valid values and writes the cookie | Frontend `lib.test.ts` language-query tests |
| 9 | Scheme assistant link lost scheme context | Eligibility page linked to `/assistant` without a slug | Link now includes `?scheme=<slug>`; assistant fetches and sends `scheme_slug` | Browser scheme-scoped answer; frontend tests |
| 10 | Assistant ignored saved profile language when AI consent was active | No default-language wiring in the UI | Defaults to saved language when consent is active; explicit `?language=`/manual choice wins | Browser Hindi default and Devanagari answer; live probe |
| 11 | Required consent offered a Withdraw button | UI treated every consent as withdrawable | Non-withdrawable consent shows “Ends only with account deletion” | Browser consent settings |
| 12 | Privacy copy did not mention search history | Copy lagged the data model | Updated privacy page and consent settings | Browser privacy page; `docs/privacy.md` |
| 13 | Admin UI lacked a published-schemes count card | UI omitted the overview field | Added the card | Browser admin page |
| 14 | Scheduled 30-day hard purge was never invoked | No worker path called `purge_expired_accounts`; `deletion_purge` jobs were never enqueued | Worker `tick()` now purges expired scheduled accounts; `User.profile/address` use `passive_deletes=True` so DB cascades work | `test_worker_purges_accounts_after_retention` |
| 15 | Known dependency advisories | Outdated `cryptography`, `pytest`, `vitest`, `vite`, `postcss` | Upgraded; `pip-audit` and `npm audit` now report zero known vulnerabilities | `pip-audit.txt`, `npm-audit.txt` |
| 16 | Documentation drift (pagination field, deletion path, broken link, privacy/consent wording) | Docs not updated with code | Corrected and cross-checked | `docs/api.md`, `docs/architecture.md`, `docs/limitations.md`, `docs/privacy.md` |

No tests were skipped or xfailed, and no assertions were weakened. The final clean backend run surfaced two non-blocking deprecation warnings (Starlette's TestClient/httpx recommendation and Alembic's missing `path_separator`); they remain visible in `pytest-110.txt`. One earlier rerun was invalidated by stale PostgreSQL locks from an interrupted pytest process; that process and its `hva_test` sessions were stopped, and the fixture recreated the schema for the final 110-pass run.

## 4. Evidence summary

| Evidence | Result | Location |
| --- | --- | --- |
| Backend lint | PASS | `docs/verification/evidence/ruff.txt` |
| Backend tests | 110 passed, 0 failed | `docs/verification/evidence/pytest-110.txt` |
| Frontend typecheck | PASS, no diagnostics | `docs/verification/evidence/tsc.txt` |
| Frontend unit tests | 12 passed | `docs/verification/evidence/vitest-12.txt` |
| Frontend build | PASS, 17/17 pages generated | `docs/verification/evidence/next-build.txt` |
| Retrieval evaluation | PASS, recall@5 1.00 | `docs/verification/evidence/evaluation.txt` |
| Live API probe | 17/17 checks | `docs/verification/evidence/live-api-probe.txt`, `live-api-probe.json` |
| Docker Compose probe | 17/17 checks | `docs/verification/evidence/compose-probe.txt`, `compose-probe-results.json`, `compose-ps.txt` |
| Browser E2E | Citizen, assistant, draft, deletion, admin/reviewer paths | `docs/verification/evidence/browser-e2e.md` |
| Dependency audits | pip-audit 0; npm audit 0 | `docs/verification/evidence/pip-audit.txt`, `npm-audit.txt` |
| Unexecuted checks | Secret scan, CI, external providers, audits | `docs/verification/evidence/unexecuted-checks.md` |

## 5. What works

- Local backend and frontend build, lint, typecheck and tests pass on the real PostgreSQL service.
- The citizen journey works end to end through the browser: registration, Hindi profile, consent, mock phone verification, PIN-code address lookup, search, scheme detail, deterministic eligibility, grounded assistant answer with citations, draft creation/edit/export, and account deletion.
- The assistant is scheme-scoped, consent-gated and multilingual; it defaults to the saved language only when AI consent is active.
- Reviewer/admin login requires TOTP MFA; the review queue, approval/publish action and audit event work; unauthorised ingestion hosts are rejected.
- Data export includes search history and omits secrets; deletion removes personal data and sessions immediately, anonymises the account, and the worker now purges expired scheduled accounts.
- Docker Compose builds and runs the database, migrations/seed, API, worker and web app; the containerised stack passed the same 17-check HTTP probe and served a working catalogue search.
- Dependency audits report no known vulnerabilities.

## 6. What does not work / is not complete

- No real SMS, SMTP, LLM, HTTP translation, speech-to-text or OIDC provider is configured or tested.
- The catalogue has only eight schemes and four development Hindi/Tamil translations; translations are unreviewed.
- Some seeded official links were unreachable from the build machine and remain flagged; link verification is 58% of returned records.
- The CSP still allows `unsafe-inline`/`unsafe-eval`; the rate limiter is in-memory and single-process.
- No secret scan, CI execution, penetration test, load/soak test, automated accessibility audit, backup/restore drill, TLS/HSTS deployment test or monitoring validation has been performed.
- No legal/DPDP review or published grievance channel exists.
- The Docker stack was tested with development secrets and mock adapters, not production configuration.
- The Cloudflare Sites/OpenNext deployment path is blocked for Next.js 15.5.28: the documented adapter supports Next.js 13.x/14.x only. The local Next.js build and Docker web image pass; no platform deployment was executed (`docs/verification/compatibility-report.md`).
- The production API image intentionally does not install pytest. The 110-test suite is run on the host; adding test-only tooling to the runtime image was rejected.

## 7. What has been tested

- Backend: 110 automated tests on real PostgreSQL, including auth, catalogue, eligibility, assistant grounding, consent, export/deletion, admin/MFA, ingestion allowlist, security headers, CSRF, request-size limits, XSS and audit hygiene.
- Frontend: 12 Vitest tests, TypeScript typecheck, production build.
- Live HTTP API: 17/17 regression checks on `127.0.0.1:8010`.
- Docker Compose: build, migrations/seed, health, worker, web, 17/17 probe, catalogue search, clean teardown.
- Browser: citizen, consent, assistant, draft/export, deletion, admin/reviewer approval paths (manual, evidence recorded).
- Retrieval: 26-query evaluation, recall@5 1.00, negative controls 5/5.
- Dependency audits: pip-audit and npm audit.

## 8. What has not been tested

- Real external providers and their delivery/quality/terms.
- GitHub Actions CI on a runner.
- Secret scanning with gitleaks.
- External penetration test, load/soak test, automated accessibility audit, backup/restore, TLS/HSTS, monitoring, production secrets management and least-privilege database role.
- Professional Hindi/Tamil translation review.
- Legal/DPDP review and grievance/support operations.
- OpenNext/Cloudflare Sites deployment and production hosting.
- Running the pytest suite inside the production API container (the verified path is the host run).

## 9. Known security and privacy risks

1. **CSP weakness:** `unsafe-inline`/`unsafe-eval` remain enabled (SEC-08). A nonce-based CSP is required before production.
2. **Single-process rate limiting:** limits are not shared across instances (SEC-09); horizontal scaling would weaken abuse protection.
3. **Development secrets and mock adapters:** the Docker stack uses local development keys, mock SMS and outbox email. These must never be used in production.
4. **Seed password logging:** the development seed prints demo account passwords to the migrate log. Treat those logs as sensitive in any shared environment.
5. **Translation quality:** Hindi/Tamil content is development-quality and unreviewed; users could misread eligibility or document requirements.
6. **Link freshness:** official links and scheme content can change; 42% of returned records had no recorded 200 response and remain flagged.
7. **Retention:** deleted accounts remain anonymised for 30 days; the worker must run continuously for the hard purge to happen.
8. **No external security validation:** no penetration test, secret scan or WAF.

## 10. External credentials and approvals required

- Funded SMS gateway account and approved sender identity.
- SMTP relay/transactional email account with SPF/DKIM.
- LLM provider contract, API key, data-processing agreement and spending cap.
- Translation vendor contract and qualified Hindi/Tamil reviewers.
- Speech-to-text provider contract and audio evaluation.
- OIDC provider registration and a reviewed authorization-code/JWKS implementation.
- Authoritative India Post PIN dataset with reuse permission.
- Legal review of the privacy notice, consent purposes, retention and provider contracts under applicable Indian law.
- Published grievance/support channel and incident-response owner.
- Production TLS certificates, DNS, secrets manager, managed PostgreSQL with encrypted backups, monitoring/alerting and a least-privilege database role.

## 11. Reproduction commands

```powershell
# Backend
cd C:\Users\girid\Downloads\HVA\backend
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m pytest -o addopts="--strict-markers" --disable-warnings
.venv\Scripts\python.exe -m evaluation.run_eval
.venv\Scripts\python.exe -m pip_audit --skip-editable

# Frontend
cd C:\Users\girid\Downloads\HVA\frontend
npx tsc --noEmit
npm test
npm run build
npm audit --audit-level=high

# Local PostgreSQL (portable install)
cd C:\Users\girid\Downloads\HVA
.\.devdb\pgsql\bin\pg_ctl.exe -D .\.devdb\data -l .\.devdb\pg.log -o "-p 55432" start

# Local API and web (two terminals)
cd backend; .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
cd frontend; $env:HVA_API_ORIGIN="http://127.0.0.1:8010"; npm run start

# Docker Compose (stop the local PostgreSQL first, or use a host-port override)
docker compose up --build

# Secret scan (when installed)
gitleaks detect --source . --no-git
```

## 12. Final status

| Area | Status |
| --- | --- |
| Local functional verification | PASS for the tested citizen, assistant, draft, privacy and reviewer journeys |
| Local quality gates | PASS for lint, backend tests, typecheck, unit tests, build, evaluation and dependency audits |
| Docker Compose | PASS on the local Docker daemon with development configuration |
| Production readiness | NOT COMPLETE — external providers, legal review, secret scan, CI, penetration test, load/accessibility/backup/TLS/monitoring gates remain BLOCKED or NOT TESTED |
| Overall | Verified restricted demonstration; not production-ready |

The application is suitable for a restricted demonstration using synthetic accounts and the seeded catalogue. It must not be described as government-approved, legally compliant, security-audited or production-ready until the blocked and untested gates above are closed with recorded evidence.
