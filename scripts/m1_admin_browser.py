"""Genuine provider-enforced password/TOTP; all credentials stay in memory."""
import json
import time

from playwright.sync_api import sync_playwright

from m1_admin_fixture import ADMIN_CLIENT, IDENTITIES, OPERATOR, PASSWORD_ONLY, totp
from m1_auth_browser import isolated_async
from m1_auth_environment import ISSUER, ORIGIN, SUBJECT
from nex_api.browser_sessions import SESSION_COOKIE
from nex_api.oidc import OIDCVerifier
from redis.asyncio import Redis
from nex_api.browser_sessions import BrowserSessions


def exercise(fixture, http):
    checks = []

    def check(name, value):
        checks.append({"check": name, "passed": bool(value)})
        (fixture.evidence / "mfa-browser-checks.json").write_text(json.dumps(checks, indent=2))
        if not value:
            raise RuntimeError("Named genuine administrator MFA check failed")

    fixture.command(fixture.compose + ["start", "keycloak"])
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            if http.get(ISSUER + "/.well-known/openid-configuration").status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise RuntimeError("Provider restart unavailable")

    async def stored(value):
        redis = Redis.from_url(fixture.env["REDIS_URL"])
        try:
            return await BrowserSessions(redis, fixture.env["NEX_SESSION_ENCRYPTION_KEY"]).load(
                "session", value
            )
        finally:
            await redis.aclose()

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        used_windows = {}
        accepted_codes = {}
        accepted_windows = {}

        def missing_totp(username, description):
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            page.goto(ORIGIN)
            page.get_by_role("button", name="Administrator MFA sign in",
                             exact=True).wait_for(timeout=20000)
            page.get_by_role("button", name="Administrator MFA sign in",
                             exact=True).click()
            page.locator("#username").fill(username)
            page.locator("#password").fill(fixture.admin_password)
            page.locator("#kc-login").click()
            try:
                page.wait_for_function(
                    """origin => (
                      location.origin === origin && location.pathname === "/" &&
                      new URL(location.href).searchParams.get("auth_error") === "MFA_REQUIRED"
                    ) || (
                      location.pathname.startsWith("/oidc/") &&
                      (document.querySelector("#otp") !== null ||
                       (location.pathname.includes("/login-actions/required-action") &&
                        document.querySelector("#totp") !== null))
                    )""",
                    arg=ORIGIN, timeout=30000,
                )
            except Exception:
                path = page.url.split("?", 1)[0]
                (fixture.evidence / "mfa-denial-diagnostic.json").write_text(json.dumps({
                    "path": path.replace(ORIGIN, ""),
                    "provider_origin": "/oidc/" in path,
                    "otp_input_present": page.locator("#otp").count() > 0,
                    "totp_setup_input_present": page.locator("#totp").count() > 0,
                    "password_input_present": page.locator("#password").count() > 0,
                    "mfa_required_callback": "?auth_error=MFA_REQUIRED" in page.url,
                    "nex_session_cookie_present": any(
                        c["name"] == SESSION_COOKIE for c in context.cookies()
                    ),
                }, indent=2))
                raise RuntimeError("Password-only administrator denial did not complete") from None
            denied = page.url == ORIGIN + "/?auth_error=MFA_REQUIRED"
            provider_challenge = "/oidc/" in page.url and page.locator("#otp").count() > 0
            totp_setup = ("/login-actions/required-action" in page.url
                          and page.locator("#totp").count() > 0)
            check(description, (denied or provider_challenge or totp_setup)
                  and not any(c["name"] == SESSION_COOKIE for c in context.cookies()))
            context.close()

        missing_totp(PASSWORD_ONLY[0],
                     "password-only ADMIN is held at a TOTP challenge or enrollment")
        missing_totp(OPERATOR[0],
                     "password-only OPERATOR is held at TOTP setup with no NEX session")

        def login(username, *, wrong=False, mfa=True, reused=False):
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            page.goto(ORIGIN)
            page.get_by_role("button", name="Administrator MFA sign in" if mfa else "Sign in",
                             exact=True).wait_for(timeout=20000)
            page.get_by_role("button", name="Administrator MFA sign in" if mfa else "Sign in",
                             exact=True).click()
            page.locator("#username").wait_for(timeout=20000)
            page.locator("#username").fill(username)
            page.locator("#password").fill(fixture.admin_password)
            page.locator("#kc-login").click()
            page.locator("#otp").wait_for(timeout=20000)
            check("real provider TOTP challenge: " + username, True)
            if wrong or reused:
                # A code several time windows old is genuinely invalid at provider.
                if reused:
                    code = accepted_codes[username]
                    if int(time.time()) // 30 != accepted_windows[username]:
                        raise RuntimeError("TOTP replay check crossed its provider time window")
                else:
                    code = totp(fixture.otp_seeds[username], -20)
                page.locator("#otp").fill(code)
                page.locator("#kc-login").click()
                page.wait_for_timeout(700)
                description = ("provider rejects reused TOTP without NEX session: "
                               if reused else "provider rejects invalid TOTP without NEX session: ")
                check(description + username,
                      page.locator("#otp").count() > 0
                      and not any(c["name"] == SESSION_COOKIE for c in context.cookies()))
                return context, page, None, None
            # Start near the beginning of a provider time window so the explicit
            # replay check can resubmit this accepted code without crossing it.
            window = int(time.time()) // 30
            if used_windows.get(username) == window or 30 - time.time() % 30 < 15:
                time.sleep(30 - time.time() % 30 + 0.5)
            window = int(time.time()) // 30
            used_windows[username] = window
            code = totp(fixture.otp_seeds[username])
            page.locator("#otp").fill(code)
            page.locator("#kc-login").click()
            try:
                page.wait_for_url(lambda url: "/oidc/" not in str(url), timeout=30000)
            except Exception:
                (fixture.evidence / "mfa-flow-diagnostic.json").write_text(json.dumps({
                    "still_at_provider": "/oidc/" in page.url,
                    "otp_field_present": page.locator("#otp").count() > 0,
                    "password_field_present": page.locator("#password").count() > 0,
                    "otp_error_present": page.locator("#input-error-otp-code").count() > 0,
                }, indent=2))
                raise RuntimeError("Provider factor flow did not complete") from None
            if not mfa:
                check("ordinary client cannot grant admin assurance despite real OTP",
                      http.get(ORIGIN + "/api/v1/me", headers={
                          "Cookie": "; ".join(c["name"] + "=" + c["value"] for c in context.cookies())
                      }).status_code == 401)
                return context, page, None, None
            accepted_codes[username] = code
            accepted_windows[username] = window
            page.get_by_role("button", name="Sign out", exact=True).wait_for(timeout=15000)
            cookie = next(c for c in context.cookies(ORIGIN + "/api/") if c["name"] == SESSION_COOKIE)
            record = isolated_async(stored(cookie["value"]))
            return context, page, cookie, record

        admin, _, subject = IDENTITIES[0]
        context, page, _, _ = login(admin, wrong=True)
        context.close()
        context, page, _, _ = login(admin, mfa=False)
        context.close()

        for username, role, subject in IDENTITIES:
            context, page, cookie, record = login(username)
            headers = {"Cookie": SESSION_COOKIE + "=" + cookie["value"], "Origin": ORIGIN,
                       "X-NEX-CSRF": record.data["csrf"]}
            me = http.get(ORIGIN + "/api/v1/me", headers=headers)
            status = http.get(ORIGIN + "/api/v1/auth/session", headers=headers)
            check("real fresh password/TOTP grants bound " + role + " session",
                  me.status_code == 200 and me.json()["role"] == role
                  and status.status_code == 200 and status.json()["administrator_mfa_verified"] is True)
            if role == "ADMIN":
                replay_context, _, _, _ = login(username, reused=True)
                replay_context.close()
            keys = http.get(ISSUER + "/protocol/openid-connect/certs").json()

            async def jwks():
                return keys

            claims = isolated_async(OIDCVerifier(
                issuer=ISSUER, audience=ADMIN_CLIENT,
                jwks_url=ISSUER + "/protocol/openid-connect/certs", fetch_jwks=jwks,
            ).verify(record.data["access_token"]))
            check("actual signed administrator token binds issuer/client/subject and factors: " + role,
                  claims["sub"] == subject and {"pwd", "otp"}.issubset(claims.get("amr", [])))
            check("actual administrator bearer token cannot bypass opaque MFA session: " + role,
                  http.get(ORIGIN + "/admin/v1/system/health", headers={
                      "Authorization": "Bearer " + record.data["access_token"],
                  }).status_code in {401, 403})
            health = http.get(ORIGIN + "/admin/v1/system/health", headers=headers)
            audit = http.get(ORIGIN + "/admin/v1/audit", headers=headers)
            # Existing OPERATOR-only PostgreSQL audit-read policy is unchanged.
            # A successful, RLS-filtered response is not proof of usable admin
            # audit rows; that policy/UI work belongs to the existing admin-view task.
            check("privileged health allowed and audit response remains RLS-scoped: " + role,
                  health.status_code == 200 and audit.status_code == 200
                  and all(row["tenant_id"] == me.json()["tenant_id"] for row in audit.json()))
            # Verify real Next.js administrator pages with the genuine MFA
            # browser cookie. No mock data, role override or bearer shortcut.
            with page.expect_response(
                lambda response: response.url.split("?", 1)[0]
                == ORIGIN + "/admin/v1/system/health",
                timeout=30000,
            ) as ui_health_response:
                page.goto(ORIGIN + "/admin/operations-center/", wait_until="domcontentloaded")
            page.locator(".admin-health .admin-status.is-ready").wait_for(timeout=30000)
            check("real MFA administrator browser renders live service health: " + role,
                  ui_health_response.value.status == 200
                  and page.get_by_role("heading", name="Service readiness").is_visible()
                  and page.locator(".admin-health .admin-status.is-ready").is_visible())

            with page.expect_response(
                lambda response: response.url.split("?", 1)[0]
                == ORIGIN + "/admin/v1/audit",
                timeout=30000,
            ) as ui_audit_response:
                page.goto(ORIGIN + "/admin/audit/", wait_until="domcontentloaded")
            ui_audit = ui_audit_response.value
            ui_rows = ui_audit.json() if ui_audit.status == 200 else []
            page.get_by_role("heading", name="Recent audit events").wait_for(timeout=30000)
            page.wait_for_function(
                """expected => Array.from(document.querySelectorAll('.admin-audit [role="status"]'))
                   .some(node => node.textContent.includes('loaded records')) &&
                   document.querySelector('.admin-audit-summary strong')?.textContent === String(expected)""",
                arg=len(ui_rows), timeout=30000,
            )
            check("real MFA administrator browser renders tenant audit response: " + role,
                  ui_audit.status == 200
                  and isinstance(ui_rows, list)
                  and all(row.get("tenant_id") == me.json()["tenant_id"] for row in ui_rows)
                  and page.locator(".admin-audit [role=alert]").count() == 0)
            other = "00000000-0000-4000-8000-000000000099"
            isolated = http.get(ORIGIN + "/api/v1/tenants/" + other + "/audit-events", headers=headers)
            check("cross-tenant privileged audit denied: " + role, isolated.status_code == 404)
            fixture.sql(f"UPDATE users SET status='disabled' WHERE subject='{subject}'")
            disabled = http.get(ORIGIN + "/admin/v1/system/health", headers=headers)
            check("disabled " + role + " identity denied despite valid MFA",
                  disabled.status_code == 403 and disabled.json()["reason_code"] == "USER_DISABLED")
            fixture.sql(f"UPDATE users SET status='active' WHERE subject='{subject}'")
            original_role = role
            fixture.sql(f"UPDATE users SET role='USER' WHERE subject='{subject}'")
            downgraded = http.get(ORIGIN + "/admin/v1/system/health", headers=headers)
            check("stale " + role + " session is denied after server-side role downgrade",
                  downgraded.status_code == 403
                  and downgraded.json()["reason_code"] == "ROLE_NOT_ALLOWED")
            fixture.sql(f"UPDATE users SET role='{original_role}' WHERE subject='{subject}'")
            fixture.sql(f"UPDATE tenants SET status='disabled' WHERE id IN "
                        f"(SELECT tenant_id FROM users WHERE subject='{subject}')")
            tenant_disabled = http.get(ORIGIN + "/admin/v1/audit", headers=headers)
            check("disabled tenant denied despite real " + role + " MFA",
                  tenant_disabled.status_code == 403
                  and tenant_disabled.json()["reason_code"] == "TENANT_DISABLED")
            fixture.sql(f"UPDATE tenants SET status='active' WHERE id IN "
                        f"(SELECT tenant_id FROM users WHERE subject='{subject}')")
            service = http.post(ISSUER + "/protocol/openid-connect/token", data={
                "client_id": "nex-test-management",
                "client_secret": fixture.env["NEX_TEST_MANAGEMENT_SECRET"],
                "grant_type": "client_credentials",
            })
            service.raise_for_status()
            management = {"Authorization": "Bearer " + service.json()["access_token"]}
            user_uri = ORIGIN + "/oidc/admin/realms/nex-m1-test/users/" + subject
            disabled_provider = http.put(user_uri, json={"enabled": False}, headers=management)
            disabled_provider.raise_for_status()
            provider_denial = http.get(ORIGIN + "/admin/v1/system/health", headers=headers)
            check("actual disabled Keycloak " + role + " identity denied server-side",
                  provider_denial.status_code == 403
                  and provider_denial.json()["reason_code"] == "MFA_REVOKED")
            http.put(user_uri, json={"enabled": True}, headers=management).raise_for_status()
            # Provider disable deleted local state; obtain a new real MFA session.
            context.close()
            context, page, cookie, record = login(username)
            headers = {"Cookie": SESSION_COOKIE + "=" + cookie["value"], "Origin": ORIGIN,
                       "X-NEX-CSRF": record.data["csrf"]}
            claims = isolated_async(OIDCVerifier(
                issuer=ISSUER, audience=ADMIN_CLIENT,
                jwks_url=ISSUER + "/protocol/openid-connect/certs", fetch_jwks=jwks,
            ).verify(record.data["access_token"]))
            page.screenshot(path=str(fixture.evidence / ("mfa-" + role.lower() + ".png")), full_page=True)
            if role == "ADMIN":
                original_mfa = record.data["mfa"].copy()
                refreshed = http.post(ORIGIN + "/api/v1/auth/refresh", headers=headers)
                record = isolated_async(stored(cookie["value"]))
                check("administrator refresh preserves verified assurance and auth_time",
                      refreshed.status_code == 200
                      and record.data.get("mfa") == original_mfa)
                revoked = http.post(ISSUER + "/protocol/openid-connect/revoke", data={
                    "client_id": ADMIN_CLIENT,
                    "client_secret": fixture.env["OIDC_ADMIN_MFA_CLIENT_SECRET"],
                    "token": record.data["refresh_token"], "token_type_hint": "refresh_token",
                })
                denial = http.get(ORIGIN + "/admin/v1/system/health", headers=headers)
                check("actual provider revocation immediately denies privileged administrator access",
                      revoked.status_code == 200 and denial.status_code == 403
                      and denial.json()["reason_code"] == "MFA_REVOKED")
                check("provider-revoked local administrator session deleted",
                      isolated_async(stored(cookie["value"])) is None)
                check("refresh cannot restore revoked privileged session",
                      http.post(ORIGIN + "/api/v1/auth/refresh", headers=headers).status_code == 401)
            else:
                # Real elapsed time, not an invented JWT timestamp or modified record.
                remaining = record.data["mfa"]["expires_at"] - time.time()
                time.sleep(max(0, remaining) + 1)
                expired = http.get(ORIGIN + "/admin/v1/system/health", headers=headers)
                check("actual bounded administrator MFA expires while access JWT remains unexpired",
                      claims["exp"] > time.time() and expired.status_code == 403
                      and expired.json()["reason_code"] == "MFA_EXPIRED")
                refresh_denial = http.post(ORIGIN + "/api/v1/auth/refresh", headers=headers)
                check("refresh cannot extend expired administrator MFA assurance",
                      refresh_denial.status_code == 403
                      and refresh_denial.json()["reason_code"] == "MFA_EXPIRED")
            context.close()

        # Exercise actual non-administrator browser sessions against the
        # existing server authorization boundary; no admin UI is introduced.
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto(ORIGIN)
        page.get_by_role("button", name="Sign in", exact=True).click()
        page.locator("#username").wait_for(timeout=20000)
        page.locator("#username").fill("nex-test-user")
        page.locator("#password").fill(fixture.user_password)
        page.locator("#kc-login").click()
        page.wait_for_url(lambda url: "/oidc/" not in str(url), timeout=30000)
        user_cookie = next(c for c in context.cookies(ORIGIN + "/api/")
                           if c["name"] == SESSION_COOKIE)
        user_headers = {"Cookie": SESSION_COOKIE + "=" + user_cookie["value"]}
        user_me = http.get(ORIGIN + "/api/v1/me", headers=user_headers)
        user_session = http.get(ORIGIN + "/api/v1/auth/session", headers=user_headers)
        denied = http.get(ORIGIN + "/admin/v1/system/health", headers=user_headers)
        user_refresh = http.post(ORIGIN + "/api/v1/auth/refresh", headers={
            **user_headers, "Origin": ORIGIN,
            "X-NEX-CSRF": user_session.json().get("csrf_token", ""),
        })
        user_session_after_refresh = http.get(
            ORIGIN + "/api/v1/auth/session", headers=user_headers
        )
        check("real USER is denied privileged health and has no administrator assurance",
              user_me.status_code == 200 and user_me.json()["role"] == "USER"
              and user_session.status_code == 200
              and user_session.json()["administrator_mfa_verified"] is False
              and denied.status_code == 403
              and denied.json()["reason_code"] == "ROLE_NOT_ALLOWED"
              and user_refresh.status_code == 200
              and user_session_after_refresh.status_code == 200
              and user_session_after_refresh.json()["administrator_mfa_verified"] is False)
        # Browser UI must not request privileged endpoints for ordinary USER.
        user_admin_requests = []
        page.on("request", lambda request: user_admin_requests.append(request.url)
                if request.url.startswith(ORIGIN + "/admin/v1/") else None)
        page.goto(ORIGIN + "/admin/operations-center/", wait_until="domcontentloaded")
        page.get_by_role("heading", name="Administrator access required").wait_for(timeout=20000)
        page.get_by_role("button", name="Sign out", exact=True).wait_for(timeout=20000)
        check("real USER browser health is gated without privileged fetch",
              not user_admin_requests)
        context.close()

        # An OPERATOR is a separate, explicitly lower-scope role in the
        # existing API policy; it cannot be mistaken for ADMIN MFA assurance.
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto(ORIGIN)
        page.get_by_role("button", name="Sign in", exact=True).click()
        page.locator("#username").wait_for(timeout=20000)
        page.locator("#username").fill(OPERATOR[0])
        page.locator("#password").fill(fixture.admin_password)
        page.locator("#kc-login").click()
        page.wait_for_url(lambda url: "/oidc/" not in str(url), timeout=30000)
        operator_cookie = next(c for c in context.cookies(ORIGIN + "/api/")
                               if c["name"] == SESSION_COOKIE)
        operator_headers = {"Cookie": SESSION_COOKIE + "=" + operator_cookie["value"]}
        operator_me = http.get(ORIGIN + "/api/v1/me", headers=operator_headers)
        operator_session = http.get(ORIGIN + "/api/v1/auth/session",
                                    headers=operator_headers)
        operator_health = http.get(ORIGIN + "/admin/v1/system/health",
                                   headers=operator_headers)
        operator_audit = http.get(ORIGIN + "/admin/v1/audit", headers=operator_headers)
        check("password-only OPERATOR is denied administrator routes and assurance",
              operator_me.status_code == 200
              and operator_me.json()["role"] == "OPERATOR"
              and operator_session.status_code == 200
              and operator_session.json()["administrator_mfa_verified"] is False
              and operator_health.status_code == 403
              and operator_health.json()["reason_code"] == "ROLE_NOT_ALLOWED"
              and operator_audit.status_code == 403
              and operator_audit.json()["reason_code"] == "ROLE_NOT_ALLOWED")
        operator_admin_requests = []
        page.on("request", lambda request: operator_admin_requests.append(request.url)
                if request.url.startswith(ORIGIN + "/admin/v1/") else None)
        page.goto(ORIGIN + "/admin/audit/", wait_until="domcontentloaded")
        page.get_by_role("heading", name="Administrator access required").wait_for(timeout=20000)
        page.get_by_role("button", name="Sign out", exact=True).wait_for(timeout=20000)
        check("real OPERATOR browser audit is gated without privileged fetch",
              not operator_admin_requests)
        context.close()

        # Capture only synthetic subject/tenant/role/status and credential-type
        # presence; never emit passwords, TOTP secrets or OTP values.
        management_response = http.post(ISSUER + "/protocol/openid-connect/token", data={
            "client_id": "nex-test-management",
            "client_secret": fixture.env["NEX_TEST_MANAGEMENT_SECRET"],
            "grant_type": "client_credentials",
        })
        management_response.raise_for_status()
        management = {"Authorization": "Bearer " + management_response.json()["access_token"]}
        expected = [
            (SUBJECT, "nex-test-user", "USER", False),
            *((subject, username, role, True) for username, role, subject in IDENTITIES),
            (PASSWORD_ONLY[2], PASSWORD_ONLY[0], PASSWORD_ONLY[1], False),
            (OPERATOR[2], OPERATOR[0], OPERATOR[1], False),
        ]
        subjects = ",".join("'" + subject + "'" for subject, _, _, _ in expected)
        rows = fixture.sql(
            "SELECT subject || '|' || tenant_id::text || '|' || role || '|' || status "
            "FROM users WHERE issuer='" + ISSUER + "' AND subject IN (" + subjects + ") "
            "ORDER BY subject"
        )
        database = {}
        for line in rows.splitlines():
            subject, tenant, role, status = line.split("|", 3)
            database[subject] = {"tenant_id": tenant, "role": role, "status": status}
        identities = []
        for subject, username, role, enrolled in expected:
            provider_url = ORIGIN + "/oidc/admin/realms/nex-m1-test/users/" + subject
            provider_user = http.get(provider_url, headers=management)
            credentials = http.get(provider_url + "/credentials", headers=management)
            provider_user.raise_for_status()
            credentials.raise_for_status()
            has_otp = any(item.get("type") == "otp" for item in credentials.json())
            row = database.get(subject)
            check("synthetic identity mapping, enabled status and MFA enrollment: " + role,
                  row is not None and row["role"] == role and row["status"] == "active"
                  and provider_user.json().get("username") == username
                  and provider_user.json().get("enabled") is True
                  and has_otp is enrolled)
            identities.append({
                "provider_subject": subject, "nex_subject": subject,
                "tenant_id": row["tenant_id"] if row else None,
                "role": role, "database_status": row["status"] if row else None,
                "provider_username": username, "provider_enabled": True,
                "mfa_enrollment": "TOTP enrolled" if enrolled else "not enrolled",
                "assurance_evidence": (
                    "Signed provider pwd+otp AMR, fresh auth_time, dedicated client and live "
                    "provider introspection were independently verified."
                    if enrolled and role in {"ADMIN", "SUPER_ADMIN"}
                    else "No administrator MFA assurance is claimed."
                ),
            })
        (fixture.evidence / "synthetic-administrator-identities.json").write_text(
            json.dumps({
                "provider": "Keycloak 26.6.3",
                "environment": "isolated, disposable, non-production",
                "policy": "keycloak-password-totp-v1",
                "identities": identities,
                "secrets_or_otp_values_retained": False,
            }, indent=2)
        )

        context, page, cookie, record = login(IDENTITIES[0][0])
        headers = {"Cookie": SESSION_COOKIE + "=" + cookie["value"], "Origin": ORIGIN,
                   "X-NEX-CSRF": record.data["csrf"]}
        logout = http.post(ORIGIN + "/api/v1/auth/logout", headers=headers)
        check("actual MFA administrator logout revokes provider and opaque local session",
              logout.status_code == 200 and logout.json()["provider_revoked"] is True
              and isolated_async(stored(cookie["value"])) is None
              and http.get(ORIGIN + "/admin/v1/system/health", headers=headers).status_code == 401)
        context.close()
        context, page, cookie, record = login(IDENTITIES[0][0])
        headers = {"Cookie": SESSION_COOKIE + "=" + cookie["value"]}
        # No-cookie and bearer replay cannot claim administrator MFA.
        check("no-session privileged route fails closed",
              http.get(ORIGIN + "/admin/v1/system/health").status_code == 401)
        fixture.command(fixture.compose + ["stop", "keycloak"])
        unavailable = http.get(ORIGIN + "/admin/v1/system/health", headers=headers)
        check("provider outage denies an otherwise fresh real administrator MFA session",
              unavailable.status_code == 503
              and unavailable.json()["reason_code"] == "MFA_PROVIDER_UNAVAILABLE")
        context.close()
        browser.close()
    return checks
