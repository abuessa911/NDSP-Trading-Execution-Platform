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
