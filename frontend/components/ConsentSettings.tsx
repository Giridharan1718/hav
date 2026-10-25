"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "./AuthProvider";
import { Alert, Badge, Field, Spinner } from "./ui";

interface ConsentEntry {
  purpose: string;
  required: boolean;
  title: string;
  description: string;
  granted: boolean;
  updated_at: string | null;
}

export function ConsentSettings() {
  const { refresh } = useAuth();
  const [entries, setEntries] = useState<ConsentEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyPurpose, setBusyPurpose] = useState<string | null>(null);
  const [exportPassword, setExportPassword] = useState("");
  const [exportBusy, setExportBusy] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteWord, setDeleteWord] = useState("");
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deletion, setDeletion] = useState<{ status: string; execute_after?: string } | null>(null);

  const load = useCallback(async () => {
    try {
      const [consents, status] = await Promise.all([
        api<{ consents: ConsentEntry[] }>("/me/consents"),
        api<{ status: string; execute_after?: string }>("/me/deletion").catch(() => ({ status: "none" })),
      ]);
      setEntries(consents.consents);
      setDeletion(status.status === "none" ? null : status);
    } catch {
      setError("Could not load consent settings.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggle(entry: ConsentEntry, granted: boolean) {
    setBusyPurpose(entry.purpose);
    setError(null);
    setNotice(null);
    try {
      await api(`/me/consents/${entry.purpose}`, { method: "PUT", json: { granted } });
      setNotice(`${entry.title}: ${granted ? "granted" : "withdrawn"}.`);
      await load();
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update consent.");
    } finally {
      setBusyPurpose(null);
    }
  }

  async function exportData(event: React.FormEvent) {
    event.preventDefault();
    setExportBusy(true);
    setError(null);
    try {
      const data = await api<Record<string, unknown>>("/me/export", {
        method: "POST",
        json: { password: exportPassword },
      });
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `hva-export-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
      setExportPassword("");
      setNotice("Export downloaded. It contains your personal data and should be stored safely.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Export failed.");
    } finally {
      setExportBusy(false);
    }
  }

  async function requestDeletion(event: React.FormEvent) {
    event.preventDefault();
    setDeleteBusy(true);
    setError(null);
    try {
      const result = await api<{ status: string; execute_after: string; message: string }>("/me/deletion", {
        method: "POST",
        json: { password: deletePassword, confirmation: "DELETE" },
      });
      setNotice(result.message);
      setDeletion({ status: result.status, execute_after: result.execute_after });
      setDeletePassword("");
      setDeleteWord("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Deletion request failed.");
    } finally {
      setDeleteBusy(false);
    }
  }

  if (!entries) return <Spinner label="Loading consent settings…" />;

  return (
    <div className="stack">
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {notice ? <Alert tone="success">{notice}</Alert> : null}
      {deletion ? (
        <Alert tone="warning" title="Deletion scheduled">
          Status: {deletion.status}
          {deletion.execute_after ? ` · purge after ${deletion.execute_after}` : ""}. All sessions were
          signed out and personal content was removed immediately.
        </Alert>
      ) : null}

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Consent by purpose</h2>
        <p className="small muted">
          Withdrawal applies to future processing. Required account processing can only be ended by
          deleting the account.
        </p>
        <div className="stack">
          {entries.map((entry) => (
            <div key={entry.purpose} className="draft-field">
              <div className="spread">
                <div>
                  <h3 style={{ marginBottom: "0.2rem" }}>
                    {entry.title}{" "}
                    {entry.required ? <Badge tone="neutral">required</Badge> : <Badge tone="info">optional</Badge>}
                  </h3>
                  <p className="small muted" style={{ marginBottom: 0 }}>
                    {entry.description}
                  </p>
                </div>
                <div className="row">
                  <Badge tone={entry.granted ? "ok" : "neutral"}>
                    {entry.granted ? "granted" : "not granted"}
                  </Badge>
                  {entry.required ? (
                    <span className="small muted">Ends only with account deletion</span>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-secondary btn-small"
                      disabled={busyPurpose === entry.purpose}
                      onClick={() => void toggle(entry, !entry.granted)}
                    >
                      {entry.granted ? "Withdraw" : "Grant"}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Export your data</h2>
        <p className="small muted">
          Downloads a JSON file with your account, profile, address, consents, drafts, search history,
          session history and activity. Password confirmation is required.
        </p>
        <form onSubmit={exportData} className="inline-form">
          <Field id="export_password" label="Confirm your password" required>
            <input
              id="export_password"
              className="input"
              type="password"
              autoComplete="current-password"
              value={exportPassword}
              onChange={(event) => setExportPassword(event.target.value)}
              required
            />
          </Field>
          <button type="submit" className="btn btn-secondary" disabled={exportBusy}>
            {exportBusy ? "Preparing…" : "Download export"}
          </button>
        </form>
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Delete your account</h2>
        <p className="small muted">
          Immediate: profile, address, drafts, search history, consents, phone challenges, reset
          requests and sessions are removed, and every device is signed out. The remaining account row is purged after the
          30-day retention window. This cannot be undone from the app.
        </p>
        <form onSubmit={requestDeletion} className="stack">
          <Field id="delete_password" label="Confirm your password" required>
            <input
              id="delete_password"
              className="input"
              type="password"
              autoComplete="current-password"
              value={deletePassword}
              onChange={(event) => setDeletePassword(event.target.value)}
              required
            />
          </Field>
          <Field id="delete_word" label='Type DELETE to confirm' required>
            <input
              id="delete_word"
              className="input"
              value={deleteWord}
              onChange={(event) => setDeleteWord(event.target.value)}
              required
            />
          </Field>
          <button
            type="submit"
            className="btn btn-danger"
            disabled={deleteBusy || deleteWord !== "DELETE"}
          >
            {deleteBusy ? "Requesting…" : "Request account deletion"}
          </button>
        </form>
      </section>
    </div>
  );
}
