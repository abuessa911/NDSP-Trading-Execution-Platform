"""Entire private CLI lifecycle against an in-process USD-M exchange fixture.

No socket/network transport, real key, Binance account or exchange order is used.
The actual signer, executor, config validation, locks and durable state are used.
"""
from decimal import Decimal
import hashlib
import hmac
import json
from pathlib import Path
import time
from urllib.parse import parse_qsl, urlencode

import httpx
import pytest

from nex_api import hunter_live_executor as engine
from nex_api import hunter_m5_testnet_pilot as pilot

ROOT = Path(__file__).resolve().parents[3]
KEY = "SYNTHETIC_DEMO_KEY"
SECRET = "SYNTHETIC_DEMO_SECRET"


class ExchangeFixture:
    def __init__(self, state_path):
        self.state_path = state_path
        self.quantity = Decimal(0)
        self.mark = Decimal("110")
        self.orders = {}
        self.stop = None
        self.calls = []
        self.lost_entry_ack = False
        self.mutations = []

    def handle(self, request):
        assert request.url.host == "demo-fapi.binance.com"
        path, method = request.url.path, request.method
        params = dict(parse_qsl(request.content.decode())) if method == "POST" else dict(request.url.params)
        self.calls.append((method, path))
        public = path in ("/fapi/v1/time", "/fapi/v1/exchangeInfo", "/fapi/v1/klines", "/fapi/v1/premiumIndex")
        if public:
            assert "x-mbx-apikey" not in request.headers
        else:
            assert request.headers["X-MBX-APIKEY"] == KEY
            signature = params.pop("signature")
            expected = hmac.new(SECRET.encode(), urlencode(params).encode(), hashlib.sha256).hexdigest()
            assert hmac.compare_digest(signature, expected)
            assert abs(int(params["timestamp"])-int(time.time()*1000)) < 5000
        if method == "GET":
            return self.read(path, params)
        state = engine.load_json(self.state_path)
        assert state["pending_order"], "Write-ahead intent must exist before any mutation"
        pending = state["pending_order"]
        if method == "POST" and path == "/fapi/v1/algoOrder":
            assert params["clientAlgoId"] == pending["id"]+"s"
            assert self.quantity == 0 and self.stop is None
            assert params["side"] == "SELL" and params["closePosition"] == "true"
            assert params["workingType"] == "MARK_PRICE"
            self.stop = {"symbol": "BTCUSDT", "algoId": 101,
                "clientAlgoId": params["clientAlgoId"], "side": "SELL", "positionSide": "BOTH",
                "orderType": "STOP_MARKET", "algoStatus": "NEW", "closePosition": True,
                "workingType": "MARK_PRICE", "triggerPrice": params["triggerPrice"]}
            assert 0 < Decimal(self.stop["triggerPrice"]) < self.mark
            self.mutations.append("PROTECTIVE_STOP")
            return httpx.Response(200, json=self.stop)
        if method == "POST" and path == "/fapi/v1/order":
            quantity = Decimal(params["quantity"])
            client_id = params["newClientOrderId"]
            assert quantity > 0 and client_id not in self.orders
            assert self.stop and self.stop["algoStatus"] == "NEW"
            if params["side"] == "BUY":
                assert self.quantity == 0 and client_id == pending["id"]+"e"
                self.quantity = quantity
                self.mutations.append("ENTRY_FILLED")
            else:
                assert params["side"] == "SELL" and params["reduceOnly"] == "true"
                assert quantity == self.quantity and client_id == pending["id"]+"x"
                self.quantity = Decimal(0)
                self.mutations.append("REDUCE_ONLY_EXIT_FILLED")
            receipt = {"symbol": "BTCUSDT", "clientOrderId": client_id,
                "orderId": len(self.orders)+1, "side": params["side"], "type": "MARKET",
                "positionSide": "BOTH", "status": "FILLED", "executedQty": str(quantity),
                "reduceOnly": params.get("reduceOnly") == "true", "avgPrice": str(self.mark)}
            self.orders[client_id] = receipt
            if params["side"] == "BUY" and self.lost_entry_ack:
                raise httpx.ReadTimeout("SYNTHETIC_LOST_ACKNOWLEDGEMENT", request=request)
            return httpx.Response(200, json=receipt)
        if method == "DELETE" and path == "/fapi/v1/algoOrder":
            assert self.quantity == 0 and state["stop_cleanup_attempted"] is True
            assert params["clientAlgoId"] == self.stop["clientAlgoId"]
            self.stop["algoStatus"] = "CANCELED"
            self.mutations.append("ORPHAN_STOP_CANCELED")
            return httpx.Response(200, json={"code": 200})
        raise AssertionError((method, path))

    def read(self, path, params):
        active_stop = self.stop is not None and self.stop["algoStatus"] == "NEW"
        position = {"symbol": "BTCUSDT", "positionSide": "BOTH",
                    "positionAmt": str(self.quantity), "marginAsset": "USDT"}
        data = {
            "/fapi/v1/time": {"serverTime": int(time.time()*1000)},
            "/fapi/v1/accountConfig": {"canTrade": True, "dualSidePosition": False, "multiAssetsMargin": False},
            "/fapi/v1/symbolConfig": [{"symbol": "BTCUSDT", "leverage": 1, "marginType": "CROSSED",
                "isAutoAddMargin": False, "maxNotionalValue": "1000000"}],
            "/fapi/v3/account": {"totalMarginBalance": "1000", "positions": [position] if self.quantity else []},
            "/fapi/v3/positionRisk": [position] if self.quantity or active_stop else [],
            "/fapi/v1/openOrders": [],
            "/fapi/v1/openAlgoOrders": [self.stop] if active_stop else [],
            "/fapi/v1/premiumIndex": {"markPrice": str(self.mark)},
            "/fapi/v1/commissionRate": {"symbol": "BTCUSDT", "takerCommissionRate": "0.0005"},
            "/fapi/v1/exchangeInfo": {"symbols": [{"symbol": "BTCUSDT", "status": "TRADING",
                "contractType": "PERPETUAL", "quoteAsset": "USDT", "filters": [
                    {"filterType": "MARKET_LOT_SIZE", "stepSize": "0.001", "minQty": "0.001"},
                    {"filterType": "PRICE_FILTER", "tickSize": "0.1"},
                    {"filterType": "MIN_NOTIONAL", "notional": "5"}]}]},
        }
        if path == "/fapi/v1/algoOrder":
            assert self.stop and params["clientAlgoId"] == self.stop["clientAlgoId"]
            return httpx.Response(200, json=self.stop)
        if path == "/fapi/v1/order":
            receipt = self.orders.get(params["origClientOrderId"])
            return httpx.Response(200 if receipt else 404, json=receipt or {"code": -2013})
        if path == "/fapi/v1/klines":
            assert params["interval"] == "1h" and params["symbol"] == "BTCUSDT"
            span = 3600000
            end = int(time.time()*1000)//span*span
            values = [Decimal("100")]*116+[Decimal("99")]*3+[Decimal("110")]
            assert engine.crossed_up(values)
            rows = []
            for i, close in enumerate(values):
                opened = end-(120-i)*span
                rows.append([opened, str(close), str(close), str(close), str(close), "10", opened+span-1])
            return httpx.Response(200, json=rows)
        assert path in data
        return httpx.Response(200, json=data[path])


