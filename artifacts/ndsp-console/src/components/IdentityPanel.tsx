"use client";

import { useAuth } from "./AuthProvider";
import { Tx } from "../ndsp/ui";

export default function IdentityPanel({ entitlementsOnly = false }: { entitlementsOnly?: boolean }) {
  const { state, identity } = useAuth();
  if (!identity || state !== "authenticated") {
    return <section className="panel"><h2><Tx>{"Protected account information"}</Tx></h2><p className="muted"><Tx>{"An active, provisioned application session is required. Account and tenant information are not available while signed out."}</Tx></p></section>;
  }
  return (
    <section className="panel">
      <h2>{entitlementsOnly ? <Tx>{"Server-authoritative entitlements"}</Tx> : <Tx>{"Account and tenant"}</Tx>}</h2>
      {!entitlementsOnly && <dl className="kv-list">
        <div className="kv-row"><dt><Tx>{"Email"}</Tx></dt><dd>{identity.email}</dd></div>
        <div className="kv-row"><dt><Tx>{"User ID"}</Tx></dt><dd className="mono">{identity.user_id}</dd></div>
        <div className="kv-row"><dt><Tx>{"Tenant ID"}</Tx></dt><dd className="mono">{identity.tenant_id}</dd></div>
        <div className="kv-row"><dt><Tx>{"Role"}</Tx></dt><dd>{identity.role}</dd></div>
        <div className="kv-row"><dt><Tx>{"Status"}</Tx></dt><dd>{identity.status}</dd></div>
      </dl>}
      <dl className="kv-list">
        {Object.entries(identity.entitlements ?? {}).map(([feature, allowed]) =>
          <div key={feature} className="kv-row"><dt className="mono">{feature}</dt><dd>{allowed ? <Tx>{"Permitted by identity API"}</Tx> : <Tx>{"Not permitted"}</Tx>}</dd></div>)}
      </dl>
      <p className="muted"><Tx>{"These values come from /api/v1/me, not provider role claims or browser settings. Entitlement alone never enables trading."}</Tx></p>
      {entitlementsOnly && <p className="notice"><Tx>{"No subscription plan, billing service or purchase flow exists in M1. No plan is inferred from an entitlement."}</Tx></p>}
    </section>
  );
}