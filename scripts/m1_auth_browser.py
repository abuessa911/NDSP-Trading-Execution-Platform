"""Browser/user acceptance with actual provider-issued credentials kept in memory."""
import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright
from redis.asyncio import Redis

from m1_auth_environment import CLIENT, ISSUER, ORIGIN, SUBJECT, AuthEnvironment
from nex_api.browser_sessions import BrowserSessions, SESSION_COOKIE
from nex_api.oidc import OIDCVerifier


def isolated_async(coroutine):
    # Playwright's synchronous dispatcher already owns an event loop in this
    # thread. Redis/JWT coroutines run separately, never against that loop.
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coroutine).result()


def exercise(fixture: AuthEnvironment, http) -> list[dict]:
    checks = []

    def check(name: str, condition: bool) -> None:
        checks.append({"check": name, "passed": bool(condition)})
        (fixture.evidence / "browser-checks.json").write_text(json.dumps(checks, indent=2))
        if not condition:
            raise RuntimeError("A named browser acceptance check failed")

    async def server_record(opaque: str):
        redis = Redis.from_url(fixture.env["REDIS_URL"])
        try:
            store = BrowserSessions(redis, fixture.env["NEX_SESSION_ENCRYPTION_KEY"])
            record = await store.load("session", opaque)
            assert record is not None
            sealed = await redis.get(store.key("session", opaque))
            assert record.data["refresh_token"].encode() not in sealed
            return record
        finally:
            await redis.aclose()

    async def change_flow(state: str, field: str, value: str) -> None:
        redis = Redis.from_url(fixture.env["REDIS_URL"])
        try:
            store = BrowserSessions(redis, fixture.env["NEX_SESSION_ENCRYPTION_KEY"])
            record = await store.load("flow", state)
            assert record is not None
            record.data[field] = value
            await redis.set(store.key("flow", state), store.seal(record.data), ex=300)
        finally:
            await redis.aclose()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        delivery = {"javascript_errors": [], "responses": []}

        def frontend_error(error):
            message = str(error)
            known = ("React is not defined", "Cannot read properties of undefined",
                     "Cannot read properties of null", "Failed to fetch dynamically imported module")
            delivery["javascript_errors"].append(
                next((label for label in known if label in message), "UNCLASSIFIED_JAVASCRIPT_ERROR")
            )

        def frontend_response(response):
            path = urlsplit(response.url).path
            if path in {"/", "/api/health/auth", "/api/v1/auth/session"} or path.startswith("/assets/"):
                mime = response.headers.get("content-type", "").split(";")[0]
                delivery["responses"].append({
                    "path": path, "status": response.status,
                    "content_type": mime if mime in {
                        "text/html", "text/css", "text/plain", "application/json",
                        "application/javascript", "application/octet-stream"
                    } else "OTHER",
                })

        def frontend_console(message):
            if message.type == "error":
                frontend_error(message.text)

        page.on("pageerror", frontend_error)
        page.on("console", frontend_console)
        page.on("response", frontend_response)

        def fetch(path: str, method: str = "GET", csrf: str = "") -> dict:
            return page.evaluate("""async ({path,method,csrf}) => {
              const response = await fetch(path, {method, credentials:'same-origin',
                cache:'no-store', headers: csrf ? {'X-NEX-CSRF':csrf} : {}});
              return {status:response.status, body:await response.json()};
            }""", {"path": path, "method": method, "csrf": csrf})

        def authenticate() -> None:
            page.wait_for_function("""() => location.pathname === '/' ||
              document.querySelector('#username') !== null""", timeout=20000)
            if page.locator("#username").count():
                page.locator("#username").fill("nex-test-user")
                page.locator("#password").fill(fixture.user_password)
                page.locator("#kc-login").click()
            page.wait_for_url(lambda url: urlsplit(str(url)).path == "/", timeout=30000)

        initial = page.goto(ORIGIN)
        check("actual frontend document HTTP 200", initial is not None and initial.status == 200)
        page.screenshot(path=str(fixture.evidence / "initial-frontend.png"), full_page=True)
        try:
            page.get_by_role("button", name="Sign in", exact=True).wait_for()
        finally:
            (fixture.evidence / "frontend-delivery.json").write_text(json.dumps(delivery, indent=2))
            page.remove_listener("pageerror", frontend_error)
            page.remove_listener("console", frontend_console)
            page.remove_listener("response", frontend_response)
        check("browser begins on actual NEX frontend", page.title() != "")
        page.get_by_role("button", name="Sign in", exact=True).click()
        page.locator("#username").wait_for(timeout=20000)
        provider_url = urlsplit(page.url)
        params = parse_qs(provider_url.query)
        check("real Keycloak authorization redirect and PKCE S256",
              page.url.startswith(ISSUER + "/protocol/openid-connect/auth?")
              and params.get("code_challenge_method") == ["S256"]
              and params.get("redirect_uri") == [ORIGIN + "/api/v1/auth/callback"]
              and bool(params.get("state")) and bool(params.get("nonce")))
        authenticate()
        page.get_by_role("button", name="Sign out", exact=True).wait_for(timeout=15000)
        check("real callback clean redirect", page.url == ORIGIN + "/")
        me = fetch("/api/v1/me")
        check("protected M1 identity endpoint succeeds",
              me["status"] == 200 and me["body"]["role"] == "USER")
        status = fetch("/api/v1/auth/session")
        check("authenticated opaque session and CSRF token",
              status["status"] == 200 and bool(status["body"]["csrf_token"]))
        cookie = next(c for c in context.cookies(ORIGIN + "/api/") if c["name"] == SESSION_COOKIE)
        check("secure scoped bounded HttpOnly SameSite=Lax cookie",
              cookie["secure"] and cookie["httpOnly"] and cookie["sameSite"] == "Lax"
              and cookie["path"] == "/api" and 0 < cookie["expires"] - time.time() <= 1800)
        record = isolated_async(server_record(cookie["value"]))
        check("tokens encrypted in Redis, not in frontend storage",
              page.evaluate("localStorage.length === 0 && sessionStorage.length === 0"))
        (fixture.evidence / "cookie-properties.json").write_text(json.dumps({
            k: cookie[k] for k in ("name", "domain", "path", "secure", "httpOnly", "sameSite", "expires")
        }, indent=2))
        page.screenshot(path=str(fixture.evidence / "authenticated.png"), full_page=True)
        page.get_by_role("button", name="Refresh session", exact=True).click()
        page.get_by_text("Session refreshed.", exact=True).wait_for(timeout=15000)
        refreshed = isolated_async(server_record(cookie["value"]))
        check("actual provider refresh and rotation",
              refreshed.data["refresh_token"] != record.data["refresh_token"])
        record = refreshed
        # Read real provider JWKS over certificate-verified HTTPS, not a fixture.
        keys = http.get(ISSUER + "/protocol/openid-connect/certs").json()

        async def jwks():
            return keys

        claims = isolated_async(OIDCVerifier(
            issuer=ISSUER, audience=CLIENT, jwks_url=ISSUER + "/protocol/openid-connect/certs",
            fetch_jwks=jwks,
        ).verify(record.data["access_token"]))
        check("actual provider access JWT independently signature/issuer/audience verified",
              claims["sub"] == SUBJECT)
        logout_results = []
        page.expose_function("__nexCaptureLogout", lambda value: logout_results.append(value))
        page.evaluate("""() => {
          const original = window.fetch;
          window.fetch = async (...args) => {
            const response = await original(...args);
            if (new URL(response.url).pathname === '/api/v1/auth/logout') {
              const value = await response.clone().json();
              await window.__nexCaptureLogout({
                http_status: response.status, status: value.status,
                provider_revoked: value.provider_revoked, logout_url: value.logout_url
              });
            }
            return response;
          };
        }""")
        # Capture the unchanged real response before the frontend navigates.
        # Chromium can discard old-document response bodies after navigation.
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.get_by_role("button", name="Sign out", exact=True).click()
        result = logout_results[-1]
        check("local logout and provider revocation completed",
              result["http_status"] == 200 and result.get("provider_revoked") is True)
        check("standards provider end-session URL contains no ID/access/refresh token",
              result["logout_url"].startswith(ISSUER + "/protocol/openid-connect/logout?")
              and set(parse_qs(urlsplit(result["logout_url"]).query))
              == {"client_id", "post_logout_redirect_uri"})
        if urlsplit(page.url).path != "/":
            page.locator("#kc-logout").click()
        page.wait_for_url(ORIGIN + "/", timeout=20000)
        page.get_by_role("button", name="Sign in", exact=True).wait_for()
        check("provider logout returns to exact registered URI", page.url == ORIGIN + "/")
        check("NEX session cookie securely removed",
              not any(c["name"] == SESSION_COOKIE for c in context.cookies(ORIGIN + "/api/")))
        page.screenshot(path=str(fixture.evidence / "logged-out.png"), full_page=True)
        sid, csrf = cookie["value"], record.data["csrf"]
        replay_headers = {"Origin": ORIGIN, "Cookie": SESSION_COOKIE + "=" + sid, "X-NEX-CSRF": csrf}
        reused = http.get(ORIGIN + "/api/v1/me", headers=replay_headers)
        check("terminated local session cannot access protected endpoint",
              reused.status_code == 401 and reused.json()["reason_code"] == "SESSION_REVOKED")
        refresh = http.post(ORIGIN + "/api/v1/auth/refresh", headers=replay_headers)
        check("refresh cannot recreate logged-out NEX session",
              refresh.status_code == 401 and refresh.json()["reason_code"] == "SESSION_REVOKED")
        external = http.get(ORIGIN + "/api/v1/me",
                            headers={"Authorization": "Bearer " + record.data["access_token"]})
        check("unexpired provider JWT cannot bypass locally terminated NEX session",
              claims["exp"] > time.time() and external.status_code == 401)
        provider_refresh = http.post(ISSUER + "/protocol/openid-connect/token", data={
            "client_id": CLIENT, "grant_type": "refresh_token",
            "refresh_token": record.data["refresh_token"],
        })
        check("real provider rejects revoked refresh token",
              provider_refresh.status_code == 400 and provider_refresh.json()["error"] == "invalid_grant")
        retry = fetch("/api/v1/auth/logout", "POST", csrf)
        check("second logout fails explicitly", retry["status"] == 401)
        page.get_by_role("button", name="Sign in", exact=True).click()
        page.locator("#username").wait_for(timeout=15000)
        check("provider SSO session ended: fresh credentials required", True)
        # Do not complete that pending transaction; new tests initiate their own.
        page.goto(ORIGIN)

        def denied_login(expected: str, *, mutation: tuple[str, str] | None = None):
            page.goto(ORIGIN)
            started = fetch("/api/v1/auth/login", "POST")
            check("negative case login transaction starts: " + expected, started["status"] == 200)
            url = started["body"]["authorization_url"]
            if mutation:
                state = parse_qs(urlsplit(url).query)["state"][0]
                isolated_async(change_flow(state, *mutation))
            page.goto(url)
            authenticate()
            page.get_by_text("Sign-in rejected: " + expected, exact=True).wait_for(timeout=15000)
            check("genuine callback rejected: " + expected, fetch("/api/v1/me")["status"] == 401)

        fixture.sql(f"UPDATE users SET status='disabled' WHERE subject='{SUBJECT}'")
        try:
            denied_login("USER_DISABLED")
        finally:
            fixture.sql(f"UPDATE users SET status='active' WHERE subject='{SUBJECT}'")
        fixture.sql(f"UPDATE tenants SET status='disabled' WHERE id IN "
                    f"(SELECT tenant_id FROM users WHERE subject='{SUBJECT}')")
        try:
            denied_login("TENANT_DISABLED")
        finally:
            fixture.sql(f"UPDATE tenants SET status='active' WHERE id IN "
                        f"(SELECT tenant_id FROM users WHERE subject='{SUBJECT}')")
        denied_login("OIDC_TOKEN_NOT_VALID", mutation=("nonce", "wrong-expected-nonce"))
        denied_login("OIDC_EXCHANGE_FAILED", mutation=("verifier", "x" * 64))
        check("invalid role is rejected by database constraint", fixture.invalid_role_rejected())
        # Actual provider outage must not be masked by cached JWKS/readiness.
        fixture.command(fixture.compose + ["stop", "keycloak"])
        ready = http.get(ORIGIN + "/api/health/ready")
        check("provider outage fails readiness despite cached keys",
              ready.status_code == 503 and ready.json()["components"]["oidc"] == "unavailable")
        failed = fetch("/api/v1/auth/login", "POST")
        check("provider outage login fails explicitly", failed["status"] == 503)
        browser.close()
    return checks