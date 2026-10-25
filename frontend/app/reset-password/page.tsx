"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError, fieldIssues } from "@/lib/api";
import { Alert, Field } from "@/components/ui";

export default function ResetPasswordPage() {
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setToken(params.get("token"));
  }, []);

  async function request(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await api<{ message: string }>("/auth/password/reset/request", {
        method: "POST",
        json: { email },
      });
      setMessage(response.message);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function confirm(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/password/reset/confirm", {
        method: "POST",
        json: { token, new_password: password },
      });
      setMessage("Password updated. All existing sessions were signed out.");
      setToken(null);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const issues = fieldIssues(error);

  return (
    <div className="card" style={{ maxWidth: 540, marginInline: "auto" }}>
      <h1>{token ? "Choose a new password" : "Reset your password"}</h1>
      {message ? <Alert tone="success">{message}</Alert> : null}
      {error ? (
        <Alert tone="danger">
          {error instanceof ApiError ? error.message : "The request failed. Try again."}
        </Alert>
      ) : null}
      {token ? (
        <form onSubmit={confirm}>
          <Field id="password" label="New password" required hint="At least 10 characters." error={issues.new_password}>
            <input
              id="password"
              className="input"
              type="password"
              autoComplete="new-password"
              minLength={10}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </Field>
          <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
            {busy ? "Updating…" : "Update password"}
          </button>
        </form>
      ) : (
        <form onSubmit={request}>
          <p>
            Enter the email registered with your account. If it exists, a reset link is sent. The
            response is the same either way, to limit account enumeration.
          </p>
          <Field id="email" label="Email" required>
            <input
              id="email"
              className="input"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </Field>
          <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
            {busy ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}
      <p className="small" style={{ marginTop: "1rem" }}>
        <Link href="/login">Back to sign in</Link>
      </p>
      <p className="small muted">
        In development, reset messages are written to <code>backend/.dev-outbox</code> instead of being
        emailed. Production requires an SMTP or provider adapter to be configured.
      </p>
    </div>
  );
}
