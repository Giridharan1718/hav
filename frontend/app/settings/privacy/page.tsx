"use client";

import Link from "next/link";
import { ConsentSettings } from "@/components/ConsentSettings";
import { useRequireAuth } from "@/components/useRequireAuth";
import { Alert } from "@/components/ui";

export default function PrivacySettingsPage() {
  const { me, loading } = useRequireAuth();

  if (loading) return <div className="card">Loading your privacy settings…</div>;
  if (!me) return <div className="card">Redirecting to sign in…</div>;

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Privacy and consent</h1>
          <p className="lead">
            Signed in as {me.user.email}. Manage optional processing, export your data or request
            account deletion.
          </p>
        </div>
        <div className="page-actions">
          <Link href="/privacy" className="btn btn-secondary">
            Read the privacy notice
          </Link>
          <Link href="/settings/security" className="btn btn-ghost">
            Security settings
          </Link>
        </div>
      </header>
      <Alert tone="info" title="Questionnaire answers are never stored">
        Age, income, category, landholding and similar answers used for an eligibility check exist only
        in that request. Drafts contain only what you explicitly save.
      </Alert>
      <ConsentSettings />
    </>
  );
}
