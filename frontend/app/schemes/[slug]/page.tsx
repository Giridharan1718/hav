"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { useLang } from "@/lib/lang";
import { tr } from "@/lib/strings";
import {
  Alert,
  Badge,
  Breadcrumbs,
  ErrorBlock,
  PageHeader,
  ReviewStatusBadge,
  Spinner,
} from "@/components/ui";
import type { Draft, Lang, SchemeDetail } from "@/lib/types";

export default function SchemeDetailPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const router = useRouter();
  const lang = useLang() as Lang;
  const { me } = useAuth();
  const [detail, setDetail] = useState<SchemeDetail | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [draftBusy, setDraftBusy] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [reuseProfile, setReuseProfile] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api<SchemeDetail>(`/schemes/${slug}?language=${lang}`);
      setDetail(response);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [slug, lang]);

  useEffect(() => {
    void load();
  }, [load]);

  async function createDraft() {
    if (!me) {
      router.push(`/login?next=${encodeURIComponent(`/schemes/${slug}`)}`);
      return;
    }
    setDraftBusy(true);
    setDraftError(null);
    try {
      const draft = await api<Draft>("/drafts", {
        method: "POST",
        json: { scheme_slug: slug, language: lang, reuse_profile: reuseProfile },
      });
      router.push(`/drafts/${draft.id}`);
    } catch (err) {
      setDraftError(errorMessage(err));
    } finally {
      setDraftBusy(false);
    }
  }

  if (loading) return <div className="card"><Spinner label="Loading scheme record…" /></div>;
  if (error) return <ErrorBlock error={error} onRetry={() => void load()} />;
  if (!detail) return null;

  const documents = detail.documents.map((item) =>
    typeof item === "string" ? { name: item, note: null, required: true } : item,
  );

  return (
    <>
      <Breadcrumbs
        items={[
          { href: "/schemes", label: "Scheme catalogue" },
          { label: detail.name },
        ]}
      />
      <PageHeader
        title={detail.name}
        lead={`${detail.department} · ${detail.scope === "central" ? "Central scheme" : detail.state ?? "State scheme"} · ${detail.category}`}
        actions={
          <>
            <Link href={`/schemes/${slug}/eligibility`} className="btn btn-primary">
              {tr(lang, "check_eligibility")}
            </Link>
            <Link href={`/schemes/${slug}/documents`} className="btn btn-secondary">
              {tr(lang, "documents_checklist")}
            </Link>
            <button type="button" className="btn btn-secondary" onClick={() => void createDraft()} disabled={draftBusy}>
              {draftBusy ? "Preparing…" : tr(lang, "prepare_draft")}
            </button>
          </>
        }
      />

      {draftError ? <Alert tone="danger">{draftError}</Alert> : null}
      {me ? (
        <label className="check" style={{ marginBottom: 12 }}>
          <input
            type="checkbox"
            checked={reuseProfile}
            onChange={(event) => setReuseProfile(event.target.checked)}
          />
          <span>
            Use my saved profile name, date of birth, phone and address to prefill this draft.
            Leave this off to start empty. You can edit or remove every value afterwards.
          </span>
        </label>
      ) : null}
      {!me ? (
        <Alert tone="info">
          Sign in to prepare a private draft. You can still read the scheme and check criteria without an
          account.
        </Alert>
      ) : null}
      {!detail.translation_available ? (
        <Alert tone="warning">{tr(lang, "translation_unavailable")}</Alert>
      ) : null}
      {detail.version.review_status !== "verified" ? (
        <Alert tone="warning" title="Not yet verified by a content reviewer">
          {detail.version.review_label}. {detail.version.review_notes}
        </Alert>
      ) : null}

      <div className="grid-2">
        <section className="card">
          <h2 style={{ marginTop: 0 }}>What the scheme provides</h2>
          <p>{detail.benefit_summary}</p>
          <h3>Who can apply</h3>
          <p>{detail.eligibility_summary}</p>
          {detail.deadline ? <p><strong>Deadline recorded:</strong> {detail.deadline}</p> : (
            <p className="small muted">No deadline is recorded for this scheme. Check the official page for the current cycle.</p>
          )}
          <h3>How to apply</h3>
          <ol className="steps">
            {detail.application_steps.map((step, index) => (
              <li key={`${step}-${index}`}>{step}</li>
            ))}
          </ol>
          {detail.application_mode ? (
            <p className="small muted">Application mode recorded: {detail.application_mode}.</p>
          ) : null}
        </section>

        <aside className="stack">
          <section className="card">
            <h2 style={{ marginTop: 0 }}>Official evidence</h2>
            <div className="stack-tight">
              <div className="row">
                <ReviewStatusBadge status={detail.version.review_status} label={detail.version.review_label} />
                <Badge tone={detail.source.link_verified ? "ok" : "warn"}>
                  {detail.source.link_verified
                    ? `Official page reachable (HTTP ${detail.source.http_status})`
                    : "Official page could not be verified"}
                </Badge>
              </div>
              <p className="small">
                <strong>Source:</strong>{" "}
                <a href={detail.source.url ?? detail.official_url} target="_blank" rel="noopener noreferrer">
                  {detail.source.host ?? detail.official_url}
                </a>
                {detail.source.title ? ` — ${detail.source.title}` : ""}
              </p>
              <p className="small muted">
                Retrieved:{" "}
                {detail.source.retrieved_at
                  ? new Date(detail.source.retrieved_at).toLocaleString()
                  : "not recorded"}
                <br />
                Content hash:{" "}
                <code>{detail.source.content_hash ? `${detail.source.content_hash.slice(0, 20)}…` : "not available"}</code>
                <br />
                Version {detail.version.version_no} · effective from{" "}
                {detail.version.effective_from ?? "unknown"}
              </p>
              <div className="row">
                <a
                  href={detail.official_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary btn-small"
                >
                  Official page ↗
                </a>
                <a
                  href={detail.application_link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-ghost btn-small"
                >
                  Application portal ↗
                </a>
              </div>
              <p className="small muted">
                Application link:{" "}
                {detail.application_link.verified
                  ? `checked (HTTP ${detail.application_link.http_status})`
                  : "could not be verified from this environment"}{" "}
                {detail.application_link.checked_at
                  ? `on ${new Date(detail.application_link.checked_at).toLocaleDateString()}`
                  : ""}
                . Open it manually and confirm the address before sharing any details.
              </p>
            </div>
          </section>

          <section className="card">
            <h2 style={{ marginTop: 0 }}>Eligibility rules on record</h2>
            {detail.eligibility.rules.length === 0 ? (
              <p className="small muted">No machine-checkable rules are recorded for this scheme.</p>
            ) : (
              <ul className="rule-list">
                {detail.eligibility.rules.map((rule) => (
                  <li key={rule.rule_key}>
                    <span>{rule.description}</span>
                    <Badge tone={rule.validation_status === "valid" ? "ok" : "warn"}>
                      {rule.validation_status}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
            <p className="small muted" style={{ marginTop: "0.6rem" }}>
              {detail.eligibility.evaluable
                ? "The questionnaire evaluates these documented rules and reports anything it cannot decide."
                : "At least one criterion depends on an official list and cannot be evaluated from self-reported answers."}
            </p>
          </section>
        </aside>
      </div>

      <section className="card" style={{ marginTop: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Documents mentioned in the source</h2>
        <ul className="list-clean">
          {documents.map((document, index) => (
            <li key={`${document.name}-${index}`}>
              <div className="spread">
                <div>
                  <strong>{document.name}</strong>
                  {document.note ? <div className="small muted">{document.note}</div> : null}
                </div>
                {document.required === false ? <Badge tone="neutral">not always required</Badge> : null}
              </div>
            </li>
          ))}
        </ul>
        <p className="small muted">
          Requirements can change. Confirm on the official portal before applying; nothing is uploaded to
          HVA in this build.
        </p>
      </section>

      <p className="disclaimer">{detail.disclaimer}</p>
      <p className="disclaimer">
        Source status is recorded per version. A successful link check is not a content review; only the
        “reviewed by a content reviewer” badge means a human verified the wording.
      </p>
    </>
  );
}
