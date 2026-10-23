import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "../../..");
const read = (path) => readFileSync(resolve(root, path), "utf8");
const apiMain = read("apps/api/nex_api/main.py");
const authApi = read("apps/api/nex_api/routes/auth.py");
const adminClient = read("lib/api-client-react/src/admin-browser.ts");
const previews = read("artifacts/ndsp-console/src/ndsp/services.ts");
const staticServer = read("artifacts/ndsp-console/scripts/serve-static.mjs");

test("M1 auth and admin routes are declared in backend and client", () => {
  for (const endpoint of ["/api/v1/admin/system/health", "/api/v1/admin/audit", "/api/v1/admin/directory", "/api/v1/admin/operations"]) {
    assert.ok(apiMain.includes(endpoint), "Missing backend: " + endpoint);
    assert.ok(adminClient.includes(endpoint), "Missing client: " + endpoint);
  }
  for (const action of ['@router.post("/login"', '@router.get("/session"', '@router.post("/logout"', '@router.post("/refresh"']) {
    assert.ok(authApi.includes(action), "Missing auth action: " + action);
  }
});

test("administrator data endpoints require the server authorization dependency", () => {
  for (const name of ["admin_health", "admin_audit", "admin_directory", "admin_operations"]) {
    const declaration = apiMain.indexOf("async def " + name + "(");
    assert.ok(declaration > -1, "Missing admin function " + name);
    assert.match(apiMain.slice(declaration, declaration + 270), /Depends\(get_administrator\)/);
  }
});

test("market, orders, positions, risk, signals, and dashboard adapters are explicitly demo", () => {
  assert.match(previews, /import \* as d from "\.\/mocks\/demo-data"/);
  for (const service of ["marketService", "positionService", "orderService", "tradeService", "strategyService", "signalService", "riskService", "alertService", "dashboardService"]) {
    assert.match(previews, new RegExp("export const " + service + " = "));
  }
  const trading = read("artifacts/ndsp-console/src/ndsp/views-trading.tsx");
  assert.match(trading, /Live execution is disabled/);
  const workspace = read("artifacts/ndsp-console/src/components/TradingWorkspace.tsx");
  assert.match(workspace, /saved preferences; order execution and exchange limits are not enabled/);
});

test("the separately gated candle preview is read-only and does not proxy general /api requests", () => {
  const live = read("artifacts/ndsp-console/src/ndsp/LiveMarketPreview.tsx");
  assert.ok(live.includes('fetch("/api/v1/trading/profile/workspace/candles'));
  assert.ok(staticServer.includes('pathname === "/preview/market/closed-candles"'));
  assert.ok(staticServer.includes('request.method !== "GET" && request.method !== "HEAD"'));
  assert.ok(staticServer.includes("HUNTER_READONLY_MARKET_PREVIEW"));
});

test("backend declares unimplemented operational capabilities rather than supplying synthetic state", () => {
  for (const code of ["BILLING_NOT_IMPLEMENTED", "EXCHANGE_CONNECTOR_NOT_CONFIGURED", "NDSP_CONNECTOR_NOT_CONFIGURED", "M1_DATA_SOURCE_NOT_IMPLEMENTED"]) {
    assert.ok(apiMain.includes(code), "Missing explicit capability state: " + code);
  }
});
