import pytest
from nex_api import hunter_testnet_short_cycle as cycle
from nex_api import hunter_live_executor as legacy
from nex_api.hunter_testnet_cycle_v1 import TestnetLedger

ENTRY="HK1"+"c"*24

class Fake:
    mode="testnet"
    def __init__(self, *, stop_ok=True):
        self.actions=[];self.stop_ok=stop_ok
    def signed_get(self,path,**kw):
        if path.endswith("openOrders"):return []
        if path.endswith("openAlgoOrders"):return [{"clientAlgoId":ENTRY+"s"}] if self.actions else []
        if path.endswith("algoOrder"):
            return {"symbol":"BTCUSDT","clientAlgoId":ENTRY+"s",
                    "side":"BUY" if self.stop_ok else "SELL","positionSide":"BOTH",
                    "orderType":"STOP_MARKET","algoStatus":"NEW","closePosition":True,
                    "workingType":"MARK_PRICE","triggerPrice":"65000"}
        raise AssertionError(path)
    def get(self,path,**kw):return {"markPrice":"64000"}
    def signed_post(self,path,**kw):
        self.actions.append((path,kw))
        if path.endswith("algoOrder"):return {"algoId":123}
        return {"symbol":"BTCUSDT","clientOrderId":ENTRY+"e",
                "side":"SELL","type":"MARKET","status":"FILLED",
                "executedQty":"0.001"}

def test_short_stop_verified_before_entry(tmp_path):
    ex=Fake()
    result=cycle.protected_short_entry(ex,symbol="BTCUSDT",entry_id=ENTRY,
        quantity="0.001",stop_price="65000",mark_price="64000",ledger=TestnetLedger(tmp_path/"ledger.db"))
    assert result["status"]=="SHORT_ENTRY_SENT_RECONCILE_REQUIRED"
    assert [a[0] for a in ex.actions]==["/fapi/v1/algoOrder","/fapi/v1/order"]
    assert ex.actions[0][1]["side"]=="BUY" and ex.actions[1][1]["side"]=="SELL"

def test_reject_bad_stop_without_entry(tmp_path):
    ex=Fake(stop_ok=False)
    with pytest.raises(legacy.Halt,match="STOP_NOT_PROVEN_PROTECTIVE"):
        cycle.protected_short_entry(ex,symbol="BTCUSDT",entry_id=ENTRY,
            quantity="0.001",stop_price="65000",mark_price="64000",ledger=TestnetLedger(tmp_path/"ledger.db"))
    assert len(ex.actions)==1

def test_reject_mainnet(tmp_path):
    ex=Fake();ex.mode="mainnet"
    with pytest.raises(legacy.Halt,match="TESTNET_ONLY"):
        cycle.protected_short_entry(ex,symbol="BTCUSDT",entry_id=ENTRY,
            quantity="0.001",stop_price="65000",mark_price="64000",ledger=TestnetLedger(tmp_path/"ledger.db"))
    assert ex.actions==[]

def test_reject_stop_below_market(tmp_path):
    ex=Fake()
    with pytest.raises(legacy.Halt,match="SHORT_STOP_MUST_BE_ABOVE_MARK"):
        cycle.protected_short_entry(ex,symbol="BTCUSDT",entry_id=ENTRY,
            quantity="0.001",stop_price="63000",mark_price="64000",ledger=TestnetLedger(tmp_path/"ledger.db"))
    assert ex.actions==[]


def test_duplicate_intent_rejected_without_second_order(tmp_path):
    ex=Fake();ledger=TestnetLedger(tmp_path/"orders.db")
    args=dict(symbol="BTCUSDT",entry_id=ENTRY,quantity="0.001",
              stop_price="65000",mark_price="64000",ledger=ledger)
    cycle.protected_short_entry(ex,**args)
    count=len(ex.actions)
    with pytest.raises(Exception,match="DUPLICATE_ORDER_BLOCKED"):
        cycle.protected_short_entry(ex,**args)
    assert len(ex.actions)==count
    assert ledger.state(ENTRY)=="RECONCILE_REQUIRED"

def test_missing_ledger_rejected_before_write():
    ex=Fake()
    with pytest.raises(legacy.Halt,match="DURABLE_LEDGER_REQUIRED"):
        cycle.protected_short_entry(ex,symbol="BTCUSDT",entry_id=ENTRY,
            quantity="0.001",stop_price="65000",mark_price="64000",ledger=None)
    assert not ex.actions
