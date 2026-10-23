import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const source = readFileSync(new URL("../src/components/HunterControlPanel.tsx", import.meta.url), "utf8");
const settings = readFileSync(new URL("../src/components/SettingsPanel.tsx", import.meta.url), "utf8");
const trading = readFileSync(new URL("../src/ndsp/views-trading.tsx", import.meta.url), "utf8");
const backend = readFileSync(new URL("../../../apps/api/nex_api/routes/trading_control.py", import.meta.url), "utf8");

test("live market control is surfaced in settings and trading, not a fake local toggle", () => {
  assert.match(settings, /<HunterControlPanel\s*\/>/);
  assert.match(trading, /<HunterControlPanel\s*\/>/);
  assert.match(source, /fetch\(`\$\{endpoint\}\$\{path\}`/);
  assert.match(source, /Start market monitor/);
  assert.match(source, /Stop monitor/);
  assert.match(source, /getCsrfToken/);
  assert.doesNotMatch(source, /localStorage\.(setItem|getItem)|sessionStorage\.(setItem|getItem)|new WebSocket\(/);
});

test("signed connector uses only testnet host and no order methods", () => {
  assert.match(backend, /testnet_connect/);
  assert.match(backend, /verify_mutation/);
  assert.match(backend, /encryptor\.encrypt/);
  assert.match(backend, /fetch_closed_candles/);
  assert.doesNotMatch(backend, /["\x27]\/fapi\/v1\/order|\bplace_order\s*\(|\bpost_order\s*\(/);
  assert.match(backend, /order_submission_available: Literal\[False\]/);
});
