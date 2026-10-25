"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { useRequireAuth } from "@/components/useRequireAuth";
import { Alert, Badge, PageHeader, Spinner } from "@/components/ui";

interface QueueItem {
  version_id: string;
  scheme_slug: string;
  scheme_name: string;
  department: string;
  version_no: number;
  review_status: string;
  retrieved_at: string | null;
  source_document_id: string | null;
  application_url: string;
  rule_count: boolean;
}

interface AuditItem {
  id: string;
  action: string;
  actor_role: string | null;
  resource_type: string;
  resource_id: string | null;
  outcome: string;
  created_at: string;
  metadata: Record<string, unknown>;
}

interface IngestionRun {
  id: string;
  url: string;
  host: string;
  status: string;
  http_status: number | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

interface Overview {
  counts: {
    published_schemes: number;
    pending_versions: number;
    failed_jobs_24h: number;
  };
  integrity_note: string;
}

export default function AdminPage() {
  const { me, loading } = useRequireAuth();
  const [queue, setQueue] = useState<QueueItem[] | null>(null);
  const [audit, setAudit] = useState<AuditItem[]>([]);
  const [runs, setRuns] = useState<IngestionRun[]>([]);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [ingestUrl, setIngestUrl] = useState("");
  const [jobsNote, setJobsNote] = useState<string | null>(null);

  const allowed = me?.permissions.reviewer ?? false;

  const load = useCallback(async () => {
    try {
      const [queueData, auditData, runsData, overviewData, jobsData] = await Promise.all([
        api<{ items: QueueItem[] }>("/admin/review/queue"),
        api<{ items: AuditItem[] }>("/admin/audit?limit=40"),
        api<{ items: IngestionRun[] }>("/admin/ingestion/runs"),
        api<Overview>("/admin/overview"),
        api<{ worker_note: string }>("/admin/jobs"),
      ]);
      setQueue(queueData.items);
      setAudit(auditData.items);
      setRuns(runsData.items);
      setOverview(overviewData);
      setJobsNote(jobsData.worker_note);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    if (allowed) void load();
  }, [allowed, load]);

  async function decide(versionId: string, decision: "approve" | "reject") {
    setBusy(versionId);
    setError(null);
    setNotice(null);
    try {
      const result = await api<{ review_status: string; scheme_slug: string }>(
        `/admin/schemes/${versionId}/review`,
        {
          method: "POST",
          json: { decision, notes: notes[versionId] || null },
        },
      );
      setNotice(`${result.scheme_slug}: ${decision} recorded (status ${result.review_status}).`);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function startIngestion(event: React.FormEvent) {
    event.preventDefault();
    setBusy("ingestion");
    setError(null);
    try {
      const result = await api<{ run_id: string; host: string; status: string }>("/admin/ingestion", {
        method: "POST",
        json: { url: ingestUrl },
      });
      setNotice(`Ingestion queued for ${result.host}. Run the worker to fetch and hash the page.`);
      setIngestUrl("");
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <div className="card">Checking access…</div>;
  if (!me) return <div className="card">Redirecting to sign in…</div>;
  if (!allowed) {
    return (
      <div className="card">
        <h1>Not available</h1>
        <p>This area is for content reviewers and administrators.</p>
        <Link href="/" className="btn btn-secondary">
          Return home
        </Link>
      </div>
    );
  }

  return (
    <>
      <PageHeader
        title="Administration"
        lead="Review source records, queue authorised ingestion and inspect the audit trail. Every action is recorded."
        actions={<Badge tone={me.user.mfa_enabled ? "ok" : "warn"}>MFA {me.user.mfa_enabled ? "enabled" : "missing"}</Badge>}
      />

      {!me.user.mfa_enabled ? (
        <Alert tone="danger" title="Review actions are blocked">
          Review endpoints require an MFA-enrolled account. <Link href="/settings/security">Set up MFA</Link>{" "}
          and sign in again.
        </Alert>
      ) : null}
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {notice ? <Alert tone="success">{notice}</Alert> : null}

      <div className="grid-3">
        <div className="card">
          <h3>Published schemes</h3>
          <p style={{ fontSize: "1.8rem", margin: "0.2rem 0" }}>{overview?.counts.published_schemes ?? 0}</p>
          <p className="small muted">Records currently visible in the public catalogue.</p>
        </div>
        <div className="card">
          <h3>Pending versions</h3>
          <p style={{ fontSize: "1.8rem", margin: "0.2rem 0" }}>{overview?.counts.pending_versions ?? "—"}</p>
          <p className="small muted">Including records only source-checked, never auto-verified.</p>
        </div>
        <div className="card">
          <h3>Failed jobs (24h)</h3>
          <p style={{ fontSize: "1.8rem", margin: "0.2rem 0" }}>{overview?.counts.failed_jobs_24h ?? "—"}</p>
          <p className="small muted">{jobsNote}</p>
        </div>
        <div className="card">
          <h3>Your session</h3>
          <p>{me.user.email}</p>
          <p className="small muted">
            Role {me.user.role} · MFA satisfied: {me.permissions.mfa_satisfied ? "yes" : "no"}
          </p>
        </div>
      </div>

      <section className="card" style={{ marginTop: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Review queue</h2>
        <p className="small muted">{overview?.integrity_note}</p>
        {queue === null ? <Spinner label="Loading queue…" /> : null}
        {queue && queue.length === 0 ? <p className="muted">Nothing is waiting for review.</p> : null}
        {queue && queue.length > 0 ? (
          <div className="stack">
            {queue.map((item) => (
              <div key={item.version_id} className="draft-field">
                <div className="spread">
                  <div>
                    <h3 style={{ marginBottom: "0.2rem" }}>
                      {item.scheme_name} <span className="small muted">v{item.version_no}</span>
                    </h3>
                    <p className="small muted" style={{ marginBottom: "0.3rem" }}>
                      {item.department} · slug {item.scheme_slug} ·{" "}
                      {item.retrieved_at ? `retrieved ${new Date(item.retrieved_at).toLocaleDateString()}` : "no retrieval time"}
                    </p>
                  </div>
                  <div className="row">
                    <Badge tone="warn">{item.review_status}</Badge>
                    <Badge tone={item.rule_count ? "info" : "neutral"}>
                      {item.rule_count ? "rules recorded" : "no rules"}
                    </Badge>
                  </div>
                </div>
                <p className="small">
                  <a href={item.application_url} target="_blank" rel="noopener noreferrer">
                    Open the recorded application page ↗
                  </a>{" "}
                  · <Link href={`/schemes/${item.scheme_slug}`}>Preview record</Link>
                </p>
                <label className="sr-only" htmlFor={`notes-${item.version_id}`}>
                  Review notes
                </label>
                <input
                  id={`notes-${item.version_id}`}
                  className="input"
                  placeholder="Review notes (required when rejecting; recorded with your reviewer id)"
                  value={notes[item.version_id] ?? ""}
                  onChange={(event) => setNotes({ ...notes, [item.version_id]: event.target.value })}
                  maxLength={2000}
                />
                <div className="row" style={{ marginTop: "0.5rem" }}>
                  <button
                    type="button"
                    className="btn btn-primary btn-small"
                    disabled={busy === item.version_id || !me.user.mfa_enabled}
                    onClick={() => void decide(item.version_id, "approve")}
                  >
                    Approve and publish
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger btn-small"
                    disabled={busy === item.version_id || !me.user.mfa_enabled}
                    onClick={() => void decide(item.version_id, "reject")}
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </section>

      <section className="card" style={{ marginTop: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Source ingestion</h2>
        <p className="small muted">
          Only https URLs on the approved host list are accepted. The fetcher rejects private and
          loopback addresses, validates every redirect and records the page hash and retrieval time. It
          never auto-writes eligibility rules.
        </p>
        <form onSubmit={startIngestion} className="inline-form">
          <label className="sr-only" htmlFor="ingest-url">
            Source URL
          </label>
          <input
            id="ingest-url"
            className="input"
            type="url"
            placeholder="https://pmkisan.gov.in/"
            value={ingestUrl}
            onChange={(event) => setIngestUrl(event.target.value)}
            required
          />
          <button type="submit" className="btn btn-secondary" disabled={busy === "ingestion"}>
            Queue ingestion
          </button>
        </form>
        {runs.length > 0 ? (
          <div className="table-wrap" style={{ marginTop: "0.8rem" }}>
            <table>
              <thead>
                <tr>
                  <th scope="col">Host</th>
                  <th scope="col">Status</th>
                  <th scope="col">HTTP</th>
                  <th scope="col">Error</th>
                  <th scope="col">Queued</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id}>
                    <td>{run.host}</td>
                    <td>{run.status}</td>
                    <td>{run.http_status ?? "—"}</td>
                    <td>{run.error ?? "—"}</td>
                    <td>{new Date(run.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="small muted">No ingestion runs yet.</p>
        )}
      </section>

      <section className="card" style={{ marginTop: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Audit trail</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">When</th>
                <th scope="col">Action</th>
                <th scope="col">Role</th>
                <th scope="col">Resource</th>
                <th scope="col">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {audit.map((event) => (
                <tr key={event.id}>
                  <td>{new Date(event.created_at).toLocaleString()}</td>
                  <td>{event.action}</td>
                  <td>{event.actor_role ?? "—"}</td>
                  <td>
                    {event.resource_type}
                    {event.resource_id ? ` · ${event.resource_id.slice(0, 8)}…` : ""}
                  </td>
                  <td>{event.outcome}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {audit.length === 0 ? <p className="small muted">No audit events yet.</p> : null}
        <p className="small muted">
          Audit metadata excludes passwords, OTPs, tokens and questionnaire answers.
        </p>
      </section>
    </>
  );
}
