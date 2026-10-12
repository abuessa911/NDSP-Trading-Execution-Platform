"use client";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <section className="panel"><h1>Console unavailable</h1><p>No operation has been confirmed. No access was granted.</p><button className="button" onClick={reset}>Retry page</button></section>;
}