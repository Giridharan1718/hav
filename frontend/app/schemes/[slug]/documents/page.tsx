"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { tr } from "@/lib/strings";
import { useLang } from "@/lib/lang";
import { Alert, Badge, Breadcrumbs, ErrorBlock, PageHeader, Spinner } from "@/components/ui";
import type { Lang } from "@/lib/types";

interface ChecklistDocument {
  key: string;
  name: string;
  note: string | null;
  required: boolean;
  source_reference: string | null;
}

interface ChecklistResponse {
  scheme: { slug: string; name: string; version_no: number };
  documents: ChecklistDocument[];
  translation_available: boolean;
  language: Lang;
  note: string;
  source: { url: string | null; link_verified: boolean; retrieved_at: string | null };
  disclaimer: string;
}

export default function DocumentsPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const lang = useLang() as Lang;
  const [data, setData] = useState<ChecklistResponse | null>(null);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  const storageKey = `hva-checklist-${slug}`;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api<ChecklistResponse>(`/schemes/${slug}/checklist?language=${lang}`);
      setData(response);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [slug, lang]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(storageKey);
      setChecked(stored ? (JSON.parse(stored) as Record<string, boolean>) : {});
    } catch {
      setChecked({});
    }
  }, [storageKey]);

  function toggle(key: string) {
    setChecked((current) => {
      const next = { ...current, [key]: !current[key] };
      try {
        window.localStorage.setItem(storageKey, JSON.stringify(next));
      } catch {
        // Storage may be unavailable in private mode; the checklist still works for this visit.
      }
      return next;
    });
  }

  if (loading) return <div className="card"><Spinner label="Loading the checklist…" /></div>;
  if (error) return <ErrorBlock error={error} onRetry={() => void load()} />;
  if (!data) return null;

  const done = data.documents.filter((item) => checked[item.key]).length;

  return (
    <>
      <Breadcrumbs
        items={[
          { href: "/schemes", label: "Scheme catalogue" },
          { href: `/schemes/${slug}`, label: data.scheme.name },
          { label: "Document checklist" },
        ]}
      />
      <PageHeader
        title="Document checklist"
        lead={data.scheme.name}
        actions={
          <Link href={`/schemes/${slug}`} className="btn btn-secondary">
            Back to scheme
          </Link>
        }
      />
      {!data.translation_available ? <Alert tone="warning">{tr(lang, "translation_unavailable")}</Alert> : null}
      <Alert tone="info" title="Checklist stays in your browser">
        Ticks are saved in this browser only — no document is uploaded, scanned or shared. Never send
        document copies to anyone claiming to act for HVA.
      </Alert>

      <section className="card">
        <div className="spread">
          <h2 style={{ marginTop: 0 }}>
            {done} of {data.documents.length} collected
          </h2>
          <button type="button" className="btn btn-ghost btn-small" onClick={() => { setChecked({}); window.localStorage.removeItem(storageKey); }}>
            Reset checklist
          </button>
        </div>
        <ul className="list-clean">
          {data.documents.map((document) => (
            <li key={document.key}>
              <div className="check">
                <input
                  id={`doc-${document.key}`}
                  type="checkbox"
                  checked={Boolean(checked[document.key])}
                  onChange={() => toggle(document.key)}
                />
                <label htmlFor={`doc-${document.key}`}>
                  <strong>{document.name}</strong>{" "}
                  {document.required ? <Badge tone="warn">required</Badge> : <Badge tone="neutral">if applicable</Badge>}
                  {document.note ? <div className="small muted">{document.note}</div> : null}
                </label>
              </div>
            </li>
          ))}
        </ul>
        <p className="small muted">{data.note}</p>
        <p className="small muted">
          Source:{" "}
          {data.source.url ? (
            <a href={data.source.url} target="_blank" rel="noopener noreferrer">
              {data.source.url}
            </a>
          ) : (
            "not recorded"
          )}{" "}
          · {data.source.link_verified ? "link checked" : "link could not be verified"}
          {data.source.retrieved_at
            ? ` · retrieved ${new Date(data.source.retrieved_at).toLocaleDateString()}`
            : ""}
        </p>
        <p className="disclaimer">{data.disclaimer}</p>
      </section>
      <div className="row" style={{ marginTop: "1rem" }}>
        <Link href={`/schemes/${slug}/eligibility`} className="btn btn-secondary">
          Check eligibility
        </Link>
        <Link href={`/schemes/${slug}`} className="btn btn-ghost">
          Read the full scheme record
        </Link>
      </div>
    </>
  );
}
