export default function Loading() {
  return (
    <div className="card" aria-busy="true" aria-live="polite">
      <p>Loading this page…</p>
      <p className="small muted">
        If the service is slow, you can still read the privacy notice and offline help.
      </p>
    </div>
  );
}
