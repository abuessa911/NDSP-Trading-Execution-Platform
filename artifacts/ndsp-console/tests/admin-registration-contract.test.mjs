import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "../../..");
const read = path => readFileSync(resolve(root,path),"utf8");
test("registration form is hosted behind the existing administrator MFA view gate", () => {
  const directory=read("artifacts/ndsp-console/src/components/AdminUsersTenantsPanel.tsx");
  const form=read("artifacts/ndsp-console/src/components/AdminRegistrationPanel.tsx");
  assert.match(directory, /<AdminAccessGate>/);
  assert.match(directory, /<AdminRegistrationPanel\s*\/>/);
  assert.match(form, /administratorMfaVerified/);
  assert.match(form, /identity\?\.role === "ADMIN"/);
  assert.match(form, /identity\?\.role === "SUPER_ADMIN"/);
});
test("registration form and API client pass CSRF and do not accept passwords or assign roles", () => {
  const form=read("artifacts/ndsp-console/src/components/AdminRegistrationPanel.tsx");
  const api=read("lib/api-client-react/src/admin-browser.ts");
  const provider=read("artifacts/ndsp-console/src/components/AuthProvider.tsx");
  assert.match(form, /getCsrfToken\(\)/);
  assert.match(form, /createBrowserAdminRegistration\(email\.trim\(\)\.toLowerCase\(\), csrf/);
  assert.match(api, /"X-NEX-CSRF": csrf/);
  assert.match(api, /JSON\.stringify\(\{ email \}\)/);
  assert.match(provider, /session\.current\?\.csrf_token/);
  assert.doesNotMatch(form, /type="password"|localStorage/);
});
test("new protected server routes never enable public registration or admin escalation", () => {
  const api=read("apps/api/nex_api/routes/registrations.py");
  const sql=read("apps/api/migrations/versions/0005_m1_verified_invitation_registration.py");
  assert.match(api, /Depends\(get_administrator\)/);
  assert.match(api, /csrf\(request,record\)/);
  assert.match(sql, /role='USER'/);
  assert.match(sql, /p_email_verified IS DISTINCT FROM true/);
  assert.match(sql, /REVOKE UPDATE,DELETE,TRUNCATE/);
  assert.match(sql, /ACCOUNT_INVITATION_ACCEPTED/);
});
