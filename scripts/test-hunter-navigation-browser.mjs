/**
 * Real exported documents, actual link clicks/taps and history.
 * Only the disposable loopback API is mocked. RSC files deliberately redirect
 * to sign-in, reproducing the gateway condition that broke client navigation.
 * No real session, account, exchange request or protected data is used.
 */
import assert from "node:assert/strict";
import http from "node:http";
import { readFile } from "node:fs/promises";
import { resolve, sep, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const root = process.env.HUNTER_NAV_EXPORT || resolve(fileURLToPath(new URL("..", import.meta.url)), "artifacts/ndsp-console/out");
let rscRequests = 0;
const server = http.createServer(async (request, response) => {
  try {
    let pathname = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
    if (pathname.endsWith(".txt")) {
      rscRequests++;
      response.writeHead(302, { Location: "/account-access/", "Cache-Control": "no-store" });
      response.end(); return;
    }
    if (pathname.endsWith("/")) pathname += "index.html";
    const path = resolve(root, "." + pathname);
    if (!path.startsWith(root + sep)) throw Error("PATH_REJECTED");
    const body = await readFile(path);
    const mime = { ".html": "text/html", ".js": "application/javascript", ".css": "text/css", ".svg": "image/svg+xml" };
    response.writeHead(200, { "Content-Type": mime[extname(path)] || "application/octet-stream", "Cache-Control": "no-store" });
    response.end(body);
  } catch { response.writeHead(404); response.end("Not found"); }
});
await new Promise(done => server.listen(0, "127.0.0.1", done));
const origin = "http://127.0.0.1:" + server.address().port;
let browser;
try {
  browser = await chromium.launch({ headless: true });
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 844 }, isMobile: width < 740, hasTouch: width < 740 });
    const page = await context.newPage(), errors = [], documents = [];
    page.setDefaultTimeout(12000);
    page.on("pageerror", error => errors.push(error.message));
    page.on("request", request => { if (request.resourceType() === "document") documents.push(new URL(request.url()).pathname); });
    const identity = { user_id: "00000000-0000-0000-0000-000000000004", tenant_id: "00000000-0000-0000-0000-000000000003", role: "OPERATOR" };
    await page.route("**/*", async route => {
      const url = new URL(route.request().url());
      if (url.origin !== origin) return route.abort();
      if (!url.pathname.startsWith("/api/")) return route.continue();
      const reply = (body, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
      if (url.pathname === "/api/health/auth") return reply({ browser_login_enabled: true, administrator_mfa_configured: true });
      if (url.pathname.endsWith("/auth/session")) return reply({ ...identity, authenticated: true, csrf_token: "fixture-csrf", administrator_mfa_verified: false });
      if (url.pathname === "/api/v1/me") return reply({ ...identity, status: "active", email: "fixture@example.test", entitlements: { live_trading: false } });
      if (url.pathname === "/api/health/live") return reply({ status: "alive" });
      if (url.pathname === "/api/health/ready") return reply({ status: "ready", dependencies: {} });
      return reply({ reason_code: "NAVIGATION_FIXTURE_READ_UNAVAILABLE" }, 503);
    });
    await page.goto(origin + "/trading/");
    await page.locator(".console-top .seg button").first().waitFor();
    const nav = page.locator("#console-navigation");
    async function openMenu() {
      if (width < 740) {
        const toggle = page.locator('[aria-controls="console-navigation"]');
        if (await toggle.getAttribute("aria-expanded") !== "true") await toggle.tap();
        await nav.waitFor({ state: "visible" });
        await page.waitForFunction(() => {
          const menu = document.querySelector("#console-navigation").getBoundingClientRect();
          const header = document.querySelector(".console-top").getBoundingClientRect();
          return menu.top >= header.bottom - 1;
        });
      }
    }
    async function navigate(path) {
      await openMenu();
      if (path.startsWith("/admin")) {
        const details = nav.locator("details");
        if (await details.getAttribute("open") === null) await details.locator("summary").click();
      }
      const link = nav.locator('a[href="' + path + '"]').first();
      await link.scrollIntoViewIfNeeded();
      const before = documents.length;
      try {
        await Promise.all([
          page.waitForURL(origin + path),
          width < 740 ? link.tap() : link.click(),
        ]);
      } catch (error) {
        console.log("FAILED_NAVIGATION", width, path, "actual", page.url(), "documents", documents.slice(-4));
        console.log("FAILED_GEOMETRY", await link.evaluate(el => {
          const r = el.getBoundingClientRect(); const hit = document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
          return { box:r.toJSON(),hit:hit?.outerHTML.slice(0,300),header:document.querySelector(".console-top")?.getBoundingClientRect().toJSON(),open:document.querySelector('[aria-controls="console-navigation"]')?.getAttribute("aria-expanded") };
        }));
        throw error;
      }
      await page.locator('main#console-content').waitFor();
      await page.waitForFunction(path => {
        const current = document.querySelector('#console-navigation a.nav-link.active');
        return current?.getAttribute("href") === path;
      }, path);
      assert(documents.length > before, "Navigation must load the exported document: " + path);
      if (width < 740) assert.equal(await page.locator('[aria-controls="console-navigation"]').getAttribute("aria-expanded"), "false");
      assert.equal(new URL(page.url()).pathname, path);
    }
    const paths = ["/markets/", "/strategies/", "/positions/", "/orders/", "/trade-history/", "/performance/",
      "/risk-center/", "/binance-connection/", "/notifications/", "/settings/", "/security/", "/subscription/",
      "/user-guide/", "/health/", "/activity/", "/audit/", "/registration/", "/account-access/",
      "/ndsp-decisions/", "/execution-trace/", "/replay-lab/", "/", "/admin/", "/admin/owner-guide/",
      "/admin/operations-center/", "/admin/users-tenants/", "/admin/subscriptions/", "/admin/trading-safety/",
      "/admin/exchange-health/", "/admin/ndsp-health/", "/admin/audit/", "/admin/notifications/",
      "/admin/workers-queues/", "/admin/incidents/", "/trading/"];
    for (const path of paths) await navigate(path);
    await page.getByRole("button", { name: "AR · العربية", exact: true }).click();
    await page.waitForFunction(() => document.documentElement.dir === "rtl");
    for (const path of ["/markets/", "/settings/", "/user-guide/", "/admin/owner-guide/", "/trading/"]) {
      await navigate(path);
      await page.waitForFunction(() => document.documentElement.dir === "rtl");
    }
    await page.goBack(); await page.waitForURL(origin + "/admin/owner-guide/");
    await page.goForward(); await page.waitForURL(origin + "/trading/");
    if (width < 740) {
      await openMenu();
      await page.locator(".nav-scrim").tap({ position: { x: 5, y: 200 } });
      assert.equal(await page.locator('[aria-controls="console-navigation"]').getAttribute("aria-expanded"), "false");
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    }
    assert.deepEqual(errors, []);
    console.log("NAVIGATION_FIXTURE_PASS", width, paths.length + 5, "links; mobile tap, scroll, RTL, history, protected API unchanged");
    await context.close();
  }
  assert.equal(rscRequests, 0, "Document navigation must not request gated RSC text");
} finally {
  if (browser) await browser.close();
  await new Promise(done => server.close(done));
}
