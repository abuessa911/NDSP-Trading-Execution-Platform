"""Offline security and lifecycle tests: never contact Binance."""
from __future__ import annotations
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from nex_api import hunter_live_executor as legacy
from nex_api import hunter_m5_testnet_pilot as m5
from nex_api import hunter_testnet_reconcile as m4

ENTRY = "HK1" + "a"*24
EXIT = "HK1" + "b"*24


def config(mode="testnet", **updates):
    output = {
        "symbol": "BTCUSDT", "strategy": legacy.STRATEGY, "mode": mode,
        "daily_loss_pct": "1.5", "trade_risk_pct": "0.5",
        "max_exposure_pct": "5", "stop_pct": "1"
    }
    output.update(updates)
    return output


class ExchangeFake:
    key = "testnet-key"
    def __init__(self, **overrides):
        self.calls = []
        self.options = overrides

    def signed_get(self, path, **kwargs):
        self.calls.append(("GET", path, kwargs))
        if path == "/fapi/v1/positionSide/dual":
            return {"dualSidePosition": False}
        if path == "/fapi/v3/account":
            return {"totalMarginBalance": "1000", "positions": []}
        if path == "/fapi/v1/accountConfig":
            return {"canTrade": True, "dualSidePosition": False, "multiAssetsMargin": False}
        if path == "/fapi/v1/symbolConfig":
            return [{"symbol": "BTCUSDT", "leverage": 1, "marginType": "CROSSED",
                     "isAutoAddMargin": False, "maxNotionalValue": "1000000"}]
        if path == "/fapi/v3/positionRisk":
            return [{"symbol": "BTCUSDT", "positionAmt": "0",
                     "positionSide": "BOTH", "marginAsset": "USDT"}]
        if path in ("/fapi/v1/openOrders", "/fapi/v1/openAlgoOrders"):
            return []
        raise AssertionError(path)

    def get(self, path, **kwargs):
        self.calls.append(("GET", path, kwargs))
        if path == "/fapi/v1/time":
            import time
            return {"serverTime": int(time.time()*1000)}
        if path == "/fapi/v1/exchangeInfo":
            return {"symbols": [{"symbol":"BTCUSDT","status":"TRADING",
                 "contractType":"PERPETUAL","quoteAsset":"USDT","filters":[
                    {"filterType":"MARKET_LOT_SIZE","stepSize":"0.001","minQty":"0.001"},
                    {"filterType":"PRICE_FILTER","tickSize":"0.1"},
                    {"filterType":"MIN_NOTIONAL","notional":"5"}
                 ]}]}
        raise AssertionError(path)


