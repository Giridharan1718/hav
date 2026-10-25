# Provider adapters

Every external dependency sits behind an adapter with an explicit configuration switch.
The application reports which capabilities are genuinely configured via
`GET /api/v1/health` (`features`), never optimistically. When a provider is not
configured, the capability is visibly disabled or a documented local fallback is used —
it is never silently mocked as if it were a production integration.

All adapters live in `backend/app/adapters/`. Configuration is via `HVA_*` environment
variables (see `backend/.env.example`).

## SMS (phone verification)

`app/adapters/notification.py` — `send_otp`.

| Mode | Config | Behaviour |
| --- | --- | --- |
| `disabled` (default when unset) | `HVA_SMS_PROVIDER=disabled` | `503 sms_unavailable`; the UI hides phone verification |
| `mock` | `HVA_SMS_PROVIDER=mock` | Appends the code to `backend/.dev-outbox/sms.log` and returns a `dev_code`. **Refused when `HVA_ENV=production`** — the settings validator refuses to boot |
| `http` | `HVA_SMS_PROVIDER=http`, `HVA_SMS_HTTP_URL`, `HVA_SMS_HTTP_TOKEN` | `POST` JSON `{"to": "+91…", "message": "…"}` with `Authorization: Bearer <token>`; expects 2xx. This is a bring-your-own-gateway contract, **not** a claim about any specific vendor |

The OTP itself is never stored in plaintext (HMAC-hashed), expires in 10 minutes, is
limited to 5 attempts and has a 60-second resend cooldown.

## Email (password reset)

`app/adapters/notification.py` — `send_email`.

| Mode | Config | Behaviour |
| --- | --- | --- |
| `disabled` | `HVA_EMAIL_PROVIDER=disabled` | `503 email_unavailable` |
| `outbox` (default) | `HVA_EMAIL_PROVIDER=outbox` | Writes each message to `backend/.dev-outbox/<timestamp>.txt` and keeps it in an in-memory outbox for tests |
| `smtp` | `HVA_SMTP_HOST/PORT/USERNAME/PASSWORD/FROM` | Standard SMTP with STARTTLS via the Python standard library |

## Language model (assistant)

`app/adapters/llm.py`.

| Mode | Config | Behaviour |
| --- | --- | --- |
| `disabled` (default) | `HVA_LLM_PROVIDER=disabled` | The assistant uses the **deterministic grounded composer** in `app/services/assistant.py`. It is labelled `grounded_template`, never presented as an LLM |
| `openai_compatible` | `HVA_LLM_PROVIDER=openai_compatible`, `HVA_LLM_BASE_URL`, `HVA_LLM_API_KEY`, `HVA_LLM_MODEL` | `POST <base>/chat/completions` with `temperature: 0` and a JSON response format; output is parsed and validated against a Pydantic schema |

If the provider is selected but the configuration is incomplete, it is treated as
disabled (with a warning) rather than failing at request time.

**Output is untrusted.** Before anything is shown to the citizen, the answer is checked
against the retrieved evidence: unknown citations, numbers not present in the source,
foreign URLs and answers that fail to name the cited scheme are rejected. On any
provider error or validation failure the assistant falls back to the deterministic
composer rather than showing an error page or a fabricated answer.

## Translation

`app/adapters/translation.py`.

| Mode | Config | Behaviour |
| --- | --- | --- |
| `catalog` (default) | `HVA_TRANSLATION_PROVIDER=catalog` | Uses the curated, reviewed translations in `scheme_translations`. No machine translation is applied silently |
| `http` | `HVA_TRANSLATION_PROVIDER=http`, `HVA_TRANSLATION_HTTP_URL/TOKEN` | `POST {"text", "source", "target"}` -> `{"translation"}`. Output is marked machine-translated and is not presented as reviewed content |

Official English text is always preserved alongside any translation.

## Speech-to-text (transcription)

`app/adapters/transcription.py`.

| Mode | Config | Behaviour |
| --- | --- | --- |
| `disabled` (default) | `HVA_TRANSCRIPTION_PROVIDER=disabled` | The endpoint returns a structured `503 transcription_unavailable`; the UI offers typed input instead of pretending audio was processed |
| `http` | `HVA_TRANSCRIPTION_PROVIDER=http`, `HVA_TRANSCRIPTION_HTTP_URL/TOKEN` | `POST {"audio_base64", "language"}` -> `{"text"}` |

Transcription additionally requires an active `voice_processing` consent and a
per-request consent flag in the payload.

## Postal lookup

`app/adapters/postal.py`.

| Mode | Config | Behaviour |
| --- | --- | --- |
| `local` (default) | `HVA_POSTAL_SOURCE=local` | Queries the seeded, clearly-labelled sample dataset in `postal_offices`, with provenance and refresh time from `postal_dataset` |
| `http` | `HVA_POSTAL_SOURCE=http`, `HVA_POSTAL_HTTP_URL/TOKEN` | An authorized provider endpoint |

Results are cached in `postal_lookup_cache` with a configurable freshness policy
(`HVA_POSTAL_CACHE_TTL_HOURS`). Invalid format, unknown code, ambiguous match and
provider failure are distinct outcomes. A well-formed PIN is never assumed to be a
valid location, and an address is never silently rewritten from a PIN alone.

## Source ingestion (SSRF-safe fetcher)

`app/services/ingestion.py`. Fetches are restricted to hosts on the approved list
(`HVA_APPROVED_INGEST_HOSTS`), HTTPS only, with private-IP and DNS-rebinding checks,
redirect limits and a response size cap (`HVA_INGESTION_MAX_BYTES`). Retrieved
documents are treated as untrusted content and are never executed or trusted as
instructions.

## OIDC single sign-on — NOT IMPLEMENTED

`app/core/config.py` exposes `HVA_OIDC_ISSUER/CLIENT_ID/CLIENT_SECRET/REDIRECT_URI` and
`features()` reports an `oidc.enabled` flag, **but no authorization-code flow, token
exchange or JWKS validation is implemented.** The implemented and tested
authentication path is email + password with TOTP MFA for privileged roles. The OIDC
flags must not be treated as a working integration; wiring a real OIDC provider is a
documented follow-up.

## Adding a provider

1. Implement the adapter interface for the capability.
2. Add a configuration switch and include it in `Settings.features()` so the health
   endpoint reports it honestly.
3. Refuse to run in production when a development-only fallback is selected.
4. On provider failure, return a structured error or the documented local fallback —
   never fabricate data.
5. Document the contract and the fields sent to the provider in this file.
