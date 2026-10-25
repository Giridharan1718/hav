"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage, fieldIssues } from "@/lib/api";
import { useLang } from "@/lib/lang";
import { tr } from "@/lib/strings";
import {
  Alert,
  Badge,
  Breadcrumbs,
  ErrorBlock,
  PageHeader,
  Spinner,
} from "@/components/ui";
import type { EligibilityField, EligibilityResult, Lang, Questions } from "@/lib/types";

const OUTCOME_TEXT: Record<string, { title: string; tone: "ok" | "danger" | "warn" | "info" }> = {
  eligible: { title: "You appear to meet the documented criteria", tone: "ok" },
  not_eligible: { title: "You do not appear to meet the documented criteria", tone: "danger" },
  insufficient_information: { title: "More information is needed", tone: "warn" },
  cannot_evaluate: { title: "This cannot be evaluated from a questionnaire", tone: "info" },
};

const RULE_STATUS: Record<string, { label: string; tone: "ok" | "danger" | "warn" | "info" | "neutral" }> = {
  met: { label: "met", tone: "ok" },
  not_met: { label: "not met", tone: "danger" },
  missing: { label: "not answered", tone: "warn" },
  unsupported: { label: "cannot evaluate", tone: "info" },
  not_applicable: { label: "not applicable today", tone: "neutral" },
};

