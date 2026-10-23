"""Current documented USD-M contracts, using real HTTP transport validation offline."""
from decimal import Decimal
import time

import httpx
import pytest

from nex_api import hunter_live_executor as executor
from nex_api import hunter_testnet_reconcile as reconcile

SYMBOL = "BTCUSDT"


def payloads():
    return {
        "/fapi/v1/time": {"serverTime": int(time.time()*1000)},
        "/fapi/v1/accountConfig": {
            "canTrade": True, "dualSidePosition": False, "multiAssetsMargin": False,
        },
        "/fapi/v1/symbolConfig": [{"symbol": SYMBOL, "marginType": "CROSSED",
            "isAutoAddMargin": False, "leverage": 1, "maxNotionalValue": "1000000"}],
        # V3 account does not carry the account configuration flags.
        "/fapi/v3/account": {"totalMarginBalance": "1000", "positions": []},
        # V3 returns only symbols with positions/orders; a flat result may be empty.
        "/fapi/v3/positionRisk": [],
        "/fapi/v1/openOrders": [],
        "/fapi/v1/openAlgoOrders": [],
    }


def exchange(data, mode="testnet"):
    calls = []
    def handle(request):
        calls.append(request)
        assert request.method == "GET", "These tests must never issue an exchange mutation"
        assert request.url.path in data
        if request.url.path != "/fapi/v1/time":
            assert "signature" in request.url.params
        return httpx.Response(200, json=data[request.url.path])
    return executor.Exchange(mode, "SYNTHETIC_KEY", "SYNTHETIC_SECRET",
                             transport=httpx.MockTransport(handle)), calls


def test_current_v3_empty_position_is_flat_only_with_verified_configuration():
    ex, calls = exchange(payloads())
    try:
        assert executor.account_snapshot(ex, SYMBOL) == (Decimal("1000"), Decimal(0), Decimal(0))
        assert "/fapi/v1/symbolConfig" in [r.url.path for r in calls]
        assert "/fapi/v1/accountConfig" in [r.url.path for r in calls]
    finally:
        ex.close()


def test_leverage_comes_from_symbol_config_and_not_an_extra_v3_field():
    data = payloads()
    data["/fapi/v1/symbolConfig"][0]["leverage"] = 20
    ex, _ = exchange(data)
    try:
        assert executor.account_snapshot(ex, SYMBOL, required_leverage=20)[1] == 0
        with pytest.raises(executor.Halt, match="LEVERAGE_MISMATCH"):
            executor.account_snapshot(ex, SYMBOL, required_leverage=1)
    finally:
        ex.close()


@pytest.mark.parametrize("field,value", [
    ("dualSidePosition", True), ("dualSidePosition", "false"),
    ("multiAssetsMargin", True), ("multiAssetsMargin", None), ("canTrade", False),
])
def test_unsupported_or_unproved_account_mode_is_not_assumed(field, value):
    data = payloads()
    data["/fapi/v1/accountConfig"][field] = value
    ex, _ = exchange(data)
    try:
        with pytest.raises(executor.Halt):
            executor.account_snapshot(ex, SYMBOL)
    finally:
        ex.close()


@pytest.mark.parametrize("config", [[], None, [{"symbol": "ETHUSDT"}],
    [{"symbol": SYMBOL, "leverage": 1}],
])
def test_missing_symbol_configuration_does_not_prove_a_flat_account(config):
    data = payloads()
    data["/fapi/v1/symbolConfig"] = config
    ex, _ = exchange(data)
    try:
        with pytest.raises(executor.Halt):
            executor.account_snapshot(ex, SYMBOL)
    finally:
        ex.close()


def test_flat_v3_cannot_hide_a_nonzero_account_position():
    data = payloads()
    data["/fapi/v3/account"]["positions"] = [{"symbol": SYMBOL,
        "positionSide": "BOTH", "positionAmt": "0.1"}]
    ex, _ = exchange(data)
    try:
        with pytest.raises(executor.Halt, match="POSITION.*MISMATCH"):
            executor.account_snapshot(ex, SYMBOL)
    finally:
        ex.close()


