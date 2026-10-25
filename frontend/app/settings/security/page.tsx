"use client";

import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { useRequireAuth } from "@/components/useRequireAuth";
import { useAuth } from "@/components/AuthProvider";
import { Alert, Badge, Field, PageHeader } from "@/components/ui";
import type { SessionInfo } from "@/lib/types";

export default function SecurityPage() {
  const { me, loading } = useRequireAuth();
  const { refresh } = useAuth();
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [setup, setSetup] = useState<{ secret: string; provisioning_uri: string } | null>(null);
  const [code, setCode] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadSessions = useCallback(async () => {
    try {
      setSessions(await api<SessionInfo[]>("/auth/sessions"));
    } catch (err) {
      setError(err);
    }
  }, []);

  useEffect(() => {
    if (me) void loadSessions();
  }, [me, loadSessions]);

  async function startMfa() {
    setBusy(true);
    setError(null);
    try {
      const result = await api<{ secret: string; provisioning_uri: string }>("/auth/mfa/setup", {
        method: "POST",
      });
      setSetup(result);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function confirmMfa(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/mfa/confirm", { method: "POST", json: { code } });
      setNotice("Multifactor authentication enabled for this account.");
      setSetup(null);
      setCode("");
      await refresh();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function changePassword(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await api("/auth/password/change", {
        method: "POST",
        json: { current_password: currentPassword, new_password: newPassword },
      });
      setNotice("Password changed. Other sessions were signed out.");
      setCurrentPassword("");
      setNewPassword("");
      await loadSessions();
      await refresh();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function revoke(id: string) {
    setError(null);
    try {
      await api(`/auth/sessions/${id}`, { method: "DELETE" });
      await loadSessions();
      await refresh();
    } catch (err) {
      setError(err);
    }
  }

  async function revokeOthers() {
    setError(null);
    try {
      await api("/auth/sessions", { method: "DELETE" });
      setNotice("All other sessions were revoked.");
      await loadSessions();
    } catch (err) {
      setError(err);
    }
  }

  if (loading) return <div className="card">Loading security settings…</div>;
  if (!me) return <div className="card">Redirecting to sign in…</div>;

  return (
    <>
      <PageHeader
        title="Security"
        lead="Sessions, password and multifactor authentication."
      />
      {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}
      {notice ? <Alert tone="success">{notice}</Alert> : null}

      <div className="grid-2">
        <section className="card">
          <h2 style={{ marginTop: 0 }}>Multifactor authentication</h2>
          <p>
            Status:{" "}
            {me.user.mfa_enabled ? <Badge tone="ok">enabled</Badge> : <Badge tone="warn">not enabled</Badge>}
          </p>
          <p className="small muted">
            Reviewer and administrator accounts must enable TOTP before any review action is permitted.
            Accounts with MFA enabled sign in with a second step.
          </p>
          {setup ? (
            <form onSubmit={confirmMfa}>
              <Alert tone="info" title="Add this secret to your authenticator app">
                <p style={{ wordBreak: "break-all" }}>
                  <strong>{setup.secret}</strong>
                </p>
                <p className="small" style={{ wordBreak: "break-all" }}>
                  {setup.provisioning_uri}
                </p>
                <p className="small">
                  The secret is stored encrypted. No QR code is generated in this build; paste the
                  secret into the app manually.
                </p>
              </Alert>
              <Field id="mfa-code" label="6-digit code" required>
                <input
                  id="mfa-code"
                  className="input"
                  inputMode="numeric"
                  value={code}
                  onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                  autoComplete="one-time-code"
                  required
                />
              </Field>
              <button type="submit" className="btn btn-primary" disabled={busy || code.length !== 6}>
                Confirm and enable
              </button>
            </form>
          ) : me.user.mfa_enabled ? (
            <p className="small muted">To reset MFA, contact the operator; no self-service reset is implemented.</p>
          ) : (
            <button type="button" className="btn btn-primary" onClick={() => void startMfa()} disabled={busy}>
              Set up authenticator app
            </button>
          )}
        </section>

        <section className="card">
          <h2 style={{ marginTop: 0 }}>Change password</h2>
          <form onSubmit={changePassword}>
            <Field id="current" label="Current password" required>
              <input
                id="current"
                className="input"
                type="password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                required
              />
            </Field>
            <Field id="new" label="New password" required hint="At least 10 characters; other sessions will be signed out.">
              <input
                id="new"
                className="input"
                type="password"
                autoComplete="new-password"
                minLength={10}
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                required
              />
            </Field>
            <button type="submit" className="btn btn-secondary" disabled={busy}>
              Update password
            </button>
          </form>
        </section>
      </div>

      <section className="card" style={{ marginTop: "1rem" }}>
        <div className="spread">
          <h2 style={{ marginTop: 0 }}>Active sessions</h2>
          <button type="button" className="btn btn-secondary btn-small" onClick={() => void revokeOthers()}>
            Sign out other sessions
          </button>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Created</th>
                <th scope="col">Last seen</th>
                <th scope="col">Expires</th>
                <th scope="col">Auth level</th>
                <th scope="col">Action</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr key={session.id}>
                  <td>{new Date(session.created_at).toLocaleString()}</td>
                  <td>{new Date(session.last_seen_at).toLocaleString()}</td>
                  <td>{new Date(session.expires_at).toLocaleString()}</td>
                  <td>
                    {session.auth_level}
                    {session.current ? <Badge tone="info">this device</Badge> : null}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-ghost btn-small"
                      onClick={() => void revoke(session.id)}
                      disabled={session.current}
                    >
                      {session.current ? "Current" : "Revoke"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="small muted">
          Session cookies are HttpOnly and SameSite=Lax. Only token hashes are stored server-side.
        </p>
      </section>
    </>
  );
}
