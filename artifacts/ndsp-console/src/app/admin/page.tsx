import type { Metadata } from "next";
import Link from "next/link";
import AdminHomePanel from "../../components/AdminHomePanel";
import PageFrame from "../../components/PageFrame";
import { adminPages, pageHref } from "../../lib/console-pages";

export const metadata: Metadata = { title: "M1 Admin", description: "Tenant-scoped service health and audit views protected by server-verified administrator MFA." };

export default function AdminIndex() {
  const unavailablePages = adminPages.filter(page => ![
    "operations-center", "users-tenants", "subscriptions", "trading-safety",
    "exchange-health", "ndsp-health", "audit", "notifications", "workers-queues", "incidents",
  ].includes(page.slug));
  return <PageFrame title="M1 Admin" description="Read-only tenant operations. Access is verified server-side on every request.">
    <AdminHomePanel />
    <section className="panel"><h2>Other specified administrator routes</h2><p className="muted">Navigation never grants access. Unsupported data sources are shown as NOT_CONFIGURED or NOT_IMPLEMENTED.</p>
      <ul>{unavailablePages.map(page => <li key={page.slug}><Link href={pageHref(page, true)}>{page.title}</Link></li>)}</ul>
    </section>
  </PageFrame>;
}
