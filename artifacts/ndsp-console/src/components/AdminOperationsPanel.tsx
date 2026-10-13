"use client";

import { useCallback, useEffect, useState } from "react";
import { getBrowserAdminOperations, type AdminOperationsView } from "@workspace/api-client-react";
import { browserRequest, useAuth } from "./AuthProvider";
import AdminAccessGate, { useHasAdministratorAccess } from "./AdminAccessGate";

const labels: Record<string, string> = {
  subscriptions: "Subscriptions / entitlements",
  "trading-safety": "Trading safety",
  "exchange-health": "Exchange connector health",
  "ndsp-health": "NDSP connector health",
  notifications: "Notifications",
  "workers-queues": "Workers / queues",
  incidents: "Incidents",
};

function OperationsContent({ section }: { section: string }) {
  const allowed = useHasAdministratorAccess();
  const { revalidate } = useAuth();
  const [data, setData] = useState<AdminOperationsView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!allowed) return;
    setLoading(true); setError(null);
    try { setData(await getBrowserAdminOperations(browserRequest)); }
    catch (cause) {
      const failure = cause as { status?: number; data?: { reason_code?: unknown } };
      const reason = failure.data?.reason_code;
      setData(null);
      setError(typeof reason === "string" && /^[A-Z0-9_]{1,60}$/.test(reason)
        ? reason : "ADMIN_OPERATIONS_UNAVAILABLE");
      if (failure.status === 401 || failure.status === 403) void revalidate();
    } finally { setLoading(false); }
  }, [allowed, revalidate]);

  useEffect(() => { if (allowed) void refresh(); else setLoading(false); }, [allowed, refresh]);

  let rows: [string, string][] = [];
  if (data) {
    const capability = section === "subscriptions" ? data.subscription
      : section === "exchange-health" ? data.exchange
      : section === "ndsp-health" ? data.ndsp_connector
      : section === "notifications" ? data.notifications
      : section === "workers-queues" ? data.worker_queues : data.incidents;
    rows = section === "trading-safety" ? Object.entries(data.trading_safety).map(([k, v]) => [k, String(v)])
      : section === "subscriptions" ? [
        ["subscription", `${capability.status} · ${capability.reason_code}`],
        ...Object.entries(data.entitlements).map(([k, v]) => [`entitlement: ${k}`, String(v)]),
      ] : [["status", capability.status], ["reason", capability.reason_code]];
  }

  return <section className="panel">
    <div className="row admin-panel-heading"><div>
      <p className="eyebrow">SERVER AUTHORITATIVE · TENANT SCOPED · READ ONLY</p>
      <h2>{labels[section]}</h2>
      <p className="muted">Unavailable dependencies are reported explicitly; no synthetic operational data is substituted.</p>
    </div><button className="button" type="button" disabled={loading} onClick={() => void refresh()}>Refresh</button></div>
    {loading && <p role="status">Loading authorized operational status…</p>}
    {error && <p className="admin-error" role="alert">Could not load operational status ({error}).</p>}
    {data && <><p className="muted mono">Tenant {data.tenant_id}</p><dl className="admin-audit-summary">
      {rows.map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd><strong>{value}</strong></dd></div>)}
    </dl></>}
  </section>;
}

export default function AdminOperationsPanel({ section }: { section: string }) {
  const { identity } = useAuth();
  return <AdminAccessGate><OperationsContent key={`${identity?.user_id}:${section}`} section={section} /></AdminAccessGate>;
}
