"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getAdminAudit, type AuditEventView } from "@workspace/api-client-react";
import { browserRequest, useAuth } from "./AuthProvider";
import AdminAccessGate, { useHasAdministratorAccess } from "./AdminAccessGate";

type RequestFailure = { status?: number; data?: unknown };
type OutcomeFilter = "ALL" | AuditEventView["outcome"];

function safeCode(value: unknown) {
  return typeof value === "string" && /^[A-Z0-9_]{1,60}$/.test(value) ? value : null;
}

function formatTimestamp(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Unknown time"
    : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function AuditContent() {
  const allowed = useHasAdministratorAccess();
  const { revalidate } = useAuth();
  const [events, setEvents] = useState<AuditEventView[]>([]);
  const [search, setSearch] = useState("");
  const [outcome, setOutcome] = useState<OutcomeFilter>("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);
  const inFlight = useRef(false);
  const alive = useRef(true);
  const request = useRef<AbortController | null>(null);

  const refresh = useCallback(async () => {
    if (!allowed || inFlight.current) return;
    inFlight.current = true;
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminAudit({ ...browserRequest, signal: controller.signal });
      if (!controller.signal.aborted && alive.current) setEvents(result);
    } catch (cause) {
      if (controller.signal.aborted || !alive.current) return;
      const failure = cause as RequestFailure;
      setEvents([]);
      setError(safeCode((failure?.data as Record<string, unknown> | undefined)?.reason_code)
        ?? (failure?.status === 401 || failure?.status === 403
          ? "ADMIN_ACCESS_NO_LONGER_VALID"
          : "ADMIN_AUDIT_UNAVAILABLE"));
      if (failure?.status === 401 || failure?.status === 403) void revalidate();
    } finally {
      if (alive.current && !controller.signal.aborted) {
        setCheckedAt(new Date());
        setLoading(false);
      }
      if (request.current === controller) { inFlight.current = false; request.current = null; }
    }
  }, [allowed, revalidate]);

  useEffect(() => {
    alive.current = true;
    if (!allowed) {
      setEvents([]);
      setError(null);
      setLoading(false);
      return () => { alive.current = false; };
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30_000);
    return () => {
      alive.current = false;
      request.current?.abort();
      request.current = null;
      inFlight.current = false;
      window.clearInterval(timer);
    };
  }, [allowed, refresh]);

  const filtered = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase();
    return events.filter(event => {
      if (outcome !== "ALL" && event.outcome !== outcome) return false;
      if (!needle) return true;
      return [event.action, event.actor_type, event.object_type, event.outcome,
        event.reason_code ?? "", event.correlation_id]
        .some(value => value.toLocaleLowerCase().includes(needle));
    });
  }, [events, outcome, search]);

  const counts = useMemo(() => ({
    success: events.filter(event => event.outcome === "SUCCESS").length,
    denied: events.filter(event => event.outcome === "DENIED").length,
    failed: events.filter(event => event.outcome === "FAILED").length,
  }), [events]);

  return (
      <section className="panel admin-audit">
        <div className="admin-audit-intro">
          <div>
            <p className="eyebrow">TENANT-SCOPED · READ ONLY</p>
            <h2>Recent audit events</h2>
            <p className="muted">
              Latest 100 records for your current tenant, ordered newest first.
              Sensitive request data and actor identifiers are not shown.
            </p>
          </div>
          <button className="button" type="button" disabled={loading} onClick={() => void refresh()}>
            Refresh events
          </button>
        </div>

        <div className="admin-audit-summary" aria-label="Results in current page">
          <div><span>Loaded</span><strong>{events.length}</strong></div>
          <div><span>Success</span><strong>{counts.success}</strong></div>
          <div><span>Denied</span><strong>{counts.denied}</strong></div>
          <div><span>Failed</span><strong>{counts.failed}</strong></div>
        </div>

        <div className="admin-audit-tools">
          <label>
            <span>Search current results</span>
            <input value={search} onChange={event => setSearch(event.target.value)}
              placeholder="Action, reason or correlation ID" />
          </label>
          <label>
            <span>Outcome</span>
            <select value={outcome} onChange={event => setOutcome(event.target.value as OutcomeFilter)}>
              <option value="ALL">All outcomes</option>
              <option value="SUCCESS">Success</option>
              <option value="DENIED">Denied</option>
              <option value="FAILED">Failed</option>
            </select>
          </label>
        </div>

        <p className="muted" role="status" aria-live="polite">
          {loading ? "Loading tenant-scoped audit records…" : checkedAt
            ? `${filtered.length} of ${events.length} loaded records · refreshed ${checkedAt.toLocaleTimeString()}`
            : "Audit records have not been loaded."}
          {!loading && events.length === 100 ? " · Showing the latest 100 only" : ""}
        </p>

        {error && <p className="admin-error" role="alert">
          {error === "ADMIN_ACCESS_NO_LONGER_VALID"
            ? "Administrator access expired or was revoked. Re-authenticate to load audit records."
            : `Audit records could not be loaded (${error}).`}
        </p>}

        {!error && filtered.length === 0 && (
          <p className="empty-state" role="status">
            {loading ? "Waiting for the authenticated audit response…"
              : events.length === 0 ? "No audit records are available for this tenant."
                : "No loaded records match these filters."}
          </p>
        )}

        {filtered.length > 0 && (
          <div className="admin-audit-table-wrap">
            <table className="admin-audit-table">
              <caption className="visually-hidden">Latest tenant-scoped administrator audit events</caption>
              <thead><tr>
                <th scope="col">Time</th><th scope="col">Event</th>
                <th scope="col">Actor</th><th scope="col">Outcome</th>
                <th scope="col">Reason</th><th scope="col">Correlation</th>
              </tr></thead>
              <tbody>{filtered.map(event => (
                <tr key={event.id}>
                  <td className="mono admin-audit-time">{formatTimestamp(event.created_at)}</td>
                  <td><strong>{event.action}</strong><span className="admin-audit-object">{event.object_type}</span></td>
                  <td>{event.actor_type}</td>
                  <td><span className={`audit-outcome outcome-${event.outcome.toLowerCase()}`}>{event.outcome}</span></td>
                  <td className="mono">{event.reason_code ?? "—"}</td>
                  <td><code className="admin-correlation" title={event.correlation_id}>{event.correlation_id.slice(0, 8)}</code></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
  );
}

export default function AdminAuditPanel() {
  const { identity } = useAuth();
  return <AdminAccessGate><AuditContent key={`${identity?.user_id}:${identity?.tenant_id}:${identity?.role}`} /></AdminAccessGate>;
}
