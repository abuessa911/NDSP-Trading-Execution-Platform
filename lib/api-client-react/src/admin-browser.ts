import { customFetch, type CustomFetchOptions } from "./custom-fetch";
import type { ReadyResponse, AuditEventView } from "./generated/api.schemas";

export type AdminDirectoryUser = {
  id: string;
  email: string;
  role: "USER" | "OPERATOR" | "ADMIN" | "SUPER_ADMIN";
  status: "active" | "disabled";
};

export type AdminDirectoryView = {
  tenant_id: string;
  tenant_name: string;
  tenant_status: "active" | "disabled";
  users: AdminDirectoryUser[];
  truncated: boolean;
};

export type OperationalCapability = {
  status: "CONFIGURED" | "NOT_CONFIGURED" | "NOT_IMPLEMENTED";
  reason_code: string;
};

export type AdminOperationsView = {
  tenant_id: string;
  entitlements: Record<string, boolean>;
  subscription: OperationalCapability;
  trading_safety: {
    trading_mode: string;
    live_trading_enabled: boolean;
    global_kill_switch: boolean;
    binance_allow_withdraw: boolean;
  };
  exchange: OperationalCapability;
  ndsp_connector: OperationalCapability;
  worker_queues: OperationalCapability;
  notifications: OperationalCapability;
  incidents: OperationalCapability;
};

// The existing external /admin/v1/... contracts remain unchanged.
// Browser cookies are intentionally limited to /api. These aliases have
// identical FastAPI get_administrator/MFA/RLS dependencies to canonical routes.
// Do not send bearer credentials or alter the HttpOnly cookie scope.
export const getBrowserAdminHealth = (options?: CustomFetchOptions): Promise<ReadyResponse> =>
  customFetch<ReadyResponse>("/api/v1/admin/system/health", { ...options, method: "GET" });

export const getBrowserAdminAudit = (options?: CustomFetchOptions): Promise<AuditEventView[]> =>
  customFetch<AuditEventView[]>("/api/v1/admin/audit", { ...options, method: "GET" });

export const getBrowserAdminDirectory = (options?: CustomFetchOptions): Promise<AdminDirectoryView> =>
  customFetch<AdminDirectoryView>("/api/v1/admin/directory", { ...options, method: "GET" });

export const getBrowserAdminOperations = (options?: CustomFetchOptions): Promise<AdminOperationsView> =>
  customFetch<AdminOperationsView>("/api/v1/admin/operations", { ...options, method: "GET" });

export type RegistrationInvitation = {
  id: string;
  email: string;
  role: "USER";
  status: "PENDING" | "ACCEPTED" | "REVOKED";
  expires_at: string;
};
export type RegistrationInvitationsResponse = {
  invitations: RegistrationInvitation[];
  truncated: boolean;
};

// Administrator-authenticated, same-origin M1 registration operations.
// Writes additionally require an ephemeral CSRF token from the verified session.
export const getBrowserAdminRegistrations = (
  options?: CustomFetchOptions,
): Promise<RegistrationInvitationsResponse> =>
  customFetch<RegistrationInvitationsResponse>(
    "/api/v1/admin/registrations", { ...options, method: "GET" });

export const createBrowserAdminRegistration = (
  email: string, csrf: string, options?: CustomFetchOptions,
): Promise<RegistrationInvitation> =>
  customFetch<RegistrationInvitation>("/api/v1/admin/registrations", {
    ...options, method: "POST",
    headers: { "Content-Type": "application/json", "X-NEX-CSRF": csrf },
    body: JSON.stringify({ email }),
  });
