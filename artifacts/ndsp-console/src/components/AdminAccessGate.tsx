"use client";

import type { ReactNode } from "react";
import { useAuth } from "./AuthProvider";
import { hasAdministratorAccess } from "../lib/admin-access";

export function useHasAdministratorAccess() {
  const { state, identity, administratorMfaVerified } = useAuth();
  return hasAdministratorAccess(state, identity?.role, administratorMfaVerified);
}

export default function AdminAccessGate({ children }: { children: ReactNode }) {
  const { state, identity, administratorMfaVerified } = useAuth();
  const roleAllowed = identity?.role === "ADMIN" || identity?.role === "SUPER_ADMIN";
  const allowed = hasAdministratorAccess(state, identity?.role, administratorMfaVerified);

  if (allowed) return children;

  let message = "Checking your server-verified administrator session.";
  if (state === "anonymous") {
    message = "Sign in with an administrator account and complete password + TOTP verification.";
  } else if (state === "unavailable") {
    message = "Authentication could not be confirmed. No privileged data was requested.";
  } else if (state === "unconfigured") {
    message = "Administrator sign-in is not configured in this environment.";
  } else if (state === "authenticated" && !roleAllowed) {
    message = "This view is limited to ADMIN and SUPER_ADMIN accounts.";
  } else if (state === "authenticated" && roleAllowed && !administratorMfaVerified) {
    message = "A fresh, server-verified password + TOTP session is required.";
  }

  return (
    <section className="panel admin-gate" role="status" aria-live="polite">
      <span className="tag">SERVER-ENFORCED MFA</span>
      <h2>Administrator access required</h2>
      <p>{message}</p>
      <p className="muted">
        The browser does not unlock access from a URL or role claim. The control API
        checks the administrator role and current MFA assurance on every request.
      </p>
    </section>
  );
}
