import Link from "next/link";

export const metadata = { title: "Offline and failure help" };

export default function OfflinePage() {
  return (
    <article className="card prose" style={{ maxWidth: 800 }}>
      <h1>When the connection or a service fails</h1>
      <p className="lead">
        HVA degrades visibly rather than pretending. This page explains what you can still do and what
        the application will not do on your behalf.
      </p>

      <h2>If you are offline</h2>
      <ul>
        <li>A banner appears across the site while the browser reports no connection.</li>
        <li>Any page loaded earlier may be out of date; check the recorded retrieval date before acting.</li>
        <li>Forms are not queued for later submission in this build. Copy anything important before you lose the page.</li>
        <li>Official scheme links open in a new tab and depend on your own connection.</li>
      </ul>

      <h2>If scheme records cannot load</h2>
      <p>
        The page shows an error with a retry action. The catalogue does not fall back to cached or
        invented content. If the database is unavailable, the health endpoint reports the service as
        degraded.
      </p>

      <h2>If the assistant is unavailable</h2>
      <p>
        With no model provider configured, the assistant already answers with deterministic summaries
        from the catalogue. If a configured provider fails or returns an answer that cannot be verified
        against the evidence, the response says so and shows the grounded summary instead.
      </p>

      <h2>If speech input is unavailable</h2>
      <p>
        The assistant reports that transcription is not configured and offers the text box. Audio is
        never sent anywhere unless a provider is configured and you have granted voice-processing
        consent.
      </p>

      <h2>If you cannot sign in</h2>
      <ul>
        <li>Use “Forgot your password” to request a reset link. The response is the same whether or not the account exists.</li>
        <li>Too many failed attempts temporarily lock the account; wait and try again.</li>
        <li>Reviewer and administrator accounts require a 6-digit authenticator code after the password.</li>
      </ul>

      <h2>If an external link is flagged</h2>
      <p>
        A link that could not be checked is labelled “could not be verified” rather than shown as
        working. Open it manually and confirm the address before entering any personal details. HVA
        never asks for a document copy.
      </p>

      <div className="row" style={{ marginTop: "1.5rem" }}>
        <Link href="/schemes" className="btn btn-primary">
          Return to the catalogue
        </Link>
        <Link href="/privacy" className="btn btn-secondary">
          Privacy notice
        </Link>
      </div>
    </article>
  );
}
