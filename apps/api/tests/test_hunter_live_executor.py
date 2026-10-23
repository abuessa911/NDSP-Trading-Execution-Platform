import json
import os
from decimal import Decimal as D
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import httpx
import importlib.util
HERE = Path(__file__).resolve().parent
MODULE_FILE = HERE / "hunter_live_executor.py"
if not MODULE_FILE.is_file():
    MODULE_FILE = HERE.parent / "nex_api" / "hunter_live_executor.py"
SPEC = importlib.util.spec_from_file_location("_hunter_executor_under_test", MODULE_FILE)
h = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(h)

class RiskTests(unittest.TestCase):
    def test_fractional_loss_percentage(self):
        self.assertEqual(h.pct("1.25"),D("1.25"))
    def test_bad_percentage(self):
        for x in ("0","101","NaN","Infinity",-1,True):
            with self.assertRaises(h.Halt): h.pct(x)
    def test_qty_calculation(self):
        q=h.exposure_plan("1000","1000","2","0.5","10","100","95",".01",".01","5")
        self.assertEqual(q,D("1"))
    def test_daily_drawdown_halt(self):
        with self.assertRaisesRegex(h.Halt,"DAILY_LOSS_LIMIT_REACHED"):
            h.exposure_plan("900","1000","2","0.5","10","100","95",".01",".01","5")
    def test_stop_not_under_entry(self):
        with self.assertRaisesRegex(h.Halt,"RISK_CONFIGURATION_REJECTED"):
            h.exposure_plan("1000","1000","2","1","10","100","101",".01",".01","5")
    def test_minimum_too_large(self):
        with self.assertRaisesRegex(h.Halt,"ORDER_BELOW_EXCHANGE_MINIMUM"):
            h.exposure_plan("100","100","2","1","1","100","99",".001",".001","10")
    def test_reject_negative_and_nan(self):
        for x in ("NaN","Inf","-0.5"):
            with self.assertRaises(h.Halt): h.D(x)
    def test_quantization(self):
        self.assertEqual(h.quantize_down("0.123","0.005"),D("0.12"))
    def test_no_strategy_default(self):
        with self.assertRaisesRegex(h.Halt,"CONFIG_INCOMPLETE"):
            h.require_config({})
    def test_reject_unapproved_strategy(self):
        cfg=dict(symbol="BTCUSDT",strategy="random",daily_loss_pct=2,
            trade_risk_pct=1,max_exposure_pct=10,stop_pct=1,mode="testnet")
        with self.assertRaisesRegex(h.Halt,"STRATEGY_NOT_EXPLICITLY_SELECTED"):
            h.require_config(cfg)
    def test_reject_mainnet_without_explicit_flag(self):
        cfg=dict(symbol="BTCUSDT",strategy=h.STRATEGY,daily_loss_pct=2,
            trade_risk_pct=1,max_exposure_pct=10,stop_pct=1,mode="mainnet")
        with self.assertRaisesRegex(h.Halt,"MAINNET_DISABLED"):
            h.require_config(cfg)
    def test_reject_risk_increase_after_baseline(self):
        prev=dict(account=h.hashlib.sha256(b"APIKEY").hexdigest(),
                  date=h.day(),opening="1000", daily_pct="2")
        with self.assertRaisesRegex(h.Halt,"CANNOT_INCREASE"):
            h.guarded_state(prev,"APIKEY",D("1000"),h.day(),"5")
    def test_never_reset_pending_overnight(self):
        prev=dict(pending_order=dict(id="x"),date="2026-01-01",opening="1000")
        with self.assertRaisesRegex(h.Halt,"UNRECONCILED"):
            h.guarded_state(prev,"APIKEY",D("1100"),h.day(),"2")
    def test_key_rotation_block(self):
        with self.assertRaisesRegex(h.Halt,"ACCOUNT_CHANGED"):
            h.guarded_state({"account":"other"}, "APIKEY",D("1000"),h.day(),"2")
    def test_emacross_straight_bull(self):
        self.assertFalse(h.crossed_up([D(i) for i in range(1,122)]))
    def test_state_persist_no_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"state.json"
            h.save_state(path,{"last_signal_candle":123})
            self.assertEqual(h.load_json(path),{"last_signal_candle":123})
            self.assertEqual(path.stat().st_mode & 0o777,0o600)

class ExchangeTests(unittest.TestCase):
    def test_mainnet_post_unconditionally_blocked(self):
        calls=[]
        def handler(req):
            calls.append(req)
            return httpx.Response(200,json={})
        ex=h.Exchange("mainnet","KEY","SECRET",transport=httpx.MockTransport(handler))
        with self.assertRaisesRegex(h.Halt,"MAINNET_ORDER_WRITES_NOT_RELEASED"):
            ex.signed_post("/fapi/v1/order",symbol="BTCUSDT")
        self.assertEqual(calls,[])
        ex.close()
    def test_only_allowlisted_post(self):
        ex=h.Exchange("testnet","KEY","SECRET",transport=httpx.MockTransport(lambda req: httpx.Response(200,json={})))
        with self.assertRaisesRegex(h.Halt,"ORDER_ROUTE_FORBIDDEN"):
            ex.signed_post("/sapi/v1/capital/withdraw/apply")
        ex.close()
    def test_signed_get(self):
        def handler(req):
            self.assertEqual(req.url.host,"demo-fapi.binance.com")
            self.assertIn("signature",req.url.params)
            self.assertEqual(req.headers.get("X-MBX-APIKEY"),"KEY")
            return httpx.Response(200,json={"dualSidePosition":False})
        ex=h.Exchange("testnet","KEY","SECRET",transport=httpx.MockTransport(handler))
        self.assertFalse(ex.signed_get("/fapi/v1/positionSide/dual")["dualSidePosition"])
        ex.close()
    def test_error_never_includes_response(self):
        ex=h.Exchange("testnet","KEY","SECRET",transport=httpx.MockTransport(
            lambda req:httpx.Response(400,text="PRIVATE ACCOUNT DATA")))
        with self.assertRaisesRegex(h.Halt,"EXCHANGE_REQUEST_REJECTED"):
            ex.signed_get("/fapi/v3/account")
        ex.close()
    def test_no_redirect(self):
        ex=h.Exchange("testnet","KEY","SECRET",transport=httpx.MockTransport(
            lambda req:httpx.Response(302,headers={"Location":"https://evil.example"})))
        with self.assertRaises(h.Halt):
            ex.get("/fapi/v1/time")
        ex.close()
    def test_testnet_post_signs(self):
        def handler(req):
            self.assertEqual(req.url.host,"demo-fapi.binance.com")
            self.assertIn(b"signature=",req.content)
            return httpx.Response(200,json={"algoId":123})
        ex=h.Exchange("testnet","KEY","SECRET",transport=httpx.MockTransport(handler))
        self.assertEqual(ex.signed_post("/fapi/v1/algoOrder",symbol="BTCUSDT")["algoId"],123)
        ex.close()

if __name__=="__main__":
    unittest.main()
