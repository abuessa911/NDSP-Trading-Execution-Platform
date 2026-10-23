"""Deterministic coverage only. Genuine acceptance is verify-m1-auth.py."""
import asyncio
import hashlib
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import jwt
import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from nex_api.audit import AuditUnavailable
from nex_api.browser_provider import BrowserProvider, ProviderFailure, pkce_challenge
from nex_api.browser_sessions import BrowserSessions, SESSION_COOKIE
from nex_api.config import Settings
from nex_api.dependencies import Principal, get_provisioned_user, get_session
from nex_api.main import create_app
from nex_api.models import Tenant, User
from nex_api.oidc import OIDCTokenError, OIDCVerifier
from nex_api.routes import auth

ISSUER = "https://provider.example.test/realm"
ORIGIN = "https://app.example.test"


def settings(**extra):
    return Settings(_env_file=None, oidc_browser_login_enabled=True,
                    oidc_issuer=ISSUER, oidc_audience="nex-browser",
                    oidc_jwks_url=ISSUER + "/certs", oidc_client_id="nex-browser",
                    oidc_redirect_uri=ORIGIN + "/api/v1/auth/callback",
                    oidc_post_logout_redirect_uri=ORIGIN + "/",
                    oidc_post_login_redirect_uri=ORIGIN + "/dashboard/",
                    nex_session_encryption_key=Fernet.generate_key().decode(), **extra)


class FakeRedis:
    def __init__(self):
        self.data = {}

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True

    async def get(self, key):
        return self.data.get(key)

    async def getdel(self, key):
        return self.data.pop(key, None)

    async def eval(self, script, number, key, expected, *arguments):
        if self.data.get(key) != expected.encode():
            return None
        if "GETDEL" in script:
            return self.data.pop(key)
        self.data[key] = arguments[0].encode()
        return 1


@pytest.fixture
def browser(monkeypatch):
    cfg = settings()
    user = User(id=UUID(int=4), tenant_id=UUID(int=3), email="unit@example.test",
                role="USER", status="active", issuer=ISSUER, subject="unit-subject")
    tenant = Tenant(id=UUID(int=3), name="Unit fixture", status="active")
    database = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="sqlite")),
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: user)),
        get=AsyncMock(return_value=tenant),
    )
    store = BrowserSessions(FakeRedis(), cfg.nex_session_encryption_key.get_secret_value())
    events = []

    async def event(request, action, outcome="SUCCESS", reason=None):
        events.append((action, outcome, reason))

    async def authorize(request, data):
        return await get_provisioned_user(request, Principal(data["issuer"], data["subject"]), database)

    async def db():
        yield database

    provider = SimpleNamespace(
        authorization=AsyncMock(side_effect=lambda state, nonce, verifier:
                                ISSUER + "/auth?state=" + state),
        exchange=AsyncMock(return_value={
            "claims": {"iss": ISSUER, "sub": "unit-subject", "exp": time.time() + 120},
            "access_token": "unit-only-not-provider-proof", "refresh_token": "unit-only-refresh",
            "expires_in": 120,
        }),
        revoke=AsyncMock(return_value=True), logout_url=AsyncMock(return_value=ISSUER + "/logout"),
        refresh=AsyncMock(return_value={"access_token": "unit-only-refreshed",
                                       "refresh_token": "unit-only-rotated", "expires_in": 120}),
    )
    monkeypatch.setattr(auth, "event", event)
    monkeypatch.setattr(auth, "authorize", authorize)
    monkeypatch.setattr("nex_api.main.persist_audit", AsyncMock())
    app = create_app(cfg)
    app.dependency_overrides[get_session] = db
    with TestClient(app, base_url=ORIGIN, follow_redirects=False) as client:
        app.state.browser_sessions = store
        app.state.browser_provider = provider
        yield SimpleNamespace(client=client, provider=provider, store=store,
                              events=events, user=user, tenant=tenant)


def begin(browser):
    started = browser.client.post("/api/v1/auth/login", headers={"Origin": ORIGIN})
    assert started.status_code == 200
    state = parse_qs(urlsplit(started.json()["authorization_url"]).query)["state"][0]
    return "/api/v1/auth/callback?code=unit-only-code&state=" + state


def signed_in(browser):
    response = browser.client.get(begin(browser))
    assert response.status_code == 303
    status = browser.client.get("/api/v1/auth/session")
    assert status.status_code == 200
    return status.json()["csrf_token"], browser.client.cookies.get(SESSION_COOKIE)


