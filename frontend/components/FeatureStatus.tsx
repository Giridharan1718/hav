"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Health } from "@/lib/types";
import { Alert, Badge, Spinner } from "./ui";

interface CatalogueHealth {
  published_schemes: number;
  postal_dataset: {
    name: string;
    is_sample: boolean;
    record_count: number;
    retrieved_at: string | null;
    source_url: string | null;
  } | null;
  note: string;
}

export function FeatureStatus() {
  const [health, setHealth] = useState<Health | null>(null);
  const [catalogue, setCatalogue] = useState<CatalogueHealth | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api<Health>("/health"), api<CatalogueHealth>("/health/catalogue")])
      .then(([h, c]) => {
        if (!cancelled) {
          setHealth(h);
          setCatalogue(c);
        }
      })
      .catch(() => {
        if (!cancelled) setError("Service status is unavailable right now.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <Alert tone="warning">{error}</Alert>;
  if (!health) return <Spinner label="Checking service status…" />;

  const assistant = health.features.assistant;
  const transcription = health.features.transcription;

  return (
    <div className="stack">
      <div className="row">
        <Badge tone={health.database === "ok" ? "ok" : "danger"}>
          Database {health.database}
        </Badge>
        <Badge tone="neutral">{health.environment}</Badge>
        <Badge tone="info">{catalogue?.published_schemes ?? 0} published schemes</Badge>
        <Badge tone="neutral">
          {health.features.translation.provider === "catalog"
            ? "Curated translations"
            : "Machine translation provider"}
        </Badge>
        <Badge tone="neutral">
          Assistant: {assistant.configured ? assistant.provider : "local grounded summaries"}
        </Badge>
        <Badge tone={transcription.configured ? "ok" : "warn"}>
          Speech input: {transcription.configured ? "available" : "not configured"}
        </Badge>
      </div>
      {catalogue?.postal_dataset ? (
        <p className="small muted">
          Postal data: {catalogue.postal_dataset.name} ({catalogue.postal_dataset.record_count} sample
          records). This is a development sample, not the full India Post directory.
        </p>
      ) : null}
      <p className="small muted">
        Assistant answers are built from the cited catalogue records. Where no reviewed translation
        exists, the English source text is shown rather than an unreviewed machine translation.
      </p>
    </div>
  );
}
