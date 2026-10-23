"""Hunter M4 — reconciliation and guarded reduce-only exit for the isolated Testnet engine.

This module is intentionally NOT mounted on any HTTP API, has NO scheduler, and
hard-rejects Mainnet. The existing order initiator remains separately gated.
An exit is a one-time, journaled Testnet-only action, never blindly repeated.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import uuid

from nex_api import hunter_live_executor as legacy

STOP_ACTIVE = {"NEW"}  # fail closed on unknown future Binance statuses
STOP_DONE = {"FINISHED", "CANCELED", "EXPIRED", "REJECTED"}
CLIENT_ID = re.compile(r"^HK1[a-f0-9]{24}$")


def reject(msg: str):
    raise legacy.Halt(msg)


def checked_config(data: dict) -> dict:
    if not isinstance(data, dict) or data.get("mode") != "testnet":
        reject("M4_TESTNET_ONLY")
    return legacy.require_config(data)


def checked_ids(state: dict):
    if not isinstance(state, dict):
        reject("INVALID_STATE")
    pending = state.get("pending_order")
    if pending is not None:
        if not isinstance(pending, dict) or not CLIENT_ID.fullmatch(str(pending.get("id", ""))):
            reject("PENDING_ORDER_UNRECOGNIZED")
        if pending.get("signal") not in {"ENTER_LONG", "EXIT_LONG", "ENTER_SHORT", "EXIT_SHORT"}:
            reject("PENDING_SIGNAL_UNRECOGNIZED")
    active = state.get("active_position")
    if active is not None and (
        not isinstance(active, dict) or not CLIENT_ID.fullmatch(str(active.get("id", "")))
    ):
        reject("ACTIVE_POSITION_UNRECOGNIZED")
    if pending and pending["signal"] in {"EXIT_LONG", "EXIT_SHORT"} and not active:
        reject("EXIT_WITHOUT_ACTIVE_POSITION")
    return pending, active


def get_position(ex, symbol, required_leverage=1, required_margin_mode=None, *, allow_tracked_short=False):
    legacy.account_settings(ex)
    qty = legacy.position_snapshot(ex, symbol, required_leverage, required_margin_mode)
    if qty < 0 and not allow_tracked_short:
        reject("OPEN_SHORT_POSITION_NOT_ALLOWED")
    return qty


def ordinary_orders(ex, symbol):
    rows = ex.signed_get("/fapi/v1/openOrders", symbol=symbol)
    if not isinstance(rows, list):
        reject("REGULAR_ORDERS_UNVERIFIED")
    return rows


def algo_orders(ex, symbol):
    rows = ex.signed_get("/fapi/v1/openAlgoOrders", symbol=symbol,
                         algoType="CONDITIONAL")
    if not isinstance(rows, list):
        reject("STOP_INVENTORY_UNVERIFIED")
    return rows


def ensure_stop(stop, symbol, entry_id, current_open, *, expected_trigger=None, direction="LONG"):
    sid = entry_id + "s"
    if not isinstance(stop, dict):
        reject("STOP_UNKNOWN")
    if (stop.get("symbol") != symbol or stop.get("clientAlgoId") != sid
        or stop.get("side") != ("BUY" if direction == "SHORT" else "SELL") or stop.get("positionSide") not in (None, "BOTH")
        or stop.get("orderType") not in ("STOP_MARKET", None)
        or stop.get("algoStatus") not in STOP_ACTIVE
        or stop.get("closePosition") is not True
        or stop.get("workingType") != "MARK_PRICE"):
        reject("STOP_NOT_PROVEN_PROTECTIVE")
    if len(current_open) != 1 or current_open[0].get("clientAlgoId") != sid:
        reject("STOP_INVENTORY_CONFLICT")
    price = legacy.D(stop.get("triggerPrice"), positive=True)
    if price <= 0:
        reject("STOP_TRIGGER_INVALID")
    if expected_trigger is not None and price != legacy.D(expected_trigger, positive=True):
        reject("STOP_TRIGGER_CHANGED_FROM_PLAN")


def ensure_order(order, symbol, client_id, side, reduce_only=False):
    if not isinstance(order, dict) or order.get("symbol") != symbol:
        reject("ORDER_IDENTITY_UNVERIFIED")
    if (order.get("clientOrderId") != client_id
        or order.get("side") != side
        or order.get("status") != "FILLED"
        or order.get("type") != "MARKET"):
        reject("ORDER_NOT_PROVEN_FILLED")
    if reduce_only and order.get("reduceOnly") is not True:
        reject("EXIT_NOT_REDUCE_ONLY")
    qty = legacy.D(order.get("executedQty"), positive=True)
    return qty


def inspect(ex, config, state):
    """Return only verified evidence; never mutate state or place orders."""
    checked_config(config)
    pending, active = checked_ids(state)
    symbol = config["symbol"]
    if not pending and not active:
        return {"status": "NO_TRACKED_TRADE", "write_enabled": False}
    if state.get("account") != hashlib.sha256(ex.key.encode()).hexdigest():
        reject("ACCOUNT_KEY_ROTATION_BLOCKED")
    tracked_short = (pending is not None and pending["signal"] in {"ENTER_SHORT", "EXIT_SHORT"}) or (active is not None and active.get("direction") == "SHORT")
    qty = get_position(ex, symbol, config.get("leverage", 1), config.get("margin_mode"), allow_tracked_short=tracked_short)
    ordinary = ordinary_orders(ex, symbol)
    stops = algo_orders(ex, symbol)
    if ordinary:
        reject("UNEXPECTED_OPEN_ORDERS")
    entry_id = (active or pending)["id"] if pending and pending["signal"] not in {"ENTER_LONG", "ENTER_SHORT"} else (pending or active)["id"]
    # For EXIT pending, active carries ENTRY id; do not query the exit id for stop.
    if active:
        entry_id = active["id"]
    stop = ex.signed_get("/fapi/v1/algoOrder", clientAlgoId=entry_id + "s")
    if not isinstance(stop, dict) or stop.get("clientAlgoId") != entry_id + "s" or stop.get("symbol") != symbol:
        reject("STOP_IDENTITY_UNVERIFIED")
    signal = pending.get("signal") if pending else "ACTIVE"
    expected_trigger = (active or pending).get("stop_price")
    direction = "SHORT" if signal in {"ENTER_SHORT", "EXIT_SHORT"} or (active and active.get("direction") == "SHORT") else "LONG"
    if signal in {"ENTER_LONG", "ENTER_SHORT"}:
        entry = ex.signed_get("/fapi/v1/order", symbol=symbol,
                              origClientOrderId=pending["id"] + "e")
        filled = ensure_order(entry, symbol, pending["id"] + "e", "SELL" if direction == "SHORT" else "BUY")
        if qty != (-filled if direction == "SHORT" else filled):
            reject("ENTRY_POSITION_MISMATCH")
        if pending.get("quantity") is not None and filled != legacy.D(pending["quantity"], positive=True):
            reject("ENTRY_QUANTITY_CHANGED_FROM_PLAN")
        ensure_stop(stop, symbol, entry_id, stops, expected_trigger=expected_trigger, direction=direction)
        if state.get("halted"):
            reject("HALTED_REQUIRES_OPERATOR_REVIEW")
        return {"status": "ENTRY_PROTECTED_CONFIRMED", "id": entry_id,
                "quantity": str(abs(qty)), "write_enabled": False}
    if signal in {"EXIT_LONG", "EXIT_SHORT"}:
        exit_order = ex.signed_get("/fapi/v1/order", symbol=symbol,
                                   origClientOrderId=pending["id"] + "x")
        filled = ensure_order(exit_order, symbol, pending["id"] + "x",
                              "BUY" if direction == "SHORT" else "SELL", reduce_only=True)
        expected = legacy.D(active["quantity"], positive=True)
        if filled != expected or qty != 0:
            reject("EXIT_NOT_FULLY_RECONCILED")
        if stop.get("algoStatus") not in STOP_DONE and stop.get("algoStatus") not in STOP_ACTIVE:
            reject("STOP_UNKNOWN_STATUS")
        if stop.get("algoStatus") in STOP_ACTIVE:
            ensure_stop(stop, symbol, entry_id, stops, expected_trigger=expected_trigger, direction=direction)
            return {"status": "EXIT_FILLED_STOP_STILL_ACTIVE", "id": pending["id"],
                    "write_enabled": False}
        if stops:
            reject("ORPHAN_STOP_ORDERS_PRESENT")
        return {"status": "EXIT_FLAT_STOP_GONE", "id": pending["id"], "write_enabled": False}
    # Natural protective-stop activation may have closed the entire position.
    # FINISHED and no open orders are the minimum evidence for a flat transition.
    if qty == 0:
        if stop.get("algoStatus") == "FINISHED" and not stops:
            return {"status": "STOP_FILLED_FLAT_CONFIRMED", "id": entry_id,
                    "write_enabled": False}
        reject("POSITION_FLAT_NEEDS_STOP_RECONCILIATION")
    expected = legacy.D(active["quantity"], positive=True)
    if qty != (-expected if direction == "SHORT" else expected):
        reject("POSITION_SIZE_CHANGED_OUTSIDE_ENGINE")
    ensure_stop(stop, symbol, entry_id, stops, expected_trigger=expected_trigger, direction=direction)
    return {"status": "ACTIVE_PROTECTED_CONFIRMED", "id": entry_id,
            "quantity": str(abs(qty)), "write_enabled": False}


def reconcile(state_path, state, evidence):
    """Locally commit only fully proved transitions; no Binance write."""
    status = evidence["status"]
    if status == "ENTRY_PROTECTED_CONFIRMED":
        p, active = checked_ids(state)
        if not p or p["signal"] not in {"ENTER_LONG", "ENTER_SHORT"} or active:
            reject("ENTRY_TRANSITION_INVALID")
        next_state = dict(state, active_position={
            "id": p["id"], "quantity": evidence["quantity"],
            "direction": "SHORT" if p["signal"] == "ENTER_SHORT" else "LONG",
            **({"stop_price": p["stop_price"]} if "stop_price" in p else {})},
            pending_order=None)
    elif status == "STOP_FILLED_FLAT_CONFIRMED":
        p, active = checked_ids(state)
        if p or not active:
            reject("STOP_TRANSITION_INVALID")
        next_state = dict(state, active_position=None, pending_order=None,
                          stop_cleanup_attempted=False)
    elif status == "EXIT_FLAT_STOP_GONE":
        p, active = checked_ids(state)
        if not p or p["signal"] not in {"EXIT_LONG", "EXIT_SHORT"} or not active:
            reject("EXIT_TRANSITION_INVALID")
        next_state = dict(state, active_position=None, pending_order=None,
                          stop_cleanup_attempted=False)
    else:
        return False
    legacy.save_state(state_path, next_state)
    return True


def stage_exit(state_path, state, evidence):
    if evidence.get("status") != "ACTIVE_PROTECTED_CONFIRMED":
        reject("EXIT_REQUIRES_PROTECTED_POSITION")
    pending, active = checked_ids(state)
    if pending or not active or state.get("halted"):
        reject("EXIT_PENDING_OR_HALTED")
    exit_id = "HK1" + uuid.uuid4().hex[:24]
    updated = dict(state, pending_order={
        "id": exit_id, "signal": "EXIT_SHORT" if active.get("direction") == "SHORT" else "EXIT_LONG",
        "created": int(time.time())})
    legacy.save_state(state_path, updated)
    return exit_id


def send_exit(ex, config, exit_id, amount, direction="LONG"):
    checked_config(config)
    if not CLIENT_ID.fullmatch(exit_id):
        reject("EXIT_ID_INVALID")
    qty = legacy.D(amount, positive=True)
    if direction not in {"LONG", "SHORT"}:
        reject("INVALID_EXIT_DIRECTION")
    return ex.signed_post(
        "/fapi/v1/order", symbol=config["symbol"], side="BUY" if direction == "SHORT" else "SELL",
        positionSide="BOTH", type="MARKET", reduceOnly="true",
        quantity=str(qty), newClientOrderId=exit_id+"x", newOrderRespType="RESULT",
    )


def cleanup_stop_once(ex, config, state_path, state, evidence):
    """One-shot attempt to cancel a now-orphaned Testnet stop, never retry on ambiguity."""
    if evidence.get("status") != "EXIT_FILLED_STOP_STILL_ACTIVE":
        reject("CLEANUP_REQUIRES_FLAT_POSITION")
    if state.get("stop_cleanup_attempted"):
        reject("CLEANUP_PREVIOUSLY_ATTEMPTED_REVIEW_REQUIRED")
    active = state.get("active_position")
    if not active:
        reject("CLEANUP_ENTRY_UNKNOWN")
    state = dict(state, stop_cleanup_attempted=True)
    legacy.save_state(state_path, state)
    return ex.signed_delete("/fapi/v1/algoOrder", clientAlgoId=active["id"]+"s")


def cli(argv=None):
    parser = argparse.ArgumentParser(description="Testnet-only, fail-closed reconciliation")
    parser.add_argument("--config", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--action", choices=["status", "inspect", "reconcile",
                                            "exit-testnet", "cleanup-flat-stop"],
                        default="status")
    args = parser.parse_args(argv)
    config_path, state_path = Path(args.config), Path(args.state)
    if (not config_path.is_file() or config_path.is_symlink()
        or config_path.stat().st_mode & 0o077):
        reject("CONFIG_MISSING_OR_INSECURE")
    config = checked_config(legacy.load_json(config_path))
    if state_path.is_symlink() or (state_path.is_file() and state_path.stat().st_mode & 0o077):
        reject("STATE_INSECURE")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(state_path.parent, 0o700)
    with open(state_path.with_suffix(".m4.lock"), "a+b") as lock:
        os.fchmod(lock.fileno(), 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = legacy.load_json(state_path) if state_path.is_file() else {}
        checked_ids(state)
        if args.action == "status":
            print(json.dumps({"mode": "testnet", "pending": bool(state.get("pending_order")),
                              "active": bool(state.get("active_position")),
                              "halted": bool(state.get("halted")),
                              "mainnet_writes": False}))
            return 0
        key, secret = os.getenv("HUNTER_EXEC_API_KEY"), os.getenv("HUNTER_EXEC_API_SECRET")
        if not key or not secret:
            reject("SEPARATE_TESTNET_CREDENTIALS_REQUIRED")
        ex = legacy.Exchange("testnet", key, secret)
        try:
            evidence = inspect(ex, config, state)
            if args.action in ("inspect", "reconcile"):
                wrote = args.action == "reconcile" and reconcile(state_path, state, evidence)
                print(json.dumps(dict(evidence, local_state_updated=wrote)))
                return 0
            if os.getenv("HUNTER_TESTNET_EXIT_CONFIRM") != "EXPLICITLY_APPROVED":
                reject("EXPLICIT_TESTNET_CONFIRMATION_REQUIRED")
            if args.action == "exit-testnet":
                exit_id = stage_exit(state_path, state, evidence)
                # Once persisted, NO retry: ambiguous HTTP error remains pending.
                result = send_exit(ex, config, exit_id, evidence["quantity"], direction=state.get("active_position", {}).get("direction", "LONG"))
                print(json.dumps({"status": "EXIT_SENT_NEEDS_RECONCILIATION",
                                  "acknowledged": isinstance(result, dict)}))
            else:
                result = cleanup_stop_once(ex, config, state_path, state, evidence)
                print(json.dumps({"status": "STOP_CLEANUP_SENT_NEEDS_RECONCILIATION",
                                  "acknowledged": isinstance(result, dict)}))
            return 0
        finally:
            ex.close()


if __name__ == "__main__":
    try:
        sys.exit(cli())
    except (legacy.Halt, BlockingIOError) as exc:
        print("BLOCKED="+str(exc), file=sys.stderr)
        sys.exit(2)