@pytest.mark.parametrize(("path", "destination"), [
    ("/api/v1/auth/start", "/auth"),
    ("/api/v1/auth/start?register=true", "/registrations"),
])
def test_native_browser_navigation_protects_pkce_without_javascript(browser, path, destination):
    response = browser.client.get(path)
    assert response.status_code == 303
    uri = urlsplit(response.headers["location"])
    assert uri.path.endswith(destination)
    state = parse_qs(uri.query)["state"][0]
    assert len(state) >= 48
    assert response.headers["cache-control"] == "no-store"
    assert any("Secure" in c and "HttpOnly" in c and "SameSite=lax" in c
               for c in response.headers.get_list("set-cookie"))
    assert browser.client.get("/api/v1/auth/callback?code=unit-only-code&state=" + state).status_code == 303
    assert browser.client.get("/api/v1/auth/session").status_code == 200


def test_native_browser_navigation_rejects_admin_registration(browser):
    response = browser.client.get("/api/v1/auth/start?admin_mfa=true&register=true")
    assert response.status_code == 403
    assert not browser.store.redis.data


def test_pkce_rfc7636_s256_vector():
    assert pkce_challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk") == \
        "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


@pytest.mark.parametrize("origin", ["https://evil.example.test", "", "null"])
def test_login_cross_origin_denied(browser, origin):
    assert browser.client.post("/api/v1/auth/login", headers={"Origin": origin}).status_code == 403
    assert not browser.store.redis.data


def test_state_tampering_and_replay_are_denied(browser):
    callback = begin(browser)
    tampered = browser.client.get("/api/v1/auth/callback?code=unit&state=" + "x" * 64)
    assert "OIDC_STATE_NOT_VALID" in tampered.headers["location"]
    # Tampered callback cleared the binding cookie; begin an independent flow.
    callback = begin(browser)
    assert browser.client.get(callback).status_code == 303
    replay = browser.client.get(callback)
    assert "OIDC_STATE_NOT_VALID" in replay.headers["location"]
    assert browser.provider.exchange.await_count == 1


@pytest.mark.parametrize(("field", "value", "code"), [
    ("status", "disabled", "USER_DISABLED"),
    ("role", "UNRECOGNIZED", "ROLE_NOT_ALLOWED"),
    ("role", "ADMIN", "MFA_EXTERNAL_REQUIREMENT"),
    ("role", "SUPER_ADMIN", "MFA_EXTERNAL_REQUIREMENT"),
])
def test_identity_boundaries_remain_closed(browser, field, value, code):
    setattr(browser.user, field, value)
    response = browser.client.get(begin(browser))
    assert code in response.headers["location"]
    assert browser.client.cookies.get(SESSION_COOKIE) is None
    assert ("LOGIN_DENIED", "DENIED", code) in browser.events


def test_disabled_tenant_denied(browser):
    browser.tenant.status = "disabled"
    assert "TENANT_DISABLED" in browser.client.get(begin(browser)).headers["location"]


def test_secure_cookie_and_no_token_callback_url(browser):
    response = browser.client.get(begin(browser))
    values = response.headers.get_list("set-cookie")
    assert any("HttpOnly" in v and "Secure" in v and "SameSite=lax" in v
               and "Path=/api" in v and "Max-Age=1800" in v for v in values)
    assert response.headers["location"] == ORIGIN + "/dashboard/"
    assert response.headers["cache-control"] == "no-store"
    for value in browser.store.redis.data.values():
        assert b"unit-only-refresh" not in value


@pytest.mark.parametrize("csrf", ["", "wrong-csrf"])
def test_logout_csrf_does_not_terminate_or_clear_session(browser, csrf):
    _, sid = signed_in(browser)
    response = browser.client.post("/api/v1/auth/logout",
                                   headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf})
    assert response.status_code == 403
    assert browser.client.cookies.get(SESSION_COOKIE) == sid
    assert browser.client.get("/api/v1/me").status_code == 200


def test_logout_revocation_and_refresh_replay(browser):
    csrf, sid = signed_in(browser)
    assert browser.client.post("/api/v1/auth/refresh",
                               headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf}).status_code == 200
    result = browser.client.post("/api/v1/auth/logout",
                                 headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf})
    assert result.status_code == 200 and result.json()["provider_revoked"]
    assert browser.client.cookies.get(SESSION_COOKIE) is None
    browser.client.cookies.set(SESSION_COOKIE, sid, path="/api")
    assert browser.client.get("/api/v1/me").status_code == 401
    assert browser.client.post("/api/v1/auth/refresh",
                               headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf}).status_code == 401
    assert browser.client.get("/api/v1/me", headers={"Authorization": "Bearer unit"}).status_code == 401
    assert ("SESSION_REVOKED", "SUCCESS", None) in browser.events


