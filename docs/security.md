# Security, threat model and checklist

This document records the security controls implemented in this build, the threat model
they address, and what has actually been tested. It is a baseline against
OWASP ASVS and OWASP API Security, not a certification. No independent audit has been
performed and no compliance or certification is claimed.

## Threat model

### Assets

| Asset | Sensitivity | Where it lives |
| --- | --- | --- |
| Citizen account credentials | High | `users.password_hash` (Argon2id) |
| TOTP secret | High | `users.mfa_secret_enc` (Fernet) |
| Session token | High | SHA-256 hash in `sessions`; raw value only in the HttpOnly cookie |
| OTP / reset tokens | High | HMAC / SHA-256 hashes, short expiry, single use |
| Profile, address, DOB | High | `profiles`, `addresses` (DOB Fernet-encrypted) |
| Application drafts | High | `application_drafts`, `draft_fields` (owner-scoped) |
| Personal-data export | High | Generated on demand, reauthenticated |
| Scheme catalogue and provenance | Public | `schemes`, `scheme_versions`, `source_documents` |
| Audit trail | Internal | `audit_events` (no personal data in metadata) |
| Application secrets and keys | Critical | Environment only, never in the database |

### Actors

| Actor | Capability | Primary mitigations |
| --- | --- | --- |
| Anonymous visitor | Read public catalogue | Rate limits; no private data exposure |
| Authenticated citizen | Read/write own private data | Owner checks on every private resource; CSRF + Origin; MFA for privileged roles |
| Malicious or compromised client | Crafted requests, forged cross-site calls, injection | Validation, CSRF, Origin allowlist, parameterised SQL, output encoding |
| Server-side request forgery | Reach internal network via ingestion | Host allowlist, HTTPS-only, private-IP and DNS-rebinding checks, redirect limits, size caps |
| Prompt injection / untrusted model output | Fabricated sources, numbers, instructions | Retrieval-grounded validation; unknown citations, unsupported numbers and foreign URLs are rejected |
| Privileged insider | Abuse admin APIs | Mandatory TOTP for reviewer/admin, per-action audit, least-privilege database user expected |
| Third-party provider | See personal data, fail | Minimal fields sent; provider failure degrades to deterministic fallback |

### Trust boundaries and abuse cases addressed

1. Cross-site request forgery on any mutation — double-submit CSRF token + Origin check.
2. Session theft — HttpOnly, SameSite=Lax, Secure-in-production cookies; rotation on
   login; revocation list; cross-device revocation endpoint.
3. Credential stuffing and account enumeration — generic auth errors, per-email and
   per-IP rate limits, OTP attempt limits and resend cooldowns.
4. Privilege escalation via mass assignment — request models reject unknown fields;
   a registration attempt with a `role` field is rejected (`422`).
5. Cross-user data access — ownership filter on every read/write; a foreign draft id
   returns `404` so existence is not confirmed.
6. SQL injection — SQLAlchemy ORM with bound parameters only; no raw string SQL.
7. Reflected/stored XSS — React escapes by default; draft values are returned as data,
   not markup, and are never rendered as HTML.
8. SSRF and unsafe downloads through ingestion — see `app/services/ingestion.py`.
9. Prompt injection — model output is schema-validated and checked against retrieved
   evidence before it is shown; failures fall back to the deterministic composer.
10. Secret exposure — secrets come from the environment; logs omit PII, tokens and
    OTPs; tests assert no secret material appears in responses or audit metadata.
11. Insecure production configuration — the app refuses to boot in production with the
    development secret, without an explicit 32+ character secret, with the mock SMS
    adapter, or with insecure cookies.
12. Denial of service — per-route rate limits, request and audio size caps, bounded
    in-memory rate-limiter buckets.

## Implemented controls (with evidence)