export default function EligibilityPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const lang = useLang() as Lang;
  const [questions, setQuestions] = useState<Questions | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<EligibilityResult | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [usedSuggestions, setUsedSuggestions] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api<Questions>(`/schemes/${slug}/eligibility/questions?language=${lang}`);
      setQuestions(response);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [slug, lang]);

  useEffect(() => {
    void load();
  }, [load]);

  function useProfileSuggestions() {
    if (!questions) return;
    const next: Record<string, string> = {};
    for (const [key, value] of Object.entries(questions.prefill)) {
      if (key.startsWith("_")) continue;
      if (value === null || value === undefined) continue;
      next[key] = String(value);
    }
    setValues({ ...values, ...next });
    setUsedSuggestions(true);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!questions) return;
    setBusy(true);
    setSubmitError(null);
    const inputs: Record<string, string | number | boolean> = {};
    for (const field of questions.fields) {
      const raw = values[field.key];
      if (raw === undefined || raw === "") continue;
      if (field.type === "bool") inputs[field.key] = raw === "true";
      else if (field.type === "int") inputs[field.key] = Number.parseInt(raw, 10);
      else if (field.type === "number") inputs[field.key] = Number.parseFloat(raw);
      else inputs[field.key] = raw;
    }
    try {
      const response = await api<EligibilityResult>(`/schemes/${slug}/eligibility/evaluate`, {
        method: "POST",
        json: { inputs, language: lang },
      });
      setResult(response);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setSubmitError(err);
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="card"><Spinner label="Loading the questionnaire…" /></div>;
  if (error) return <ErrorBlock error={error} onRetry={() => void load()} />;
  if (!questions) return null;

  const issues = fieldIssues(submitError);

  return (
    <>
      <Breadcrumbs
        items={[
          { href: "/schemes", label: "Scheme catalogue" },
          { href: `/schemes/${slug}`, label: questions.scheme.name ?? "Scheme" },
          { label: "Eligibility check" },
        ]}
      />
      <PageHeader
        title="Eligibility check"
        lead={questions.scheme.name ?? undefined}
      />

      <Alert tone="info" title="This is not an official decision">
        {questions.disclaimer} Answers are evaluated in this request and are not stored.
      </Alert>

      {result ? (
        <section className={`outcome outcome-${result.outcome}`} aria-live="polite">
          <h2 style={{ marginTop: 0 }}>
            {OUTCOME_TEXT[result.outcome]?.title ?? result.outcome}{" "}
            <Badge tone={OUTCOME_TEXT[result.outcome]?.tone ?? "neutral"}>{result.outcome}</Badge>
          </h2>
          {result.outcome === "insufficient_information" ? (
            <p>
              Answer these to continue: {result.missing_fields.map((field) => field.label).join(", ")}.
            </p>
          ) : null}
          {result.outcome === "cannot_evaluate" ? (
            <p>
              One or more criteria depend on official lists or are not validated, so HVA cannot determine
              eligibility. Read the official eligibility text and check the department's list.
            </p>
          ) : null}
          {result.outcome === "eligible" ? (
            <p>
              You appear to meet the recorded criteria. Documents are still checked by the department,
              and some schemes depend on selection lists or budget availability.
            </p>
          ) : null}
          {result.outcome === "not_eligible" ? (
            <p>
              At least one documented criterion is not met. If an answer was entered incorrectly, change
              it and evaluate again.
            </p>
          ) : null}
        </section>
      ) : null}

      {result ? (
        <section className="card" style={{ marginTop: "1rem" }}>
          <h2 style={{ marginTop: 0 }}>Rule-by-rule result</h2>
          <ul className="rule-list">
            {result.rules.map((rule) => (
              <li key={rule.rule_key}>
                <span>
                  {rule.description ?? rule.label ?? rule.rule_key}
                  {rule.source_reference ? (
                    <span className="small muted"> · source recorded</span>
                  ) : null}
                </span>
                <Badge tone={RULE_STATUS[rule.status]?.tone ?? "neutral"}>
                  {RULE_STATUS[rule.status]?.label ?? rule.status}
                </Badge>
              </li>
            ))}
          </ul>
          <p className="disclaimer">{result.disclaimer}</p>
          <div className="row">
            <Link href={`/schemes/${slug}`} className="btn btn-secondary">
              Back to scheme details
            </Link>
            <Link href={`/assistant?scheme=${encodeURIComponent(slug)}`} className="btn btn-ghost">
              Ask about this scheme
            </Link>
          </div>
        </section>
      ) : null}

      <section className="card" style={{ marginTop: "1rem" }}>
        <div className="spread">
          <div>
            <h2 style={{ marginTop: 0 }}>Answer only what is asked</h2>
            <p className="small muted">
              {questions.fields.length} field{questions.fields.length === 1 ? "" : "s"} are needed for this
              scheme. Sensitive answers are marked and are never saved.
            </p>
          </div>
          {Object.keys(questions.prefill).length > 0 ? (
            <button type="button" className="btn btn-secondary btn-small" onClick={useProfileSuggestions}>
              Use profile suggestions
            </button>
          ) : null}
        </div>

        {usedSuggestions ? (
          <Alert tone="info">
            Values copied from your profile were inserted as suggestions. Check or change each one; they
            are still only sent with this check.
          </Alert>
        ) : null}

        {submitError ? <Alert tone="danger">{errorMessage(submitError)}</Alert> : null}

        <form onSubmit={submit}>
          {questions.fields.map((field) => (
            <QuestionField
              key={field.key}
              field={field}
              value={values[field.key] ?? ""}
              error={issues[field.key]}
              onChange={(value) => setValues((current) => ({ ...current, [field.key]: value }))}
            />
          ))}
          <div className="row">
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? "Evaluating…" : "Evaluate against documented criteria"}
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                setValues({});
                setResult(null);
                setUsedSuggestions(false);
              }}
            >
              Clear answers
            </button>
          </div>
        </form>
        <p className="small muted" style={{ marginTop: "0.8rem" }}>
          Rules on record: {questions.rules.map((rule) => rule.rule_key).join(", ") || "none"}. Version{" "}
          {questions.scheme.version_no} · {questions.scheme.review_status.replaceAll("_", " ")}.
        </p>
      </section>
    </>
  );
}

function QuestionField({
  field,
  value,
  error,
  onChange,
}: {
  field: EligibilityField;
  value: string;
  error?: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="field">
      <label htmlFor={`q-${field.key}`}>
        {field.label} {field.sensitive ? <Badge tone="warn">sensitive · not saved</Badge> : null}
      </label>
      {field.type === "bool" ? (
        <select id={`q-${field.key}`} className="select" value={value} onChange={(event) => onChange(event.target.value)}>
          <option value="">Select…</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      ) : field.choices ? (
        <select id={`q-${field.key}`} className="select" value={value} onChange={(event) => onChange(event.target.value)}>
          <option value="">Select…</option>
          {field.choices.map((choice) => (
            <option key={choice} value={choice}>
              {choice.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={`q-${field.key}`}
          className="input"
          type={field.type === "int" || field.type === "number" ? "number" : "text"}
          min={field.minimum ?? undefined}
          max={field.maximum ?? undefined}
          step={field.type === "number" ? "0.01" : undefined}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
      <p className="hint">{field.purpose}</p>
      {error ? <p className="field-error">{error}</p> : null}
    </div>
  );
}
