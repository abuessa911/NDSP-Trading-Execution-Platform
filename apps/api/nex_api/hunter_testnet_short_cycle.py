"""Isolated Testnet SHORT orchestration. No mainnet or scheduler.

Pre-place and verify the close-position BUY STOP before SELL entry.
Fails closed on any ambiguity; reconciliation is required, never retry.
"""
from decimal import Decimal
from nex_api.hunter_testnet_cycle_v1 import TestnetLedger
from nex_api import hunter_testnet_reconcile as reconcile
from nex_api import hunter_live_executor as legacy


def protected_short_entry(ex, *, symbol, entry_id, quantity, stop_price, mark_price, ledger):
    if getattr(ex, "mode", None) != "testnet":
        raise legacy.Halt("TESTNET_ONLY")
    if not reconcile.CLIENT_ID.fullmatch(entry_id):
        raise legacy.Halt("INVALID_ENTRY_ID")
    quantity = legacy.D(quantity, positive=True)
    trigger = legacy.D(stop_price, positive=True)
    mark = legacy.D(mark_price, positive=True)
    if trigger <= mark:
        raise legacy.Halt("SHORT_STOP_MUST_BE_ABOVE_MARK")
    if not isinstance(ledger, TestnetLedger):
        raise legacy.Halt("DURABLE_LEDGER_REQUIRED")
    if ledger.state(entry_id) is not None:
        raise legacy.Halt("DUPLICATE_ORDER_BLOCKED")
    if reconcile.ordinary_orders(ex, symbol) or reconcile.algo_orders(ex, symbol):
        raise legacy.Halt("EXISTING_ORDERS_NEED_RECONCILIATION")
    if not isinstance(ledger, TestnetLedger):
        raise legacy.Halt("DURABLE_LEDGER_REQUIRED")
    # A durable reservation is made before either broker write.
    ledger.reserve(entry_id, symbol)
    ledger.update(entry_id, "SUBMISSION_UNKNOWN")
    try:
        return _send_reserved_short(ex, symbol, entry_id, quantity, trigger, mark, ledger)
    except Exception:
        ledger.update(entry_id, "RECONCILE_REQUIRED")
        raise


def _send_reserved_short(ex, symbol, entry_id, quantity, trigger, mark, ledger):
    stop_result = ex.signed_post(
        "/fapi/v1/algoOrder", algoType="CONDITIONAL", symbol=symbol,
        side="BUY", positionSide="BOTH", type="STOP_MARKET",
        triggerPrice=str(trigger), closePosition="true",
        workingType="MARK_PRICE", clientAlgoId=entry_id+"s")
    if not isinstance(stop_result, dict) or not stop_result.get("algoId"):
        raise legacy.Halt("SHORT_STOP_UNCONFIRMED_RECONCILE")
    stop = ex.signed_get("/fapi/v1/algoOrder", clientAlgoId=entry_id+"s")
    inventory = reconcile.algo_orders(ex, symbol)
    reconcile.ensure_stop(stop, symbol, entry_id, inventory,
                          expected_trigger=trigger, direction="SHORT")
    current_mark = legacy.D(ex.get("/fapi/v1/premiumIndex",symbol=symbol).get("markPrice"), positive=True)
    if current_mark >= trigger or abs(current_mark-mark)/mark > Decimal("0.001"):
        raise legacy.Halt("SHORT_PRICE_MOVED_BEFORE_ENTRY_RECONCILE")
    filled = ex.signed_post(
        "/fapi/v1/order", symbol=symbol, side="SELL", positionSide="BOTH",
        type="MARKET", quantity=str(quantity),
        newClientOrderId=entry_id+"e", newOrderRespType="RESULT")
    if not isinstance(filled, dict) or filled.get("status") != "FILLED":
        raise legacy.Halt("SHORT_ENTRY_UNCERTAIN_RECONCILE")
    reconcile.ensure_order(filled, symbol, entry_id+"e", "SELL")
    ledger.update(entry_id, "RECONCILE_REQUIRED")
    return {"status":"SHORT_ENTRY_SENT_RECONCILE_REQUIRED", "entry_id":entry_id}


def guarded_short_exit(ex, *, config, exit_id, quantity):
    if getattr(ex, "mode", None) != "testnet":
        raise legacy.Halt("TESTNET_ONLY")
    return reconcile.send_exit(ex, config, exit_id, quantity, direction="SHORT")