class TestM5(unittest.TestCase):
    def test_pilot_is_testnet_only_even_if_live_flag_set(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"config.json"
            path.write_text(json.dumps(config(mode="mainnet", mainnet_enabled=True)))
            path.chmod(0o600)
            with self.assertRaisesRegex(legacy.Halt, "M5_TESTNET_ONLY"):
                m5.load_config(path)

    def test_testnet_with_live_flag_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"config.json"
            path.write_text(json.dumps(config(mainnet_enabled=True)))
            path.chmod(0o600)
            with self.assertRaisesRegex(legacy.Halt, "MAINNET_FLAG_FORBIDDEN"):
                m5.load_config(path)

    def test_no_default_risk_policy(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"config.json"
            cfg=config()
            del cfg["daily_loss_pct"]
            path.write_text(json.dumps(cfg))
            path.chmod(0o600)
            with self.assertRaisesRegex(legacy.Halt, "CONFIG_INCOMPLETE"):
                m5.load_config(path)

    def test_config_world_readable_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"config.json"
            path.write_text(json.dumps(config()))
            path.chmod(0o644)
            with self.assertRaisesRegex(legacy.Halt, "PRIVATE_FILE_PERMISSIONS"):
                m5.load_config(path)

    def test_symlink_config_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            real=Path(d)/"secret"
            real.write_text(json.dumps(config()))
            real.chmod(0o600)
            link=Path(d)/"link"
            link.symlink_to(real)
            with self.assertRaisesRegex(legacy.Halt, "SYMLINK_FORBIDDEN"):
                m5.load_config(link)

    def test_no_trade_without_approval(self):
        state={}
        ex=ExchangeFake()
        with patch.dict(os.environ, {"HUNTER_M5_TESTNET_CONFIRM": "NO"}):
            with self.assertRaisesRegex(legacy.Halt, "APPROVAL"):
                m5.perform("entry-testnet", config(),Path("/unused"),state,ex)
        self.assertEqual(ex.calls, [])

    def test_testnet_preflight_readonly(self):
        result=m5.preflight(ExchangeFake(),config(),{})
        self.assertEqual(result["status"], "TESTNET_ACCOUNT_AND_MARKET_READABLE")
        self.assertIs(result["network_writes"], False)
        self.assertIs(result["mainnet_order_execution"], False)

    def test_preflight_has_no_order_writes(self):
        ex=ExchangeFake()
        m5.preflight(ex,config(),{})
        self.assertTrue(ex.calls)
        self.assertTrue(all(x[0]=="GET" for x in ex.calls))

    def test_preflight_blocks_daily_limit(self):
        state={"account": hashlib.sha256(b"testnet-key").hexdigest(),
               "date":legacy.day(),"opening":"1000","daily_pct":"1.5"}
        class LowerEquity(ExchangeFake):
            def signed_get(self, path, **params):
                result=super().signed_get(path,**params)
                if path=="/fapi/v3/account":
                    result["totalMarginBalance"]="900"
                return result
        with self.assertRaisesRegex(legacy.Halt,"DAILY_LOSS_LIMIT_REACHED"):
            m5.preflight(LowerEquity(),config(),state)

    def test_cannot_increase_limit_during_day(self):
        state={"account": hashlib.sha256(b"testnet-key").hexdigest(),
               "date":legacy.day(),"opening":"1000","daily_pct":"0.5"}
        with self.assertRaisesRegex(legacy.Halt, "CANNOT_INCREASE"):
            m5.preflight(ExchangeFake(),config(),state)

    def test_pending_requires_reconciliation(self):
        state={"pending_order":{"id":ENTRY, "signal":"ENTER_LONG","created":1}}
        with self.assertRaisesRegex(legacy.Halt, "RECONCILE_BEFORE"):
            m5.perform("dry-run",config(),Path("/unused"),state,ExchangeFake())

    def test_state_halt_is_sticky(self):
        with self.assertRaisesRegex(legacy.Halt,"HALTED"):
            m5.check_state({"halted":True})

    def test_private_state_dir_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/"state.json"
            Path(d).chmod(0o755)
            with ExitStack() as s:
                with self.assertRaisesRegex(legacy.Halt, "STATE_DIRECTORY_PERMISSIONS"):
                    m5.lock_state(state,s)

    def test_status_does_not_need_credentials(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            state_dir=root/"private"
            state_dir.mkdir(mode=0o700)
            conf=root/"config.json"
            safety=root/"safety.env"
            conf.write_text(json.dumps(config()))
            conf.chmod(0o600)
            safety.write_text("LIVE_TRADING_ENABLED=false\nGLOBAL_KILL_SWITCH=true\n")
            safety.chmod(0o600)
            with patch.dict(os.environ, {k:"" for k in m5.SECRET_VARS}):
                self.assertEqual(m5.cli(["--config",str(conf),"--state",
                               str(state_dir/"position.json"),
                               "--safety-config",str(safety),
                               "--action","status"]),0)

    def test_unknown_account_state_rejected(self):
        bad={"active_position":{"id":"BAD", "quantity":"0.1"}}
        with self.assertRaisesRegex(legacy.Halt,"ACTIVE_POSITION_UNRECOGNIZED"):
            m5.check_state(bad)

    def test_m4_exit_still_reduce_only(self):
        calls=[]
        class Ex:
            def signed_post(self,path, **kwargs):
                calls.append((path, kwargs))
                return {"ok":True}
        m4.send_exit(Ex(), config(),EXIT,"0.1")
        self.assertEqual(calls[0][1]["reduceOnly"],"true")

    def test_mainnet_exchange_never_writes(self):
        ex=legacy.Exchange("mainnet","FAKE_KEY","FAKE_SECRET")
        try:
            with self.assertRaisesRegex(legacy.Halt,"MAINNET_ORDER_WRITES_NOT_RELEASED"):
                ex.signed_post("/fapi/v1/order", symbol="BTCUSDT")
        finally:
            ex.close()

    def test_reconcile_is_only_action_that_commits_verified_state(self):
        # Tests M4's protection evidence -> persistent local transition.
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/"state.json"
            old={"pending_order":{"id":ENTRY,"signal":"ENTER_LONG","created":1},
                 "account":"fingerprint"}
            result=m4.reconcile(state,old,{"status":"ENTRY_PROTECTED_CONFIRMED",
                                           "quantity":"0.1"})
            self.assertTrue(result)
            new=legacy.load_json(state)
            self.assertIsNone(new["pending_order"])
            self.assertEqual(new["active_position"]["quantity"],"0.1")

    def test_env_guard_must_be_exact(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"guard.env"
            path.write_text("LIVE_TRADING_ENABLED=false\nGLOBAL_KILL_SWITCH=false\n")
            path.chmod(0o600)
            with self.assertRaisesRegex(legacy.Halt,"GLOBAL_MAINNET_KILL_SWITCH"):
                m5.validate_guards(path)


if __name__ == "__main__":
    unittest.main()