def test_expired_provider_access_token_can_be_refreshed_with_bound_session(browser):
    csrf, sid = signed_in(browser)
    record = asyncio.run(browser.store.load("session", sid))
    record.data["auth_expires_at"] = time.time() - 10
    browser.store.redis.data[browser.store.key("session", sid)] = browser.store.seal(record.data)
    assert browser.client.get("/api/v1/me").status_code == 401
    response = browser.client.post("/api/v1/auth/refresh",
                                   headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf})
    assert response.status_code == 200
    assert browser.client.get("/api/v1/me").status_code == 200
    assert ("TOKEN_REFRESH_SUCCESS", "SUCCESS", None) in browser.events


def test_refresh_rechecks_user_status_after_provider_rotation(browser):
    csrf, sid = signed_in(browser)
    browser.user.status = "disabled"
    response = browser.client.post("/api/v1/auth/refresh",
                                   headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf})
    assert response.status_code == 403
    assert response.json()["reason_code"] == "USER_DISABLED"
    assert ("TOKEN_REFRESH_SUCCESS", "SUCCESS", None) not in browser.events
    browser.provider.revoke.assert_awaited()
    assert browser.client.get("/api/v1/me").status_code == 403


def test_refresh_requires_valid_csrf_even_with_active_session(browser):
    _, sid = signed_in(browser)
    response = browser.client.post("/api/v1/auth/refresh",
                                   headers={"Origin": ORIGIN, "X-NEX-CSRF": "invalid"})
    assert response.status_code == 403
    assert response.json()["reason_code"] == "CSRF_NOT_VALID"
    assert asyncio.run(browser.store.load("session", sid)) is not None
    browser.provider.refresh.assert_not_awaited()


def test_provider_logout_failure_still_terminates_local_session(browser):
    csrf, sid = signed_in(browser)
    browser.provider.revoke.side_effect = ProviderFailure("Unit provider outage")
    response = browser.client.post("/api/v1/auth/logout",
                                   headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf})
    assert response.status_code == 503
    assert browser.client.cookies.get(SESSION_COOKIE) is None
    assert asyncio.run(browser.store.load("session", sid)) is None
    assert ("LOGOUT_FAILED", "FAILED", "OIDC_LOGOUT_FAILED") in browser.events


def test_refresh_race_cannot_resurrect_logged_out_session(browser):
    csrf, sid = signed_in(browser)

    async def racing_refresh(token):
        await browser.store.take("session", sid)
        return {"access_token": "unit-racing-access", "refresh_token": "unit-racing-refresh",
                "expires_in": 120}

    browser.provider.refresh.side_effect = racing_refresh
    response = browser.client.post("/api/v1/auth/refresh",
                                   headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf})
    assert response.status_code == 401 and response.json()["reason_code"] == "SESSION_REVOKED"
    assert asyncio.run(browser.store.load("session", sid)) is None
    browser.provider.revoke.assert_awaited()


def test_refresh_nonce_mismatch_is_denied_and_new_tokens_revoked(browser):
    csrf, _ = signed_in(browser)
    browser.provider.refresh.return_value["id_token"] = "unit-id-token"
    browser.provider.verifier = SimpleNamespace(verify=AsyncMock(return_value={
        "iss": ISSUER, "sub": "unit-subject", "nonce": "wrong-refresh-nonce",
    }))
    response = browser.client.post("/api/v1/auth/refresh",
                                   headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf})
    assert response.status_code == 503
    browser.provider.revoke.assert_awaited()


def test_required_audit_failure_never_creates_session(browser, monkeypatch):
    callback = begin(browser)
    monkeypatch.setattr(auth, "event", AsyncMock(side_effect=AuditUnavailable("Unit audit outage")))
    response = browser.client.get(callback)
    assert "AUDIT_PERSISTENCE_UNAVAILABLE" in response.headers["location"]
    assert browser.client.cookies.get(SESSION_COOKIE) is None
    assert not browser.store.redis.data


def test_expired_session_denied(browser):
    _, sid = signed_in(browser)
    key = browser.store.key("session", sid)
    record = asyncio.run(browser.store.load("session", sid))
    record.data["expires_at"] = time.time() - 1
    browser.store.redis.data[key] = browser.store.seal(record.data)
    assert browser.client.get("/api/v1/me").status_code == 401


@pytest.mark.parametrize("role", ["USER", "OPERATOR"])
def test_non_administrator_browser_session_cannot_read_operations(browser, role):
    signed_in(browser)
    browser.user.role = role
    response = browser.client.get("/api/v1/admin/operations")
    assert response.status_code == 403
    assert response.json()["reason_code"] == "ROLE_NOT_ALLOWED"