@pytest.fixture
def environment(tmp_path, monkeypatch, capsys):
    directory = tmp_path/"private"
    directory.mkdir(mode=0o700)
    config = directory/"config.json"
    config.write_text((ROOT/"infra/testing/hunter-testnet-pilot.json").read_text())
    config.chmod(0o600)
    guards = directory/"safety.env"
    guards.write_text("LIVE_TRADING_ENABLED=false\nGLOBAL_KILL_SWITCH=true\n")
    guards.chmod(0o600)
    state = directory/"state.json"
    venue = ExchangeFixture(state)
    actual_exchange = engine.Exchange
    def connector(mode, key, secret):
        assert mode == "testnet" and key == KEY and secret == SECRET
        return actual_exchange(mode, key, secret, transport=httpx.MockTransport(venue.handle))
    monkeypatch.setattr(engine, "Exchange", connector)
    monkeypatch.setenv("HUNTER_EXEC_API_KEY", KEY)
    monkeypatch.setenv("HUNTER_EXEC_API_SECRET", SECRET)
    monkeypatch.setenv("HUNTER_M5_TESTNET_CONFIRM", pilot.APPROVAL)
    def run(action):
        result = pilot.cli(["--config", str(config), "--state", str(state),
                            "--safety-config", str(guards), "--action", action])
        assert result == 0
        output = capsys.readouterr().out
        return json.loads(output)
    return venue, state, run


