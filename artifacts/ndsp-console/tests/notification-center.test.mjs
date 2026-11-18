import { test } from "node:test";
import { strict as assert } from "node:assert";
import { readFileSync } from "node:fs";
const panel = readFileSync(new URL("../src/components/NotificationsPanel.tsx", import.meta.url), "utf8");
const route = readFileSync(new URL("../src/app/[section]/page.tsx", import.meta.url), "utf8");

test("notifications use the authenticated source, not preview data", () => {
  assert.match(panel, /useAuth/);
  assert.match(panel, /state !== "authenticated"/);
  assert.match(route, /section === "notifications"\) content = <NotificationsPanel/);
  assert.doesNotMatch(panel, /fakeEvents|mockNotifications|demo-data/);
});

test("bilingual and fail-closed when messaging transport is not implemented", () => {
  assert.match(panel, /dir=\{ar \? "rtl" : "ltr"\}/);
  assert.match(panel, /"Telegram"/);
  assert.match(panel, /not enabled/i);
  assert.match(panel, /غير مفعّل/);
  assert.match(panel, /never open or close trades/);
  assert.doesNotMatch(panel, /fetch\(.*sendMessage/);
});

test("no browser-supplied secrets, chat IDs or trading action controls", () => {
  for (const secret of ["botToken", "telegram_chat_id", "API_SECRET", "privateKey", "armingControl"]) {
    assert.equal(panel.includes(secret), false);
  }
});
