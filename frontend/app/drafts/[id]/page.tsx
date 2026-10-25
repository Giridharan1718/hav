"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { useRequireAuth } from "@/components/useRequireAuth";
import { Alert, Badge, Breadcrumbs, PageHeader, Spinner } from "@/components/ui";
import type { Draft, DraftExport } from "@/lib/types";

const SOURCE_LABEL: Record<string, string> = {
  profile: "from profile",
  user: "entered by you",
  assistant: "assistant suggestion",
  empty: "not filled",
};

export default function DraftEditorPage() {
  const params = useParams<{ id: string }>();
  const draftId = params.id;
  const router = useRouter();
  const { me, loading } = useRequireAuth();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [confirmed, setConfirmed] = useState<Record<string, boolean>>({});
  const [removed, setRemoved] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [exportFormat, setExportFormat] = useState<"json" | "text">("text");
  const [exportConfirm, setExportConfirm] = useState(false);
  const [exported, setExported] = useState<DraftExport | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const applyDraft = useCallback((next: Draft) => {
    setDraft(next);
    const nextValues: Record<string, string> = {};
    const nextConfirmed: Record<string, boolean> = {};
    for (const field of next.fields) {
      nextValues[field.key] = field.value ?? "";
      nextConfirmed[field.key] = field.user_confirmed;
    }
    setValues(nextValues);
    setConfirmed(nextConfirmed);
    setRemoved({});
  }, []);

  const load = useCallback(async () => {
    try {
      const response = await api<Draft>(`/drafts/${draftId}`);
      applyDraft(response);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [draftId, applyDraft]);

  useEffect(() => {
    if (me) void load();
  }, [me, load]);

  async function save() {
    if (!draft) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    const fields = draft.fields
      .filter((field) => !removed[field.key])
      .map((field) => ({
        key: field.key,
        value: values[field.key] ?? "",
        confirmed: Boolean(confirmed[field.key]) && Boolean(values[field.key]),
      }));
    const remove = Object.keys(removed).filter((key) => removed[key]);
    const confirm = Object.entries(confirmed)
      .filter(([key, value]) => value && values[key] && !removed[key])
      .map(([key]) => key);
    try {
      const response = await api<Draft>(`/drafts/${draftId}`, {
        method: "PATCH",
        json: { fields, remove, confirm },
      });
      applyDraft(response);
      setNotice("Draft saved. Values marked confirmed are treated as reviewed by you.");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function exportDraft(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = await api<DraftExport>(`/drafts/${draftId}/export`, {
        method: "POST",
        json: { format: exportFormat, confirm: exportConfirm, language: draft?.language ?? "en" },
      });
      setExported(response);
      applyDraft(response.draft);
      setNotice("Draft exported. Nothing was submitted to any department.");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function downloadExport() {
    if (!exported) return;
    const content =
      typeof exported.document === "string" ? exported.document : JSON.stringify(exported.document, null, 2);
    const type = exported.format === "text" ? "text/plain" : "application/json";
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `hva-draft-${draftId}.${exported.format === "text" ? "txt" : "json"}`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function deleteDraft() {
    if (!window.confirm("Delete this draft permanently?")) return;
    setDeleteBusy(true);
    try {
      await api(`/drafts/${draftId}`, { method: "DELETE" });
      router.push("/drafts");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setDeleteBusy(false);
    }
  }

  if (loading) return <div className="card">Loading draft…</div>;
  if (!me) return <div className="card">Redirecting to sign in…</div>;
  if (!draft) {
    return (
      <div className="card">
        {error ? <Alert tone="danger">{error}</Alert> : <Spinner label="Loading draft…" />}
      </div>
    );
  }

  const missing = draft.fields.filter((field) => field.required && !(values[field.key] ?? "").trim());
  const unconfirmed = draft.fields.filter(
    (field) => (values[field.key] ?? "").trim() && !confirmed[field.key] && !removed[field.key],
  );

  return (
    <>
      <Breadcrumbs items={[{ href: "/drafts", label: "Drafts" }, { label: draft.scheme.title }]} />
      <PageHeader
        title={draft.scheme.title}
        lead="Review every proposed value. Profile-derived suggestions are not confirmed until you confirm them."
        actions={
          <>
            <Link href={`/schemes/${draft.scheme.slug ?? ""}`} className="btn btn-ghost">
              Scheme details
            </Link>
            <button type="button" className="btn btn-danger" onClick={() => void deleteDraft()} disabled={deleteBusy}>
              Delete draft
            </button>
          </>
        }
      />

      {error ? <Alert tone="danger">{error}</Alert> : null}
      {notice ? <Alert tone="success">{notice}</Alert> : null}
      <Alert tone="info" title="No automatic submission">
        This is a preparation draft. HVA does not file applications, impersonate you or claim that an
        application was submitted. Export the draft and apply on the official portal yourself.
      </Alert>

      <div className="grid-2">
        <section className="card">
          <div className="spread">
            <h2 style={{ marginTop: 0 }}>Draft fields</h2>
            <div className="row">
              <Badge tone={missing.length ? "warn" : "ok"}>{missing.length} required missing</Badge>
              <Badge tone={unconfirmed.length ? "warn" : "ok"}>{unconfirmed.length} unconfirmed</Badge>
            </div>
          </div>
          <p className="small muted">
            Fields marked “from profile” were proposed by HVA from data you saved. Edit or remove any
            value. Proposals are never sent anywhere.
          </p>
          <div className="stack">
            {draft.fields.map((field) => (
              <div key={field.key} className="draft-field">
                <div className="meta">
                  <strong>{field.label}</strong>
                  {field.required ? <Badge tone="warn">required</Badge> : <Badge tone="neutral">optional</Badge>}
                  <Badge tone={field.source === "profile" ? "info" : field.source === "user" ? "ok" : "neutral"}>
                    {SOURCE_LABEL[field.source] ?? field.source}
                  </Badge>
                  {field.source_reference ? <span className="small muted">({field.source_reference})</span> : null}
                  {field.user_confirmed ? <Badge tone="ok">confirmed by you</Badge> : null}
                </div>
                {field.help_text ? <p className="small muted">{field.help_text}</p> : null}
                {removed[field.key] ? (
                  <p className="small">
                    Removed from this draft.{" "}
                    <button
                      type="button"
                      className="btn btn-ghost btn-small"
                      onClick={() => setRemoved({ ...removed, [field.key]: false })}
                    >
                      Undo
                    </button>
                  </p>
                ) : (
                  <>
                    <label className="sr-only" htmlFor={`draft-${field.key}`}>
                      {field.label}
                    </label>
                    <input
                      id={`draft-${field.key}`}
                      className="input"
                      value={values[field.key] ?? ""}
                      maxLength={500}
                      onChange={(event) => {
                        setValues({ ...values, [field.key]: event.target.value });
                        setConfirmed({ ...confirmed, [field.key]: false });
                      }}
                    />
                    <div className="row" style={{ marginTop: "0.5rem" }}>
                      <label className="check" style={{ marginBottom: 0 }}>
                        <input
                          type="checkbox"
                          checked={Boolean(confirmed[field.key])}
                          onChange={(event) => setConfirmed({ ...confirmed, [field.key]: event.target.checked })}
                          disabled={!(values[field.key] ?? "").trim()}
                        />
                        <span>I confirm this value</span>
                      </label>
                      <button
                        type="button"
                        className="btn btn-ghost btn-small"
                        onClick={() => {
                          setValues({ ...values, [field.key]: "" });
                          setConfirmed({ ...confirmed, [field.key]: false });
                          setRemoved({ ...removed, [field.key]: true });
                        }}
                      >
                        Remove
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
          <div className="row" style={{ marginTop: "1rem" }}>
            <button type="button" className="btn btn-primary" onClick={() => void save()} disabled={busy}>
              {busy ? "Saving…" : "Save draft"}
            </button>
          </div>
        </section>

        <aside className="stack">
          <section className="card">
            <h2 style={{ marginTop: 0 }}>Export</h2>
            <p className="small muted">
              Export includes confirmed and proposed values with their status, so you can tell them apart.
              Files are generated in your browser session and are not stored by HVA beyond the draft
              record.
            </p>
            <form onSubmit={exportDraft}>
              <div className="field">
                <label htmlFor="export-format">Format</label>
                <select
                  id="export-format"
                  className="select"
                  value={exportFormat}
                  onChange={(event) => setExportFormat(event.target.value as "json" | "text")}
                >
                  <option value="text">Plain text</option>
                  <option value="json">JSON</option>
                </select>
              </div>
              <label className="check">
                <input
                  type="checkbox"
                  checked={exportConfirm}
                  onChange={(event) => setExportConfirm(event.target.checked)}
                />
                <span>I understand this is a draft and nothing is submitted.</span>
              </label>
              <button type="submit" className="btn btn-secondary btn-block" disabled={busy || !exportConfirm}>
                Export draft
              </button>
            </form>
            {exported ? (
              <div style={{ marginTop: "0.8rem" }}>
                <button type="button" className="btn btn-primary btn-block" onClick={downloadExport}>
                  Download exported file
                </button>
                <pre
                  className="small"
                  style={{
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    maxHeight: 240,
                    overflow: "auto",
                    background: "var(--surface-2)",
                    padding: "0.7rem",
                    borderRadius: 8,
                  }}
                >
                  {typeof exported.document === "string"
                    ? exported.document
                    : JSON.stringify(exported.document, null, 2)}
                </pre>
              </div>
            ) : null}
            <p className="small muted">
              Last exported:{" "}
              {draft.last_exported_at ? new Date(draft.last_exported_at).toLocaleString() : "never"}
            </p>
          </section>

          <section className="card">
            <h2 style={{ marginTop: 0 }}>Checklist</h2>
            <p className="small">
              Missing required fields: {missing.length ? missing.map((field) => field.label).join(", ") : "none"}.
            </p>
            <p className="small">
              Proposed values still unconfirmed:{" "}
              {unconfirmed.length ? unconfirmed.map((field) => field.label).join(", ") : "none"}.
            </p>
            <Link href={`/schemes/${draft.scheme.slug ?? ""}/documents`} className="btn btn-secondary btn-small">
              Document checklist
            </Link>
          </section>
          <p className="disclaimer">{draft.disclaimer}</p>
        </aside>
      </div>
    </>
  );
}
