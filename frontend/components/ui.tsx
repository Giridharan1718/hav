"use client";

import Link from "next/link";
import { errorMessage } from "@/lib/api";

export function Alert({
  tone = "info",
  title,
  children,
}: {
  tone?: "info" | "success" | "warning" | "danger";
  title?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className={`alert alert-${tone}`} role={tone === "danger" ? "alert" : "status"}>
      {title ? <strong>{title}</strong> : null}
      {children ? <div>{children}</div> : null}
    </div>
  );
}

export function Badge({
  tone = "neutral",
  children,
  title,
}: {
  tone?: "neutral" | "ok" | "warn" | "danger" | "info";
  children: React.ReactNode;
  title?: string;
}) {
  return (
    <span className={`badge badge-${tone}`} title={title}>
      {children}
    </span>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <span className="spinner" role="status" aria-live="polite">
      <span className="spinner-dot" aria-hidden="true" />
      {label}
    </span>
  );
}

export function Field({
  id,
  label,
  hint,
  error,
  required,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="field">
      <label htmlFor={id}>
        {label} {required ? <span className="req">*</span> : <span className="muted small">(optional)</span>}
      </label>
      {children}
      {hint ? <p className="hint">{hint}</p> : null}
      {error ? (
        <p className="field-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function ErrorBlock({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <Alert tone="danger" title="Could not load this information">
      <p>{errorMessage(error)}</p>
      {onRetry ? (
        <button type="button" className="btn btn-secondary btn-small" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </Alert>
  );
}

export function EmptyState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

export function PageHeader({
  title,
  lead,
  actions,
}: {
  title: string;
  lead?: string;
  actions?: React.ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {lead ? <p className="lead">{lead}</p> : null}
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}

export function ReviewStatusBadge({
  status,
  label,
}: {
  status: string;
  label?: string;
}) {
  const map: Record<string, { tone: "ok" | "warn" | "danger" | "info" | "neutral"; text: string }> = {
    verified: { tone: "ok", text: "Reviewed by a content reviewer" },
    source_checked: { tone: "warn", text: "Source link checked; content review pending" },
    pending_review: { tone: "warn", text: "Awaiting content review" },
    draft: { tone: "neutral", text: "Draft" },
    rejected: { tone: "danger", text: "Rejected in review" },
    superseded: { tone: "neutral", text: "Superseded" },
  };
  const entry = map[status] ?? { tone: "neutral" as const, text: status };
  return (
    <Badge tone={entry.tone} title={label ?? entry.text}>
      {entry.text}
    </Badge>
  );
}

export function Breadcrumbs({ items }: { items: Array<{ href?: string; label: string }> }) {
  return (
    <nav aria-label="Breadcrumb" className="breadcrumbs">
      <ol>
        {items.map((item, index) => (
          <li key={`${item.label}-${index}`}>
            {item.href ? <Link href={item.href}>{item.label}</Link> : <span aria-current="page">{item.label}</span>}
          </li>
        ))}
      </ol>
    </nav>
  );
}

export function Notice({ children }: { children: React.ReactNode }) {
  return <p className="notice">{children}</p>;
}
