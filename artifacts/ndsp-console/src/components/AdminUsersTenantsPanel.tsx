"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  getBrowserAdminDirectory, type AdminDirectoryView,
} from "@workspace/api-client-react";
import { browserRequest, useAuth } from "./AuthProvider";
import AdminAccessGate, { useHasAdministratorAccess } from "./AdminAccessGate";

type RequestFailure = { status?: number; data?: unknown };

function safeReason(value: unknown) {
  return typeof value === "string" && /^[A-Z0-9_]{1,60}$/.test(value)
    ? value : null;
}

function DirectoryContent() {
  const allowed = useHasAdministratorAccess();
  const { revalidate } = useAuth();
  const [directory, setDirectory] = useState<AdminDirectoryView | null>(null);
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
      const result = await getBrowserAdminDirectory({
        ...browserRequest, signal: controller.signal,
      });
      const valid = result && typeof result.tenant_id === "string"
        && typeof result.tenant_name === "string"
        && Array.isArray(result.users)
        && result.users.every(user => user && typeof user.id === "string"
          && typeof user.email === "string"
          && typeof user.role === "string"
          && typeof user.status === "string");
      if (!valid) throw new Error("INVALID_ADMIN_DIRECTORY_RESPONSE");
      if (!controller.signal.aborted && alive.current) setDirectory(result);
    } catch (cause) {
      if (controller.signal.aborted || !alive.current) return;
      const failure = cause as RequestFailure;
      setDirectory(null);
      setError(safeReason((failure.data as Record<string, unknown> | undefined)?.reason_code)
        ?? (failure.status === 401 || failure.status === 403
          ? "ADMIN_ACCESS_NO_LONGER_VALID" : "ADMIN_DIRECTORY_UNAVAILABLE"));
      if (failure.status === 401 || failure.status === 403) void revalidate();
    } finally {
      if (alive.current && !controller.signal.aborted) {
        setCheckedAt(new Date());
        setLoading(false);
      }
      if (request.current === controller) {
        inFlight.current = false;
        request.current = null;
      }
    }
  }, [allowed, revalidate]);

  useEffect(() => {
    alive.current = true;
    if (!allowed) {
      setDirectory(null);
      setError(null);
      setLoading(false);
      return () => { alive.current = false; };
    }
    void refresh();
    const interval = window.setInterval(() => void refresh(), 30_000);
    return () => {
      alive.current = false;
      request.current?.abort();
      request.current = null;
      inFlight.current = false;
      window.clearInterval(interval);
    };
  }, [allowed, refresh]);

  return (
    <section className="panel admin-directory">
      <div className="row admin-panel-heading">
        <div>
          <p className="eyebrow">SERVER-ENFORCED MFA · TENANT SCOPED · READ ONLY</p>
          <h2>Tenant users</h2>
          <p className="muted">Only users from the authenticated administrator&apos;s
            tenant. Account status and permissions cannot be changed here.</p>
        </div>
        <button className="button" type="button" disabled={loading}
          onClick={() => void refresh()}>Refresh users</button>
      </div>
      <p className="muted" role="status">
        {loading ? "Loading authorized tenant users…" : checkedAt
          ? "Last checked " + checkedAt.toLocaleTimeString() + "."
          : "No server-authorized directory has been loaded."}
      </p>
      {error && <p className="admin-error" role="alert">
        {error === "ADMIN_ACCESS_NO_LONGER_VALID"
          ? "Administrator access expired or was revoked."
          : "Could not load tenant users (" + error + ")."}
      </p>}
      {!error && directory && (
        <>
          <div className="admin-audit-summary">
            <div><span>Tenant</span><strong>{directory.tenant_name}</strong></div>
            <div><span>Status</span><strong>{directory.tenant_status}</strong></div>
            <div><span>Users in page</span><strong>{directory.users.length}</strong></div>
          </div>
          {directory.truncated && <p role="status">
            Showing the latest 100 users only; no pagination in this milestone.
          </p>}
          {directory.users.length ? (
            <div className="admin-audit-table-wrap">
              <table className="admin-audit-table">
                <caption className="visually-hidden">Read-only tenant user directory</caption>
                <thead><tr><th scope="col">Email</th><th scope="col">Role</th>
                  <th scope="col">Status</th></tr></thead>
                <tbody>{directory.users.map(user => (
                  <tr key={user.id}><td>{user.email}</td>
                    <td>{user.role}</td><td>{user.status}</td></tr>
                ))}</tbody>
              </table>
            </div>
          ) : <p className="empty-state">No users are available in this tenant.</p>}
        </>
      )}
    </section>
  );
}

export default function AdminUsersTenantsPanel() {
  const { identity } = useAuth();
  return <AdminAccessGate><DirectoryContent
    key={String(identity?.user_id) + ":" + String(identity?.tenant_id) + ":" + String(identity?.role)} />
  </AdminAccessGate>;
}
