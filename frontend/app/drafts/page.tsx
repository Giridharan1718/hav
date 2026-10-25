"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { useRequireAuth } from "@/components/useRequireAuth";
import { Alert, Badge, PageHeader, Spinner } from "@/components/ui";

interface DraftSummary {
  id: string;
  title: string;
  status: string;
  field_count: number;
  missing_required: number;
  updated_at: string;
}

export default function DraftsPage() {
  const { me, loading } = useRequireAuth();
  const [drafts, setDrafts] = useState<DraftSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const response = await api<{ drafts: DraftSummary[] }>("/drafts");
      setDrafts(response.drafts);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    if (me) void load();
  }, [me, load]);

  if (loading) return <div className="card">Loading drafts…</div>;
  if (!me) return <div className="card">Redirecting to sign in…</div>;

  return (
    <>
      <PageHeader
        title="Saved drafts"
        lead="Application-preparation drafts are private to your account. Nothing is submitted automatically."
        actions={
          <Link href="/schemes" className="btn btn-primary">
            Find a scheme to draft
          </Link>
        }
      />
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {drafts === null && !error ? <div className="card"><Spinner label="Loading drafts…" /></div> : null}
      {drafts && drafts.length === 0 ? (
        <div className="empty">
          <h3>No drafts yet</h3>
          <p>Open a scheme and choose “Prepare application draft”.</p>
        </div>
      ) : null}
      {drafts && drafts.length > 0 ? (
        <div className="stack">
          {drafts.map((draft) => (
            <article key={draft.id} className="card">
              <div className="spread">
                <div>
                  <h3 style={{ marginBottom: "0.2rem" }}>
                    <Link href={`/drafts/${draft.id}`}>{draft.title}</Link>
                  </h3>
                  <p className="small muted" style={{ marginBottom: 0 }}>
                    {draft.field_count} fields · updated {new Date(draft.updated_at).toLocaleString()}
                  </p>
                </div>
                <div className="row">
                  <Badge tone="neutral">{draft.status}</Badge>
                  {draft.missing_required > 0 ? (
                    <Badge tone="warn">
                      {draft.missing_required} required field{draft.missing_required === 1 ? "" : "s"} missing
                    </Badge>
                  ) : (
                    <Badge tone="ok">required fields present</Badge>
                  )}
                  <Link href={`/drafts/${draft.id}`} className="btn btn-secondary btn-small">
                    Open
                  </Link>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : null}
      <p className="disclaimer">
        Drafts contain personal data you entered. Export only to a device you trust.
      </p>
    </>
  );
}
