import assert from "node:assert/strict";
import { test } from "node:test";
import { readFileSync } from "node:fs";
import { readClosedCandles, MarketUnavailable } from "../scripts/hunter-readonly-market.mjs";

const ms = 1770000030000;
const span = 300_000;
function rows({ stale = false, gap = false, malformed = false, current = false } = {}) {
  const newest = current ? Math.floor(ms / span) * span : Math.floor((ms - span) / span) * span;
  const start = newest - 7 * span - (stale ? 4 * span : 0);
  return Array.from({ length: 8 }, (_, i) => {
    const opened = start + i * span + (gap && i >= 3 ? span : 0);
    return [opened, "100.0", "110.0", malformed && i === 4 ? "120.0" : "90.0",
      "101.0", "15.0", opened + span - 1];
  });
}
function provider(items) {
  const called = [];
  const mock = async (url, opts) => {
    called.push({ url, ...opts });
    const path = new URL(url).pathname;
    if (path.endsWith("/time")) return new Response(JSON.stringify({ serverTime: ms }), { status: 200 });
    if (path.endsWith("/klines")) return new Response(JSON.stringify(items), { status: 200 });
    throw new Error("unknown path");
  };
  return { called, mock };
}
const selected = { market: "spot", symbol: "BTCUSDT", interval: "5m" };

test("accepts contiguous provider-closed candles, never submits an order", async () => {
  const { called, mock } = provider(rows());
  const r = await readClosedCandles(selected, mock);
  assert.equal(r.status, "READ_ONLY_OK");
  assert.equal(r.source, "BINANCE_PUBLIC_REST");
  assert.equal(r.candles.length, 5);
  assert.equal(r.orders_sent, 0);
  assert.equal(r.execution_authorized, false);
  assert.equal(called.length, 2);
  for (const req of called) {
    assert.equal(req.method, "GET");
    assert.equal(new URL(req.url).hostname, "api.binance.com");
    assert.ok(!req.url.includes("/order"));
    assert.ok(!JSON.stringify(req).includes("API-KEY"));
  }
});

test("never returns a current unclosed bar", async () => {
  const { mock } = provider(rows({ current: true }));
  const r = await readClosedCandles(selected, mock);
  assert.ok(r.candles.at(-1).closeTimeMs < ms);
});

test("fails closed on gaps, invalid OHLC, or stale data", async () => {
  for (const spec of [{ gap: true }, { malformed: true }, { stale: true }]) {
    const { mock } = provider(rows(spec));
    await assert.rejects(readClosedCandles(selected, mock), MarketUnavailable);
  }
});

test("invalid symbols and requests cannot generate any HTTP call", async () => {
  for (const props of [
    { symbol: "BTCUSDT&apikey=foo" },
    { market: "live_trade" },
    { interval: "1m" },
    { symbol: "DOGEUSDT" },
  ]) {
    const { called, mock } = provider(rows());
    await assert.rejects(readClosedCandles({ ...selected, ...props }, mock), MarketUnavailable);
    assert.equal(called.length, 0);
  }
});

test("USD-M futures market uses public data and no user account", async () => {
  const { called, mock } = provider(rows());
  const output = await readClosedCandles({ ...selected, market: "usdm_futures" }, mock);
  assert.equal(output.market, "usdm_futures");
  assert.equal(output.orders_sent, 0);
  assert.ok(called.every(c => new URL(c.url).hostname === "fapi.binance.com"));
  assert.ok(called.every(c => !c.url.includes("order")));
});

test("UI keeps live verified data separate from demo data and never enables execution", () => {
  const source = readFileSync(new URL("../src/ndsp/LiveMarketPreview.tsx", import.meta.url), "utf8");
  assert.match(source, /READ_ONLY_OK/);
  assert.match(source, /execution_authorized !== false/);
  assert.match(source, /orders_sent !== 0/);
  assert.match(source, /لا أوامر تداول/);
  // Protected Basic-auth pages must forward the cached same-origin browser
  // credentials to the read-only endpoint. Cross-origin requests stay excluded.
  assert.match(source, /credentials: "same-origin"/);
  assert.doesNotMatch(source, /credentials: "omit"/);
  assert.match(source, /fetch\("/preview/market/closed-candles\?/);
  const server = readFileSync(new URL("../scripts/serve-static.mjs", import.meta.url), "utf8");
  assert.match(server, /HUNTER_READONLY_MARKET_PREVIEW === "true"/);
  assert.match(server, /127\.0\.0\.1/);
  assert.doesNotMatch(server, /order\/test|api\/v3\/order|fapi\/v1\/order/);
});
