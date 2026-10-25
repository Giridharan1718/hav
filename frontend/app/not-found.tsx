import Link from "next/link";

export default function NotFound() {
  return (
    <section className="card">
      <h1>Page not found</h1>
      <p>The page or scheme you asked for is not available. It may have been unpublished.</p>
      <div className="row">
        <Link href="/schemes" className="btn btn-primary">
          Browse the scheme catalogue
        </Link>
        <Link href="/" className="btn btn-secondary">
          Go to the home page
        </Link>
      </div>
    </section>
  );
}
