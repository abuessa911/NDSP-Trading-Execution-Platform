"""Mainnet key acceptance must never imply order authority."""
import httpx
import pytest

from nex_api.binance_live_readonly_connector import (
    FUTURES_ORIGIN, WALLET_ORIGIN, LiveConnectivityError,
    probe_live_readonly_account,
)

KEY = "real_readonly_key123"
SECRET = "test_only_secret_do_not_use_on_exchange"

PERMISSIONS = {
    "enableReading": True,
    "ipRestrict": True,
    "enableWithdrawals": False,
    "enableSpotAndMarginTrading": False,
    "enableFutures": False,
    "enableMargin": False,
    "enableInternalTransfer": False,
    "permitsUniversalTransfer": False,
    "enablePortfolioMarginTrading": False,
    "enableVanillaOptions": False,
    "enableFixApiTrade": False,
}


@pytest.mark.asyncio
async def test_live_signed_get_checks_permissions_and_futures_read_only():
    calls = []

    def respond(req: httpx.Request) -> httpx.Response:
        calls.append(str(req.url))
        assert req.method == "GET"
        assert req.headers["X-MBX-APIKEY"] == KEY
        assert "timestamp=1700000000000" in str(req.url)
        assert "signature=" in str(req.url)
        if str(req.url).startswith(WALLET_ORIGIN + "/sapi/v1/account/apiRestrictions?"):
            return httpx.Response(200, json=PERMISSIONS)
        assert str(req.url).startswith(FUTURES_ORIGIN + "/fapi/v3/account?")
        return httpx.Response(200, json={"assets": []})

    result = await probe_live_readonly_account(
        KEY, SECRET, timestamp_ms=1700000000000,
        transport=httpx.MockTransport(respond)
    )
    assert result.authenticated and result.ip_restricted
    assert result.read_only_permission_verified
    assert result.can_place_orders is False
    assert len(calls) == 2
    assert all(SECRET not in url and KEY not in url for url in calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("overrides,code", [
    ({"ipRestrict": False}, "LIVE_IP_ALLOWLIST_REQUIRED"),
    ({"enableFutures": True}, "LIVE_PRIVILEGED_KEY_REJECTED"),
    ({"enableWithdrawals": True}, "LIVE_PRIVILEGED_KEY_REJECTED"),
    ({"enableReading": False}, "LIVE_READ_ACCESS_REQUIRED"),
    ({"enableSpotAndMarginTrading": True}, "LIVE_PRIVILEGED_KEY_REJECTED"),
    ({"enableInternalTransfer": True}, "LIVE_PRIVILEGED_KEY_REJECTED"),
    ({"enableFixApiTrade": True}, "LIVE_PRIVILEGED_KEY_REJECTED"),
    ({"enableMargin": None}, "LIVE_PRIVILEGED_KEY_REJECTED"),
])
async def test_rejects_any_unverified_or_privileged_key_before_futures_call(overrides, code):
    calls = []
    def respond(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        return httpx.Response(200, json=PERMISSIONS | overrides)

    with pytest.raises(LiveConnectivityError, match=code):
        await probe_live_readonly_account(
            KEY, SECRET, timestamp_ms=1700000000000,
            transport=httpx.MockTransport(respond),
        )
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_mainnet_failure_never_leaks_response_body():
    def respond(req: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="secret-from-upstream")
    with pytest.raises(LiveConnectivityError, match="LIVE_AUTH_REJECTED") as info:
        await probe_live_readonly_account(
            KEY, SECRET, transport=httpx.MockTransport(respond),
            timestamp_ms=1700000000000,
        )
    assert "secret-from-upstream" not in str(info.value)


@pytest.mark.asyncio
async def test_rejects_bad_key_without_http():
    with pytest.raises(LiveConnectivityError, match="INVALID_LIVE_CREDENTIAL"):
        await probe_live_readonly_account("bad", SECRET)
