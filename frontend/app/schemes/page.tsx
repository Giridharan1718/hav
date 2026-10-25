"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { setLang, useLang } from "@/lib/lang";
import { tr } from "@/lib/strings";
import { Alert, Badge, ErrorBlock, PageHeader, ReviewStatusBadge, Spinner } from "@/components/ui";
import type { Lang, SchemeCard, SearchResponse } from "@/lib/types";

const BENEFICIARIES = [
  { value: "", label: "Any beneficiary" },
  { value: "farmer", label: "Farmer" },
  { value: "student", label: "Student" },
  { value: "senior_citizen", label: "Senior citizen" },
  { value: "girl_child", label: "Girl child" },
  { value: "worker", label: "Worker" },
  { value: "rural", label: "Rural household" },
  { value: "sc", label: "Scheduled Caste" },
  { value: "low_income", label: "Low income" },
];

const STATES = ["", "Delhi", "Maharashtra", "Tamil Nadu", "Karnataka", "Telangana", "West Bengal",
  "Gujarat", "Rajasthan", "Uttar Pradesh", "Bihar", "Odisha", "Assam"];

export default function SchemesPage() {
  const cookieLang = useLang();
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [language, setLanguage] = useState<Lang>("en");
  const [state, setState] = useState("");
  const [category, setCategory] = useState("");
  const [beneficiary, setBeneficiary] = useState("");
  const [sort, setSort] = useState("relevance");
  const [page, setPage] = useState(1);
  const [categories, setCategories] = useState<string[]>([]);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const fromUrl = params.get("language");
    if (fromUrl === "hi" || fromUrl === "ta" || fromUrl === "en") {
      setLang(fromUrl);
      setLanguage(fromUrl);
    } else {
      setLanguage(cookieLang);
    }
    setQuery(params.get("q") ?? "");
    setSubmitted(params.get("q") ?? "");
  }, [cookieLang]);

  useEffect(() => {
    api<{ categories: string[] }>("/schemes/meta/categories")
      .then((response) => setCategories(response.categories))
      .catch(() => setCategories([]));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams();
    if (submitted) params.set("query", submitted);
    params.set("language", language);
    if (state) params.set("state", state);
    if (category) params.set("category", category);
    if (beneficiary) params.set("beneficiary", beneficiary);
    params.set("page", String(page));
    params.set("sort", sort);
    params.set("page_size", "10");
    try {
      const response = await api<SearchResponse>(`/schemes?${params.toString()}`);
      setData(response);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [submitted, language, state, category, beneficiary, page, sort]);

  useEffect(() => {
    void load();
  }, [load]);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setPage(1);
    setSubmitted(query.trim());
  }

  function clear() {
    setQuery("");
    setSubmitted("");
    setState("");
    setCategory("");
    setBeneficiary("");
    setSort("relevance");
    setPage(1);
  }

  return (
    <>
      <PageHeader
        title="Scheme catalogue"
        lead="Search the reviewed catalogue. Every record shows its official source, retrieval time and review state."
      />

      <section className="card">
        <form onSubmit={submit} className="search-bar" role="search">
          <label className="sr-only" htmlFor="scheme-query">
            Search schemes
          </label>
          <input
            id="scheme-query"
            className="input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={tr(cookieLang, "search_placeholder")}
            maxLength={200}
          />
          <button type="submit" className="btn btn-primary">
            {tr(cookieLang, "search")}
          </button>
          <button type="button" className="btn btn-ghost" onClick={clear}>
            {tr(cookieLang, "clear")}
          </button>
        </form>

        <div className="filter-grid">
          <div className="field">
            <label htmlFor="filter-language">Content language</label>
            <select
              id="filter-language"
              className="select"
              value={language}
              onChange={(event) => {
                setLanguage(event.target.value as Lang);
                setPage(1);
              }}
            >
              <option value="en">English</option>
              <option value="hi">हिन्दी</option>
              <option value="ta">தமிழ்</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="filter-state">State or UT</label>
            <select id="filter-state" className="select" value={state} onChange={(event) => { setState(event.target.value); setPage(1); }}>
              {STATES.map((item) => (
                <option key={item || "any"} value={item}>
                  {item || "Any state"}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="filter-category">Category</label>
            <select id="filter-category" className="select" value={category} onChange={(event) => { setCategory(event.target.value); setPage(1); }}>
              <option value="">Any category</option>
              {categories.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="filter-beneficiary">Beneficiary</label>
            <select id="filter-beneficiary" className="select" value={beneficiary} onChange={(event) => { setBeneficiary(event.target.value); setPage(1); }}>
              {BENEFICIARIES.map((item) => (
                <option key={item.value || "any"} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="filter-sort">Sort</label>
            <select id="filter-sort" className="select" value={sort} onChange={(event) => setSort(event.target.value)}>
              <option value="relevance">Relevance</option>
              <option value="name">Name</option>
              <option value="updated">Recently checked</option>
            </select>
          </div>
        </div>
      </section>

      <div style={{ marginTop: "1rem" }} aria-live="polite">
        {loading ? <Spinner label="Searching the catalogue…" /> : null}
        {error ? <ErrorBlock error={error} onRetry={() => void load()} /> : null}
        {!loading && data ? (
          <p className="small muted">
            {data.total} {tr(cookieLang, "results")}
            {data.language_detected ? ` · detected ${data.language_detected[0]} (${data.language_detected[1]})` : ""}
            {" · "}
            {data.filters.state || data.filters.category || data.filters.beneficiary
              ? "filters applied"
              : "no filters"}
          </p>
        ) : null}
      </div>

      {!loading && data && data.items.length === 0 ? (
        <div className="empty">
          <h3>{tr(cookieLang, "no_results")}</h3>
          <p>
            Try a simpler word, or clear the filters. The assistant can search the same catalogue and
            explain what it finds.
          </p>
          <div className="row" style={{ justifyContent: "center" }}>
            <Link href="/assistant" className="btn btn-secondary">
              Ask the assistant
            </Link>
            <button type="button" className="btn btn-ghost" onClick={clear}>
              Clear search
            </button>
          </div>
        </div>
      ) : null}

      <div className="stack" style={{ marginTop: "1rem" }}>
        {data?.items.map((scheme: SchemeCard) => (
          <article key={scheme.slug} className="card result-card">
            <div className="spread">
              <div>
                <h3>
                  <Link href={`/schemes/${scheme.slug}?language=${language}`}>{scheme.name}</Link>
                </h3>
                <p className="small muted" style={{ marginBottom: "0.3rem" }}>
                  {scheme.department} · {scheme.scope === "central" ? "Central" : scheme.state ?? "State"} ·{" "}
                  {scheme.category}
                </p>
              </div>
              <div className="row">
                <ReviewStatusBadge status={scheme.source_status.code} label={scheme.source_status.label} />
                {!scheme.translation_available ? <Badge tone="warn">English text</Badge> : null}
              </div>
            </div>
            <p className="result-summary">{scheme.summary}</p>
            <div className="tag-list">
              {scheme.beneficiary_groups.map((group) => (
                <span className="tag" key={group}>
                  {group.replaceAll("_", " ")}
                </span>
              ))}
              {scheme.match.terms.slice(0, 4).map((term) => (
                <span className="tag" key={`t-${term}`}>
                  matched: {term}
                </span>
              ))}
            </div>
            <p className="small muted">
              {scheme.deadline ? `Deadline listed: ${scheme.deadline}. ` : "No deadline recorded. "}
              {scheme.retrieved_at
                ? `Source retrieved ${new Date(scheme.retrieved_at).toLocaleDateString()}.`
                : "Source retrieval time unavailable."}
            </p>
            <div className="row">
              <Link href={`/schemes/${scheme.slug}?language=${language}`} className="btn btn-primary btn-small">
                {tr(cookieLang, "view_details")}
              </Link>
              <Link href={`/schemes/${scheme.slug}/eligibility?language=${language}`} className="btn btn-secondary btn-small">
                {tr(cookieLang, "check_eligibility")}
              </Link>
              <a
                href={scheme.official_url}
                className="btn btn-ghost btn-small"
                target="_blank"
                rel="noopener noreferrer"
              >
                {tr(cookieLang, "official_page")} ↗
              </a>
            </div>
          </article>
        ))}
      </div>

      {data && data.pages > 1 ? (
        <nav className="row" style={{ justifyContent: "center", marginTop: "1.2rem" }} aria-label="Pagination">
          <button
            type="button"
            className="btn btn-secondary btn-small"
            disabled={page <= 1 || loading}
            onClick={() => setPage((value) => Math.max(1, value - 1))}
          >
            {tr(cookieLang, "previous")}
          </button>
          <span className="small">
            {tr(cookieLang, "page")} {data.page} / {data.pages}
          </span>
          <button
            type="button"
            className="btn btn-secondary btn-small"
            disabled={page >= data.pages || loading}
            onClick={() => setPage((value) => value + 1)}
          >
            {tr(cookieLang, "next")}
          </button>
        </nav>
      ) : null}

      {data ? <p className="disclaimer">{data.disclaimer}</p> : null}
      {!loading && !error && data && data.items.length > 0 && data.total > 0 ? (
        <Alert tone="info" title="How ranking works">
          Results use PostgreSQL full-text matching over scheme text plus reviewed translations,
          with a keyword fallback for spelling variation. The “matched” tags show which query terms
          actually appear in the record; no other relevance claim is made.
        </Alert>
      ) : null}
    </>
  );
}
