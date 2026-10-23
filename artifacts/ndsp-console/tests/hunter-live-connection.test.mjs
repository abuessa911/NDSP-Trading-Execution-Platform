import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const ui = readFileSync(new URL("../src/components/HunterControlPanel.tsx", import.meta.url), "utf8");
const route = readFileSync(new URL("../../../apps/api/nex_api/routes/trading_control.py", import.meta.url), "utf8");
const connector = readFileSync(new URL("../../../apps/api/nex_api/binance_live_readonly_connector.py", import.meta.url), "utf8");

test("mainnet form uses same-origin authenticated server and never browser storage", () => {
  assert.match(ui, /\/live\/connect/);
  assert.match(ui, /getCsrfToken/);
  assert.match(ui, /type="password"/);
  assert.doesNotMatch(ui, /localStorage\.|sessionStorage\./);
  assert.match(ui, /read.only/i);
});

test("production connector allows only read-only signed GETs", () => {
  assert.match(connector, /https:\/\/fapi\.binance\.com/);
  assert.match(connector, /fapi\/v3\/account/);
  assert.match(connector, /account\/apiRestrictions/);
  assert.match(connector, /enableWithdrawals/);
  assert.match(connector, /ipRestrict/);
  assert.doesNotMatch(connector, /client\.post\(|client\.delete\(|\/fapi\/v1\/order/);
  assert.match(route, /live_cipher/);
  assert.match(route, /execution_enabled: Literal\[False\]/);
});
