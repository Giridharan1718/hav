import Link from "next/link";
import { FeatureStatus } from "@/components/FeatureStatus";

export default function HomePage() {
  return (
    <>
      <section className="hero">
        <div>
          <p className="kicker">Independent assistance · English · हिन्दी · தமிழ்</p>
          <h1>Understand government schemes, in the language you think in.</h1>
          <p className="lead">
            HVA helps you find relevant central and state schemes, read the official eligibility
            criteria, prepare a document checklist and build an application draft — without an
            intermediary. Every substantive answer cites the scheme record it came from.
          </p>
          <div className="row">
            <Link href="/schemes" className="btn btn-primary">
              Search schemes
            </Link>
            <Link href="/assistant" className="btn btn-secondary">
              Ask the assistant
            </Link>
            <Link href="/privacy" className="btn btn-ghost">
              Read the privacy notice
            </Link>
          </div>
          <p className="notice" style={{ marginTop: "1rem" }}>
            HVA is not a government website. It does not file applications, certify identity or
            guarantee benefits. The administering department decides eligibility.
          </p>
        </div>
        <aside className="hero-panel" aria-label="How HVA works">
          <h2 style={{ marginTop: 0 }}>How it works</h2>
          <ol className="steps">
            <li>
              <strong>Find</strong> schemes by keyword, state, category or beneficiary group. Search
              also works in Hindi and Tamil, using the reviewed translations that exist.
            </li>
            <li>
              <strong>Check</strong> documented criteria with a deterministic questionnaire. You see
              which rule you meet, which you do not, and what is still unknown.
            </li>
            <li>
              <strong>Prepare</strong> a private draft with a document checklist and clear source
              attribution. Nothing is submitted for you.
            </li>
          </ol>
          <p className="small muted" style={{ marginBottom: 0 }}>
            Your questionnaire answers are not stored. Date of birth and TOTP secrets are encrypted
            at rest; no advertising or analytics scripts are included.
          </p>
        </aside>
      </section>

      <section aria-labelledby="honest-status" className="card">
        <h2 id="honest-status" style={{ marginTop: 0 }}>
          What this build actually provides
        </h2>
        <p className="lead">
          Provider and catalogue status is read live from the service, so nothing here claims an
          integration that is not configured.
        </p>
        <FeatureStatus />
      </section>

      <section className="grid-3" style={{ marginTop: "1.5rem" }} aria-label="Platform principles">
        <div className="card">
          <h3>Privacy by default</h3>
          <p className="small">
            Optional profile fields are marked. Sensitive answers used for an eligibility check stay
            in that request. Consent is per purpose and can be withdrawn.
          </p>
          <Link href="/privacy">Privacy notice</Link>
        </div>
        <div className="card">
          <h3>Evidence, not guesswork</h3>
          <p className="small">
            Records carry the official URL, retrieval time, content hash and review state. Links that
            could not be checked are flagged unavailable, not shown as working.
          </p>
          <Link href="/schemes">Browse the catalogue</Link>
        </div>
        <div className="card">
          <h3>Honest limits</h3>
          <p className="small">
            Some criteria depend on official lists (for example SECC entitlement) and cannot be
            evaluated from a questionnaire. HVA says so instead of guessing.
          </p>
          <Link href="/offline">Fallback and offline behaviour</Link>
        </div>
      </section>

      <section className="card" style={{ marginTop: "1.5rem" }}>
        <h2 style={{ marginTop: 0 }}>Choose a language</h2>
        <p>
          The interface and scheme records are available in English, Hindi and Tamil. Hindi and Tamil
          translations in this development catalogue are marked unreviewed, and untranslated records
          fall back to English with a visible notice.
        </p>
        <div className="row">
          <Link href="/schemes?language=hi" className="btn btn-secondary">
            हिन्दी में देखें
          </Link>
          <Link href="/schemes?language=ta" className="btn btn-secondary">
            தமிழில் பார்க்கவும்
          </Link>
          <Link href="/schemes?language=en" className="btn btn-secondary">
            Continue in English
          </Link>
        </div>
      </section>
    </>
  );
}