def test_complete_cli_entry_restart_reconcile_exit_and_cleanup(environment):
    venue, state, run = environment
    assert run("status")["pending"] is False
    assert run("preflight")["status"] == "TESTNET_ACCOUNT_AND_MARKET_READABLE"
    assert run("dry-run")["result"] == {"status": "DRY_RUN", "signal": "ENTER_LONG"}
    assert not venue.mutations
    entry = run("entry-testnet")
    assert entry["result"]["status"] == "ENTRY_SENT_NEEDS_RECONCILIATION"
    assert engine.load_json(state)["pending_order"]["signal"] == "ENTER_LONG"
    count = len(venue.calls)
    with pytest.raises(engine.Halt, match="RECONCILE_BEFORE"):
        run("entry-testnet")
    assert len(venue.calls) == count
    assert run("inspect")["status"] == "ENTRY_PROTECTED_CONFIRMED"
    assert run("reconcile")["state_modified"] is True
    saved = engine.load_json(state)
    assert saved["active_position"] and saved["pending_order"] is None
    # Each CLI action reloads its journal from disk, as after process restart.
    assert run("status")["active"] is True
    assert run("exit-testnet")["status"] == "TESTNET_EXIT_SENT_RECONCILIATION_REQUIRED"
    assert run("inspect")["status"] == "EXIT_FILLED_STOP_STILL_ACTIVE"
    assert run("cleanup-flat-stop")["acknowledged"] is True
    assert run("reconcile")["status"] == "EXIT_FLAT_STOP_GONE"
    assert run("reconcile")["status"] == "NO_TRACKED_TRADE"
    final = run("status")
    assert not final["pending"] and not final["active"] and not final["halted"]
    assert venue.mutations == ["PROTECTIVE_STOP", "ENTRY_FILLED", "REDUCE_ONLY_EXIT_FILLED", "ORPHAN_STOP_CANCELED"]
    assert len(venue.orders) == 2 and venue.quantity == 0
    assert state.stat().st_mode & 0o777 == 0o600
    print("LOCAL_SIGNED_TESTNET_FIXTURE_PASS: protected entry, durable reload, no duplicate, reduce-only exit, stop cleanup, flat")


def test_lost_entry_ack_halts_without_duplicate_and_keeps_protection(environment):
    venue, state, run = environment
    venue.lost_entry_ack = True
    with pytest.raises(engine.Halt, match="CONNECTION_AMBIGUOUS"):
        run("entry-testnet")
    assert len(venue.orders) == 1 and venue.quantity > 0
    assert venue.stop["algoStatus"] == "NEW"
    saved = engine.load_json(state)
    assert saved["halted"] is True and saved["pending_order"]["signal"] == "ENTER_LONG"
    count = len(venue.calls)
    with pytest.raises(engine.Halt, match="HALTED_REQUIRES"):
        run("entry-testnet")
    assert len(venue.calls) == count


def test_no_saved_testnet_credentials_cannot_reach_exchange(environment, monkeypatch):
    venue, state, run = environment
    monkeypatch.delenv("HUNTER_EXEC_API_KEY")
    monkeypatch.delenv("HUNTER_EXEC_API_SECRET")
    with pytest.raises(engine.Halt, match="SEPARATE_BINANCE_DEMO_CREDENTIALS_REQUIRED"):
        run("preflight")
    assert venue.calls == [] and not state.exists()
