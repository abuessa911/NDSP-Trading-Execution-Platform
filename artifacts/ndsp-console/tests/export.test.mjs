import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile, access } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import net from "node:net";
import { setTimeout as delay } from "node:timers/promises";

const root = fileURLToPath(new URL("../", import.meta.url));
const read = path => readFile(root + path, "utf8");
const userRoutes = [
  "trading", "strategies", "positions", "orders", "trade-history", "performance",
  "risk-center", "ndsp-decisions", "execution-trace", "replay-lab",
  "binance-connection", "notifications", "subscription", "settings", "health", "audit", "markets", "security", "activity",
];
const adminRoutes = [
  "operations-center", "users-tenants", "subscriptions", "trading-safety", "exchange-health",
  "ndsp-health", "audit", "notifications", "workers-queues", "incidents",
];

test("every M1 and specified V1 route exports its own HTML document", async () => {
  for (const route of ["", ...userRoutes, "admin", ...adminRoutes.map(r => `admin/${r}`)]) {
    const html = await read(`out/${route ? route + "/" : ""}index.html`);
    assert.match(html, /<!DOCTYPE html>/i, route);
    assert.match(html, /M1 NOT ACCEPTED|M1 not accepted/i, route);
    assert.doesNotMatch(html, /csrf_token|__Secure-nex_session|user@nex\.example/i, route);
  }
  await access(root + "out/404.html");
});

test("every administrator surface exports a closed session gate without privileged data", async () => {
  for (const route of ["audit", "admin", ...adminRoutes.map(r => `admin/${r}`)]) {
    const html = await read(`out/${route}/index.html`);
    if (route === "admin") {
      assert.match(html, /Read-only tenant operations/, route);
      assert.match(html, /Navigation does not grant access/, route);
    } else if (route.startsWith("admin/")) {
      assert.match(html, /Administrator access required/, route);
      assert.match(html, /server-verified administrator session/, route);
    } else {
      assert.match(html, /NOT AVAILABLE IN M1|Administrator access required/, route);
      assert.match(html, /not enabled|server-verified administrator session/, route);
    }
    assert.doesNotMatch(html, /<table|actor_id|metadata_json|source_ip_hash/, route);
  }
  const guard = await read("src/components/AdminBlocked.tsx");
  assert.doesNotMatch(guard, /getMe|fetch\(|useAuth|listTenantAuditEvents|getAdmin/);
});

test("future workflow pages conspicuously label synthetic frontend-only previews", async () => {
  for (const route of userRoutes.filter(r => !["subscription", "settings", "health", "audit", "security"].includes(r))) {
    const html = await read(`out/${route}/index.html`);
    assert.match(html, /DEMO DATA/, route);
    assert.match(html, /NOT CONNECTED/, route);
    assert.match(html, /READ-ONLY UI PREVIEW/, route);
    assert.match(html, /BLOCKED/, route);
  }
  const services = await read("src/ndsp/services.ts");
  assert.doesNotMatch(services, /fetch\(|WebSocket|Authorization|Bearer|api[_-]?key/i);
});

test("session contracts and provider harness are preserved", async () => {
  const auth = await read("src/components/AuthProvider.tsx");
  assert.match(auth, /credentials: "same-origin"/);
  assert.match(auth, /"X-NEX-CSRF": csrf/);
  assert.match(auth, /getBrowserSession/);
  assert.match(auth, /getMe/);
  assert.doesNotMatch(auth, /localStorage|sessionStorage|Authorization:|Bearer /);
  assert.match(auth, /epoch\.current === refreshEpoch/);
  const fixture = await readFile(root + "../../scripts/m1_auth_environment.py", "utf8");
  assert.match(fixture, /artifacts\/ndsp-console\/out/);
});

test("exported production documents and scripts are delivered with real statuses and MIME types", async () => {
  // Self-owned ephemeral test process only; never replaces an artifact workflow.
  const allocator = net.createServer();
  await new Promise(resolve => allocator.listen(0, "127.0.0.1", resolve));
  const port = allocator.address().port;
  await new Promise(resolve => allocator.close(resolve));
  const server = spawn(process.execPath, [root + "scripts/serve-static.mjs"], {
    env: { PATH: process.env.PATH, PORT: String(port) }, stdio: "ignore",
  });
  const base = `http://127.0.0.1:${port}`;
  try {
    let response;
    for (let i = 0; i < 30; i++) {
      try { response = await fetch(base + "/"); break; } catch { await delay(50); }
    }
    assert.ok(response, "static test server started");
    assert.equal(response.status, 200);
    assert.match(response.headers.get("content-type"), /text\/html/);
    assert.equal(response.headers.get("referrer-policy"), "no-referrer");
    assert.equal(response.headers.get("cache-control"), "no-store");
    const html = await response.text();
    const script = html.match(/<script[^>]+src="([^"]+\.js[^"]*)"/)?.[1];
    assert.ok(script, "Next client script exists");
    const asset = await fetch(base + script);
    assert.equal(asset.status, 200);
    assert.match(asset.headers.get("content-type"), /javascript/);
    const settings = await fetch(base + "/settings/");
    assert.equal(settings.status, 200);
    assert.match(await settings.text(), /Display preferences/);
    const admin = await fetch(base + "/admin/audit/");
    assert.equal(admin.status, 200);
    assert.match(await admin.text(), /Administrator access required/);
    const missing = await fetch(base + "/definitely-unknown-route/");
    assert.equal(missing.status, 404);
    assert.match(await missing.text(), /Page not found/);
    const post = await fetch(base + "/settings/", { method: "POST" });
    assert.equal(post.status, 405);
  } finally {
    server.kill("SIGTERM");
    await new Promise(resolve => server.once("exit", resolve));
  }
});
