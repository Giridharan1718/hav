"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError, fieldIssues } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { Alert, Field } from "@/components/ui";
import { useLang } from "@/lib/lang";
import type { Lang } from "@/lib/types";

export default function RegisterPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const lang = useLang();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    preferred_language: lang as Lang,
    accept_privacy_notice: false,
    consent_ai_assistant: false,
    consent_analytics: false,
    consent_voice_processing: false,
  });
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const issues = fieldIssues(error);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/register", { method: "POST", json: form });
      await refresh();
      router.push("/dashboard");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid-2">
      <section className="card">
        <h1>Create your account</h1>
        <p className="lead">
          An account lets you save a private profile, prepare application drafts and manage consent.
          You can search schemes without an account.
        </p>
        {error ? (
          <Alert tone="danger" title="Account not created">
            {error instanceof ApiError ? error.message : "Please check the form and try again."}
          </Alert>
        ) : null}
        <form onSubmit={submit} noValidate>
          <Field id="full_name" label="Full name" required hint="Use the name on your identity document. Any Indian script is accepted." error={issues.full_name}>
            <input
              id="full_name"
              className="input"
              autoComplete="name"
              value={form.full_name}
              onChange={(event) => setForm({ ...form, full_name: event.target.value })}
              required
            />
          </Field>
          <Field id="email" label="Email" required hint="Used for sign-in and essential account messages." error={issues.email}>
            <input
              id="email"
              className="input"
              type="email"
              autoComplete="email"
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
              required
            />
          </Field>
          <Field
            id="password"
            label="Password"
            required
            hint="At least 10 characters. Do not reuse your email or a common password."
            error={issues.password}
          >
            <input
              id="password"
              className="input"
              type="password"
              autoComplete="new-password"
              minLength={10}
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
              required
            />
          </Field>
          <Field id="preferred_language" label="Preferred language">
            <select
              id="preferred_language"
              className="select"
              value={form.preferred_language}
              onChange={(event) => setForm({ ...form, preferred_language: event.target.value as Lang })}
            >
              <option value="en">English</option>
              <option value="hi">हिन्दी</option>
              <option value="ta">தமிழ்</option>
            </select>
          </Field>

          <fieldset>
            <legend>Privacy choices</legend>
            <div className="check">
              <input
                id="accept_privacy"
                type="checkbox"
                checked={form.accept_privacy_notice}
                onChange={(event) => setForm({ ...form, accept_privacy_notice: event.target.checked })}
                required
              />
              <label htmlFor="accept_privacy">
                I have read the <Link href="/privacy">privacy notice</Link> and understand what is
                collected and why. (required)
              </label>
            </div>
            <div className="check">
              <input
                id="consent_ai"
                type="checkbox"
                checked={form.consent_ai_assistant}
                onChange={(event) => setForm({ ...form, consent_ai_assistant: event.target.checked })}
              />
              <label htmlFor="consent_ai">
                Personalised assistant answers using my saved language and location. Optional.
              </label>
            </div>
            <div className="check">
              <input
                id="consent_analytics"
                type="checkbox"
                checked={form.consent_analytics}
                onChange={(event) => setForm({ ...form, consent_analytics: event.target.checked })}
              />
              <label htmlFor="consent_analytics">
                Store my search terms to improve the catalogue. Optional, no advertising.
              </label>
            </div>
            <div className="check">
              <input
                id="consent_voice"
                type="checkbox"
                checked={form.consent_voice_processing}
                onChange={(event) => setForm({ ...form, consent_voice_processing: event.target.checked })}
              />
              <label htmlFor="consent_voice">
                Send recorded audio to a speech provider if I use voice input. Optional; unavailable in
                this build until a provider is configured.
              </label>
            </div>
          </fieldset>

          <button type="submit" className="btn btn-primary btn-block" disabled={busy || !form.accept_privacy_notice}>
            {busy ? "Creating account…" : "Create account"}
          </button>
        </form>
        <p className="small muted" style={{ marginTop: "1rem" }}>
          Already registered? <Link href="/login">Sign in</Link>. Recovery uses email; phone
          verification proves access to a number, not legal identity.
        </p>
      </section>
      <aside className="card card-flat">
        <h2 style={{ marginTop: 0 }}>What you control</h2>
        <ul className="prose">
          <li>Date of birth, phone and address are optional; each field explains its purpose.</li>
          <li>Questionnaire answers for eligibility checks are not stored.</li>
          <li>Drafts are private to your account and never submitted automatically.</li>
          <li>You can export or delete your data from privacy settings at any time.</li>
        </ul>
        <Alert tone="info" title="Not an identity service">
          Creating an account does not verify your identity or citizenship. HVA is independent and not
          affiliated with any government department.
        </Alert>
      </aside>
    </div>
  );
}
