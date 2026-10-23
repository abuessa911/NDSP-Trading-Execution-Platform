import httpx
import pytest

from nex_api.binance_testnet_connector import (
    TESTNET_ORIGIN, ExchangeConnectivityError, probe_testnet_account,
)


@pytest.mark.asyncio
async def test_signed_read_only_testnet_request():
    def respond(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith(TESTNET_ORIGIN + "/fapi/v2/account?")
        assert request.method == "GET"
        assert request.headers["X-MBX-APIKEY"] == "test_key_123456"
        assert "signature=" in str(request.url)
        assert "live" not in str(request.url)
        return httpx.Response(200, json={"assets": []})
    result = await probe_testnet_account(
        "test_key_123456", "test_secret", timestamp_ms=1700000000000,
        transport=httpx.MockTransport(respond),
    )
    assert result.authenticated
    assert not result.can_place_orders


@pytest.mark.asyncio
async def test_rejects_bad_credentials_before_network():
    with pytest.raises(ExchangeConnectivityError, match="INVALID_TESTNET"):
        await probe_testnet_account("bad", "", timestamp_ms=1700000000000)


@pytest.mark.asyncio
async def test_sanitizes_auth_failures():
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="Sensitive detail")
    with pytest.raises(ExchangeConnectivityError, match="TESTNET_AUTH_REJECTED") as result:
        await probe_testnet_account(
            "test_key_123456", "secret", timestamp_ms=1700000000000,
            transport=httpx.MockTransport(respond),
        )
    assert "Sensitive detail" not in str(result.value)