def test_signed_short_amount_is_parsed_without_becoming_a_positive_long():
    data = payloads()
    position = {"symbol": SYMBOL, "positionSide": "BOTH", "positionAmt": "-0.1",
                "marginAsset": "USDT"}
    data["/fapi/v3/positionRisk"] = [position]
    data["/fapi/v3/account"]["positions"] = [position]
    ex, _ = exchange(data)
    try:
        assert executor.account_snapshot(ex, SYMBOL)[1:] == (Decimal(".1"), Decimal("-.1"))
        with pytest.raises(executor.Halt, match="SHORT"):
            reconcile.get_position(ex, SYMBOL)
    finally:
        ex.close()


def test_duplicate_or_wrong_symbol_position_inventory_is_rejected():
    for rows in [[{"symbol": "ETHUSDT"}], [
        {"symbol": SYMBOL, "positionSide": "BOTH", "positionAmt": "0", "marginAsset": "USDT"}
    ]*2]:
        data = payloads()
        data["/fapi/v3/positionRisk"] = rows
        ex, _ = exchange(data)
        try:
            with pytest.raises(executor.Halt):
                executor.account_snapshot(ex, SYMBOL)
        finally:
            ex.close()


def test_reconciliation_accepts_documented_empty_flat_inventory():
    ex, _ = exchange(payloads())
    try:
        assert reconcile.get_position(ex, SYMBOL) == 0
    finally:
        ex.close()


@pytest.mark.parametrize("path,signed", [
    ("https://other.example/fapi/v3/account", True),
    ("//other.example/fapi/v3/account", True),
    ("/sapi/v1/capital/withdraw/apply", True),
    ("/fapi/v3/account?url=https://other.example", True),
    ("/fapi/v3/account", False),
])
def test_unapproved_read_route_is_rejected_before_credential_transmission(path, signed):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(200, json={})
    ex = executor.Exchange("testnet", "KEY", "SECRET", transport=httpx.MockTransport(handle))
    try:
        with pytest.raises(executor.Halt):
            ex._call("GET", path, signed=signed)
        assert calls == []
    finally:
        ex.close()


def test_mutating_mode_cannot_turn_a_mainnet_client_into_a_testnet_writer():
    calls = []
    ex = executor.Exchange("mainnet", "KEY", "SECRET", transport=httpx.MockTransport(
        lambda request: calls.append(request) or httpx.Response(200, json={})))
    ex.mode = "testnet"
    try:
        with pytest.raises(executor.Halt):
            ex.signed_post("/fapi/v1/order", symbol=SYMBOL)
        assert calls == []
    finally:
        ex.close()


def test_explicit_margin_preference_is_verified_without_changing_exchange_settings():
    ex, calls = exchange(payloads())
    try:
        with pytest.raises(executor.Halt, match="MARGIN_MODE_MISMATCH"):
            executor.account_snapshot(ex, SYMBOL, required_margin_mode="ISOLATED")
        assert executor.account_snapshot(ex, SYMBOL, required_margin_mode="CROSS")[1] == 0
        assert all(request.method == "GET" for request in calls)
    finally:
        ex.close()


def test_mutating_client_base_url_cannot_send_credentials_to_another_host():
    calls = []
    ex = executor.Exchange("testnet", "KEY", "SECRET", transport=httpx.MockTransport(
        lambda request: calls.append(request) or httpx.Response(200, json={})))
    ex.client.base_url = "https://other.example"
    try:
        with pytest.raises(executor.Halt, match="ORIGIN_CHANGED"):
            ex.signed_get("/fapi/v3/account")
        assert not calls
    finally:
        ex.close()


def test_other_account_position_requires_reconciliation_before_new_entry():
    data = payloads()
    data["/fapi/v3/account"]["positions"] = [{"symbol": "ETHUSDT",
        "positionSide": "BOTH", "positionAmt": "1"}]
    ex, _ = exchange(data)
    try:
        with pytest.raises(executor.Halt, match="UNTRACKED_ACCOUNT_POSITION"):
            executor.account_snapshot(ex, SYMBOL)
    finally:
        ex.close()
