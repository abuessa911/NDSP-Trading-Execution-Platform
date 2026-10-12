import Link from "next/link";

export default function NotFound() {
  return <section className="panel"><h1>Page not found</h1><p>No module exists at this address. No access was granted.</p><Link className="button" href="/">Return to Command Center</Link></section>;
}