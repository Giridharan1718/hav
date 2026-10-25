# HVA — Staging Deployment Report

**Generated:** 2026-10-23
**Purpose:** Document staging deployment status per Phase N of the Mandatory Build, Test, Fix and Verify Protocol.

## 1. Staging Environment Requirements

Per the protocol, a staging environment must have:

| Requirement | Status | Notes |
|---|---|---|
| **Supported hosting configuration** | ❌ Not deployed | No staging environment deployed |
| **HTTPS** | ✅ Configuration available | Freebuff Sites provides HTTPS on preview (`https://site-*.freebuff.page`) and production (`https://site-*.freebuff.page`) |
| **Server-side environment variables** | ❌ Not set for staging | All env vars are configured for local `test` and deployed `production` environments |
| **Dedicated database** | ❌ Not provisioned for staging | D1 DB provisioned for preview + production sites (shared across environments per Freebuff isolation model) |
| **Least-privilege database credentials** | ✅ Configuration | D1 DB service tokens are scoped per environment; no raw SQL credentials in source |
| **Secure session configuration** | ✅ Implemented | `HVA_COOKIE_SECURE="false"` (dev); Freebuff Sites handles session cookie security |
| **Database migration procedures** | ✅ Configured | `alembic upgrade head` in docker compose `migrate` service; pytest `migrate_database` fixture |
| **Health and readiness endpoints** | ✅ Implemented | `/api/v1/health` endpoint returns service health status |
| **Error monitoring** | ❌ Not configured | No error monitoring service (e.g., Sentry) configured |
| **Backup and restoration procedures** | ❌ Not configured | No automated backups; PostgreSQL data depends on Docker volume `pgdata` |
| **Restricted administrative access** | ✅ Implemented | Admin routes check `user.role == "admin"`; conftest provides `admin@hva.test` credentials |
| **Explicitly labelled test data** | ✅ Configured | Seed data uses distinguishable emails (`reviewer@hva.test`, `admin@hva.test`, `citizen@hva.test`) |

## 2. Staging Deployment Checklist

| Checklist item | Status | Action Required |
|---|---|---|
| Provision staging hosting environment | ❌ Not done | Requires Freebuff Sites create + DB + auth (similar to preview env already created) |
| Configure staging environment variables | ❌ Not done | HVA_TEST_DATABASE_URL, HVA_ENV=staging, etc. |
| Run full backend test suite against staging DB | ❌ Not done | `HVA_TEST_DATABASE_URL` pointing to staging PostgreSQL |
| Run full frontend test suite | ✅ Local | `npx vitest run` passes (12/12) |
| Run frontend production build | ✅ Local | `npx next build` succeeds (exit 0) |
| Verify HTTPS on staging URL | ❌ Not done | Freebuff Sites provides HTTPS automatically |
| Verify error monitoring | ❌ Not done | No Sentry or equivalent configured |
| Verify backup procedures | ❌ Not done | No automated backups configured |
| Conduct end-to-end e2e tests | ❌ Not done | No staging environment available |
| Verify admin access controls | ❌ Not done | No staging admin without deployed environment |
| Label test data explicitly | ✅ Done | Seed data uses test emails (reviewer@hva.test, admin@hva.test, citizen@hva.test) |

## 3. End-to-End Test Suite (For When Staging Is Available)

When a staging environment is available, the following end-to-end tests must pass:

1. **Landing page and language selection** — Landing page renders; language selector (en/hi/ta) functions
2. **Registration and authentication** — Register new user; login with password; TOTP MFA enrollment; session created
3. **Profile creation and update** — Update profile; PIN code lookup; pincode validation
4. **PIN-code lookup** — Validate pincode format; requires selection when ambiguous; confirms against postal API matches
5. **Scheme search** — Search by keyword; filter by language; return scheme catalogue results
6. **Scheme details and source links** — Read scheme detail page; source URL reachability; verification status badge
7. **Eligibility evaluation** — Submit eligibility check; receive deterministic yes/no result; grounded evidence
8. **Multilingual assistant behavior** — Query in en/hi/ta; receive grounded response with source attribution
9. **Draft creation and editing** — Create draft; edit draft; ownership enforced
10. **Consent and privacy controls** — Grant/withdraw optional consents; export JSON data; request account deletion
11. **Data export and deletion** — Password-confirmed JSON download; deletion with "DELETE" confirmation; sessions signed out
12. **Unauthorized cross-user access** — User A cannot access User B's profile, drafts, consents, or drafts
13. **Provider-unavailable states** — SMS disabled, LLM disabled, speech disabled; graceful degradation without false eligibility guarantees

## 3. Deployment Status

| Environment | Status | URL |
|---|---|---|
| **Local development** | ✅ Verified | Backend on port 8000; Frontend on port 3000; PostgreSQL on 55432 |
| **Freebuff Sites preview** | ✅ Provisioned | https://site-76e98cf7f97249e7b7c022d9ec7bc436.freebuff.page |
| **Freebuff Sites production** | ✅ Provisioned | https://site-a13531069f7843898f1d7e07646a8f0d.freebuff.page |
| **Staging (custom)** | ❌ BLOCKED | No custom staging environment; Freebuff preview = closest alternative |
| **Public production** | ❌ BLOCKED | Next.js 15.5.0 / OpenNext adapter block; no Docker/GitHub Actions execution |

## 4. Recommendations

1. **Use Freebuff Sites preview as the staging alternative** — Already provisioned with D1 DB + OIDC auth; deployment blocked only by Next.js/OpenNext version constraint
2. **If custom staging is required**, evaluate the three platform alternatives:
   - **Downgrade Next.js to 14.x** and deploy to Freebuff Sites (documented compatibility path)
   - **Migrate to Vercel** for Next.js hosting (loses Freebuff D1/R2/Realtime bindings)
   - **Self-host on Node.js** (loses all Freebuff platform features)
3. **Conduct e2e tests** on the Freeburg preview environment once the Next.js compatibility is resolved
4. **Document the staging→production promotion process** — migration procedures, database seeding, environment variable promotion, feature flag management

---
*Report generated per Phase N of the Mandatory Build, Test, Fix and Verify Protocol. Staging deployment is BLOCKED due to Next.js/OpenNext compatibility constraint and lack of Docker/GitHub Actions runner. Freebuff Sites preview is provisioned as the closest alternative.*