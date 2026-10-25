"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { Alert, Field } from "@/components/ui";

interface LoginResponse {
  status: string;
  mfa_required: boolean;
  mfa_token: string | null;
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") ?? "/dashboard";
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submitPassword(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = await api<LoginResponse>("/auth/login", {
        method: "POST",
        json: { email, password },
      });
      if (response.mfa_required && response.mfa_token) {
        setMfaToken(response.mfa_token);
      } else {
        await refresh();
        router.push(next);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign-in failed. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function submitCode(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/mfa/verify", {
        method: "POST",
        json: { mfa_token: mfaToken, code },
      });
      await refresh();
      router.push(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Verification failed. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card" style={{ maxWidth: 520, marginInline: "auto" }}>
      <h1>Sign in</h1>
      <p className="lead">Your session uses a secure HttpOnly cookie. Sign out on shared devices.</p>
      {error ? <Alert tone="danger">{error}</Alert> : null}

      {mfaToken ? (
        <form onSubmit={submitCode}>
          <Alert tone="info" title="Multifactor authentication">
            Reviewer and administrator accounts require a 6-digit code from an authenticator app.
          </Alert>
          <Field id="code" label="Authentication code" required hint="The code refreshes every 30 seconds.">
            <input
              id="code"
              className="input"
              inputMode="numeric"
              pattern="[0-9]{6}"
              autoComplete="one-time-code"
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
              required
            />
          </Field>
          <button type="submit" className="btn btn-primary btn-block" disabled={busy || code.length !== 6}>
            {busy ? "Verifying…" : "Verify and continue"}
          </button>
        </form>
      ) : (
        <form onSubmit={submitPassword}>
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
          <Field id="password" label="Password" required>
            <input
              id="password"
              className="input"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </Field>
          <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      )}

      <p className="small" style={{ marginTop: "1rem" }}>
        <Link href="/reset-password">Forgot your password?</Link> · New here?{" "}
        <Link href="/register">Create an account</Link>.
      </p>
      <p className="small muted">
        Sign-in errors are deliberately generic so that accounts cannot be enumerated.
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="card">Loading sign-in…</div>}>
      <LoginForm />
    </Suspense>
  );
}
