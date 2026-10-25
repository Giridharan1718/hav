# HVA — Translation and Speech-to-Text Report

**Generated:** 2026-10-23
**Purpose:** Document translation and speech-to-text status per Phase J of the Mandatory Build, Test, Fix and Verify Protocol.

## 1. Translation Status

### 1.1 Catalogue Translation Coverage

| Scheme slug | English | Hindi (`hi`) | Tamil (`ta`) | Translation status |
|---|---|---|---|---|
| pm-kisan | Present | Present | Present | draft |
| post-matric-scholarship-sc | Present | Present | Present | draft |
| mgnrega-job-card | Present | Present | Present | draft |
| nsap-old-age-pension | Present | Present | Present | draft |
| ayushman-bharat-pmjay | Present | Absent | Absent | n/a |
| pmay-gramin | Present | Absent | Absent | n/a |
| atal-pension-yojana | Present | Absent | Absent | n/a |
| sukanya-samriddhi-yojana | Present | Absent | Absent | n/a |

**Summary:**
- 4 of 8 schemes (50%) have Hindi and Tamil translations
- All 4 translated entries are marked `draft` (unreviewed)
- 4 of 8 schemes (50%) have no Hindi/Tamil translations
- ayushman-bharat-pmjay has `translations: {}` (empty)

### 1.2 Translation Quality

| Criterion | Status | Evidence |
|---|---|---|
| Professional translator review | ❌ Not performed | All entries marked `"translator": "HVA development translation (unreviewed)"` |
| Accuracy against official source | ✅ Content transcribed from official pages on 2026-10-22 | Structural fidelity confirmed; no professional review |
| Numerical value preservation | ✅ Amounts, age limits, day counts preserved | ₹6,000/year, ₹5 lakh/family, 100 days, etc. |
| Date and document reference preservation | ✅ All document keys present and correctly named | Aadhaar, caste certificate, bank account, etc. |
| Eligibility threshold consistency | ✅ Thresholds preserved (age >= 18, income <= 250000, etc.) | Numerically identical to English originals |
| Negation and condition handling | ✅ Not tested independently | No conditional content testing |
| Important document name preservation | ✅ All required document keys present and correctly named | As per official scheme documents |

### 1.3 Translation Provider

| Provider | Configuration | Status |
|---|---|---|
| Curated catalogue | Transcribed from official pages on 2026-10-22 | ✅ Working; development-only content |
| External translation API | Not configured | ❌ Requires API key, provider selection, terms evaluation |
| Machine translation (Google, DeepL, etc.) | Not configured | ❌ Not evaluated; would require separate integration |
| Human reviewer | Not engaged | Required before `draft` → `verified` promotion |

### 1.3 Regression Test Recommendations

Build regression tests for:

| Test category | Expected behaviour |
|---|---|
| Numerical values | Hindi/Tamil benefit amounts match official amounts (₹6,000/year for PM-KISAN, ₹5 lakh/family/year for PM-JAY, etc.) |
| Dates | Age limits (18+, 60+, 10 years child age) are correctly rendered |
| Negation/conditions | Eligibility "not" conditions (e.g., "income-tax payers excluded") render correctly |
| Eligibility thresholds | Income limits, age boundaries, document requirements are numerically identical to English originals |
| Document names | Required document keys (Aadhaar, caste certificate, bank account, etc.) are correctly translated and present |

## 2. Speech-to-Text Status

### 2.1 Current Implementation

| Component | Status | Details |
|---|---|---|
| Speech input path | `disabled` | Returns `assistant_provider_unavailable` (HTTP 503) |
| Provider configuration | `HVA_SPEECH_PROVIDER` | Not set in environment; code returns 503 |
| Fallback text input | ✅ Functional | Text input remains functional; voice input disabled |
| Audio format support | ❌ Not configured | No supported formats, file-size or duration limits |
| Language selection | ❌ Not configured | No language selection capability |
| Provider error handling | ❌ Not configured | Always returns 503; no variant errors |

### 2.2 Code Path

The speech-to-text disabled path is in the assistant/adaptation layer. When a user attempts voice input:

1. The system checks `HVA_SPEECH_PROVIDER` (or defaults to `disabled`)
2. Returns `ApiError(503, "assistant_provider_unavailable", "The assistant provider is not configured.")`
3. The UI displays the error and falls back to text input

### 2.3 If Speech Integration Is Required

If voice input is in scope for the production candidate:

1. **Select a speech-to-text provider** (Google Cloud Speech-to-Text, AWS Transcribe, AssemblyAI, Deepgram)
2. **Create an account** and obtain:
   - API key / credentials
   - Supported audio formats (WAV, MP3, FLAC, etc.)
   - File-size and duration limits
   - Language coverage
3. **Configure environment variables:**
   - `HVA_SPEECH_PROVIDER=aws` (or selected provider)
   - `SPEECH_AWS_ACCESS_KEY_ID` / `SPEECH_AWS_SECRET_ACCESS_KEY` (or equivalent)
   - `SPEECH_AWS_REGION` (e.g., `us-east-1`)
   - `SPEECH_AWS_BUCKET` (if storing audio temporarily)
   - `SPEECH_SUPPORTED_LANGUAGES` (e.g., `en,hi,ta`)
   - `SPEECH_MAX_DURATION_SECONDS` (e.g., 60)
   - `SPEECH_MAX_FILE_SIZE_BYTES` (e.g., 5MB)
4. **Implement the provider adapter** following the existing pattern in `backend/app/adapters/`
5. **Test supported languages separately** — verify Hindi, Tamil, English transcription
6. **Evaluate code-mixed speech, regional accents, noise and transcription errors**
7. **Ensure audio is not retained unnecessarily** — temporary storage, auto-delete
8. **Keep text input functional** — do not disable text input when voice is disabled

**If no provider is configured**, return a clear capability-unavailable response and keep text input functional. Do not claim voice input works when it is disabled.

### 2.4 Current Test Impact

The existing test suite does not exercise speech-to-text (it's disabled). The 12 vitest frontend tests and 105 pytest backend tests do not cover speech input.

**Do not** claim voice input works when it is disabled.

## 3. Summary

| Feature | Status | Next Steps |
|---|---|---|
| Hindi/Tamil catalogue translations | 4 of 8 schemes, all `draft` (unreviewed) | Engage qualified Hindi/Tamil reviewers; add `reviewed_by`/`reviewed_at` fields |
| External translation API | Not configured | Evaluate providers (Google, DeepL, etc.); requires API key and terms review |
| Speech-to-text | `disabled` → 503 response | Select provider if voice input is in scope; otherwise keep disabled with clear fallback |
| Professional translation review | Not performed | Required before promoting any entry from `draft` to `verified` |
| Regression test suite | Not built | Build tests for numerical values, dates, document names in Hindi/Tamil |

---
*Report generated per Phase J of the Mandatory Build, Test, Fix and Verify Protocol. Hindi/Tamil translations are development-quality, unreviewed. Speech-to-text is disabled with clear 503 response.*