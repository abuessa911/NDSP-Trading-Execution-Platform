import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import {resolve} from "node:path";

const root=resolve(import.meta.dirname,"../../..");
const source=file=>readFileSync(resolve(root,file),"utf8");

test("preview bot settings save and reset persist only to browser storage",()=>{
 const view=source("artifacts/ndsp-console/src/ndsp/OperationsPreview.tsx");
 assert.match(view,/previewBotSettingsKey/);
 assert.match(view,/localStorage\.setItem\(previewBotSettingsKey/);
 assert.match(view,/localStorage\.removeItem\(previewBotSettingsKey/);
 assert.match(view,/Number\.isFinite\(positionRisk\)/);
 assert.match(view,/savePreview/);
 assert.match(view,/onClick=\{savePreview\}/);
 assert.match(view,/No trading configuration changed/);
});
test("market favorites and read/acknowledge preview states persist locally, never to a backend",()=>{
 const market=source("artifacts/ndsp-console/src/ndsp/views-trading.tsx");
 const preview=source("artifacts/ndsp-console/src/ndsp/OperationsPreview.tsx");
 assert.match(market,/hunter-ksa1-preview-favorites-v1/);
 assert.match(market,/localStorage\.setItem\("hunter-ksa1-preview-favorites-v1"/);
 assert.match(preview,/hunter-ksa1-preview-alert-flags-v1/);
 assert.match(preview,/localStorage\.setItem\("hunter-ksa1-preview-alert-flags-v1"/);
});
test("sample playback works without a historical trading execution engine",()=>{
 const trading=source("artifacts/ndsp-console/src/ndsp/views-trading.tsx");
 assert.match(trading,/Play synthetic sample/);
 assert.match(trading,/Pause synthetic playback/);
 assert.match(trading,/window\.setInterval/);
 assert.match(trading,/window\.clearInterval/);
 assert.match(trading,/No historical candles, trades, or real replay engine are used/);
 assert.match(trading,/Live execution is disabled/);
});
test("exchange configuration cannot falsely claim connectivity; read-only market navigation works",()=>{
 const operations=source("artifacts/ndsp-console/src/ndsp/OperationsPreview.tsx");
 assert.match(operations,/Actual exchange access: NOT CONNECTED/);
 assert.match(operations,/href="\/markets\/"/);
 assert.match(operations,/Open read-only market panel/);
});
