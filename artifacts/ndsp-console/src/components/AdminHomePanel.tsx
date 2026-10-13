"use client";

import Link from "next/link";
import { Activity, ClipboardList } from "lucide-react";
import { useAuth } from "./AuthProvider";
import { useHasAdministratorAccess } from "./AdminAccessGate";

export default function AdminHomePanel() {
  const { state, identity } = useAuth();
  const verified = useHasAdministratorAccess();
  const role = identity?.role;

  return (
    <>
      <section className="panel admin-home-status" aria-live="polite">
        <div>
          <p className="eyebrow">SERVER-VERIFIED ACCESS</p>
          <h2>{verified ? "Administrator session verified" : "Administrator session required"}</h2>
          <p className="muted">
            {verified
              ? "The control API confirms your administrator role and current password + TOTP assurance."
              : state === "loading"
                ? "Checking the current server session. No privileged data is loaded on this page."
                : state === "authenticated" && role !== "ADMIN" && role !== "SUPER_ADMIN"
                  ? "This account does not have an administrator role. No privileged data is loaded."
                  : "Sign in with an ADMIN or SUPER_ADMIN account and complete password + TOTP verification to open an M1 admin view."}
          </p>
        </div>
        <span className={`admin-status ${verified ? "is-ready" : "is-unknown"}`}>
          <span aria-hidden="true" />{verified ? role : "MFA REQUIRED"}
        </span>
      </section>

      <section className="panel admin-home-tools">
        <div>
          <p className="eyebrow">AVAILABLE IN M1</p>
          <h2>Control-plane tools</h2>
          <p className="muted">
            Read-only administrator views request data only after this browser has a fresh,
            server-verified administrator session. The API checks every request.
          </p>
        </div>
        <div className="admin-home-links">
          <Link className="button" href="/admin/operations-center/">
            <Activity size={15} aria-hidden /> Service health
          </Link>
          <Link className="button" href="/admin/users-tenants/">Tenant users</Link>
          <Link className="button" href="/admin/audit/">
            <ClipboardList size={15} aria-hidden /> Audit events
          </Link>
        </div>
      </section>

      <section className="panel admin-home-boundary">
        <h2>Remaining administrator surfaces</h2>
        <p className="muted">
          User and tenant changes, trading controls, exchange and NDSP health,
          queues and incident workflows remain unavailable in M1.
        </p>
      </section>
    </>
  );
}
