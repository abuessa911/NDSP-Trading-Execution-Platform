import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {resolve} from "node:path";
const root=resolve(import.meta.dirname,"../../..");
const source=p=>readFileSync(resolve(root,p),"utf8");
test("strategy choice uses the authenticated selection endpoint, not scanner start/stop buttons",()=>{
 const ui=source("artifacts/ndsp-console/src/components/HunterStrategyScannerPanel.tsx");
 assert.match(ui,/\/api\/v1\/trading\/strategies/);
 assert.match(ui,/\/api\/v1\/trading\/bot\/strategy\//);
 assert.match(ui,/\/select/);
 assert.match(ui,/administratorMfaVerified/);
 assert.match(ui,/credentials: "same-origin"/);
 assert.match(ui,/"X-NEX-CSRF"/);
 assert.match(ui,/aria-pressed=\{selected\}/);
 assert.match(ui,/اختيار الاستراتيجية/);
 assert.doesNotMatch(ui,/تشغيل الفحص|إيقاف الفحص|mutate\(s, "stop"\)|!bot\?\.powered \|\| selected/);
 assert.doesNotMatch(ui,/localStorage/);
 assert.doesNotMatch(ui,/api_secret/);
});
test("server strategy scanner uses closed candles, isolated tenant keys, never executes orders",()=>{
 const s=source("apps/api/nex_api/routes/strategy_scanner.py");
 assert.match(s,/fetch_closed_candles/);
 assert.match(s,/market="usdm_futures"/);
 assert.match(s,/user\.tenant_id/);
 assert.match(s,/get_operator/);
 assert.match(s,/verify_mutation/);
 assert.match(s,/execution_enabled: Literal\[False\]/);
 assert.doesNotMatch(s,/hunter_live_executor/);
});
test("legacy preview strategy buttons no longer pretend to turn on trading",()=>{
 const s=source("artifacts/ndsp-console/src/ndsp/views-trading.tsx");
 assert.match(s,/<HunterStrategyScannerPanel/);
 assert.doesNotMatch(s,/Preview enable/);
 assert.doesNotMatch(s,/Preview pause/);
});
