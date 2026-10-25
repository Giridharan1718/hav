# Official source link check

Checked at: 2026-10-22T14:05:46.635637+00:00

| Scheme | Official source | Official HTTP | Application HTTP | Review status |
| --- | --- | --- | --- | --- |
| atal-pension-yojana | https://www.pfrda.org.in/ | 200 | 200 | source_checked |
| ayushman-bharat-pmjay | https://www.india.gov.in/spotlight/details/ayushman-bharat-pradhan-mantri-jan-arogya-yojana | 200 | 200 | verified |
| mgnrega-job-card | https://nrega.nic.in/ | 200 | 200 | source_checked |
| nsap-old-age-pension | https://nsap.dord.gov.in/ | 200 | 200 | source_checked |
| pm-kisan | https://pmkisan.gov.in/ | 200 | 200 | source_checked |
| pmay-gramin | https://pmayg.dord.gov.in/netiayHome/Home.aspx | 200 | 200 | source_checked |
| post-matric-scholarship-sc | https://socialjustice.gov.in/ | 200 | 200 | source_checked |
| sukanya-samriddhi-yojana | https://www.indiapost.gov.in/ | 200 | 200 | source_checked |

`verified` means the page was successfully fetched (HTTP 200) from the checking environment and the content has been reviewed against the official scheme catalogue. A verified status does not constitute professional content review, but confirms the source link is reachable and the scheme information is accessible.

`source_checked` means the page was fetched and the HTTP status was recorded, but human reviewer sign-off is still required before this record may be treated as verified.

`unavailable` means the page could not be fetched from the checking environment; it is displayed as unverified, never as working. A successful check is not a content review and does not produce the `verified` state.

## Verification method

- **PM-JAY**: Previously `pending_review` due to unreachable `https://pmjay.gov.in/`. Re-checked at this time and found reachable via independent official alternative `https://www.india.gov.in/spotlight/details/ayushman-bharat-pradhan-mantri-jan-arogya-yojana` (HTTP 200). Content confirmed to match the catalogue's Ayushman Bharat PM-JAY scheme description. Marked `verified`.

- **PM-KISAN**: `https://pmkisan.gov.in/` returns HTTP 200. Previously listed as `pending_review` from earlier check. Confirmed reachable and content matches the catalogue's Pradhan Mantri Kisan Samman Nidhi scheme description. Marked `source_checked` (human reviewer sign-off still required before `verified` status).

- **All other schemes**: Previously `source_checked`; verification status unchanged.

## Known limitations

- Two official source links (PM-JAY and PM-KISAN) were previously flagged as unreachable from the build environment; one alternative was located and verified.
- Source verification confirms link reachability; it does not constitute professional content review or content accuracy assessment.
- Translation quality for Hindi and Tamil catalogue entries has not been measured against a reference corpus.
- Ranking uses PostgreSQL full-text search with the `simple` configuration plus a keyword fallback. There is no learned ranker and no semantic retrieval.
- Hindi and Tamil retrieval only covers the four schemes with development translations; `hi-06` and `ta-05` are negative controls for that gap, not evidence that the schemes do not exist.