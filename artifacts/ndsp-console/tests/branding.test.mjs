import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../..");
const read = (name) => readFileSync(path.join(root, name), "utf8");
const label = "hunter_ksa1 bot";
const ui = [
  "ndsp-console/src/lib/bot-profile.ts",
  "ndsp-console/src/components/ConsoleShell.tsx",
  "ndsp-console/src/components/CommandCenter.tsx",
  "ndsp-console/src/components/PageFrame.tsx",
  "ndsp-console/src/app/layout.tsx",
  "ndsp-console/src/app/page.tsx",
  "ndsp-console/src/lib/console-pages.ts",
  "ndsp-console/src/ndsp/preview-copy.ts",
];

test("official bot name matches user-approved spelling exactly", () => {
  assert.match(read("ndsp-console/src/lib/bot-profile.ts"),
    /^export const BOT_NAME = "hunter_ksa1 bot";$/m);
  assert.match(read("../README.md"), /^# hunter_ksa1 bot — Trading Execution Platform$/m);
});

test("navigation, document title and page framing use canonical bot name", () => {
  const header = read("ndsp-console/src/components/ConsoleShell.tsx");
  assert.match(header, /<strong>\{BOT_NAME\}<\/strong>/);
  assert.match(header, /brand-mark">H<\/span>/);
  assert.match(header, /\{BOT_NAME\} · \{t\("Account workspace"\)\}/);
  const meta = read("ndsp-console/src/app/layout.tsx");
  assert.match(meta, /title: \{ default: \`\$\{BOT_NAME\} · M1 Console\`/);
  assert.match(read("ndsp-console/src/components/PageFrame.tsx"), /\{BOT_NAME\}/);
});

test("deprecated public-facing NAWAF brand strings were removed from scoped UI", () => {
  for (const name of ui) {
    const content = read(name);
    assert.doesNotMatch(content, /\bNAWAF\b/gi, name);
    assert.doesNotMatch(content, /Hunter_KSA1/, name);
  }
  assert.match(read("ndsp-console/src/ndsp/preview-copy.ts"),
    /"Independent trading bot": "بوت تداول مستقل"/);
});

test("NEX protocol, internal API module and safety gates intentionally remain", () => {
  const readme = read("../README.md");
  assert.match(readme, /historical specification references, \`nex_api\` modules/);
  assert.match(readme, /TRADING_MODE=paper/);
  assert.match(readme, /GLOBAL_KILL_SWITCH=true/);
  assert.match(readme, /LIVE_TRADING_ENABLED=false/);
  assert.match(readme, /BINANCE_ALLOW_WITHDRAW=false/);
});