| Control | Implementation | Test |
| --- | --- | --- |
| Password hashing | Argon2id, minimum length 10, small blocklist | `test_registration_rejects_weak_password` |
| Generic auth errors | One message for unknown user or bad password | `test_login_failure_is_generic_and_locks_after_repeated_attempts`, `test_unknown_account_does_not_reveal_existence` |
| Session cookie | `HttpOnly`, `SameSite=Lax`, `Secure` in production, 12h TTL, hash stored server-side | `test_login_logout_revokes_session` |
| Session revocation | Per-session and all-session endpoints | `test_session_listing_and_cross_device_revocation` |
| Expired session handling | Server-side expiry check | `test_expired_session_is_rejected` |
| CSRF | Double-submit cookie + `X-CSRF-Token` header on `/api/*` unsafe methods | `test_csrf_is_required_for_mutations` |
| Origin validation | Allowlist of app/API/CORS origins on unsafe methods | `test_cross_origin_mutation_is_rejected` |
| Authorization (RBAC) | Role dependency for reviewer/admin; MFA required for privileged routes | `test_anonymous_and_citizen_cannot_reach_admin`, `test_reviewer_without_mfa_is_blocked` |
| Object-level authorization | Owner check on drafts, profile, consents, deletion | `test_draft_requires_authentication`, cross-user `404` tests in `test_security_admin.py` |
| Mass assignment rejection | Pydantic `Strict` models reject unknown fields | `test_registration_rejects_role_mass_assignment` |
| Rate limiting | Sliding-window limiter, per-route and per-identity | `429` responses exercised in the auth and assistant tests |
| OTP hardening | HMAC-hashed, 10-minute expiry, 5 attempts, 60s resend cooldown, per-user and per-IP limits, mock adapter refused in production | `test_otp_attempt_limit`, `test_phone_challenge_and_verification` |
| MFA (TOTP) | Mandatory for reviewer/admin, verified server-side per request | `test_mfa_login_for_privileged_account`, `test_reviewer_without_mfa_is_blocked` |
| Reauthentication | Password confirmation for export and deletion | `test_data_export_requires_password_and_omits_secrets` |
| Security headers | `nosniff`, `DENY` framing, referrer and permissions policy, CORP, HSTS in production | `test_security_headers_present` |
| Content Security Policy | Configured in `next.config.ts` (script-src still allows inline/eval — see gaps) | Manual review |
| Request size limits | 1 MB body cap → `413` | `test_oversized_request_is_rejected` |
| Output encoding | React escaping; draft values returned as data | `test_draft_values_are_returned_as_data_not_markup` |
| Parameterised SQL | ORM bound parameters only | Code review |
| SSRF protection | Host allowlist, HTTPS only, private-IP and DNS-rebinding checks, redirect limits, size cap | `test_ingestion_rejects_unapproved_hosts`, `test_ingestion_worker_records_source_document` |
| Grounding validation | Unknown citation, unsupported number and foreign URL rejected | `test_assistant_rejects_fabricated_provider_output`, `test_assistant_accepts_grounded_provider_output` |
| Secret hygiene | Environment-only secrets; logs and audit metadata omit them | `test_me_never_exposes_secrets`, `test_audit_metadata_has_no_credentials` |
| Error handling | Centralized handlers; generic 500; no stack traces to clients | `test_invalid_uuid_paths_return_not_found_not_server_error` |
| Account deletion | Immediate personal-data removal, anonymised account, 30-day hard delete | `test_account_deletion_removes_personal_data_and_sessions` |

Rate limits currently configured (see `app/core/ratelimit.py`):

| Scope | Limit |
| --- | --- |
| register | 5 / hour / IP |
| login | 10 / 15 min / email + IP |
| mfa_verify | 10 / 15 min / IP |
| password_reset_request | 5 / hour / email + IP |
| password_reset_confirm | 10 / hour / IP |
| phone_challenge | 5 / hour / user |
| phone_verify | 10 / hour / user |
| scheme_search | 120 / min |
| assistant | 30 / hour / IP (+ per-user daily quota) |
| postal | 60 / min |
| draft_export | 10 / hour / user |
| data_export | 3 / hour / user |
| admin_write | 60 / hour |

## Known gaps and residual risk

These are real and unresolved; each must be closed or explicitly accepted before a
public production launch.

1. **CSP still allows `unsafe-inline` and `unsafe-eval` for scripts.** Next.js injects
   inline bootstrap scripts; a nonce-based policy is the follow-up. Frame, object and
   connection restrictions already apply.
2. **Rate limiter is single-process and in-memory.** Running more than one API instance
   requires a shared counter store (e.g. Redis); until then, limits are per-instance.
3. **No automated dependency or secret scanning is executed on this machine.** The CI
   workflow (`.github/workflows/ci.yml`) adds `pip-audit`, `npm audit` and `gitleaks`,
   but Docker/GitHub Actions were not exercised here (see [testing.md](testing.md)).
4. **No web application firewall, bot management or anomaly detection.** Rate limits are
   the only abuse detection.
5. **Backups, restore testing and incident-response rotation are documented in the
   runbook but not exercised.** No backup automation exists in this repository.
6. **No penetration test or external audit.** The threat model above is internal.
7. **CERT-In security-log retention and incident-reporting obligations are not
   implemented as an automated process.** Retention of `audit_events` and logs must be
   wired to a managed log store with the required retention before launch.
8. **OIDC single sign-on is not implemented.** Configuration flags exist and are reported
   honestly, but no authorization-code flow, token exchange or JWKS validation is wired;
   password + TOTP is the implemented authentication path.

## Pre-production checklist

- [ ] Terminate TLS at a reverse proxy; confirm `HSTS` and `Secure` cookies end to end.
- [ ] Generate and manage `HVA_SECRET_KEY` and `HVA_ENCRYPTION_KEY` in a secrets manager;
      confirm production refuses to boot without them.
- [ ] Replace the mock SMS adapter with a real provider and retest OTP delivery and
      cooldowns.
- [ ] Replace the SMTP email adapter and verify password-reset delivery.
- [ ] Add a shared store for rate limiting before scaling beyond one API instance.
- [ ] Apply a nonce-based CSP and remove `unsafe-inline`/`unsafe-eval`.
- [ ] Run `pip-audit`, `npm audit` and `gitleaks` in CI; triage all findings.
- [ ] Configure encrypted backups with documented retention; perform and record a restore
      test.
- [ ] Wire audit and application logs to a store with the CERT-In retention period;
      document the incident-reporting procedure.
- [ ] Conduct an external penetration test and resolve critical/high findings.
- [ ] Run the OWASP ASVS L1 checklist and record evidence per control.
- [ ] Restrict the database role to least privilege; confirm no superuser in the
      application connection.
- [ ] Verify the production database is not reachable from the public internet.
- [ ] Confirm CORS allowlist contains only the deployed origins.
