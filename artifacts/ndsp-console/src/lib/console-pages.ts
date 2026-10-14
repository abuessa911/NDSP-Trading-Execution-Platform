export type ConsolePage = {
  slug: string;
  title: string;
  description: string;
  milestone?: string;
};

// Future workflow routes are frontend-only previews, not authorization for a later milestone.
export const userPages: ConsolePage[] = [
  { slug: "command-center", title: "Command Center", description: "Trading-control UI preview, real M1 health and protected identity." },
  { slug: "markets", title: "Markets", description: "Searchable demo watchlist. Static synthetic prices, no exchange connection.", milestone: "UI PREVIEW" },
  { slug: "trading", title: "Trading", description: "Mode, arming, execution controls and latest decisions.", milestone: "M3–M8" },
  { slug: "strategies", title: "Strategies", description: "Versions, assignments and paper/shadow/live readiness.", milestone: "M3–M6" },
  { slug: "positions", title: "Positions", description: "Open and closed positions and protective state.", milestone: "M3 onward" },
  { slug: "orders", title: "Orders", description: "Orders, fills, partials and reconciliation states.", milestone: "M3 onward" },
  { slug: "trade-history", title: "Trade History", description: "Completed executions and their evidence.", milestone: "M3 onward" },
  { slug: "performance", title: "Performance", description: "PnL, drawdown, win rate, fees and slippage.", milestone: "M3 onward" },
  { slug: "risk-center", title: "Risk Center", description: "Limits, exposure, circuit breakers and blocks.", milestone: "M4" },
  { slug: "ndsp-decisions", title: "NDSP Decisions", description: "Illustrative signal lifecycle and evidence. No NDSP contract access.", milestone: "M7" },
  { slug: "execution-trace", title: "Execution Trace / Why?", description: "Decision, risk, policy, order, fills and result.", milestone: "M3–M7" },
  { slug: "replay-lab", title: "Replay Lab", description: "Scrub a synthetic sample sequence. No historical replay runs.", milestone: "M6" },
  { slug: "binance-connection", title: "Binance Connection", description: "Permissions, masked keys, rotation and exchange health.", milestone: "M2" },
  { slug: "notifications", title: "Notifications", description: "Telegram/email setup, history and preferences.", milestone: "Later notification milestone" },
  { slug: "subscription", title: "Subscription", description: "Server-authoritative entitlements. Plan and billing are not implemented in M1." },
  { slug: "settings", title: "Settings", description: "Account identity, tenant, session security and local display preferences." },
  { slug: "security", title: "Security", description: "Current server-authoritative session assurance and authentication boundaries." },
  { slug: "activity", title: "Activity Preview", description: "Searchable synthetic activity examples, separate from protected M1 audit evidence.", milestone: "UI PREVIEW" },
  { slug: "health", title: "Service Health", description: "Live liveness and readiness checks from the hunter_ksa1 bot control API." },
  { slug: "audit", title: "Audit Access", description: "Audit access remains blocked pending independently verified administrative MFA." },
];

export const adminPages: ConsolePage[] = [
  { slug: "operations-center", title: "Operations Center", description: "Control API and tenant dependency health from the protected M1 route." },
  { slug: "users-tenants", title: "Users / Tenants", description: "Read-only, MFA-protected directory of users in the current tenant; no user mutations or plans." },
  { slug: "subscriptions", title: "Subscriptions", description: "Plans and server-authoritative entitlements." },
  { slug: "trading-safety", title: "Trading Safety", description: "Governed global, account and strategy kill switches." },
  { slug: "exchange-health", title: "Exchange Health", description: "Adapters, WebSockets and rate budgets." },
  { slug: "ndsp-health", title: "NDSP Health", description: "Contract intake, signature failures and freshness." },
  { slug: "audit", title: "Audit", description: "Searchable immutable audit evidence." },
  { slug: "notifications", title: "Notifications", description: "Channel health and delivery failures." },
  { slug: "workers-queues", title: "Workers / Queues", description: "Queue lag, retries and dead letters." },
  { slug: "incidents", title: "Incidents", description: "Incident timeline and recovery evidence." },
];

export function pageHref(page: ConsolePage, admin = false) {
  return admin ? `/admin/${page.slug}/` : page.slug === "command-center" ? "/" : `/${page.slug}/`;
}