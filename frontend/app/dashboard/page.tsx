"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/components/useRequireAuth";
import { Alert, Badge, PageHeader } from "@/components/ui";

interface DraftSummary {
  id: string;
  title: string;
  status: string;
  field_count: number;
  missing_required: number;
  updated_at: string;
}

export default function DashboardPage() {
  const { me, loading } = useRequireAuth();
  const [drafts, setDrafts] = useState<DraftSummary[] | null>(null);
  const [draftsError, setDraftsError] = useState(false);

  useEffect(() => {
    if (!me) return;
    api<{ drafts: DraftSummary[] }>("/drafts")
      .then((response) => setDrafts(response.drafts))
      .catch(() => setDraftsError(true));
  }, [me]);

  if (loading) return <div className="card">Loading your dashboard…</div>;
  if (!me) return <div className="card">Redirecting to sign in…</div>;

  const profileReady = Boolean(me.profile?.full_name);
  const addressReady = Boolean(me.address?.post_office_confirmed);
  const analytics = me.consents.find((item) => item.purpose === "analytics")?.granted ?? false;

  return (
    <>
      <PageHeader
        title={`Welcome${me.profile?.full_name ? `, ${me.profile.full_name.split(" ")[0]}` : ""}`}
        lead="Your starting points, privacy state and saved drafts."
        actions={
          <>
            <Link href="/schemes" className="btn btn-primary">
              Find schemes
            </Link>
            <Link href="/assistant" className="btn btn-secondary">
              Ask the assistant
            </Link>
          </>
        }
      />

      {me.permissions.reviewer && !me.user.mfa_enabled ? (
        <Alert tone="warning" title="Multifactor authentication is not enabled">
          Reviewer actions are blocked until you enrol an authenticator app.{" "}
          <Link href="/settings/security">Set up MFA</Link>.
        </Alert>
      ) : null}

      <div className="grid-3">
        <section className="card">
          <h2 style={{ marginTop: 0 }}>Profile</h2>
          <p>
            {profileReady ? <Badge tone="ok">name saved</Badge> : <Badge tone="warn">not set</Badge>}{" "}
            {me.profile?.phone_verified ? <Badge tone="ok">phone verified</Badge> : null}
          </p>
          <p className="small muted">
            {me.profile?.date_of_birth
              ? "Date of birth is stored encrypted and used only for age criteria."
              : "Date of birth is optional and not stored."}
          </p>
          <Link href="/profile">Edit profile</Link>
        </section>
        <section className="card">
          <h2 style={{ marginTop: 0 }}>Address</h2>
          <p>
            {addressReady ? <Badge tone="ok">post office confirmed</Badge> : <Badge tone="warn">incomplete</Badge>}
          </p>
          <p className="small muted">
            {me.address
              ? `${me.address.pincode}${me.address.post_office ? ` · ${me.address.post_office}` : ""}${
                  me.address.state ? `, ${me.address.state}` : ""
                }`
              : "No address saved. State-specific schemes need a state or UT."}
          </p>
          <Link href="/profile">Edit address</Link>
        </section>
        <section className="card">
          <h2 style={{ marginTop: 0 }}>Privacy</h2>
          <p>
            Search analytics: <Badge tone={analytics ? "info" : "neutral"}>{analytics ? "on" : "off"}</Badge>
          </p>
          <p className="small muted">
            Questionnaire answers are not stored. Assistant messages are not stored in this build.
          </p>
          <Link href="/settings/privacy">Manage consent and data</Link>
        </section>
      </div>

      <section className="card" style={{ marginTop: "1rem" }}>
        <div className="spread">
          <h2 style={{ marginTop: 0 }}>Application drafts</h2>
          <Link href="/drafts" className="btn btn-secondary btn-small">
            View all drafts
          </Link>
        </div>
        {draftsError ? <Alert tone="danger">Could not load drafts.</Alert> : null}
        {drafts === null && !draftsError ? <p className="muted">Loading drafts…</p> : null}
        {drafts && drafts.length === 0 ? (
          <p className="muted">
            No drafts yet. Open a scheme and choose “Prepare application draft”. Nothing is submitted
            automatically.
          </p>
        ) : null}
        {drafts && drafts.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Scheme</th>
                  <th scope="col">Fields</th>
                  <th scope="col">Missing required</th>
                  <th scope="col">Updated</th>
                </tr>
              </thead>
              <tbody>
                {drafts.slice(0, 5).map((draft) => (
                  <tr key={draft.id}>
                    <td>
                      <Link href={`/drafts/${draft.id}`}>{draft.title}</Link>
                    </td>
                    <td>{draft.field_count}</td>
                    <td>{draft.missing_required}</td>
                    <td>{new Date(draft.updated_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="card" style={{ marginTop: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Account</h2>
        <p className="small">
          {me.user.email} · role: {me.user.role} · MFA:{" "}
          {me.user.mfa_enabled ? "enabled" : "not enabled"}
        </p>
        <div className="row">
          <Link href="/settings/security" className="btn btn-secondary btn-small">
            Security and sessions
          </Link>
          <Link href="/settings/privacy" className="btn btn-ghost btn-small">
            Export or delete account
          </Link>
        </div>
      </section>
    </>
  );
}
