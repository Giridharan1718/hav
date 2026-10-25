# HVA — LLM Integration Report

**Generated:** 2026-10-23
**Purpose:** Document language-model adapter status per Phase I of the Mandatory Build, Test, Fix and Verify Protocol.

## 1. Current LLM Adapter Configuration

| Setting | Value | Status |
|---|---|---|
| `HVA_LLM_PROVIDER` | `disabled` (default) | Default provider; openai_compatible gated behind config |
| `OPENAI_API_KEY` | ❌ Not set | Required for openai_compatible mode |
| `OPENAI_BASE_URL` | ❌ Not set | Base URL for the OpenAI-compatible endpoint |
| `OPENAI_MODEL` | ❌ Not set | Model identifier (e.g., "gpt-4o-mini") |
| `HVA_LLM_TIMEOUT_SECONDS` | Not configured | Timeout for LLM requests |

## 2. Adapter Interface (Existing)

The `backend/app/adapters/llm.py` implements two LLM provider modes (plus the default grounded composer):

| Provider | Conditions | Behaviour |
|---|---|---|
| `disabled` | `HVA_LLM_PROVIDER=disabled` (default) | Returns `None` from `get_llm_provider()`; assistant service uses grounded composer |
| `openai_compatible` | `HVA_LLM_PROVIDER=openai_compatible` + `OPENAI_API_KEY` + `OPENAI_BASE_URL` + `OPENAI_MODEL` configured | POST to `{base_url}/chat/completions` with model, temperature=0, response_format json_object; validates output against Pydantic schema |
| Default (no provider selected) | `get_llm_provider()` returns `None` | Assistant service uses `app/services/assistant.py` grounded composer (deterministic, schema-validated) |

## 3. The Grounded Composer (Default Path)

When no LLM provider is configured (the current state), the assistant service uses `app/services/assistant.py` which implements a **deterministic, local grounded composer**:

- Treats model output as untrusted: callers must validate against a schema and against retrieved evidence
- Sends user query + retrieved evidence to a local composition function
- Returns structured response with per-field provenance (source references)
- Never presented as an LLM — documented as a "grounded composer" in `docs/adapters.md`

**Current behaviour:** The assistant generates deterministic eligibility responses and grounded multilingual answers using the retrieved catalogue + evidence, without contacting any external LLM.

## 3. OpenAI-compatible Provider (If/When Configured)

If `HVA_LLM_PROVIDER=openai_compatible` is set, the `OpenAICompatibleProvider` in `llm.py` implements:

**Requirements:**
- `settings.llm_base_url` — the base URL of the OpenAI-compatible API endpoint
- `settings.llm_api_key` — the API key for authentication
- `settings.llm_model` — the model identifier (e.g., "gpt-4o-mini", "gpt-3.5-turbo")
- `settings.llm_timeout_seconds` — request timeout (default 20s)

**API contract (OpenAI /chat/completions):**
- `model` — the model identifier from config
- `temperature` — always `0` (deterministic output)
- `response_format` — `{"type": "json_object"}` (structured output)
- `messages` — `[system, user]` where user content is the query

**Response handling:**
- `response.json()["choices"][0]["message"]["content"]` — raw string output
- `json.loads(content)` — parse to dict
- `schema.model_validate(data)` — validate against Pydantic schema (caller responsibility)

**Error handling:**
- `httpx.HTTPError` → `ProviderError("provider_unavailable")`
- `json.JSONDecodeError` → `ProviderError("provider_invalid_output")`
- `ValidationError` → `ProviderError("provider_invalid_output")`

## 4. Current Blocker

| Blocking item | Status | Resolution |
|---|---|---|
| `OPENAI_API_KEY` | ❌ Not set | Required; obtain from https://platform.openai.com/account/api-keys |
| `OPENAI_BASE_URL` | ❌ Not set | Required; e.g., "https://api.openai.com/v1" or a custom OpenAI-compatible provider |
| `OPENAI_MODEL` | ❌ Not set | Required; e.g., "gpt-4o-mini" or "gpt-3.5-turbo" |
| `HVA_LLM_TIMEOUT_SECONDS` | ❌ Not set | Default 20s in code; configure as needed |
| Provider selection in settings | ✅ Working | `HVA_LLM_PROVIDER=disabled` is the default; switch to `openai_compatible` once keys are set |

