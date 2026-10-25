# Privacy and consent workflows

HVA is built privacy-first: it collects the minimum needed to help a citizen find and
prepare a scheme application, and it never submits anything on their behalf. This
document describes what is collected, why, how consent is recorded and withdrawn, and
how export and deletion work.

This is a description of implemented behaviour, **not** a claim of legal compliance.
Applicable Indian privacy law (including phased commencement of the DPDP Act), its
security requirements and any provider contracts must be reviewed by counsel before a
public launch. HVA is not certified or legally compliant merely because these features
exist.

## What is collected and why

| Data | Required? | Purpose | Where |
| --- | --- | --- | --- |
| Email | Required | Account identity, password reset | `users.email` |
| Password | Required | Account access | `users.password_hash` (Argon2id) |
| Full name | Required | Fill application drafts | `profiles.full_name` |
| Date of birth | Optional, only when a feature needs it | Age-based eligibility | `profiles.date_of_birth` (Fernet) |
| Phone + verification | Optional | Contact proof, not identity | `profiles.phone`, `phone_verifications` |
| Preferred language | Optional | Interface and content language | `profiles.preferred_language` |
| Address, State, district, PIN, post office | Optional, only when useful | Location-based eligibility | `addresses` |
| TOTP secret | Optional | MFA for privileged roles | `users.mfa_secret_enc` (Fernet) |
| Application draft fields | Optional | Prepare an application | `application_drafts`, `draft_fields` |
| Search queries | Optional (analytics consent) | Improve retrieval | `search_history` |
| Assistant messages | Not stored | — | Only a daily usage counter |
| Eligibility answers | Not stored | — | Evaluated in-request, discarded |
| Audit events | System | Security, abuse detection | `audit_events` (no personal data) |

Fields are explained in the UI before they are collected, and each states why it is
needed. Names from any Indian script are accepted; there is no ASCII restriction.

## Consent purposes

Consent is recorded per purpose in `consents` (unique per user + purpose), with the
notice version at grant time and a timestamp for grant and withdrawal.

| Purpose | Type | Effect when granted |
| --- | --- | --- |
| `required_account` | Required | Account creation and basic processing |
| `ai_assistant` | Optional | Answer in the saved language preference and allow the question plus retrieved catalogue evidence to be sent to a configured language-model provider. Without it the deterministic composer is used and the language is detected from the message. |
| `analytics` | Optional | Search queries recorded in `search_history` |
| `voice_processing` | Optional | Audio may be sent to a transcription provider |

Withdrawal is available in settings and takes effect for **future** processing: an
analytics withdrawal stops new search rows, and a voice withdrawal blocks transcription
at the API. Withdrawal does not undo past processing that has already been completed,
and required-account processing is separate from the optional purposes.

`GET /consents/catalog` exposes the current notice version and purpose list so the UI
never hard-codes them.

## Personal-data export

`POST /me/export` requires password reauthentication and returns a JSON export
containing: account fields, profile, address, consents with grant/withdrawal
timestamps, all drafts with field provenance, search history recorded under analytics
consent, session metadata (no token values), audited activity and any pending deletion
request. It explicitly notes that questionnaire answers were not stored. Rate-limited
to 3/hour.

## Account deletion

`POST /me/deletion` requires password reauthentication plus a typed confirmation. It:

1. Immediately deletes profile, address, drafts, consents, search history, phone
   challenges and password-reset tokens.
2. Anonymises the account row (email replaced, password hash discarded, MFA cleared,
   marked inactive).
3. Revokes all sessions and clears the cookie.
4. Schedules a hard delete after a 30-day retention window (`DELETE_RETENTION_DAYS`).

The background worker runs `purge_expired_accounts` to hard-delete accounts whose
window has elapsed and remove their account-level audit rows. The effect on future
processing is immediate; the retention window exists only to honour account-recovery
requests and is stated in the notice.

## Retention

| Data | Retention |
| --- | --- |
| Sessions | 12 hours; revoked on logout and password change |
| Phone challenges | 10 minutes, single use |
| Password reset tokens | 30 minutes, single use |
| Deleted account personal data | Removed immediately; account hard-deleted after 30 days |
| Audit events | Retained without personal data |
| Search queries | Only with analytics consent; removed with the account |
| Backups | Must be configured with an expiry; deletion cannot reach immutable backups until they expire |

## Third parties

Personal data is sent to third parties only when an adapter is configured and, for
optional purposes, only with consent:

- **SMS gateway** (phone verification): phone number and OTP only. Not sent when the
  adapter is disabled or mock.
- **SMTP provider** (password reset): email address only.
- **Language model** (assistant): when a provider is configured and the signed-in
  citizen has granted `ai_assistant` consent, the question and the minimal retrieved
  evidence needed to answer. Without that consent, or for anonymous use, the
  deterministic composer is used and nothing is sent. The full profile is never
  included in a prompt.
- **Translation / transcription** (optional): the specific text or audio for that
  request, only when those providers are configured.

The scheme catalogue and postal lookups are public data and involve no citizen personal
data.

## Children

HVA is not directed at children and does not knowingly collect a child's data. A scheme
that requires a minor's details should be prepared by a guardian on their own account.

## Grievances

A contact channel for questions, corrections and complaints must be published before a
public launch; it is intentionally not invented here.
