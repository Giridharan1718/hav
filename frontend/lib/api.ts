"use client";

export class ApiError extends Error {
  code: string;
  status: number;
  details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

let csrfInFlight: Promise<string | null> | null = null;

async function ensureCsrf(): Promise<string | null> {
  const existing = readCookie("hva_csrf");
  if (existing) return existing;
  if (!csrfInFlight) {
    csrfInFlight = fetch("/api/v1/auth/csrf", { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) return null;
        const body = (await response.json()) as { csrf_token?: string };
        return body.csrf_token ?? readCookie("hva_csrf");
      })
      .catch(() => null)
      .finally(() => {
        csrfInFlight = null;
      });
  }
  return csrfInFlight;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  json?: unknown;
  signal?: AbortSignal;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const csrf = await ensureCsrf();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.json !== undefined) headers["Content-Type"] = "application/json";
  if (csrf && method !== "GET") headers["X-CSRF-Token"] = csrf;

  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      credentials: "include",
      headers,
      body: options.json === undefined ? undefined : JSON.stringify(options.json),
      signal: options.signal,
    });
  } catch {
    throw new ApiError(0, "network_error", "Could not reach the service. Check your connection and try again.");
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  let payload: unknown = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const error = (payload as { error?: { code?: string; message?: string; details?: unknown } } | null)?.error;
    throw new ApiError(
      response.status,
      error?.code ?? "request_failed",
      error?.message ?? "The request could not be completed.",
      error?.details,
    );
  }
  return payload as T;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong. Please try again.";
}

export function fieldIssues(error: unknown): Record<string, string> {
  const result: Record<string, string> = {};
  if (!(error instanceof ApiError) || !Array.isArray(error.details)) return result;
  for (const item of error.details as Array<{ field?: string; issue?: string }>) {
    if (item?.field && item?.issue) result[item.field.replace(/^body\./, "")] = item.issue;
  }
  return result;
}
