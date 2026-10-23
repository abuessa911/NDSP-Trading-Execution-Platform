import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "../../..");
const source = p => readFileSync(resolve(root, p), "utf8");

test("investment/speculation is separate from manual/automatic and persisted only through authenticated Hunter API", () => {
  const selector = source("artifacts/ndsp-console/src/components/TradingWorkspace.tsx");
  const ticket = source("artifacts/ndsp-console/src/ndsp/views-trading.tsx");
  assert.match(selector, /INVESTMENT/);
  assert.match(selector, /SPECULATIVE/);
  assert.match(selector, /api\/v1\/trading\/profile/);
  assert.match(selector, /credentials: "same-origin"/);
  assert.match(selector, /"X-NEX-CSRF"/);
  assert.match(selector, /execution_authorized === false/);
  assert.match(selector, /ndsp_contract_bound === false/);
  const shell = source("artifacts/ndsp-console/src/components/ConsoleShell.tsx");
  assert.match(shell, /<TradingWorkspaceBar \/>/);
  assert.doesNotMatch(ticket, /<DecisionStyleSelector \/>/);
  assert.match(selector, /Execution method/);
  assert.match(selector, /AUTOMATIC/);
  assert.match(selector, /MANUAL/);
});

test("Hunter decision profile must remain a server-scoped, non-executing preference, never an NDSP integration", () => {
  const backend = source("apps/api/nex_api/routes/trading_profile.py");
  const main = source("apps/api/nex_api/main.py");
  const contract = source("docs/M2B_NDSP_SIGNED_CONTRACT_PREVIEW.md");
  assert.match(main, /app\.include_router\(trading_profile_router\)/);
  assert.match(backend, /get_provisioned_user/);
  assert.match(backend, /get_current_principal/);
  assert.match(backend, /same_origin\(request\)/);
  assert.match(backend, /hmac\.compare_digest/);
  assert.match(backend, /Literal\[False\]/);
  assert.match(backend, /hunter:m1:decision-style/);
  assert.doesNotMatch(backend, /ndsp\.app|httpx|requests\.get|orderService/);
  assert.match(contract, /synthetic signature-verification prototype ONLY/);
});
