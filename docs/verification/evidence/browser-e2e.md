# Browser end-to-end evidence (manual, 2026-10-23)

Environment: local frontend `http://localhost:3000` (Next.js 15.5.28, built with
`HVA_API_ORIGIN=http://127.0.0.1:8010`), local API `http://127.0.0.1:8010`,
PostgreSQL `127.0.0.1:55432/hva`. Interactions were performed through the rendered
UI in the desktop browser; database reads below were used only to confirm server-side
effects.

## Citizen journey

- Registered a disposable citizen, selected Hindi, granted the optional consents,
  saved profile name/DOB, verified a phone number through the mock OTP flow, looked up
  and confirmed a PIN-code post office, and saved the address. All steps returned the
  UI success states.
- Searched `scholarship`; the catalogue returned the Post-Matric Scholarship record.
  Opened the scheme detail and read the source/review-status panel.
- Completed the eligibility questionnaire; result was `eligible` with all four rules
  met. The result page showed per-rule matches and the preliminary-result disclaimer.
- Opened the scheme-scoped assistant from the eligibility page; the answer cited the
  selected scheme only and returned the four expected citations.
- Created an application draft, accepted the prefill, edited fields, confirmed and
  saved it, then exported it. The downloaded `.txt` was 755 bytes.
- Granted and withdrew AI-assistant consent in consent settings, then re-granted it.
  With consent active the assistant language selector defaulted to the saved Hindi
  preference, and the answer body was Devanagari. The request body observed in the
  browser network panel was
  `{"message":"What is PM-KISAN?","language":"hi"}`.
- Required-consent row showed no Withdraw button; optional consents did.
- Deleted the account through the privacy settings UI. The app redirected to login,
  the old credentials were rejected with "Email or password is incorrect.", and the
  database showed an anonymised inactive user row with deletion scheduled for
  `2026-11-22`. Profile, address, draft, search-history, consent and session rows for
  that user were removed. This is the expected 30-day-retention deletion behaviour,
  not immediate hard deletion.

## Reviewer/admin journey

- Logged in as a reviewer with TOTP MFA; `/admin` displayed Published schemes `8`,
  Pending versions `9`, and the review queue.
- Submitted an unauthorised ingestion host; the UI showed a 422 validation error.
- Created a disposable scheme version `UI Review Probe Scheme v1`
  (`ui-review-probe-053132d7`) and a disposable reviewer account with MFA.
- The review queue listed the disposable record first. Entered review notes and
  clicked **Approve and publish**. The UI reported
  `ui-review-probe-053132d7: approve recorded (status verified).` Published schemes
  changed to `9`, pending versions to `8`, and the record left the queue.
- Database confirmation:

  ```text
  review_status | verified_at_present | is_published | slug
  verified      | t                   | t            | ui-review-probe-053132d7

  action                  | actor_user_id                        | outcome | resource_type  | resource_id
  scheme_version.approved | 069bd561-b8a1-4b7d-949f-65289ca7e090 | success | scheme_version | c126022c-7bae-4ff8-b9d4-2f8d37530816

  metadata: {"scheme": "ui-review-probe-053132d7", "new_status": "verified",
             "notes_recorded": true, "previous_status": "pending_review"}
  ```

- Cleaned up the disposable scheme and reviewer. Published schemes returned to `8`;
  zero `ui.reviewer.%`/`ui.probe.%` users remain. Two orphaned pre-fix
  `search_history` rows with `user_id IS NULL` were also deleted; zero remain.

## Limits of this evidence

- This was a manual browser walkthrough, not an automated Playwright/Cypress suite.
- Screenshots were not retained in the repository; the UI and database observations
  above are the recorded evidence.
- The mock SMS/outbox adapters were used. No real provider was contacted.
