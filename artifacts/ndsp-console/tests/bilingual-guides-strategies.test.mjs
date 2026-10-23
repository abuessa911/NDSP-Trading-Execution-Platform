import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
const root = resolve(import.meta.dirname, "../../..");
const read = path => readFileSync(resolve(root, path), "utf8");

test("user and owner manuals each offer complete Arabic and English content and owned routes", () => {
  const data = read("artifacts/ndsp-console/src/components/guide-data.ts");
  const view = read("artifacts/ndsp-console/src/components/Guides.tsx");
  const pages = read("artifacts/ndsp-console/src/lib/console-pages.ts");
  const userRoute = read("artifacts/ndsp-console/src/app/[section]/page.tsx");
  const adminRoute = read("artifacts/ndsp-console/src/app/admin/[section]/page.tsx");
  const owners = data.split("export const ownerGuide:")[1];
  const users = data.split("export const ownerGuide:")[0];
  assert.ok((users.match(/title:b\(/g) || []).length >= 12, "full user manual chapters");
  assert.ok((owners.match(/title:b\(/g) || []).length >= 12, "full owner manual chapters");
  assert.match(view, /chapter\.title\[lang\]/);
  assert.match(view, /item\[lang\]/);
  assert.match(view, /<AdminAccessGate>/);
  assert.match(pages, /slug: "user-guide"/);
  assert.match(pages, /slug: "owner-guide"/);
  assert.match(userRoute, /<UserGuide \/>/);
  assert.match(adminRoute, /<OwnerGuide \/>/);
  assert.match(read("artifacts/ndsp-console/src/components/ConsoleShell.tsx"), /"user-guide"/);
});

test("strategy screen localizes sample names, descriptions, states, last signal and relative update", () => {
  const src = read("artifacts/ndsp-console/src/ndsp/views-trading.tsx");
  const dictionary = read("artifacts/ndsp-console/src/ndsp/i18n.tsx");
  const names = ["Trend Ladder", "Range Fade", "Breakout Scout", "Mean Return"];
  for (const name of names) assert.ok(dictionary.includes('"' + name + '":'));
  assert.match(src, /t\(s\.name\)/);
  assert.match(src, /t\(cur\.name\)/);
  assert.match(src, /strategySignalLabel\(cur\.lastSignal, t\)/);
  assert.match(src, /strategyUpdateLabel\(cur\.updated, lang\)/);
  assert.match(src, /t\("Risk allocation"\)/);
  assert.match(src, /<Tx>\{cur\.note\}<\/Tx>/);
  assert.match(src, /<HunterStrategyScannerPanel/);
  assert.match(src, /Historical strategy metrics and signals below remain synthetic/);
  assert.match(dictionary, /سُلّم الاتجاه/);
});
