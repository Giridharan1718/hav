import Link from "next/link";

export const metadata = { title: "Privacy notice" };

export default function PrivacyPage() {
  return (
    <article className="card prose" style={{ maxWidth: 860 }}>
      <h1>Privacy notice</h1>
      <p className="small muted">
        Notice version 2026-10-01 · Applies to this HVA deployment · This is not legal advice and HVA
        does not claim certification under any privacy framework.
      </p>

      <p className="lead">
        HVA is an independent assistance platform. It is not a government website, is not endorsed by
        any department, and does not verify identity, citizenship or entitlement. This notice explains
        what this deployment collects, why, and what you can do about it.
      </p>

      <h2>What is collected</h2>
      <ul>
        <li>
          <strong>Account:</strong> email address, password hash (Argon2id), role, session metadata
          (creation time, expiry, hashed IP, truncated user agent). Passwords are never stored or
          logged in plaintext.
        </li>
        <li>
          <strong>Profile (all optional except a display name):</strong> full name, date of birth
          (encrypted at rest), preferred language, phone number and verification state, gender if you
          choose to provide it. Name fields accept Indian scripts.
        </li>
        <li>
          <strong>Address:</strong> PIN code, selected post office, district and state. PIN codes are
          stored as text. A PIN code is never assumed to be valid until the postal dataset returns a
          match, and the district/state are only filled from a post office you explicitly select.
        </li>
        <li>
          <strong>Drafts:</strong> application-preparation drafts, field values, their source and
          whether you confirmed them.
        </li>
        <li>
          <strong>Consent records:</strong> purpose, decision, notice version, timestamps.
        </li>
        <li>
          <strong>Audit trail:</strong> security-relevant actions (sign-in, consent change, review
          decisions, exports, deletion). Audit records contain no passwords, OTPs, tokens or
          questionnaire answers.
        </li>
        <li>
          <strong>Search history (only with analytics consent):</strong> the normalized search terms,
          filters and result count. Off by default.
        </li>
      </ul>

      <h2>What is not collected or stored</h2>
      <ul>
        <li>
          Answers you type into an eligibility questionnaire (age, income, category, landholding,
          disability-related answers) are evaluated in the request and not persisted.
        </li>
        <li>Assistant questions and answers are not stored in this build.</li>
        <li>No advertising, tracking pixels or third-party analytics scripts are included.</li>
        <li>
          No identity documents are uploaded or stored. There is no document vault in this release.
        </li>
      </ul>

      <h2>Why it is used</h2>
      <p>
        Account data is used to authenticate you, secure the account and communicate essential service
        messages. Profile and address data are used to match state or district restrictions and to
        suggest draft field values. Drafts exist so you can prepare an application yourself. Consent
        records exist so that optional processing can be switched off.
      </p>

      <h2>Optional processing and consent</h2>
      <p>
        Required account processing cannot be withdrawn while the account exists; deleting the account
        removes it. Optional purposes — personalised assistant, search analytics and voice processing —
        are off unless you grant them, and can be withdrawn at any time in{" "}
        <Link href="/settings/privacy">privacy settings</Link>. Withdrawal stops future processing; it
        does not delete records that were created lawfully before withdrawal, except where deletion is
        requested.
      </p>

      <h2>Third parties and providers</h2>
      <p>
        This build is configured without a language-model provider, a speech provider or a live SMS
        gateway. Where such a provider is configured by the operator:
      </p>
      <ul>
        <li>
          Assistant retrieval is answered from the catalogue locally. If a model provider is enabled,
          only your question and the public scheme evidence are sent — never your profile, address or
          questionnaire answers. Model output is validated against the evidence before display.
        </li>
        <li>Voice input, if enabled, sends recorded audio to the configured speech provider.</li>
        <li>Phone verification sends the phone number and a one-time code to the SMS gateway.</li>
        <li>Email password recovery sends the email address to the configured mail provider.</li>
      </ul>
      <p>
        Postal lookups use the seeded dataset in this build; an authorised postal API can be configured
        by the operator. Hosting and database providers process data on the operator's behalf; their
        contracts and location are an operator responsibility and must be reviewed before production
        use.
      </p>

      <h2>Retention, export and deletion</h2>
      <ul>
        <li>Session records expire and are removed or revoked.</li>
        <li>Phone verification challenges expire after the configured window and are single-use.</li>
        <li>
          Account deletion immediately removes the profile, address, drafts, search history, consents,
          phone challenges, password-reset requests and sessions, and signs out every device. A scheduled
          purge permanently removes the remaining account row after a 30-day retention window, after
          which audit records contain no direct identifiers.
        </li>
        <li>
          You can download a JSON export of your personal data (including search history), and request
          deletion, from{" "}
          <Link href="/settings/privacy">privacy settings</Link>. Both require password confirmation.
        </li>
      </ul>

      <h2>Your choices and complaints</h2>
      <p>
        You can correct your profile, withdraw optional consent, export your data and request deletion
        from this application. If something is wrong with a scheme record, use the source link to check
        the official page and report it to the operator; the catalogue records its review state so you
        can see whether a human has verified it.
      </p>
      <p className="small muted">
        This deployment does not display a grievance officer or data-protection contact because none has
        been configured. Before public use, the operator must publish a contact, a complaint route and
        the applicable retention schedule, and must review the privacy law in force at that time.
      </p>

      <h2>Security</h2>
      <p>
        Sessions use HttpOnly, SameSite cookies with CSRF protection; administrative actions require
        multifactor authentication. Sensitive fields such as date of birth and TOTP secrets are
        encrypted at rest. See the project security documentation for the implemented controls and
        known gaps.
      </p>

      <div className="row" style={{ marginTop: "1.5rem" }}>
        <Link href="/settings/privacy" className="btn btn-primary">
          Manage consent and data
        </Link>
        <Link href="/register" className="btn btn-secondary">
          Create an account
        </Link>
      </div>
    </article>
  );
}
