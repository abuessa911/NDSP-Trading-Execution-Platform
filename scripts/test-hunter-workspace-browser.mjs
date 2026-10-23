/** Interactive wiring checks against the real exported UI and mocked API.
 * This does not prove provider MFA or broker execution. No real API receives
 * a request; the browser can access only the disposable loopback fixture.
 * Run after building, with Playwright available or PLAYWRIGHT_MODULE set.
 */
import assert from "node:assert/strict";
import http from "node:http";
import { readFile } from "node:fs/promises";
import { resolve, sep, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const root = resolve(fileURLToPath(new URL("..", import.meta.url)), "artifacts/ndsp-console/out");
const server = http.createServer(async (request, response) => {
  try {
    let pathname = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
    if (pathname.endsWith("/")) pathname += "index.html";
    const path = resolve(root, "." + pathname);
    if (!path.startsWith(root + sep)) throw Error("PATH_REJECTED");
    const bytes = await readFile(path);
    const mime = { ".html": "text/html", ".js": "application/javascript", ".css": "text/css", ".txt": "text/plain", ".svg": "image/svg+xml" };
    response.writeHead(200, { "Content-Type": mime[extname(path)] || "application/octet-stream" });
    response.end(bytes);
  } catch { response.writeHead(404); response.end("Not found"); }
});
await new Promise(done => server.listen(0, "127.0.0.1", done));
const origin = "http://127.0.0.1:" + server.address().port;
let browser;
try {
  browser = await chromium.launch({ headless: true });
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 1000 } });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    let virtual = { mode: "PAPER", configured: false, real_orders_enabled: false, position: null, orders: [], total_orders: 0 };
    const acknowledgements = new Map(); let dropFirstAck = true, orderRequests = [];
    let demo = { venue: "BINANCE_USDM_TESTNET", mainnet_orders_enabled: false, configured: false,
      revision: null, config: null, credentials_saved: false, active_position: null, pending_order: null,
      halted: false, daily_loss_hit: false, opening_equity: null, last_equity: null, receipts: [],
      automation: { state: "STOPPED", expires_at: null, last_checked_ms: null, last_result: null, reason: null } };
    let demoDropAck = true, demoFills = 0, demoRequests = [], autoRequests = [], autoDropAck = true;
    const demoReceipts = new Map();
    let signedIn = true, failedSave = false, monitor = false, scans = new Set(), puts = 0, seenStart = null;
    let settings = { mode: "SPECULATIVE", symbol: "BTCUSDT", interval: "5m", execution_method: "MANUAL", leverage: 1, margin_mode: "ISOLATED", persisted: false, execution_authorized: false, ndsp_contract_bound: false };
    const id = { user_id: "00000000-0000-0000-0000-000000000004", tenant_id: "00000000-0000-0000-0000-000000000003", role: "OPERATOR" };
    const definitions = ["trend-ladder", "range-fade", "breakout-scout", "mean-return"];
    await page.route("**/*", async route => {
      const url = new URL(route.request().url());
      if (url.origin !== origin) return route.abort();
      if (!url.pathname.startsWith("/api/")) return route.continue();
      const request = route.request(), path = url.pathname, method = request.method();
      const reply = (body, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
      if (path === "/api/health/auth") return reply({ browser_login_enabled: true, administrator_mfa_configured: true });
      if (path.endsWith("/auth/session")) return signedIn ? reply({ ...id, authenticated: true, csrf_token: "fixture-csrf", administrator_mfa_verified: false }) : reply({}, 401);
      if (path === "/api/v1/me") return reply({ ...id, email: "fixture@example.test", status: "active", entitlements: { live_trading: false } });
      if (path.endsWith("/auth/logout")) { signedIn = false; return reply({ logout_url: null }); }
      if (!signedIn) return reply({}, 401);
      if (path === "/api/v1/trading/profile/workspace") {
        if (method === "PUT") {
          puts++;
          assert.equal(request.headers()["x-nex-csrf"], "fixture-csrf");
          if (failedSave) return reply({ reason_code: "FIXTURE_UNAVAILABLE" }, 503);
          settings = { ...settings, ...request.postDataJSON(), persisted: true };
          monitor = false; scans.clear();
        }
        return reply(settings);
      }
      if (path.endsWith("/workspace/candles")) {
        const span = { "5m": 300000, "15m": 900000, "1h": 3600000, "4h": 14400000, "1d": 86400000 }[settings.interval];
        const now = Date.now(), first = Math.floor(now / span) * span - 4 * span;
        return reply({ status: "READ_ONLY_OK", contract: "HUNTER_CLOSED_CANDLES_PREVIEW_V1",
          source: "BINANCE_PUBLIC_REST", market: "usdm_futures", symbol: settings.symbol, interval: settings.interval,
          serverTimeMs: now, execution_authorized: false, orders_sent: 0,
          candles: Array.from({ length: 4 }, (_, index) => ({ openTimeMs: first + index * span, closeTimeMs: first + (index + 1) * span - 1, open: "10", high: "12", low: "9", close: "11", volume: "3" })) });
      }
      if (path.startsWith("/api/v1/trading/paper")) {
        if (method !== "GET") assert.equal(request.headers()["x-nex-csrf"], "fixture-csrf");
        if (path.endsWith("/account")) {
          const body = request.postDataJSON();
          virtual = { ...virtual, configured: true, initial: body.initial_equity, cash: body.initial_equity,
            equity: body.initial_equity, cash_change: "0", unrealized_pnl: "0", running: false,
            daily_hit: false, utc_day: "2026-10-19", policy: body.policy, profile: { ...settings }, strategy_id: body.strategy_id };
        }
        if (path.endsWith("/orders")) {
          const body = request.postDataJSON(); orderRequests.push(body);
          if (!acknowledgements.has(body.request_id)) {
            const fill = { id: body.request_id, status: "FILLED_SIMULATED", action: body.action,
              side: body.side, quantity: body.quantity || virtual.position.quantity, symbol: settings.symbol,
              price: "100", fee: "0.04", net_pnl: body.action === "CLOSE" ? "-0.08" : null, reason: "FIXTURE", created_ms: Date.now() };
            acknowledgements.set(body.request_id, fill);
            virtual.orders.unshift(fill); virtual.total_orders++;
            virtual.position = body.action === "OPEN" ? { id: fill.id, symbol: settings.symbol, interval: settings.interval,
              side: body.side, quantity: body.quantity, entry: "100", stop: "99", target: "102", leverage: 20, margin: ".05" } : null;
          }
          if (dropFirstAck) { dropFirstAck = false; return reply({ reason_code: "ACK_LOST_FIXTURE" }, 503); }
          return reply(acknowledgements.get(body.request_id));
        }
        return reply(virtual);
      }
      if (path.startsWith("/api/v1/trading/testnet")) {
        if (method !== "GET") assert.equal(request.headers()["x-nex-csrf"], "fixture-csrf");
        if (path.endsWith("/automation")) {
          const body = request.postDataJSON(); autoRequests.push(body);
          assert.equal(body.confirmation, "BINANCE_DEMO_ONLY"); assert.equal(body.revision, demo.revision);
          if (body.enabled && demo.automation.state !== "RUNNING") demo.automation = { state: "RUNNING", expires_at: Math.floor(Date.now()/1000)+3600, last_checked_ms: Date.now(), last_result: "NO_SIGNAL", reason: null };
          if (!body.enabled) demo.automation.state = "STOPPED";
          if (body.enabled && autoDropAck) { autoDropAck = false; return reply({ reason_code: "AUTOMATION_ACK_LOST_FIXTURE" }, 503); }
        }
        if (path.endsWith("/configuration")) {
          const body = request.postDataJSON();
          assert.deepEqual(Object.keys(body).sort(), ["confirmation", "daily_loss_pct", "margin_mode", "max_exposure_pct", "stop_pct", "symbol", "trade_risk_pct"].sort());
          assert.equal(body.confirmation, "BINANCE_DEMO_ONLY");
          const { confirmation, ...policy } = body;
          demo = { ...demo, configured: true, revision: "00000000-0000-0000-0000-000000000015",
            config: { ...policy, mode: "testnet", mainnet_enabled: false, strategy: "ema20_50_long_only" } };
        }
        if (path.endsWith("/actions")) {
          const body = request.postDataJSON(); demoRequests.push(body);
          assert.equal(body.confirmation, "BINANCE_DEMO_ONLY"); assert.equal(body.revision, demo.revision);
          if (!demoReceipts.has(body.request_id)) {
            const result = { mode: "testnet", status: "FIXTURE_OK", mainnet_order_execution: false };
            if (body.action === "entry") { demoFills++; demo.pending_order = { id: "HK1" + "a".repeat(24), signal: "ENTER_LONG" }; }
            if (body.action === "reconcile" && demo.pending_order?.signal === "ENTER_LONG") {
              demo.active_position = { id: demo.pending_order.id, quantity: "0.1" }; demo.pending_order = null;
            }
            if (body.action === "exit") {
              assert.equal(body.position_id, demo.active_position.id); demoFills++;
              demo.pending_order = { id: "HK1" + "b".repeat(24), signal: "EXIT_LONG" };
            }
            if (body.action === "cleanup") { demo.active_position = null; demo.pending_order = null; }
            const receipt = { request_id: body.request_id, action: body.action, status: "CONFIRMED", reason: null, result, created_ms: Date.now() };
            demoReceipts.set(body.request_id, receipt); demo.receipts.push(receipt);
          }
          if (body.action === "entry" && demoDropAck) { demoDropAck = false; return reply({ reason_code: "DEMO_ACK_LOST_FIXTURE" }, 503); }
          return reply(demoReceipts.get(body.request_id));
        }
        return reply(demo);
      }
      if (path.endsWith("/control/testnet/connect") && method === "POST") {
        assert.deepEqual(request.postDataJSON(), { api_key: "SYNTHETIC_DEMO_KEY", api_secret: "SYNTHETIC_DEMO_SECRET" });
        demo.credentials_saved = true;
        return reply({ venue: "BINANCE_USDM_TESTNET", authenticated: true, encrypted_server_storage: true, expires_in_seconds: 86400, execution_enabled: false });
      }
      if (path.startsWith("/api/v1/trading/control")) {
        if (path.endsWith("/start")) monitor = true;
        if (path.endsWith("/stop")) monitor = false;
        return reply({ mode: "BINANCE_USDM_PUBLIC_MONITOR", state: monitor ? "MONITORING" : "STOPPED",
          symbol: settings.symbol, interval: settings.interval, last_closed_price: monitor ? "11" : null,
          last_candle_closed_ms: Date.now() - 300000, last_checked_ms: Date.now(), expires_in_seconds: 899,
          testnet_key_saved: demo.credentials_saved, live_readonly_key_saved: false, execution_enabled: false, order_submission_available: false });
      }
      if (path.startsWith("/api/v1/trading/strategies")) {
        if (method === "POST") {
          const parts = path.split("/"), strategy = parts.at(-2);
          if (path.endsWith("/start")) { seenStart = request.postDataJSON(); scans.add(strategy); } else scans.delete(strategy);
        }
        const strategies = definitions.map((id, index) => ({ id, name: ["Trend Ladder", "Range Fade", "Breakout Scout", "Mean Return"][index],
          rule: "fixture research rule", symbol: settings.symbol, interval: settings.interval, status: scans.has(id) ? "SCANNING" : "STOPPED",
          signal: scans.has(id) ? "NEUTRAL" : null, last_closed_price: null, last_candle_closed_ms: null, last_checked_ms: null, expires_in_seconds: 899,
          market_source: "BINANCE_USDM_PUBLIC_CLOSED_CANDLES", ndsp_verified: false, execution_enabled: false }));
        return reply(method === "POST" ? strategies.find(row => row.id === path.split("/").at(-2)) : { strategies, order_submission_available: false });
      }
      if (path.endsWith("/execution/review")) return reply({
        stage: "M3_RESEARCH_DECISION_GATE", execution_allowed: false, mainnet_orders_enabled: false, ndsp_execution_verified: false,
        risk: { state: "NOT_CONFIGURED", daily_loss_pct: null, new_entries_blocked: true, opening_equity: null, current_equity: null },
        active_scanners: scans.size, stalled_scanners: 0, candidates: [], blockers: ["MAINNET_ORDER_ENGINE_NOT_CONNECTED"],
      });
      return reply({ reason_code: "UNEXPECTED_FIXTURE_ROUTE" }, 503);
    });
    await page.goto(origin + "/trading/");
    const bar = page.getByRole("region", { name: "Shared bot settings" });
    await bar.getByRole("button", { name: "Confirm / Apply", exact: true }).waitFor();
    await page.waitForFunction(() => !document.querySelector('section[aria-label="Shared bot settings"] fieldset')?.disabled);
    await bar.getByLabel("Asset", { exact: true }).selectOption("ETHUSDT");
    await bar.getByLabel("Timeframe", { exact: true }).selectOption("1h");
    await bar.getByLabel("Decision style", { exact: true }).selectOption("INVESTMENT");
    await bar.getByLabel("Execution method", { exact: true }).selectOption("AUTOMATIC");
    await bar.getByLabel("Requested leverage", { exact: true }).fill("20");
    await bar.getByLabel("Margin", { exact: true }).selectOption("CROSS");
    assert.equal(puts, 0);
    await bar.getByRole("button", { name: "Confirm / Apply", exact: true }).click();
    await bar.getByText("ETHUSDT · 1h · 20x", { exact: true }).waitFor();
    assert.equal(puts, 1);
    assert.equal(settings.execution_authorized, false);
    await Promise.all([
      page.waitForResponse(response => response.url().endsWith("/control/start")),
      page.getByRole("button", { name: "Start market monitor", exact: true }).click(),
    ]);
    assert.equal(monitor, true);
    await Promise.all([
      page.waitForResponse(response => response.url().endsWith("/trend-ladder/start")),
      page.getByRole("button", { name: "Start scanner", exact: true }).first().click(),
    ]);
    assert.deepEqual(seenStart, { symbol: "ETHUSDT", interval: "1h", workspace_bound: true });
    await page.reload();
    await bar.getByText("ETHUSDT · 1h · 20x", { exact: true }).waitFor();
    assert.equal(puts, 1, "Reload must retrieve settings, never auto-submit them");
    await bar.getByLabel("Execution method", { exact: true }).selectOption("MANUAL");
    await bar.getByRole("button", { name: "Confirm / Apply", exact: true }).click();
    const paper = page.getByRole("region", { name: "Paper broker", exact: true });
    await paper.getByLabel("Virtual initial capital", { exact: true }).fill("1000");
    await paper.getByLabel("Simulation rule", { exact: true }).selectOption("trend-ladder");
    for (const [label, value] of [["Daily loss limit %", "2"], ["Trade risk %", "1"], ["Maximum margin %", "10"],
      ["Stop distance from price %", "1"], ["Target distance from price %", "2"], ["Simulated fee each side %", "0.04"], ["Simulated slippage each side %", "0.02"]]) {
      await paper.getByLabel(label, { exact: true }).fill(value);
    }
    await paper.getByRole("button", { name: "Save simulation settings", exact: true }).click();
    await paper.getByText("No virtual position is open.", { exact: true }).waitFor();
    await paper.getByLabel("Virtual order quantity", { exact: true }).fill("0.01");
    await paper.getByRole("button", { name: "Virtual buy", exact: true }).click();
    await paper.getByText("ACK_LOST_FIXTURE", { exact: true }).waitFor();
    assert.equal(virtual.total_orders, 1);
    await paper.getByRole("button", { name: "Retry confirmation", exact: true }).click();
    await paper.getByRole("cell", { name: "99", exact: true }).waitFor();
    assert.equal(orderRequests.length, 2); assert.deepEqual(orderRequests[0], orderRequests[1]);
    assert.equal(virtual.total_orders, 1, "Lost acknowledgement retries never duplicate a fill");
    await page.reload();
    await paper.getByRole("cell", { name: "99", exact: true }).waitFor();
    await paper.getByRole("button", { name: "Close virtual position", exact: true }).click();
    await paper.getByText("No virtual position is open.", { exact: true }).waitFor();
    assert.equal(virtual.total_orders, 2);
    const demoPanel = page.getByRole("region", { name: "Binance Testnet execution", exact: true });
    assert.equal(await demoPanel.getByRole("button", { name: "Save Testnet setup", exact: true }).isDisabled(), true);
    await page.getByLabel("Testnet API Key", { exact: true }).fill("SYNTHETIC_DEMO_KEY");
    await page.getByLabel("Testnet API Secret", { exact: true }).fill("SYNTHETIC_DEMO_SECRET");
    await page.getByRole("button", { name: "Verify and save testnet credentials", exact: true }).click();
    await page.getByText("Verified and encrypted on server", { exact: false }).waitFor();
    assert.equal(await page.getByLabel("Testnet API Key", { exact: true }).inputValue(), "");
    assert.equal(await page.getByLabel("Testnet API Secret", { exact: true }).inputValue(), "");
    await demoPanel.getByLabel("I confirm Binance Demo operations only", { exact: true }).check();
    await demoPanel.getByRole("button", { name: "Save Testnet setup", exact: true }).click();
    await demoPanel.getByRole("button", { name: "Preflight account", exact: true }).waitFor();
    await demoPanel.getByRole("button", { name: "Execute Testnet entry signal", exact: true }).click();
    await demoPanel.getByText("DEMO_ACK_LOST_FIXTURE", { exact: true }).waitFor();
    assert.equal(demoFills, 1);
    await demoPanel.getByRole("button", { name: "Recover same request receipt", exact: true }).click();
    await demoPanel.getByRole("cell", { name: "CONFIRMED", exact: true }).first().waitFor();
    assert.equal(demoFills, 1); assert.deepEqual(demoRequests[0], demoRequests[1]);
    await page.reload();
    await demoPanel.getByLabel("I confirm Binance Demo operations only", { exact: true }).check();
    await demoPanel.getByRole("button", { name: "Reconcile journal", exact: true }).click();
    await page.waitForFunction(() => !Array.from(document.querySelectorAll('section[aria-label="Binance Testnet execution"] button')).find(e => e.textContent === "Close Testnet position")?.disabled);
    await demoPanel.getByRole("button", { name: "Close Testnet position", exact: true }).click();
    await page.waitForFunction(() => !Array.from(document.querySelectorAll('section[aria-label="Binance Testnet execution"] button')).find(e => e.textContent === "Clean stop after exit")?.disabled);
    await demoPanel.getByRole("button", { name: "Clean stop after exit", exact: true }).click();
    await demoPanel.getByRole("cell", { name: "Clean stop after exit", exact: true }).waitFor();
    assert.equal(demoFills, 2);
    const auto = page.getByLabel("Demo automation", { exact: true });
    await auto.getByRole("button", { name: "Run Demo automatically for one hour", exact: true }).click();
    await demoPanel.getByText("AUTOMATION_ACK_LOST_FIXTURE", { exact: true }).waitFor();
    const leaseEnd = demo.automation.expires_at;
    await auto.getByRole("button", { name: "Run Demo automatically for one hour", exact: true }).click();
    await auto.getByText("State: Automatic", { exact: true }).waitFor();
    assert.equal(autoRequests.length, 2); assert.equal(demo.automation.expires_at, leaseEnd);
    assert.equal(await demoPanel.getByRole("button", { name: "Execute Testnet entry signal", exact: true }).isDisabled(), true);
    assert.equal(await demoPanel.getByRole("button", { name: "Save Testnet setup", exact: true }).isDisabled(), true);
    await page.reload();
    await auto.getByText("State: Automatic", { exact: true }).waitFor();
    assert.equal(await demoPanel.getByLabel("I confirm Binance Demo operations only", { exact: true }).isChecked(), false);
    await auto.getByRole("button", { name: "Stop Demo and close its position", exact: true }).click();
    await auto.getByText("State: Stopped", { exact: true }).waitFor();
    assert.equal(autoRequests.at(-1).enabled, false);
    await page.getByRole("button", { name: "AR · العربية", exact: true }).click();
    const arabic = page.getByRole("region", { name: "إعدادات البوت الموحدة" });
    await arabic.getByRole("button", { name: "تأكيد / تطبيق", exact: true }).waitFor();
    await page.waitForFunction(() => document.documentElement.dir === "rtl");
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), "Horizontal overflow at width " + width);
    await page.getByRole("button", { name: "EN · English", exact: true }).click();
    await bar.getByText("ETHUSDT · 1h · 20x", { exact: true }).waitFor();
    failedSave = true;
    await bar.getByRole("button", { name: "Confirm / Apply", exact: true }).click();
    await bar.getByText("Save not confirmed. Reload to verify server settings.", { exact: true }).waitFor();
    assert.equal(await bar.locator("fieldset").evaluate(element => element.disabled), true);
    assert.equal(await bar.getByLabel("Asset", { exact: true }).isDisabled(), true);
    assert.equal(await page.getByRole("region", { name: "Verified closed Binance candles" }).getByText("Last closed candle", { exact: false }).count(), 0);
    await page.getByLabel("Testnet API Key", { exact: true }).fill("SYNTHETIC_UNSENT_KEY");
    await page.getByLabel("Testnet API Secret", { exact: true }).fill("SYNTHETIC_UNSENT_SECRET");
    await page.getByRole("button", { name: "Sign out", exact: true }).click();
    await page.waitForFunction(() => Array.from(document.querySelectorAll('input[type="password"]')).every(input => input.value === ""));
    assert.equal(await demoPanel.getByRole("button", { name: "Save Testnet setup", exact: true }).isDisabled(), true);
    assert.equal(await demoPanel.getByRole("cell").count(), 0);
    assert.deepEqual(errors, []);
    console.log("WORKSPACE_UI_FIXTURE_PASS", width, "draft/confirm/persist/start/paper-setup/open/retry/reload/close/demo-keys/entry/retry/reconcile/exit/cleanup/auto-start-ack-retry/reload/stop/RTL/failure/logout-secret-clear");
    await context.close();
  }
} finally {
  if (browser) await browser.close();
  await new Promise(done => server.close(done));
}
