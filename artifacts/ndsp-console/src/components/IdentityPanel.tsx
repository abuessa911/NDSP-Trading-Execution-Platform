"use client";

import { useAuth } from "./AuthProvider";

export default function IdentityPanel({ entitlementsOnly = false }: { entitlementsOnly?: boolean }) {
  const { state, identity } = useAuth();
  if (!identity || state !== "authenticated") {
    return <section className="panel"><h2>Protected account information</h2><p className="muted">An active, provisioned application session is required. Account and tenant information are not available while signed out.</p></section>;
  }
  return (
    <section className="panel">
      <h2>{entitlementsOnly ? "Server-authoritative entitlements" : "Account and tenant"}</h2>
      {!entitlementsOnly && <dl className="kv-list">
        <div className="kv-row"><dt>Email</dt><dd>{identity.email}</dd></div>
        <div className="kv-row"><dt>User ID</dt><dd className="mono">{identity.user_id}</dd></div>
        <div className="kv-row"><dt>Tenant ID</dt><dd className="mono">{identity.tenant_id}</dd></div>
        <div className="kv-row"><dt>Role</dt><dd>{identity.role}</dd></div>
        <div className="kv-row"><dt>Status</dt><dd>{identity.status}</dd></div>
      </dl>}
      <dl className="kv-list">
        {Object.entries(identity.entitlements).map(([feature, allowed]) =>
          <div key={feature} className="kv-row"><dt className="mono">{feature}</dt><dd>{allowed ? "Permitted by identity API" : "Not permitted"}</dd></div>)}
      </dl>
      <p className="muted">These values come from /api/v1/me, not provider role claims or browser settings. Entitlement alone never enables trading.</p>
      {entitlementsOnly && <p className="notice">No subscription plan, billing service or purchase flow exists in M1. No plan is inferred from an entitlement.</p>}
    </section>
  );
}