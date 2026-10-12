"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getAdminHealth, type ReadyResponse } from "@workspace/api-client-react";
import { browserRequest, useAuth } from "./AuthProvider";
import AdminAccessGate, { useHasAdministratorAccess } from "./AdminAccessGate";

type RequestFailure = { status?: number; data?: unknown };

function isReadiness(value: unknown): value is ReadyResponse {
  if (!value || typeof value !== "object") return false;
  const result = value as Record<string, unknown>;
  return typeof result.status === "string"
    && (result.reason_code === null || typeof result.reason_code === "string")
    && !!result.components && typeof result.components === "object"
    && !Array.isArray(result.components)
    && Object.values(result.components).every(component => typeof component === "string");
}

function failureCode(error: unknown) {
  const data = (error as RequestFailure | null)?.data;
  if (!data || typeof data !== "object") return null;
  const code = (data as Record<string, unknown>).reason_code;
  return typeof code === "string" && /^[A-Z0-9_]{1,60}$/.test(code) ? code : null;
}

function readinessError(error: unknown): ReadyResponse | null {
  const failure = error as RequestFailure | null;
  return failure?.status === 503 && isReadiness(failure.data) ? failure.data : null;
}

function HealthContent() {
  const allowed = useHasAdministratorAccess();
  const { revalidate } = useAuth();
  const [health, setHealth] = useState<ReadyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
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
      const result = await getAdminHealth({ ...browserRequest, signal: controller.signal });
      if (!controller.signal.aborted && alive.current) setHealth(result);
    } catch (cause) {
      if (controller.signal.aborted || !alive.current) return;
      const degraded = readinessError(cause);
      if (degraded) {
        setHealth(degraded);
      } else {
        setHealth(null);
        const failure = cause as RequestFailure;
        setError(failureCode(cause) ?? (failure?.status === 401 || failure?.status === 403
          ? "ADMIN_ACCESS_NO_LONGER_VALID"
          : "ADMIN_HEALTH_UNAVAILABLE"));
        if (failure?.status === 401 || failure?.status === 403) void revalidate();
      }
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
      setHealth(null);
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

  const ready = health?.status === "ready";
  const components = Object.entries(health?.components ?? {});

  return (
      <div className="admin-health">
        <section className="panel admin-overview">
          <div>
            <p className="eyebrow">LIVE CONTROL-PLANE CHECK</p>
            <h2>Service readiness</h2>
            <p className="muted">
              Authenticated server-side check of the control API, database, Redis and identity provider.
              It does not report trading, exchange or NDSP health.
            </p>
          </div>
          <div className={`admin-status ${ready ? "is-ready" : health ? "is-degraded" : "is-unknown"}`}
            aria-live="polite">
            <span aria-hidden="true" />
            {health?.status === "ready" ? "READY" : health ? "NOT READY" : loading ? "CHECKING" : "UNAVAILABLE"}
          </div>
        </section>

        <section className="panel">
          <div className="row admin-panel-heading">
            <div>
              <h2>System components</h2>
              <p className="muted" role="status">
                {loading ? "Refreshing health…" : checkedAt
                  ? `Last checked ${checkedAt.toLocaleTimeString()}. Auto-refreshes every 30 seconds.`
                  : "A health check has not completed."}
              </p>
            </div>
            <button className="button" type="button" disabled={loading} onClick={() => void refresh()}>
              Refresh health
            </button>
          </div>

          {error && <p className="admin-error" role="alert">
            {error === "ADMIN_ACCESS_NO_LONGER_VALID"
              ? "Administrator access expired or was revoked. Re-authenticate to check health."
              : `Health check could not be completed (${error}).`}
          </p>}
          {health?.reason_code && <p className="notice mono">{health.reason_code}</p>}

          {components.length > 0 ? (
            <ul className="admin-component-list" aria-label="Control-plane service status">
              {components.map(([name, status]) => (
                <li className="admin-component" key={name}>
                  <span>{name.replaceAll("_", " ")}</span>
                  <span className={`admin-component-state ${status === "ready" ? "is-ready" : "is-degraded"}`}>
                    {status}
                  </span>
                </li>
              ))}
            </ul>
          ) : !error && <p className="empty-state" role="status">
            {loading ? "Waiting for the authenticated health response…" : "No health data is available."}
          </p>}
        </section>
      </div>
  );
}

export default function AdminHealthPanel() {
  const { identity } = useAuth();
  return <AdminAccessGate><HealthContent key={`${identity?.user_id}:${identity?.tenant_id}:${identity?.role}`} /></AdminAccessGate>;
}
