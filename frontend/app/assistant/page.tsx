"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { languageFromQuery, useLang } from "@/lib/lang";
import { tr } from "@/lib/strings";
import { useAuth } from "@/components/AuthProvider";
import { Alert, Badge, PageHeader, Spinner } from "@/components/ui";
import type { AssistantResponse, Health, Lang, SchemeDetail } from "@/lib/types";

interface Turn {
  role: "user" | "assistant";
  text: string;
  response?: AssistantResponse;
}

const EXAMPLES = [
  "I am a farmer with two acres — what income support can I get?",
  "What documents are needed for a post-matric scholarship?",
  "मुझे 60 वर्ष से अधिक हूँ, कौन सी पेंशन योजना है?",
  "விவசாயிகளுக்கான திட்டங்கள் என்ன?",
];

export default function AssistantPage() {
  const lang = useLang() as Lang;
  const { me } = useAuth();
  const [language, setLanguage] = useState<Lang>(lang);
  const [message, setMessage] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [schemeSlug, setSchemeSlug] = useState<string | null>(null);
  const [schemeName, setSchemeName] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const languageTouched = useRef(false);
  const savedLanguageApplied = useRef(false);

  useEffect(() => {
    setLanguage(lang);
  }, [lang]);

  useEffect(() => {
    if (savedLanguageApplied.current || languageTouched.current || !me) return;
    if (languageFromQuery(window.location.search)) {
      // A shared ?language= link is an explicit choice and wins over the profile.
      savedLanguageApplied.current = true;
      return;
    }
    const aiConsent = me.consents.some(
      (consent) => consent.purpose === "ai_assistant" && consent.granted,
    );
    const saved = me.profile?.preferred_language;
    if (aiConsent && saved) {
      setLanguage(saved);
      savedLanguageApplied.current = true;
    }
  }, [me]);

  useEffect(() => {
    // The eligibility result links here as /assistant?scheme=<slug>. Read it from
    // window.location instead of useSearchParams so the page keeps building as a
    // static client route without a Suspense boundary.
    const slug = new URLSearchParams(window.location.search).get("scheme");
    if (!slug) return;
    setSchemeSlug(slug);
    let cancelled = false;
    api<SchemeDetail>(`/schemes/${encodeURIComponent(slug)}?language=${lang}`)
      .then((detail) => {
        if (!cancelled) setSchemeName(detail.name);
      })
      .catch(() => {
        if (!cancelled) setSchemeName(null);
      });
    return () => {
      cancelled = true;
    };
  }, [lang]);

  function clearSchemeFocus() {
    setSchemeSlug(null);
    setSchemeName(null);
    window.history.replaceState(null, "", "/assistant");
  }

  useEffect(() => {
    api<Health>("/health").then(setHealth).catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [turns, busy]);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const text = message.trim();
    if (!text || busy) return;
    setBusy(true);
    setError(null);
    setTurns((current) => [...current, { role: "user", text }]);
    setMessage("");
    try {
      const response = await api<AssistantResponse>("/assistant/messages", {
        method: "POST",
        json: {
          message: text,
          language,
          ...(schemeSlug ? { scheme_slug: schemeSlug } : {}),
        },
      });
      setTurns((current) => [...current, { role: "assistant", text: response.answer, response }]);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const speechConfigured = health?.features.transcription.configured ?? false;

  return (
    <>
      <PageHeader
        title="Scheme assistant"
        lead="Answers are built from cited catalogue records. The assistant does not see your profile, and questions are not stored."
      />

      <div className="grid-2">
        <section className="card">
          <div className="chat">
            {turns.length === 0 ? (
              <div>
                <p>
                  Ask about a scheme, a benefit, documents or criteria. Try one of these:
                </p>
                <div className="row">
                  {EXAMPLES.map((example) => (
                    <button
                      key={example}
                      type="button"
                      className="btn btn-secondary btn-small"
                      onClick={() => setMessage(example)}
                    >
                      {example.length > 58 ? `${example.slice(0, 58)}…` : example}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {turns.map((turn, index) => (
              <div key={`${turn.role}-${index}`} className={`chat-message ${turn.role === "user" ? "user" : ""}`}>
                <p className="small muted" style={{ marginBottom: "0.3rem" }}>
                  {turn.role === "user" ? "You" : "HVA"} ·{" "}
                  {turn.response ? (
                    <Badge tone={turn.response.fallback_used ? "warn" : "info"}>
                      {turn.response.provider === "grounded_template" ? "catalogue summary" : turn.response.provider}
                    </Badge>
                  ) : null}
                </p>
                <div>{turn.text}</div>
                {turn.response?.notices.map((notice) => (
                  <p key={notice.code} className="small" style={{ color: "var(--warn-ink)", marginTop: "0.5rem" }}>
                    {notice.message}
                  </p>
                ))}
                {turn.response?.missing_information.length ? (
                  <p className="small muted" style={{ marginTop: "0.5rem" }}>
                    Still needed for an eligibility check: {turn.response.missing_information.join(", ")}.
                  </p>
                ) : null}
                {turn.response?.citations.length ? (
                  <div className="citations">
                    {turn.response.citations.map((citation) => (
                      <div key={citation.id} className="citation">
                        <strong>{citation.scheme_name}</strong> · {citation.field} ·{" "}
                        <a href={citation.official_url} target="_blank" rel="noopener noreferrer">
                          official source
                        </a>
                        <p>{citation.excerpt}</p>
                      </div>
                    ))}
                  </div>
                ) : null}
                {turn.response?.schemes.length ? (
                  <p className="small" style={{ marginTop: "0.5rem" }}>
                    Records used:{" "}
                    {turn.response.schemes.map((scheme, index) => (
                      <span key={scheme.slug}>
                        {index > 0 ? ", " : ""}
                        <Link href={`/schemes/${scheme.slug}`}>{scheme.name}</Link>
                      </span>
                    ))}
                  </p>
                ) : null}
              </div>
            ))}
            {busy ? <Spinner label="Retrieving catalogue records…" /> : null}
            <div ref={endRef} />
          </div>
          {error ? <Alert tone="danger">{error}</Alert> : null}
        </section>

        <aside className="stack">
          <section className="card">
            <h2 style={{ marginTop: 0 }}>Ask a question</h2>
            {schemeSlug ? (
              <Alert tone="info">
                Focused on{" "}
                <Link href={`/schemes/${schemeSlug}`}>{schemeName ?? schemeSlug}</Link>. Answers and
                citations use only this scheme&apos;s catalogue record.{" "}
                <button type="button" className="btn btn-ghost btn-small" onClick={clearSchemeFocus}>
                  Clear focus
                </button>
              </Alert>
            ) : null}
            <form onSubmit={send}>
              <div className="field">
                <label htmlFor="assistant-message">Your question</label>
                <textarea
                  id="assistant-message"
                  className="textarea"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  maxLength={1000}
                  placeholder="e.g. What documents do I need for PM-KISAN?"
                  required
                />
                <p className="hint">{message.length}/1000 characters. Do not include Aadhaar or bank numbers.</p>
              </div>
              <div className="field">
                <label htmlFor="assistant-language">Answer language</label>
                <select
                  id="assistant-language"
                  className="select"
                  value={language}
                  onChange={(event) => {
                    languageTouched.current = true;
                    setLanguage(event.target.value as Lang);
                  }}
                >
                  <option value="en">English</option>
                  <option value="hi">हिन्दी</option>
                  <option value="ta">தமிழ்</option>
                </select>
              </div>
              <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
                {busy ? "Thinking…" : "Ask"}
              </button>
            </form>
            <p className="small muted" style={{ marginTop: "0.8rem" }}>
              {health?.features.assistant.configured
                ? `A language-model provider (${health.features.assistant.provider}) is configured; its output is checked against the evidence before display.`
                : "No language-model provider is configured. Answers are deterministic summaries built directly from the catalogue, with citations."}
            </p>
          </section>

          <section className="card">
            <h2 style={{ marginTop: 0 }}>Voice input</h2>
            {speechConfigured ? (
              <p className="small">
                A speech provider is configured, but the recording control is not enabled in this build.
                Type your question instead. Do not use the browser's dictation if you have not consented to
                audio processing.
              </p>
            ) : (
              <p className="small">
                Speech input is not configured in this environment. The assistant does not pretend to
                transcribe audio; type your question, or use your device's own keyboard dictation.
              </p>
            )}
            <button type="button" className="btn btn-secondary" disabled>
              Record audio (unavailable)
            </button>
          </section>

          <section className="card card-flat">
            <h2 style={{ marginTop: 0 }}>What it will not do</h2>
            <ul className="small">
              <li>It will not invent a scheme, amount, date or eligibility rule.</li>
              <li>It will not tell you that you are officially eligible.</li>
              <li>It will not submit an application or contact a department.</li>
              <li>It shows the English source when no reviewed translation exists.</li>
            </ul>
            <Link href="/schemes" className="btn btn-secondary btn-small">
              Browse the catalogue instead
            </Link>
          </section>
        </aside>
      </div>

      <p className="disclaimer">
        Assistant answers can be wrong or out of date. Every substantive claim lists the catalogue record
        it came from; verify on the official portal before acting. {tr(language, "independent_notice")}
      </p>
    </>
  );
}
