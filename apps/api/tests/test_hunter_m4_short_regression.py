"""Short-direction reconciliation regression with a fake exchange only."""
import hashlib
from pathlib import Path
from types import SimpleNamespace
import pytest
from nex_api import hunter_testnet_reconcile as m4

ENTRY="HK1"+"a"*24
EXIT="HK1"+"b"*24

class Exchange:
    key="TESTKEY"
    def __init__(self, qty="-0.1", stop_status="NEW"):
        self.qty=qty; self.stop_status=stop_status; self.posts=[]
    def signed_get(self, path, **kw):
        if path.endswith("accountConfig"):
            return {"canTrade":True, "dualSidePosition":False,"multiAssetsMargin":False}
        if path.endswith("symbolConfig"):
            return [{"symbol":"BTCUSDT","leverage":1,"marginType":"CROSSED","isAutoAddMargin":False,"maxNotionalValue":"1000000"}]
        if path.endswith("positionRisk"):
            return [{"symbol":"BTCUSDT","positionSide":"BOTH","marginAsset":"USDT","positionAmt":self.qty}]
        if path.endswith("openOrders"): return []
        if path.endswith("openAlgoOrders"): return [{"clientAlgoId":ENTRY+"s"}] if self.stop_status=="NEW" else []
        if path.endswith("algoOrder"):
            return {"symbol":"BTCUSDT","clientAlgoId":ENTRY+"s","algoStatus":self.stop_status,
                    "side":"BUY","positionSide":"BOTH","closePosition":True,
                    "workingType":"MARK_PRICE","triggerPrice":"95000","orderType":"STOP_MARKET"}
        if path.endswith("/order"):
            exit_order=kw.get("origClientOrderId")==EXIT+"x"
            return {"symbol":"BTCUSDT","clientOrderId":EXIT+"x" if exit_order else ENTRY+"e",
                    "status":"FILLED","side":"BUY" if exit_order else "SELL",
                    "type":"MARKET","executedQty":"0.1",
                    "reduceOnly":bool(exit_order)}
        raise AssertionError(path)
    def signed_post(self,path,**kw):
        self.posts.append((path,kw));return {"status":"FILLED"}

CFG={"symbol":"BTCUSDT","strategy":"ema20_50_long_only","mode":"testnet",
     "daily_loss_pct":"2","trade_risk_pct":"0.5","max_exposure_pct":"10","stop_pct":"1"}

def state(signal="ENTER_SHORT",active=False):
    d={"account":hashlib.sha256(b"TESTKEY").hexdigest()}
    if signal:d["pending_order"]={"id":EXIT if signal=="EXIT_SHORT" else ENTRY,
                                  "signal":signal,"quantity":"0.1","stop_price":"95000"}
    if active:d["active_position"]={"id":ENTRY,"quantity":"0.1","direction":"SHORT","stop_price":"95000"}
    return d

def test_short_entry_verified_then_reconciled(tmp_path):
    evidence=m4.inspect(Exchange(),CFG,state())
    assert evidence["status"]=="ENTRY_PROTECTED_CONFIRMED"
    assert evidence["quantity"]=="0.1"
    target=tmp_path/"state.json"
    assert m4.reconcile(target,state(),evidence)
    import json
    assert json.loads(target.read_text())["active_position"]["direction"]=="SHORT"

def test_short_exit_verified_flat_and_stop_gone():
    evidence=m4.inspect(Exchange(qty="0",stop_status="CANCELED"),CFG,state("EXIT_SHORT",True))
    assert evidence["status"]=="EXIT_FLAT_STOP_GONE"

def test_short_requires_matching_buy_stop():
    ex=Exchange()
    original=ex.signed_get
    def wrong_stop(path,**kw):
        row=original(path,**kw)
        if path.endswith("algoOrder") and not path.endswith("openAlgoOrders"):
            return dict(row,side="SELL")
        return row
    ex.signed_get=wrong_stop
    with pytest.raises(Exception,match="STOP_NOT_PROVEN_PROTECTIVE"):
        m4.inspect(ex,CFG,state())

def test_short_exit_is_reduce_only_buy():
    ex=Exchange()
    m4.send_exit(ex,CFG,EXIT,"0.1",direction="SHORT")
    assert ex.posts[0][1]["side"]=="BUY"
    assert ex.posts[0][1]["reduceOnly"]=="true"
