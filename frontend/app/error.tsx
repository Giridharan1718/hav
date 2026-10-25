"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // The API returns a request id; the client never logs personal data.
    console.error("page error", error.digest ?? "no-digest");
  }, [error]);

  return (
    <section className="card" role="alert">
      <h1>Something went wrong on this page</h1>
      <p>
        The action could not be completed. Your saved data is unchanged unless the page confirmed a
        save. You can retry, return to the catalogue, or use the offline help page.
      </p>
      <div className="row">
        <button type="button" className="btn btn-primary" onClick={() => reset()}>
          Try again
        </button>
        <Link href="/schemes" className="btn btn-secondary">
          Browse schemes
        </Link>
        <Link href="/offline" className="btn btn-ghost">
          Offline help
        </Link>
      </div>
      {error.digest ? <p className="small muted">Reference: {error.digest}</p> : null}
    </section>
  );
}