@pytest.mark.parametrize("case", ["wrong_nonce", "missing_nonce", "issuer", "audience",
                                 "expired", "nbf", "signature", "azp"])
def test_browser_id_token_rejections(case, monkeypatch):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(RSAAlgorithm.to_jwk(private.public_key()))
    jwk.update(kid="unit-key", use="sig", alg="RS256")
    claims = {"iss": ISSUER, "sub": "unit-subject", "aud": "nex-browser", "iat": int(time.time()),
              "exp": int(time.time()) + 120, "nonce": "expected-nonce"}
    changes = {
        "wrong_nonce": {"nonce": "wrong"}, "missing_nonce": {"nonce": None},
        "issuer": {"iss": "https://evil.example.test"}, "audience": {"aud": "wrong"},
        "expired": {"exp": int(time.time()) - 60}, "nbf": {"nbf": int(time.time()) + 120},
        "azp": {"azp": "wrong"},
    }
    claims.update(changes.get(case, {}))
    signing = rsa.generate_private_key(public_exponent=65537, key_size=2048) if case == "signature" else private
    token = jwt.encode(claims, signing, algorithm="RS256", headers={"kid": "unit-key"})

    async def jwks():
        return {"keys": [jwk]}

    provider = BrowserProvider(settings())
    provider.verifier = OIDCVerifier(issuer=ISSUER, audience="nex-browser",
                                     jwks_url=ISSUER + "/certs", fetch_jwks=jwks)
    monkeypatch.setattr(provider, "document", AsyncMock(return_value={"token_endpoint": ISSUER + "/token"}))
    monkeypatch.setattr(provider, "post", AsyncMock(return_value={"id_token": token, "access_token": "unit"}))
    with pytest.raises(OIDCTokenError):
        asyncio.run(provider.exchange("unit-code", "v" * 64, "expected-nonce"))


def test_invalid_pkce_verifier_rejected_before_exchange():
    with pytest.raises(OIDCTokenError):
        asyncio.run(BrowserProvider(settings()).exchange("unit-code", "too-short", "nonce"))


def test_server_cookie_identifier_is_hashed():
    store = BrowserSessions(FakeRedis(), Fernet.generate_key().decode())
    opaque = "opaque-unit-id-" + "x" * 48
    assert store.key("session", opaque) == "nex:m1:session:" + hashlib.sha256(opaque.encode()).hexdigest()


def test_hunter_style_requires_authenticated_session(browser):
    # This is a bot-local preference, never an NDSP decision or order authority.
    response = browser.client.get("/api/v1/trading/profile")
    assert response.status_code == 401


def test_hunter_investment_and_speculation_persist_server_side(browser):
    csrf, _ = signed_in(browser)
    default = browser.client.get("/api/v1/trading/profile")
    assert default.status_code == 200
    assert default.json() == {
        "mode": "SPECULATIVE", "persisted": False,
        "execution_authorized": False, "ndsp_contract_bound": False,
    }
    for mode in ("INVESTMENT", "SPECULATIVE"):
        saved = browser.client.put("/api/v1/trading/profile",
            headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf}, json={"mode": mode})
        assert saved.status_code == 200
        assert saved.json() == {
            "mode": mode, "persisted": True,
            "execution_authorized": False, "ndsp_contract_bound": False,
        }
        fetched = browser.client.get("/api/v1/trading/profile")
        assert fetched.json() == saved.json()
    browser.user.id = UUID(int=5)
    changed_owner = browser.client.get("/api/v1/trading/profile")
    assert changed_owner.status_code == 200
    assert changed_owner.json()["persisted"] is False


def test_hunter_decision_style_rejects_csrf_origin_and_unsupported_fields(browser):
    csrf, _ = signed_in(browser)
    for headers in ({}, {"Origin": ORIGIN, "X-NEX-CSRF": "invalid"},
                    {"Origin": "https://evil.example.test", "X-NEX-CSRF": csrf}):
        response = browser.client.put("/api/v1/trading/profile",
            json={"mode": "INVESTMENT"}, headers=headers)
        assert response.status_code == 403
    for item in ({"mode": "AUTOMATIC"}, {"mode": "INVESTMENT", "execute": True},
                 {"mode": "SPECULATIVE", "ndsp_api_url": "https://ndsp.app"}):
        result = browser.client.put("/api/v1/trading/profile",
            json=item, headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf})
        assert result.status_code == 422
    assert browser.client.get("/api/v1/trading/profile").json()["persisted"] is False

