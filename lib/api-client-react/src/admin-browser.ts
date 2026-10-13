import { customFetch, type CustomFetchOptions } from "./custom-fetch";
import type { ReadyResponse, AuditEventView } from "./generated/api.schemas";

// The existing external /admin/v1/... contracts remain unchanged.
// Browser cookies are intentionally limited to /api. These aliases have
// identical FastAPI get_administrator/MFA/RLS dependencies to canonical routes.
// Do not send bearer credentials or alter the HttpOnly cookie scope.
export const getBrowserAdminHealth = (options?: CustomFetchOptions): Promise<ReadyResponse> =>
  customFetch<ReadyResponse>("/api/v1/admin/system/health", { ...options, method: "GET" });

export const getBrowserAdminAudit = (options?: CustomFetchOptions): Promise<AuditEventView[]> =>
  customFetch<AuditEventView[]>("/api/v1/admin/audit", { ...options, method: "GET" });
