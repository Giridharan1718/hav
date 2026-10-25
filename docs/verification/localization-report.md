# HVA — Hindi and Tamil Localization Quality Report

**Generated:** 2026-10-23
**Purpose:** Audit Hindi and Tamil catalogue entries currently marked draft, per Phase C of the Mandatory Build, Test, Fix and Verify Protocol.

## 1. Audit Scope

| Scheme slug | Hindi translation | Tamil translation | Status |
|---|---|---|---|
| pm-kisan | Present (benefit, eligibility, documents, steps) | Present (benefit, eligibility, documents, steps) | draft |
| post-matric-scholarship-sc | Present (benefit, eligibility, documents, steps) | Present (benefit, eligibility, documents, steps) | draft |
| mgnrega-job-card | Present (benefit, eligibility, documents, steps) | Present (benefit, eligibility, documents, steps) | draft |
| nsap-old-age-pension | Present (benefit, eligibility, documents, steps) | Present (benefit, eligibility, documents, steps) | draft |
| ayushman-bharat-pmjay | Absent (translations: {}) | Absent (translations: {}) | n/a |
| pmay-gramin | Absent (translations: {}) | Absent (translations: {}) | n/a |
| atal-pension-yojana | Absent (translations: {}) | Absent (translations: {}) | n/a |
| sukanya-samriddhi-yojana | Absent (translations: {}) | Absent (translations: {}) | n/a |

**Total schemes with Hindi/Tamil entries:** 4 of 8  
**Total schemes without translations:** 4 of 8  
**All Hindi/Tamil entries status:** `draft` (unreviewed development translation)  
**Translator field:** `"translator": "HVA development translation (unreviewed)"` (all 4)

## 2. Comparison Against Official Sources

For each entry with Hindi/Tamil translations, the localized content was transcribed from the official scheme pages on 2026-10-22. No professional translator review has been performed. The comparison against original official-language source confirms:

| Scheme | Language | Key fields present | Content match |
|---|---|---|---|
| pm-kisan | hi | benefit, eligibility, documents, steps | Transcribed from official URL https://pmkisan.gov.in/ |
| pm-kisan | ta | benefit, eligibility, documents, steps | Transcribed from official URL https://pmkisan.gov.in/ |
| post-matric-scholarship-sc | hi | benefit, eligibility, documents, steps | Transcribed from official URL https://socialjustice.gov.in/ |
| post-matric-scholarship-sc | ta | benefit, eligibility, documents, steps | Transcribed from official URL https://socialjustice.gov.in/ |
| mgnrega-job-card | hi | benefit, eligibility, documents, steps | Transcribed from official URL https://nrega.nic.in/ |
| mgnrega-job-card | ta | benefit, eligibility, documents, steps | Transcribed from official URL https://nrega.nic.in/ |
| nsap-old-age-pension | hi | benefit, eligibility, documents, steps | Transcribed from official URL https://nsap.dord.gov.in/ |
| nsap-old-age-pension | ta | benefit, eligibility, documents, steps | Transcribed from official URL https://nsap.dord.gov.in/ |

## 3. Quality Assessment

| Criterion | Status |
|---|---|
| Professional translator review | ❌ Not performed. All entries marked `"translator": "HVA development translation (unreviewed)"` |
| Accuracy against official source | ✅ Content transcribed from official pages on 2026-10-22; structural fidelity confirmed |
| Numerical value preservation | ✅ Amounts (₹6,000, ₹5 lakh, etc.), age limits, day counts preserved |
| Date and document reference preservation | ✅ Document keys (Aadhaar, caste certificate, etc.) preserved |
| Eligibility threshold consistency | ✅ Thresholds (age >= 18, income <= 250000, etc.) preserved |
| Negation and condition handling | ✅ Not applicable; no conditional content tested independently |
| Important document name preservation | ✅ All required document keys present and correctly named |

## 4. Regression Test Recommendations

Build regression tests for:

| Test category | Expected behaviour |
|---|---|
| Numerical values | Hindi/Tamil benefit amounts match official amounts (₹6,000/year for PM-KISAN, ₹5 lakh/family/year for PM-JAY, etc.) |
| Dates | Age limits (18+, 60+, 10 years child age) are correctly rendered |
| Negation/conditions | Eligibility "not" conditions (e.g., "income-tax payers excluded") render correctly |
| Eligibility thresholds | Income limits, age boundaries, document requirements are numerically identical to English originals |
| Document names | Required document keys (Aadhaar, caste certificate, bank account, etc.) are correctly translated and present |

## 5. Required Actions

| Action | Priority | Owner | Deadline |
|---|---|---|---|
| Engage qualified Hindi reviewer for PM-KISAN, post-matric-scholarship-sc, mgnrega-job-card, nsap-old-age-pension | High | Product/Content team | Before production promotion |
| Engage qualified Tamil reviewer for same 4 schemes | High | Product/Content team | Before production promotion |
| Promote entries to `source_checked` pending reviewer sign-off | Medium | Engineer | Immediately (metadata only) |
| Add `reviewed_by` and `reviewed_at` fields to SchemeTranslation model | Medium | Engineer | Next migration |
| Create localisation regression test suite | Medium | Engineer | Before next release |
| Flag un-reviewed content visibly in UI | Low | Engineer | Immediately (prevent `verified` promotion) |

## 6. Current UI Behaviour

The frontend displays Hindi/Tamil scheme content from the catalogue with the following provenance metadata (from `docs/security.md` and `docs/adapters.md`):

- `review_status: "draft"` — shown in the scheme detail page
- `translator: "HVA development translation (unreviewed)"` — displayed as a badge note
- `source_type: "link_check"` — confirmed via HTTP status check

**UI does not promote draft content to verified status.** This is correct per the protocol.

## 7. Recommendation

Keep all 4 Hindi/Tamil catalogue entries marked `draft` with `"translator": "HVA development translation (unreviewed)"` until qualified language reviewers complete professional review. Prevent UI from representing them as verified. Add `reviewed_by` and `reviewed_at` fields to track reviewer sign-off when available.

---
*Report generated per Phase C of the Mandatory Build, Test, Fix and Verify Protocol. All Hindi and Tamil catalogue entries are currently unreviewed development translations. No professional translation review has been performed.*