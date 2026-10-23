import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "../../..");
const source = file => readFileSync(resolve(root, file), "utf8");

test("real-money configuration fields are server-backed and independently non-executing", () => {
  const ui = source("artifacts/ndsp-console/src/components/HunterTradingPreferencesPanel.tsx");
  assert.match(ui, /\/api\/v1\/trading\/bot\/preferences/);
  for (const field of ["capital_limit_usdt", "trade_risk_pct", "daily_loss_pct"])
    assert.match(ui, new RegExp(field));
  assert.match(ui, /"X-NEX-CSRF"/);
  assert.match(ui, /credentials: "same-origin"/);
  assert.match(ui, /live_orders_enabled === false/);
  assert.match(ui, /execution_ready === false/);
  assert.match(ui, /إعدادات رأس المال والمخاطرة/);
  assert.match(ui, /Save trading preferences/);
  assert.doesNotMatch(ui, /localStorage|submit_order|create_order|place_order/);
});

test("trading and settings surfaces share the same configuration source", () => {
  const settings = source("artifacts/ndsp-console/src/components/SettingsPanel.tsx");
  const trading = source("artifacts/ndsp-console/src/ndsp/views-trading.tsx");
  assert.match(settings, /<HunterTradingPreferencesPanel/);
  assert.match(trading, /<HunterTradingPreferencesPanel/);
  const backend = source("apps/api/nex_api/routes/bot_power.py");
  assert.match(backend, /SAVE_TRADING_PREFERENCES/);
  assert.match(backend, /get_operator/);
  assert.match(backend, /verify_mutation/);
  assert.match(backend, /"live_orders_enabled": False/);
  assert.match(backend, /"execution_ready": False/);
});
