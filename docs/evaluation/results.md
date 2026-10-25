# Retrieval and source evaluation

Measured at: 2026-10-23T04:20:40.258360+00:00
Dataset: `backend/evaluation/dataset.json` (version 2026-10-22)
Sample size: 26 queries — en: 14, hi: 7, ta: 5

## Method

1. Each query is sent through the same search service the API uses, with the query
   language as the content-language filter and a top-five cut-off.
2. A result is a hit only if its slug is in the reviewer-defined expected list.
3. recall@5 is macro-averaged over expected records; precision@5 is the share of
   returned records that were expected; negative controls count as a pass when the
   service returns no record at all.
4. Every returned record is checked for an official URL on the approved source list
   and for a stored source document. A link counts as verified only when the
   recorded HTTP check returned 200.

The catalogue is the development dataset in this repository (8 schemes, 4 with
development Hindi/Tamil translations). These numbers describe this dataset only.

## Summary

| Slice | Queries | recall@5 | precision@5 | MRR@5 | attribution | links verified |
| --- | --- | --- | --- | --- | --- | --- |
| en | 14 | 1.00 | 0.58 | 0.86 | 100% | 43% |
| hi | 7 | 1.00 | 0.82 | 0.71 | 100% | 71% |
| ta | 5 | 1.00 | 0.90 | 0.80 | 100% | 80% |
| overall | 26 | 1.00 | 0.71 | 0.81 | 100% | 58% |

Median search latency: 5.8 ms (single process, local database).
Negative controls: 5/5 returned no records.

## Per-query results

| ID | Language | Query | Expected | Returned (top 5) | recall | precision |
| --- | --- | --- | --- | --- | --- | --- |
| en-01 | en | farmer income support | pm-kisan | pm-kisan, pmay-gramin, post-matric-scholarship-sc, atal-pension-yojana, ayushman-bharat-pmjay | 1.00 | 0.20 |
| en-02 | en | kisan samman nidhi instalment | pm-kisan | pm-kisan, pmay-gramin | 1.00 | 0.50 |
| en-03 | en | health insurance hospital cashless | ayushman-bharat-pmjay | ayushman-bharat-pmjay | 1.00 | 1.00 |
| en-04 | en | 5 lakh free treatment | ayushman-bharat-pmjay | ayushman-bharat-pmjay | 1.00 | 1.00 |
| en-05 | en | scholarship scheduled caste | post-matric-scholarship-sc | post-matric-scholarship-sc | 1.00 | 1.00 |
| en-06 | en | student scholarship family income | post-matric-scholarship-sc | post-matric-scholarship-sc, ayushman-bharat-pmjay, pm-kisan, atal-pension-yojana, nsap-old-age-pension | 1.00 | 0.20 |
| en-07 | en | rural housing assistance | pmay-gramin | pmay-gramin, mgnrega-job-card, nsap-old-age-pension, ayushman-bharat-pmjay, pm-kisan | 1.00 | 0.20 |
| en-08 | en | pucca house scheme | pmay-gramin | pmay-gramin, mgnrega-job-card, nsap-old-age-pension | 1.00 | 0.33 |
| en-09 | en | old age pension 60 years | nsap-old-age-pension | nsap-old-age-pension, atal-pension-yojana, sukanya-samriddhi-yojana, mgnrega-job-card, pm-kisan | 1.00 | 0.20 |
| en-10 | en | unorganised worker pension | atal-pension-yojana | atal-pension-yojana, nsap-old-age-pension, mgnrega-job-card | 1.00 | 0.33 |
| en-11 | en | 100 days wage employment | mgnrega-job-card | mgnrega-job-card | 1.00 | 1.00 |
| en-12 | en | girl child savings account | sukanya-samriddhi-yojana | sukanya-samriddhi-yojana, atal-pension-yojana, mgnrega-job-card, nsap-old-age-pension, pm-kisan | 1.00 | 0.20 |
| en-13 | en | quantum astrophysics telescope grant | — | — | 1.00 | 1.00 |
| en-14 | en | commercial drone licence | — | — | 1.00 | 1.00 |
| hi-01 | hi | किसान आय सहायता | pm-kisan | pm-kisan, post-matric-scholarship-sc | 1.00 | 0.50 |
| hi-02 | hi | छात्रवृत्ति अनुसूचित जाति | post-matric-scholarship-sc | post-matric-scholarship-sc | 1.00 | 1.00 |
| hi-03 | hi | पेंशन 60 वर्ष | nsap-old-age-pension | nsap-old-age-pension, mgnrega-job-card, pm-kisan, post-matric-scholarship-sc | 1.00 | 0.25 |
| hi-04 | hi | ग्रामीण रोजगार 100 दिन | mgnrega-job-card | mgnrega-job-card | 1.00 | 1.00 |
| hi-05 | hi | मजदूरी कार्ड | mgnrega-job-card | mgnrega-job-card | 1.00 | 1.00 |
| hi-06 | hi | बालिका बचत योजना | — | — | 1.00 | 1.00 |
| hi-07 | hi | खगोल भौतिकी अनुदान | — | — | 1.00 | 1.00 |
| ta-01 | ta | விவசாயி வருமான உதவி | pm-kisan | pm-kisan, post-matric-scholarship-sc | 1.00 | 0.50 |
| ta-02 | ta | கல்வி உதவித்தொகை | post-matric-scholarship-sc | post-matric-scholarship-sc | 1.00 | 1.00 |
| ta-03 | ta | ஓய்வூதியம் 60 வயது | nsap-old-age-pension | nsap-old-age-pension | 1.00 | 1.00 |
| ta-04 | ta | வேலை உறுதி 100 நாட்கள் | mgnrega-job-card | mgnrega-job-card | 1.00 | 1.00 |
| ta-05 | ta | பெண் குழந்தை சேமிப்பு | — | — | 1.00 | 1.00 |

## Known limitations surfaced by this evaluation

- Hindi and Tamil retrieval only covers the four schemes with development
  translations; `hi-06` and `ta-05` are negative controls for that gap, not
  evidence that the schemes do not exist.
- Translations in the catalogue are marked `draft` and were not reviewed by a
  professional translator. Translation quality has not been measured against a
  reference corpus.
- Ranking uses PostgreSQL full-text search with the `simple` configuration plus a
  keyword fallback. There is no learned ranker and no semantic retrieval.
- Two seeded official links (PM-JAY and PM-KISAN) could not be reached from the
  build environment and are flagged unverified; see
  `docs/evaluation/links.md`.

## Negative-control failures

None.