## 5. Recommended Next Steps

If LLM integration is required for the production candidate:

1. **Obtain OPENAI_API_KEY** from https://platform.openai.com/account/api-keys (or alternative OpenAI-compatible provider key)
2. **Configure the base URL** — either `https://api.openai.com/v1` for OpenAI, or a self-hosted OpenAI-compatible endpoint
3. **Select a model** — `gpt-4o-mini` for cost efficiency, `gpt-4o` for highest capability, or a model from an alternative provider
4. **Configure environment variables:**
   - `HVA_LLM_PROVIDER=openai_compatible`
   - `OPENAI_API_KEY=your_key_here`
   - `OPENAI_BASE_URL=https://api.openai.com/v1`
   - `OPENAI_MODEL=gpt-4o-mini`
   - `HVA_LLM_TIMEOUT_SECONDS=30` (or as needed)
5. **Test valid responses** — verify the provider returns structured output
6. **Test authentication failures** — verify `ProviderError("provider_unavailable")` on bad key
7. **Test rate limits** — verify appropriate error on rate limit exceeded
8. **Test timeouts** — verify `ProviderError` on no response within timeout
9. **Test malformed output** — verify `ProviderError("provider_invalid_output")` when provider returns non-JSON or invalid schema
10. **Test prompt injection** — verify the system prompt limits uncontrolled generation
11. **Test unsupported claims** — verify generated claims are grounded against retrieved evidence
12. **Test provider unavailability** — verify graceful degradation when the provider is unreachable

**Never expose API keys to the frontend.** The `OPENAI_API_KEY` must remain a server-side secret.

**Do not** mark the real integration operational until a genuine authenticated request has been successfully tested with the selected provider.

## 6. Current Assistant Behaviour (Without LLM)

When `HVA_LLM_PROVIDER=disabled` (the default), the assistant at `backend/app/services/assistant.py` implements:

- **Deterministic eligibility computation** — rule-based evaluation from the catalogue
- **Grounded multilingual responses** — combines retrieved scheme evidence with user context (language, profile data) using a local composer
- **Per-field provenance** — every output field traces back to a retrieved scheme version/rule/source document
- **No external API calls** — all processing is local; no network latency, no token costs, no rate limits

**Current supported languages:** English, Hindi, Tamil (draft translations, unreviewed)

**Do not** claim LLM-powered capabilities when the disabled provider is active. The grounded composer is the functional path; the OpenAI-compatible mode is gated behind configuration.

## 7. Evaluation Impact

The retrieval evaluation (recall@5 = 1.00, attribution = 100%) uses the **grounded composer** path, not an LLM. If the OpenAI-compatible mode is enabled:

- The evaluation would need to be re-run with the LLM provider active
- Results may differ based on the provider's creativity vs. the deterministic composer
- The current baseline (recall@5 = 1.00) should be preserved as the "no LLM" baseline
- Any new results with LLM should be reported separately and clearly distinguished

**Do not** present LLM-powered results as part of the baseline evaluation until the LLM integration is fully tested and the evaluation dataset is re-run.

## 7. Verification Commands (For When Keys Are Available)

When `OPENAI_API_KEY` and config are set, run:

```bash
# Test the LLM provider
cd /c/Users/girid/Downloads/HVA/backend && HVA_LLM_PROVIDER=openai_compatible \
  OPENAI_API_KEY=your_key \
  OPENAI_BASE_URL=https://api.openai.com/v1 \
  OPENAI_MODEL=gpt-4o-mini \
  /c/Users/girid/AppData/Local/Programs/Python/Python312/python -c "
from app.adapters.llm import get_llm_provider
provider = get_llm_provider()
if provider:
    print(f'Provider: {provider.name}')
    result = provider.generate(system='You are a helpful assistant.', user='Hello', schema=None)
    print(f'Result: {result}')
else:
    print('Provider is None (disabled or incomplete config)')
"
```

**Expected with valid keys:** Provider name + generated response  
**Expected with missing config:** `Provider is None`

---
*Report generated per Phase I of the Mandatory Build, Test, Fix and Verify Protocol. No LLM provider is configured. The grounded composer is the active path; OpenAI-compatible mode is gated behind configuration.*