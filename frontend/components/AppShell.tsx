"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";
import { LANGUAGES, tr } from "@/lib/strings";
import { setLang, useLang, useOnline } from "@/lib/lang";
import type { Lang } from "@/lib/types";

function LanguagePicker({ lang }: { lang: Lang }) {
  return (
    <label className="lang-picker">
      <span className="sr-only">Choose language</span>
      <select
        aria-label="Choose language"
        value={lang}
        onChange={(event) => setLang(event.target.value as Lang)}
      >
        {LANGUAGES.map((item) => (
          <option key={item.code} value={item.code}>
            {item.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const lang = useLang();
  const online = useOnline();
  const pathname = usePathname();
  const router = useRouter();
  const { me, loading, signOut } = useAuth();

  const nav = [
    { href: "/schemes", label: tr(lang, "nav_schemes") },
    { href: "/assistant", label: tr(lang, "nav_assistant") },
  ];
  if (me) {
    nav.unshift({ href: "/dashboard", label: tr(lang, "nav_dashboard") });
    nav.push({ href: "/drafts", label: tr(lang, "nav_drafts") });
    nav.push({ href: "/profile", label: tr(lang, "nav_profile") });
  }
  if (me?.permissions.reviewer) {
    nav.push({ href: "/admin", label: tr(lang, "nav_admin") });
  }

  async function handleSignOut() {
    await signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      {!online ? (
        <div className="offline-banner" role="status">
          {tr(lang, "offline_title")}
        </div>
      ) : null}
      <header className="site-header">
        <div className="container header-inner">
          <Link href="/" className="brand" aria-label="HVA Assist home">
            <span className="brand-mark" aria-hidden="true">H</span>
            <span>
              <span className="brand-name">{tr(lang, "appName")}</span>
              <span className="brand-tag">{tr(lang, "tagline")}</span>
            </span>
          </Link>
          <nav className="main-nav" aria-label="Main">
            {nav.map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link key={item.href} href={item.href} aria-current={active ? "page" : undefined} className={active ? "active" : ""}>
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="header-tools">
            <LanguagePicker lang={lang} />
            {loading ? null : me ? (
              <>
                <Link href="/settings/privacy" className="btn btn-ghost btn-small">
                  {tr(lang, "nav_privacy")}
                </Link>
                <button type="button" className="btn btn-secondary btn-small" onClick={() => void handleSignOut()}>
                  {tr(lang, "sign_out")}
                </button>
              </>
            ) : (
              <>
                <Link href="/login" className="btn btn-ghost btn-small">
                  {tr(lang, "sign_in")}
                </Link>
                <Link href="/register" className="btn btn-primary btn-small">
                  {tr(lang, "sign_up")}
                </Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main id="main" className="container page">
        {children}
      </main>
      <footer className="site-footer">
        <div className="container footer-inner">
          <p>{tr(lang, "independent_notice")}</p>
          <nav aria-label="Footer">
            <Link href="/privacy">Privacy notice</Link>
            <Link href="/schemes">Scheme catalogue</Link>
            <Link href="/settings/privacy">Consent settings</Link>
            <Link href="/offline">Offline help</Link>
          </nav>
          <p className="small muted">
            Development build · source records are checked automatically and flagged until a human
            reviewer verifies them.
          </p>
        </div>
      </footer>
    </>
  );
}
