# HVA — SMS Integration Report

**Generated:** 2026-10-23
**Purpose:** Document SMS adapter status per Phase G of the Mandatory Build, Test, Fix and Verify Protocol.

## 1. Current SMS Adapter Configuration

| Setting | Value | Status |
|---|---|---|
| `HVA_SMS_PROVIDER` | `mock` | Development-only adapter |
| `HVA_ENV` | `test` (local) / `production` (deploy) | Affects mock rejection in production |
| Mock behaviour | Writes to `backend/.dev-outbox/sms.log` | ✅ Verified working in test env |
| Mock rejection in production | `ApiError(503, "sms_unavailable", ...)` | ✅ Defence-in-depth configuration |

## 2. Adapter Interface (Existing)

The `backend/app/adapters/notification.py` implements three SMS provider modes:

| Provider | Conditions | Behaviour |
|---|---|---|
| `disabled` | `HVA_LLM_PROVIDER=disabled` pattern | Raises `ApiError(503, "sms_unavailable", ...)` |
| `mock` | `HVA_SMS_PROVIDER=mock` + `HVA_ENV != "production"` | Writes OTP to `.dev-outbox/sms.log`; `delivered=True` |
| `mock` | `HVA_SMS_PROVIDER=mock` + `HVA_ENV == "production"` | Raises `ApiError(503, "sms_unavailable", ...)` (defence in depth) |
| `http` | `HVA_SMS_PROVIDER=http` + `sms_http_url` + `sms_http_token` configured | POST JSON to `sms_http_url`; returns `delivered=True` + `x-message-id` header |
| Any other / missing | — | Raises `ApiError(503, "sms_unavailable", "Phone verification is not configured.")` |

## 2. Real Provider Integration Requirements

Per the protocol, a real SMS provider adapter must support:

- Sending verification challenges (OTP codes)
- Expiration (TTL/configurable `otp_ttl_minutes`)
- Attempt limits (not currently implemented in any provider)
- Resend cooldowns (not currently implemented)
- Provider error handling (HTTP errors, timeouts, malformed responses)
- Delivery status where supported (HTTP `x-message-id`, message status callbacks)
- Request correlation IDs (not currently implemented)
- Rate limiting and abuse controls (not currently implemented)

## 3. Provider Selection

No real SMS provider has been selected or configured. The available options would require:

1. **Account creation** with a Twilio, Vonage, or other SMS gateway provider
2. **API credentials** (account SID, auth token, or API key)
3. **Approved sender configuration** (registered phone number or alphanumeric sender ID)
4. **Test sandbox** access for development testing
5. **Compliance review** (TCPA, TRAI India regulations, etc. for Indian phone numbers)

## 4. Current Blocker

| Blocking item | Status | Resolution |
|---|---|---|
| SMS provider credentials | ❌ Not configured | Requires provider account + API keys |
| `sms_http_url` env var | ❌ Not set | Needed for `http` provider mode |
| `sms_http_token` env var | ❌ Not set | Bearer token for HTTP provider |
| Production environment guard | ✅ Configured | `ApiError(503)` if `HVA_ENV=production` + `mock` provider |
| Development test support | ✅ Working | Mock provider writes to `.dev-outbox/sms.log` |

## 5. Recommended Next Steps

If SMS integration is required for the production candidate:

1. **Select a provider** (Twilio, Vonage, MSG91, or India-specific such as Karix, MsgCentral)
2. **Create an account** and obtain:
   - API key / SID
   - Auth token / API secret
   - Approved sender (phone number or template ID)
3. **Configure environment variables:**
   - `HVA_SMS_PROVIDER=http`
   - `SMS_HTTP_URL=https://api.provider.com/v1/messages`
   - `SMS_HTTP_TOKEN=your_bearer_token`
   - `OTP_TTL_MINUTES` (e.g., 10)
   - Any attempt limit or cooldown configuration
4. **Implement the `http` provider path** in `notification.py` (already coded, just needs env vars)
5. **Test with provider sandbox** — verify OTP delivery, expiration, and correlation IDs
6. **Run regression tests** for the full citizen journey including phone verification
7. **Update `HVA_ENV` guard** if needed (currently blocks `mock` in production, but `http` would need its own guard)

**Do not** claim phone verification works in production until a real delivery path has been exercised with authorized test recipients.

## 6. Current Test Coverage

The existing test suite exercises the mock SMS adapter. Verify that the SMS-related tests still pass:

```bash
# Backend tests (includes SMS/mock behavior)
cd /c/Users/girid/Downloads/HVA/backend && pytest tests/ -q --strict-markers --tb=short
# Expected: 105 passed, 0 failed (SMS mock is one of the tested code paths)
```

**Do not** use real phone numbers without authorization. Do not log OTP values or complete verification payloads in terminal output or reports.

---
*Report generated per Phase G of the Mandatory Build, Test, Fix and Verify Protocol. No real SMS provider is configured. The mock adapter is functional for development and test environments.*