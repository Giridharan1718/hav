# Production-readiness checklist

**This build is not production-ready and has not been deployed publicly.** The tables
below record the actual state of each release gate on the verification machine. A gate
is marked PASS only when the evidence was produced by executing the stated check; an
untested or externally blocked check is never treated as a pass.

Status values: **PASS**, **FAIL**, **BLOCKED**, **NOT TESTED**.

## Release gates

| Gate | Status | Evidence | Remaining action |
| --- | --- | --- | --- |
| Local backend lint | PASS | `ruff check .` in `backend/` | Keep clean in CI |
| Local backend tests on real PostgreSQL | PASS | `pytest` against `127.0.0.1:55432/hva_test` | Add CI execution (workflow is present but unexecuted) |
| Local frontend typecheck | PASS | `npx tsc --noEmit` in `frontend/` | Keep clean in CI |
| Local frontend unit tests | PASS | `npm test` (Vitest) | Add browser E2E suite |
| Local frontend production build | PASS | `npm run build` | Verify on the deployment image |
| Real citizen journey through API and UI | PASS | Recorded in [verification-report.md](verification-report.md) and [browser E2E evidence](verification/evidence/browser-e2e.md) | Re-run after any schema or auth change |
| Reviewer approval journey | PASS | Manual browser approval of a disposable scheme, DB state and audit event verified; recorded in [verification-report.md](verification-report.md) | Use a real content-review rota |
| Docker Compose stack | PASS | `docker compose up --build` on the local Docker daemon (temporary host-port override); 17/17 HTTP probe, web search and clean teardown; see [evidence](verification/evidence/docker-compose.md) | Re-test on the deployment host and with production secrets |
| Real SMS provider | BLOCKED | No gateway credentials or vendor account | Contract a provider, configure `HVA_SMS_PROVIDER=http`, test delivery and cooldowns |
| Real SMTP provider | BLOCKED | No SMTP credentials | Configure `HVA_EMAIL_PROVIDER=smtp`, test reset delivery and bounce handling |
| Real LLM provider | BLOCKED | No funded API key | Complete a data-processing agreement; verify consent gating, grounding and cost limits |
| Real translation / speech provider | BLOCKED | No vendor access | Evaluate quality, contract terms and consent wording |
| India Post postal dataset | BLOCKED | Only a small seeded sample exists | Obtain the authoritative dataset and reuse permission |
| OIDC / SSO | BLOCKED | Not implemented; configuration flags only | Implement authorization-code flow with JWKS validation or remove the flags |
| CI on GitHub Actions | NOT TESTED | `.github/workflows/ci.yml` exists but was not executed here | Run the workflow and triage failures |
| Dependency vulnerability scans | PASS | `pip-audit --skip-editable` (0 known) and `npm audit --audit-level=high` (0); logs in [evidence](verification/evidence/) | Re-run in CI on every dependency change |
| Secret scan | BLOCKED | `gitleaks` is not installed; the CI secret-scan job was not executed | Install gitleaks or run the CI job, then triage findings |
| Automated browser E2E suite | NOT TESTED | Only a manual browser walkthrough was performed | Add and run Playwright/Cypress in CI |
| External penetration test | NOT TESTED | None commissioned | Commission an independent test and resolve critical/high findings |
| Load / soak test | NOT TESTED | No load generator used | Add a shared rate-limit store and test beyond one API instance |
| Accessibility audit | NOT TESTED | Manual review only | Run a screen-reader pass and an automated axe scan |
| Backup and restore drill | NOT TESTED | No backup automation in this repository | Configure encrypted backups and record a restore test |
| CERT-In log retention and incident reporting | BLOCKED | Not automated | Wire logs to a managed store and document reporting contacts/timelines |
| DPDP Act and provider-contract review | BLOCKED | No legal review performed | Obtain counsel review of notices, consent, retention and vendor contracts |
| Grievance / support channel | BLOCKED | Not published | Publish a monitored contact channel before launch |
| Production secrets in a secrets manager | BLOCKED | Development keys are local only | Generate production keys, store them in a secrets manager, rotate on a schedule |
| TLS, HSTS and secure cookies end to end | NOT TESTED | No deployed environment | Verify at the reverse proxy with the production environment |
| Least-privilege database role | NOT TESTED | Local role is used for development | Create a restricted application role; migrations use a separate DDL role |
| Monitoring and alerting | NOT TESTED | Structured logs only | Wire logs to a managed store; add alerts for 5xx, auth abuse, provider failures and failed ingestion |

## Required external inputs

Before any public deployment, the operator must supply:

1. A funded SMS gateway account and sender identity approved for transactional OTPs.
2. An SMTP relay or transactional-email account with SPF/DKIM configured.
3. A language-model provider contract, API key, data-processing terms and a spending cap.
4. Authoritative India Post PIN data with permission to reuse it.
5. Legal review of the privacy notice, consent purposes, retention schedule and
   grievance process under applicable Indian law.
6. Production TLS certificates, DNS, a secrets manager and a managed PostgreSQL
   instance with encrypted backups.
7. An independent security test and a named incident-response owner.

## Launch decision

Do **not** describe HVA as production-ready, government-approved, legally compliant or
audited until the BLOCKED and NOT TESTED gates above are closed with recorded evidence.
The MVP is suitable only for a restricted demonstration using synthetic accounts and
the seeded catalogue.
