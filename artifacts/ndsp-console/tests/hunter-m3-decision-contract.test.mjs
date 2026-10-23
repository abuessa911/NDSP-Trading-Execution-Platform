import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = import.meta.dirname ? join(import.meta.dirname, "..") : process.cwd();
const panel = readFileSync(join(root, "src/components/HunterExecutionReviewPanel.tsx"), "utf8");
const trade = readFileSync(join(root, "src/ndsp/views-trading.tsx"), "utf8");
test("decision review connects authenticated server API and displays fail-closed claims", () => {
  assert.match(panel, /\/api\/v1\/trading\/execution\/review/);
  assert.match(panel, /credentials: "same-origin"/);
  assert.match(panel, /value\.execution_allowed !== false/);
  assert.match(panel, /value\.mainnet_orders_enabled !== false/);
  assert.match(panel, /value\.ndsp_execution_verified !== false/);
  assert.match(panel, /daily_loss_pct/);
});
test("trading screen includes the real review, while order ticket stays disabled", () => {
  assert.match(trade, /<HunterExecutionReviewPanel\s*\/>/);
  assert.match(trade, /Live execution is disabled/);
});
