"""Offline adversarial regression tests for M4 (no Binance network required)."""
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import httpx

MODULE_DIR = Path(__file__).resolve().parents[1] / "nex_api"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nex_api import hunter_live_executor as legacy
from nex_api import hunter_testnet_reconcile as m4


ENTRY = "HK1" + "a" * 24
EXIT = "HK1" + "b" * 24
SYMBOL = "BTCUSDT"

def cfg(mode="testnet"):
    return {
        "symbol": SYMBOL, "strategy": legacy.STRATEGY, "mode": mode,
        "daily_loss_pct": "1.5", "trade_risk_pct": "0.5",
        "max_exposure_pct": "5", "stop_pct": "1"
    }

def state(pending="ENTER_LONG", active=False, halted=False):
    result = {
        "account": hashlib.sha256(b"TESTKEY").hexdigest(),
        "halted": halted, "opening": "1000", "daily_pct": "1.5",
    }
    if pending:
        result["pending_order"] = {
            "id": EXIT if pending == "EXIT_LONG" else ENTRY,
            "signal": pending, "created": 1,
        }
    if active:
        result["active_position"] = {"id": ENTRY, "quantity": "0.1"}
    return result


class FakeEx:
    key = "TESTKEY"
    def __init__(self, *, qty="0.1", stop_status="NEW", stop_open=True,
                 entry_status="FILLED", exit_status="FILLED",
                 exit_reduce_only=True, extra_ord=False, stop_side="SELL",
                 stop_client=ENTRY+"s", entry_qty="0.1", exit_qty="0.1"):
        self.qty = qty
        self.stop_status = stop_status
        self.stop_open = stop_open
        self.entry_status = entry_status
        self.exit_status = exit_status
        self.exit_reduce_only = exit_reduce_only
        self.extra_ord = extra_ord
        self.stop_side = stop_side
        self.stop_client = stop_client
        self.entry_qty=entry_qty
        self.exit_qty=exit_qty
        self.calls = []
    def signed_get(self, path, **kw):
        self.calls.append(("GET", path, kw))
        if path == "/fapi/v1/accountConfig":
            return {"canTrade": True, "dualSidePosition": False, "multiAssetsMargin": False}
        if path == "/fapi/v1/symbolConfig":
            return [{"symbol": "BTCUSDT", "leverage": 1, "marginType": "CROSSED",
                     "isAutoAddMargin": False, "maxNotionalValue": "1000000"}]
        if path == "/fapi/v3/positionRisk":
            return [{"symbol":SYMBOL,"positionSide":"BOTH",
                     "marginAsset":"USDT","positionAmt":self.qty}]
        if path == "/fapi/v1/openOrders":
            return [{"symbol":SYMBOL,"orderId":99}] if self.extra_ord else []
        if path == "/fapi/v1/openAlgoOrders":
            return ([{"clientAlgoId":self.stop_client}] if self.stop_open else [])
        if path == "/fapi/v1/algoOrder":
            return {"symbol":SYMBOL,"clientAlgoId":self.stop_client,
                    "algoStatus":self.stop_status,"side":self.stop_side,
                    "positionSide":"BOTH","closePosition":True,
                    "workingType":"MARK_PRICE","triggerPrice":"95000",
                    "orderType":"STOP_MARKET"}
        if path == "/fapi/v1/order":
            exiting = kw.get("origClientOrderId") == EXIT + "x"
            return {"symbol":SYMBOL,
                    "clientOrderId":EXIT+"x" if exiting else ENTRY+"e",
                    "status":self.exit_status if exiting else self.entry_status,
                    "side":"SELL" if exiting else "BUY",
                    "type":"MARKET",
                    "executedQty":self.exit_qty if exiting else self.entry_qty,
                    "reduceOnly":self.exit_reduce_only if exiting else False}
        raise AssertionError(path)
    def signed_post(self, path, **kw):
        self.calls.append(("POST",path,kw))
        return {"status":"FILLED"}
    def signed_delete(self, path, **kw):
        self.calls.append(("DELETE",path,kw))
        return {"code":"200"}


