import { test } from "node:test";
import assert from "node:assert/strict";
import { hasAdministratorAccess } from "../src/lib/admin-access.ts";

test("administrator display gate requires authenticated server role and strict MFA assurance", () => {
  for (const role of ["ADMIN", "SUPER_ADMIN"]) {
    assert.equal(hasAdministratorAccess("authenticated", role, true), true);
    for (const state of ["loading", "anonymous", "unconfigured", "unavailable"]) {
      assert.equal(hasAdministratorAccess(state, role, true), false);
    }
    for (const mfa of [false, undefined, null, "true", 1, {}, []]) {
      assert.equal(hasAdministratorAccess("authenticated", role, mfa), false);
    }
  }
  for (const role of ["USER", "OPERATOR", "admin", "super_admin", "", null, undefined]) {
    assert.equal(hasAdministratorAccess("authenticated", role, true), false);
  }
});
