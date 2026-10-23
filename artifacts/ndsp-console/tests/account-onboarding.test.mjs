import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "../src");
const read = (path) => readFileSync(resolve(root, path), "utf8");

test("account access and registration pages are reachable through canonical navigation", () => {
  const pages = read("lib/console-pages.ts");
  const shell = read("components/ConsoleShell.tsx");
  const renderer = read("app/[section]/page.tsx");
  for (const slug of ["account-access", "registration"]) {
    assert.ok(pages.includes('slug: "' + slug + '"'));
    assert.ok(shell.includes('"' + slug + '"'));
    assert.ok(renderer.includes('section === "' + slug + '"'));
  }
});

test("public signup requires verified email and does not grant administrative access", () => {
  const panel = read("components/AccountEnrollmentPanel.tsx");
  assert.ok(panel.includes("Public self-registration is available with verified email."));
  assert.ok(panel.includes("new accounts have no administrator or trading execution permissions"));
  assert.ok(panel.includes("No user is created, role changed, or trading enabled"));
  assert.ok(!panel.includes("fetch("));
  assert.ok(!panel.includes("<form"));
});

test("account access controls match actual session, without unauthenticated logout", () => {
  const panel = read("components/AccountEnrollmentPanel.tsx");
  const shell = read("components/ConsoleShell.tsx");
  const controls = read("components/AuthControls.tsx");
  assert.ok(panel.includes("<AuthControls />"));
  assert.ok(panel.includes('signedIn ? <>'));
  assert.ok(panel.includes('administrator && <Link'));
  assert.ok(panel.includes('href="/registration/"'));
  assert.ok(!panel.includes('hunterLogoutAction'));
  assert.ok(!shell.includes('<AuthControls />'));
  assert.ok(shell.includes('className="hunter-account-status"'));
  assert.ok(controls.includes('state === "authenticated" && identity'));
  assert.ok(controls.includes('act("logout")'));
  assert.ok(shell.includes('act("logout")'));
  assert.ok(!controls.includes('M1 authentication'));
  assert.ok(controls.includes('href="/api/v1/auth/start"'));
});

test("login buttons still use existing server-backed auth, with no browser credential collection", () => {
  const controls = read("components/AuthControls.tsx");
  const provider = read("components/AuthProvider.tsx");
  assert.ok(controls.includes('href="/api/v1/auth/start"'));
  assert.ok(!controls.includes('href="/api/v1/auth/start?admin_mfa=true"'));
  assert.ok(provider.includes("await login("));
  const registration = read("components/RegistrationStart.tsx");
  assert.ok(registration.includes('href="/api/v1/auth/start?register=true"'));
  assert.ok(!registration.includes('onClick'));
  assert.ok(!registration.includes('fetch('));
  assert.ok(provider.includes('credentials: "same-origin"'));
  assert.ok(!controls.includes('type="password"'));
});

test("account onboarding copy has Arabic translations", () => {
  const translations = read("ndsp/i18n.tsx");
  for (const key of ["Account Access", "Account Registration", "No public sign-up form", "Registration policy"]) {
    assert.ok(translations.includes('"' + key + '": '));
  }
});


test("public and regular-user UI never advertises administrator sign-in", () => {
  const auth = read("components/AuthControls.tsx");
  const shell = read("components/ConsoleShell.tsx");
  assert.ok(!auth.includes('href="/api/v1/auth/start?admin_mfa=true"'));
  assert.ok(shell.includes('adminVisible && <nav'));
  assert.ok(shell.includes('adminVisible && <Link'));
  assert.ok(shell.includes('filter(slug => slug !== "audit")'));
});

test("legacy mobile menu and locale have independent functional fallback", () => {
  const shell = read("components/ConsoleShell.tsx");
  const layout = read("app/layout.tsx");
  const legacy = read("../public/hunter-legacy-controls.js");
  assert.ok(shell.includes('<details key={pathname} className="hunter-native-mobile-menu">'));
  assert.ok(shell.includes('href="?lang=ar"'));
  assert.ok(shell.includes('href="?lang=en"'));
  assert.ok(layout.includes('/hunter-legacy-controls.js'));
  assert.ok(legacy.includes('data-hunter-react-ready'));
});
