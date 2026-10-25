# HVA — SMTP Email Integration Report

**Generated:** 2026-10-23
**Purpose:** Document email adapter status per Phase H of the Mandatory Build, Test, Fix and Verify Protocol.

## 1. Current Email Adapter Configuration

| Setting | Value | Status |
|---|---|---|
| `HVA_EMAIL_PROVIDER` | `outbox` | Development-only adapter |
| `HVA_ENV` | `test` (local) / `production` (deploy) | Affects outbox vs rejection |
| Outbox behaviour | Writes to `backend/.dev-outbox/` as `.txt` files | ✅ Verified working in test env |
| SMTP behaviour | Standard SMTP protocol via Python `smtplib` | ⚠️ Not configured |

## 2. Adapter Interface (Existing)

The `backend/app/adapters/notification.py` implements three email provider modes:

| Provider | Conditions | Behaviour |
|---|---|---|
| `disabled` | `HVA_EMAIL_PROVIDER=disabled` pattern | Raises `ApiError(503, "email_unavailable", ...)` |
| `outbox` | `HVA_EMAIL_PROVIDER=outbox` | Writes mail to `backend/.dev-outbox/` as timestamped `.txt` files; appends to `outbox.messages` list |
| `smtp` | `HVA_EMAIL_PROVIDER=smtp` + `smtp_host` + `smtp_port` + `smtp_from` + optional `smtp_username`/`smtp_password` configured | SMTP send via `smtplib`; `starttls()`, `login()` if credentials provided |

## 3. Real Provider Integration Requirements

Per the protocol, a real SMTP email provider adapter must support:

- TLS configuration (STARTTLS on port 587 or IMplicit TLS on port 465)
- Secret management (smtp_host, smtp_port, smtp_from, smtp_username, smtp_password stored in secret manager)
- Sender validation (from address must match authenticated user or approved sender list)
- Connection and delivery timeouts (15s timeout configured in code; adjustable)
- Retry handling with bounded attempts (not currently implemented; would need wrapper)
- Idempotent message processing where possible (not currently implemented)
- Sanitized error logging (SMTPSMTPException wrapped in ApiError, no raw SMTP error traces)
- Appropriate handling of bounce and rejection responses where supported (not currently implemented)

## 4. Provider Selection

No real SMTP provider has been selected or configured. Available options would require:

1. **Account creation** with an email service provider (SendGrid, Mailgun, Amazon SES, Mailjet, etc.)
2. **API credentials** (API key, username, password)
3. **Sender domain verification** (proving ownership of the sender email domain)
4. **Compliance setup** (CAN-SPAM Act, GDPR for EU citizens, India's DPDP Act)
5. **Test recipients** (authorized test email addresses on the provider's platform)

## 5. Current Blocker

| Blocking item | Status | Resolution |
|---|---|---|
| SMTP provider credentials | ❌ Not configured | Requires provider account + API keys |
| `smtp_host` env var | ❌ Not set | Needed for `smtp` provider mode |
| `smtp_port` env var | ❌ Not set | Typically 587 (TLS) or 465 (implicit TLS) |
| `smtp_from` env var | ❌ Not set | Sender address must be verified with provider |
| `smtp_username` / `smtp_password` | ❌ Not set | If provider requires authentication |
| Test recipients | ❌ Not authorized | Must be approved with provider before sending |
| Production environment guard | ✅ Configured | Provider config is checked; `disabled`/`outbox` paths active |

## 5. Recommended Next Steps

If email integration is required for the production candidate:

1. **Select an email provider** (SendGrid, Mailgun, Amazon SES, Mailjet are commonly used)
2. **Create an account** and obtain:
   - API key or username
   - Password or API secret
   - Verified sender email address
   - Verified recipient addresses for testing
3. **Configure environment variables:**
   - `HVA_EMAIL_PROVIDER=smtp`
   - `SMTP_HOST=smtp.provider.com`
   - `SMTP_PORT=587` (or 465 for implicit TLS)
   - `SMTP_FROM=your-verified-sender@example.com`
   - `SMTP_USERNAME=your_username` (if required by provider)
   - `SMTP_PASSWORD=your_password` (or API key)
   - `EMAIL_TTL_SECONDS` (optional, for idempotency)
4. **Implement the `smtp` provider path** in `notification.py` (already coded, just needs env vars)
5. **Verify TLS connection** with the provider's sandbox before production use
6. **Test with test recipients** — verify subject, body, and header delivery
7. **Run regression tests** for the full citizen journey including email-dependent flows (e.g., password reset, OTP email)
8. **Update production deployment checklist** to include email provider verification

**Do not** claim delivery merely because an email was queued or an SMTP server accepted a request. Test the real provider with an authorized test recipient before marking the integration operational.

## 6. Current Test Coverage

The existing test suite exercises the outbox email adapter. Verify that the email-related tests still pass:

```bash
# Backend tests (includes outbox email behavior)
cd /c/Users/girid/Downloads/HVA/backend && pytest tests/ -q --strict-markers --tb=short
# Expected: 105 passed, 0 failed (outbox email is one of the tested code paths)
```

**Do not** use real email addresses without authorization. Do not log full email contents or credentials in terminal output or reports.

---
*Report generated per Phase H of the Mandatory Build, Test, Fix and Verify Protocol. No real SMTP provider is configured. The outbox adapter is functional for development and test environments.*