@pytest.mark.parametrize("lang", ["ar", "en"])
def test_public_browser_login_locale_is_passed_to_identity_provider(browser, lang):
    response = browser.client.get("/api/v1/auth/start?lang=" + lang)
    assert response.status_code == 303
    values = parse_qs(urlsplit(response.headers["location"]).query)
    assert values["ui_locales"] == [lang]
    assert values["kc_locale"] == [lang]
    assert "state" in values
    assert response.headers.get("set-cookie")


def test_public_browser_login_locale_rejects_unexpected_values(browser):
    assert browser.client.get("/api/v1/auth/start?lang=xyz").status_code == 422


def test_admin_role_normal_login_steps_up_only_once_without_granting_session(browser, monkeypatch):
    """An ordinary browser client must never authenticate an administrator."""
    from nex_api.dependencies import failure
    browser.client.app.state.settings.oidc_admin_mfa_policy = "keycloak-password-totp-v1"
    browser.client.app.state.settings.oidc_admin_mfa_client_id = "nex-m1-admin"
    browser.provider.administrator = lambda: browser.provider
    browser.provider.authorization.side_effect = (
        lambda state, nonce, verifier, **kw:
            ISSUER + "/auth?state=" + state + ("&mfa=1" if kw.get("fresh_mfa") else "")
    )

    async def simulate_role_and_admin_mfa(request, data):
        request.state.audit_user = {
            "id": str(browser.user.id),
            "tenant_id": browser.user.tenant_id,
            "role": "ADMIN",
        }
        if not data.get("admin_mfa"):
            raise failure("MFA_REQUIRED", "Administrator MFA required.")
        return browser.user

    monkeypatch.setattr(auth, "authorize", simulate_role_and_admin_mfa)
    monkeypatch.setattr("nex_api.administrator_mfa.assurance", lambda _settings, _claims: {
        "policy": "keycloak-password-totp-v1",
        "client": "nex-m1-admin", "auth_time": time.time(),
        "methods": ["pwd", "otp"], "expires_at": time.time() + 300,
    })
    initial = browser.client.get("/api/v1/auth/start?lang=en")
    assert initial.status_code == 303
    first_state = parse_qs(urlsplit(initial.headers["location"]).query)["state"][0]
    first = browser.client.get("/api/v1/auth/callback?code=unit-only-code&state=" + first_state)
    assert first.status_code == 303
    assert "mfa=1" in first.headers["location"]
    assert "ui_locales=en" in first.headers["location"]
    assert browser.client.cookies.get(SESSION_COOKIE) is None
    browser.provider.revoke.assert_awaited_once()
    second_state = parse_qs(urlsplit(first.headers["location"]).query)["state"][0]
    complete = browser.client.get("/api/v1/auth/callback?code=unit-only-code&state=" + second_state)
    assert complete.status_code == 303
    assert complete.headers["location"] == ORIGIN + "/dashboard/"
    assert browser.client.cookies.get(SESSION_COOKIE)


def test_admin_step_up_failure_does_not_restart_in_a_loop(browser, monkeypatch):
    from nex_api.dependencies import failure
    browser.client.app.state.settings.oidc_admin_mfa_policy = "keycloak-password-totp-v1"
    browser.client.app.state.settings.oidc_admin_mfa_client_id = "nex-m1-admin"
    browser.provider.administrator = lambda: browser.provider
    browser.provider.authorization.side_effect = (
        lambda state, nonce, verifier, **kw: ISSUER + "/auth?state=" + state
    )

    async def deny_admin(request, _data):
        request.state.audit_user = {"id": str(browser.user.id),
                                   "tenant_id": browser.user.tenant_id, "role": "ADMIN"}
        raise failure("MFA_REQUIRED", "Administrator MFA required.")

    monkeypatch.setattr(auth, "authorize", deny_admin)
    monkeypatch.setattr("nex_api.administrator_mfa.assurance", lambda *_: None)
    started = browser.client.get("/api/v1/auth/start")
    first_state = parse_qs(urlsplit(started.headers["location"]).query)["state"][0]
    stepped = browser.client.get("/api/v1/auth/callback?code=unit&state=" + first_state)
    state = parse_qs(urlsplit(stepped.headers["location"]).query)["state"][0]
    final = browser.client.get("/api/v1/auth/callback?code=unit&state=" + state)
    assert final.status_code == 303
    assert "auth_error=MFA_REQUIRED" in final.headers["location"]
    assert browser.provider.authorization.await_count == 2
    assert browser.client.cookies.get(SESSION_COOKIE) is None
