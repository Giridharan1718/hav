# Implementation plan — Human Vernacular Assist (HVA)

Status: phase A complete, phases B–G implemented in this repository, phase H partially
(deployment configuration and runbook documented; no public deployment performed).

## 1. Repository inspection (phase A)

The workspace started empty apart from `.freebuff/`. No existing code, migrations, schema or
dependencies were present, so the plan below defines the initial architecture.

Local toolchain found:

| Tool | Available | Notes |
| --- | --- | --- |
| Node.js | yes (24.22.0), npm 11.19.1, pnpm 11.25.0 | frontend |
| Python | yes (3.12.10) | backend |
| Docker | no | `docker-compose.yml` is provided but was not exercised on this machine |
| PostgreSQL | not installed | portable PostgreSQL 16.4 binaries installed under `.devdb/` (gitignored) for real database testing |

## 2. Scope of this build

A complete, runnable vertical slice of one citizen journey, plus the review and privacy
flows that surround it:

register → consent → profile + PIN-code post-office confirmation → search schemes →
read scheme evidence → answer eligibility questions → deterministic result →
grounded multilingual assistant answer → application draft with provenance → export →
account data export/deletion request → content-reviewer verification.

Explicitly out of scope for this iteration (documented in `docs/limitations.md`):
automatic application submission, live OTP delivery to phones, live LLM/translation/
speech provider credentials, semantic/vector retrieval, document upload vault,
OIDC provider registration, public deployment.

## 3. Architecture

Modular monolith.

- `backend/` FastAPI application, `app/` package, versioned `/api/v1` router,
  SQLAlchemy 2.0 ORM, Alembic migrations, PostgreSQL 16.
- `frontend/` Next.js App Router + TypeScript, mobile-first, server-rendered shell,
  client components for interactive forms, same-origin `/api` rewrite to the API.
- Provider boundaries are interfaces with explicit adapters: SMS/OTP, LLM,
  translation, transcription, OIDC, postal source. Only adapters that are configured
  are reported as available; no adapter fakes a production integration.

### Layers

```
HTTP (FastAPI router, pydantic schemas, rate limits, CSRF, error envelope)
  → services (search, eligibility, assistant pipeline, drafts, postal, audit)
    → adapters (LLM, translation, SMS, postal source, safe fetcher)
      → SQLAlchemy models / PostgreSQL
```

## 4. Data model

Tables (all UUID primary keys, timestamptz audit columns, FK constraints, indexes):
`users`, `sessions`, `phone_verifications`, `password_resets`, `profiles`, `addresses`,
`consents`, `schemes`, `scheme_versions`, `scheme_translations`, `source_documents`,
`eligibility_rules`, `postal_offices`, `postal_dataset`, `postal_lookup_cache`,
`search_history`, `application_drafts`, `draft_fields`, `audit_events`,
`background_jobs`, `ingestion_runs`, `deletion_requests`.

Private user data lives in user-scoped tables; public scheme content is separate.
Sensitive fields (TOTP secrets, date of birth) use authenticated encryption
(Fernet/AES + HMAC) with the key held outside the database. Income and other
sensitive questionnaire answers are not persisted at all — they are evaluated
in-request only.

## 5. Security decisions

- Argon2id password hashing, minimum length, small blocklist, generic auth errors.
- Opaque session tokens (only SHA-256 hashes stored), HttpOnly/SameSite=Lax cookie,
  rotation on login, revocation list, per-session listing/revocation.
- CSRF: double-submit cookie + header, plus Origin validation on unsafe methods.
- Session fixation protection, reauthentication (password) for export/deletion.
- OTP: HMAC-hashed codes, 10-minute expiry, 5 attempts, 60-second resend cooldown,
  per-user and per-IP rate limits, mock SMS adapter refused in production.
- TOTP MFA mandatory for reviewer/admin roles, verified server-side per request.
- Backend authorization on every private resource (owner checks, no client-supplied
  user ids), explicit role dependency for admin routes, audit of privileged actions.
- Rate limiting per route/identity, request size limits, strict CORS allowlist,
  security headers + CSP in Next.js, parameterised SQL only (ORM), output encoding
  by React, SSRF-safe fetcher (scheme allowlist, https only, private-IP and DNS
  rebinding checks, no redirect escapes, size limit).
- Structured logs without PII, tokens or OTPs; secrets only via environment.

## 6. Delivery sequence

| Phase | Content | This build |
| --- | --- | --- |
| A | Inspection, architecture, plan | complete |
| B | Migrations, auth, profile | complete |
| C | Postal lookup, reviewed scheme catalogue + seed | complete (curated sample dataset) |
| D | Search + deterministic eligibility | complete |
| E | Multilingual assistant + evidence retrieval | complete with local grounded composer; provider adapters config-gated |
| F | Drafts, consent, export/deletion | complete |
| G | Security, accessibility, evaluation | automated tests + documented manual review |
| H | Deployment, docs, release review | configuration + runbook + checklist; no deployment claimed |

## 7. Missing credentials and external dependencies (initial list)

- SMS provider account (adapter provided, mock only in development).
- LLM provider key (adapter provided, deterministic local composer is the default).
- Translation provider (curated catalogue translations used; HTTP adapter config-gated).
- Speech-to-text provider (endpoint returns a structured `unavailable` response).
- OIDC client registration (provider interface + config-gated code flow; password
  authentication with sessions is the implemented, tested path).
- India Post dataset/API credentials (curated postal sample seeded, clearly labelled).
