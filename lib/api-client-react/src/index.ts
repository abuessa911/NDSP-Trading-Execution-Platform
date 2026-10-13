export * from "./generated/api";
// Cookie-scoped browser aliases share the canonical admin authorization dependencies.
export { getBrowserAdminHealth, getBrowserAdminAudit } from "./admin-browser";
export * from "./generated/api.schemas";
export { setBaseUrl, setAuthTokenGetter } from "./custom-fetch";
export type { AuthTokenGetter } from "./custom-fetch";