class M4Tests(unittest.TestCase):
    def test_only_testnet(self):
        with self.assertRaisesRegex(legacy.Halt,"M4_TESTNET_ONLY"):
            m4.checked_config(cfg("mainnet"))

    def test_no_implicit_strategy(self):
        bad = cfg()
        bad["strategy"] = "range-fade"
        with self.assertRaisesRegex(legacy.Halt,"STRATEGY_NOT_EXPLICITLY_SELECTED"):
            m4.checked_config(bad)

    def test_initial_entry_reconciles_only_with_protection(self):
        evidence=m4.inspect(FakeEx(), cfg(), state())
        self.assertEqual(evidence["status"],"ENTRY_PROTECTED_CONFIRMED")
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"state.json"
            self.assertTrue(m4.reconcile(p,state(),evidence))
            saved=legacy.load_json(p)
            self.assertEqual(saved["active_position"]["quantity"],"0.1")
            self.assertIsNone(saved["pending_order"])

    def test_stale_pending_never_resubmits(self):
        ex=FakeEx()
        m4.inspect(ex,cfg(),state())
        self.assertTrue(all(method=="GET" for method,_,_ in ex.calls))

    def test_unexpected_open_order_rejected(self):
        with self.assertRaisesRegex(legacy.Halt,"UNEXPECTED_OPEN_ORDERS"):
            m4.inspect(FakeEx(extra_ord=True),cfg(),state())

    def test_stop_missing_rejected(self):
        with self.assertRaisesRegex(legacy.Halt,"STOP_INVENTORY_CONFLICT"):
            m4.inspect(FakeEx(stop_open=False),cfg(),state())

    def test_stop_wrong_direction_rejected(self):
        with self.assertRaisesRegex(legacy.Halt,"STOP_NOT_PROVEN_PROTECTIVE"):
            m4.inspect(FakeEx(stop_side="BUY"),cfg(),state())

    def test_partial_entry_rejected(self):
        with self.assertRaisesRegex(legacy.Halt,"ORDER_NOT_PROVEN_FILLED"):
            m4.inspect(FakeEx(entry_status="PARTIALLY_FILLED"),cfg(),state())

    def test_entry_position_mismatch_rejected(self):
        with self.assertRaisesRegex(legacy.Halt,"ENTRY_POSITION_MISMATCH"):
            m4.inspect(FakeEx(qty="0.05"),cfg(),state())

    def test_rotated_credentials_rejected(self):
        s=state()
        s["account"]="different"
        with self.assertRaisesRegex(legacy.Halt,"ACCOUNT_KEY_ROTATION_BLOCKED"):
            m4.inspect(FakeEx(),cfg(),s)

    def test_existing_protected_position(self):
        result=m4.inspect(FakeEx(),cfg(),state(pending=None,active=True))
        self.assertEqual(result["status"],"ACTIVE_PROTECTED_CONFIRMED")

    def test_unprotected_active_position_rejected(self):
        with self.assertRaisesRegex(legacy.Halt,"STOP_INVENTORY_CONFLICT"):
            m4.inspect(FakeEx(stop_open=False),cfg(),state(pending=None,active=True))

    def test_natural_stop_only_when_finished_and_flat(self):
        e=m4.inspect(FakeEx(qty="0",stop_status="FINISHED",stop_open=False),
                     cfg(),state(pending=None,active=True))
        self.assertEqual(e["status"],"STOP_FILLED_FLAT_CONFIRMED")
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)/"s.json"
            self.assertTrue(m4.reconcile(dest,state(pending=None,active=True),e))
            self.assertIsNone(legacy.load_json(dest)["active_position"])

    def test_stale_stop_status_does_not_clear_active(self):
        with self.assertRaisesRegex(legacy.Halt,"POSITION_FLAT"):
            m4.inspect(FakeEx(qty="0",stop_status="NEW",stop_open=True),
                       cfg(),state(pending=None,active=True))

    def test_stage_exit_is_write_ahead(self):
        e=m4.inspect(FakeEx(),cfg(),state(pending=None,active=True))
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)/"s.json"
            issued=m4.stage_exit(dest,state(pending=None,active=True),e)
            self.assertTrue(m4.CLIENT_ID.fullmatch(issued))
            self.assertEqual(legacy.load_json(dest)["pending_order"]["id"],issued)

    def test_exit_order_must_be_reduce_only(self):
        with self.assertRaisesRegex(legacy.Halt,"EXIT_NOT_REDUCE_ONLY"):
            m4.inspect(FakeEx(qty="0",exit_reduce_only=False,stop_open=True),
                       cfg(),state(pending="EXIT_LONG",active=True))

    def test_exit_filled_requires_flat(self):
        with self.assertRaisesRegex(legacy.Halt,"EXIT_NOT_FULLY_RECONCILED"):
            m4.inspect(FakeEx(qty="0.01"),cfg(),state(pending="EXIT_LONG",active=True))

    def test_exit_filled_stop_still_live(self):
        e=m4.inspect(FakeEx(qty="0"),cfg(),state(pending="EXIT_LONG",active=True))
        self.assertEqual(e["status"],"EXIT_FILLED_STOP_STILL_ACTIVE")

    def test_exit_flat_and_stop_gone(self):
        e=m4.inspect(FakeEx(qty="0",stop_status="CANCELED",stop_open=False),
                     cfg(),state(pending="EXIT_LONG",active=True))
        self.assertEqual(e["status"],"EXIT_FLAT_STOP_GONE")
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)/"s.json"
            self.assertTrue(m4.reconcile(dest,state(pending="EXIT_LONG",active=True),e))
            self.assertIsNone(legacy.load_json(dest)["active_position"])
            self.assertIsNone(legacy.load_json(dest)["pending_order"])

    def test_cleanup_one_shot_only(self):
        e=m4.inspect(FakeEx(qty="0"),cfg(),state(pending="EXIT_LONG",active=True))
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"s.json"
            ex=FakeEx(qty="0")
            m4.cleanup_stop_once(ex,cfg(),p,state(pending="EXIT_LONG",active=True),e)
            self.assertEqual(ex.calls[-1][0],"DELETE")
            saved=legacy.load_json(p)
            with self.assertRaisesRegex(legacy.Halt,"PREVIOUSLY_ATTEMPTED"):
                m4.cleanup_stop_once(ex,cfg(),p,saved,e)

    def test_only_allowlisted_delete_on_testnet(self):
        ex=legacy.Exchange("testnet","KEY","SECRET",transport=httpx.MockTransport(
            lambda req:httpx.Response(200,json={"code":"200"})))
        try:
            with self.assertRaisesRegex(legacy.Halt,"CANCEL_ROUTE_FORBIDDEN"):
                ex.signed_delete("/fapi/v1/allOpenOrders",symbol=SYMBOL)
            with self.assertRaisesRegex(legacy.Halt,"CANCEL_ORDER_ID_REQUIRED"):
                ex.signed_delete("/fapi/v1/algoOrder",symbol=SYMBOL)
        finally:
            ex.close()

    def test_delete_never_mainnet(self):
        attempts=[]
        ex=legacy.Exchange("mainnet","KEY","SECRET",transport=httpx.MockTransport(
            lambda req:(attempts.append(req) or httpx.Response(200,json={}))))
        try:
            with self.assertRaisesRegex(legacy.Halt,"MAINNET_ORDER_WRITES_NOT_RELEASED"):
                ex.signed_delete("/fapi/v1/algoOrder",clientAlgoId=ENTRY+"s")
            self.assertEqual(attempts,[])
        finally:
            ex.close()

    def test_delete_signature_query_testnet(self):
        def handler(req):
            self.assertEqual(req.method,"DELETE")
            self.assertEqual(req.url.host,"demo-fapi.binance.com")
            self.assertEqual(req.url.path,"/fapi/v1/algoOrder")
            self.assertIn("signature",req.url.params)
            return httpx.Response(200,json={"code":"200"})
        ex=legacy.Exchange("testnet","KEY","SECRET",transport=httpx.MockTransport(handler))
        try:
            self.assertEqual(ex.signed_delete("/fapi/v1/algoOrder",
                         clientAlgoId=ENTRY+"s")["code"],"200")
        finally:
            ex.close()

    def test_exit_payload_reduce_only(self):
        ex=FakeEx()
        m4.send_exit(ex,cfg(),EXIT,"0.1")
        method, path, params = ex.calls[-1]
        self.assertEqual((method,path),("POST","/fapi/v1/order"))
        self.assertEqual(params["reduceOnly"],"true")
        self.assertEqual(params["side"],"SELL")

    def test_forged_client_id_rejected(self):
        bad=state()
        bad["pending_order"]["id"]="arbitrary"
        with self.assertRaisesRegex(legacy.Halt,"PENDING_ORDER_UNRECOGNIZED"):
            m4.checked_ids(bad)


if __name__ == "__main__":
    unittest.main()
