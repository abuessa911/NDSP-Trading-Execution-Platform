"""M5 private Testnet operator pilot. Never mounted on HTTP or started as a daemon.

One guarded CLI for M4 lifecycle. The only possible network mutations are Binance
DEMO USD-M operations, requiring a separate explicit operator confirmation.

Important: M3 strategy candidates and the M2 Mainnet read-only equity monitor
are NOT authorization to trade. The executor remains EMA20/50-long-only and
requires its own explicit private Testnet risk policy. No Mainnet writes.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import fcntl
import json
import os
from pathlib import Path
import stat
import sys

from nex_api import hunter_live_executor as legacy
from nex_api import hunter_testnet_reconcile as m4

ACTIONS = ("status", "preflight", "dry-run", "entry-testnet", "inspect",
           "reconcile", "exit-testnet", "cleanup-flat-stop")
WRITES = {"entry-testnet", "exit-testnet", "cleanup-flat-stop"}
APPROVAL = "I_APPROVE_BINANCE_TESTNET_ONLY"
SECRET_VARS = ("HUNTER_EXEC_API_KEY", "HUNTER_EXEC_API_SECRET")
REQUIRED_GUARDS = ("LIVE_TRADING_ENABLED=false", "GLOBAL_KILL_SWITCH=true")


def blocked(reason: str):
    raise legacy.Halt(reason)


def private_file(path: Path, *, exists: bool = True):
    if path.is_symlink():
        blocked("SYMLINK_FORBIDDEN")
    if not path.is_file():
        if exists:
            blocked("PRIVATE_FILE_MISSING")
        return False
    info = path.stat()
    if info.st_uid != os.geteuid() or (stat.S_IMODE(info.st_mode) & 0o077):
        blocked("PRIVATE_FILE_PERMISSIONS")
    return True


def validate_guards(env_path: Path):
    if not private_file(env_path):
        blocked("GATE_NOT_FOUND")
    # Do not print the environment file; fail closed on absent kill switches.
    content = env_path.read_text(encoding="utf-8").splitlines()
    for key in REQUIRED_GUARDS:
        if content.count(key) != 1:
            blocked("GLOBAL_MAINNET_KILL_SWITCH_NOT_ASSERTED")


def load_config(config_path: Path):
    private_file(config_path)
    config = legacy.load_json(config_path)
    if not isinstance(config, dict) or config.get("mode") != "testnet":
        blocked("M5_TESTNET_ONLY")
    m4.checked_config(config)
    if config.get("mainnet_enabled") is True:
        blocked("MAINNET_FLAG_FORBIDDEN")
    return config


def lock_state(state_path: Path, stack: ExitStack):
    if state_path.is_symlink():
        blocked("STATE_SYMLINK_FORBIDDEN")
    parent = state_path.parent
    if not parent.is_dir() or parent.is_symlink():
        blocked("PRIVATE_STATE_DIRECTORY_MISSING")
    info = parent.stat()
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        blocked("PRIVATE_STATE_DIRECTORY_PERMISSIONS")
    if state_path.exists():
        private_file(state_path)
    for suffix in (".lock", ".m4.lock"):
        path = state_path.with_suffix(suffix)
        if path.is_symlink():
            blocked("STATE_LOCK_SYMLINK_FORBIDDEN")
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        lock = stack.enter_context(os.fdopen(fd, "r+b"))
        os.fchmod(lock.fileno(), 0o600)
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            blocked("CONCURRENT_OPERATOR")
    return legacy.load_json(state_path) if state_path.is_file() else {}


def check_state(state, *, allow_halted=False):
    if not isinstance(state, dict):
        blocked("STATE_INVALID")
    m4.checked_ids(state)
    if state.get("halted") and not allow_halted:
        blocked("HALTED_REQUIRES_OPERATOR_REVIEW")


def credentials():
    key, secret = (os.getenv(v) for v in SECRET_VARS)
    if not key or not secret:
        blocked("SEPARATE_BINANCE_DEMO_CREDENTIALS_REQUIRED")
    if "\n" in key or "\n" in secret:
        blocked("CREDENTIAL_INVALID")
    return key, secret


def risk_check(ex, config, state):
    """Use Testnet equity only; never Mainnet wallet/monitor budget to size Testnet orders."""
    legacy.account_settings(ex)
    snapshot = ex.signed_get("/fapi/v3/account")
    if not isinstance(snapshot, dict):
        blocked("TESTNET_EQUITY_UNVERIFIED")
    equity = legacy.D(snapshot.get("totalMarginBalance"), positive=True)
    current = legacy.day()
    evaluated = legacy.guarded_state(state, ex.key, equity, current,
                                     config["daily_loss_pct"])
    return {"equity_verified": True, "risk_day": current,
            "daily_limit_from_private_testnet_config": str(config["daily_loss_pct"]),
            "new_entries_blocked": False, "baseline_persisted": False,
            "risk_state_preview": evaluated.get("date")}


def preflight(ex, config, state):
    """Read-only probe. Never creates state or sends orders."""
    check_state(state)
    risk = risk_check(ex, config, state)
    if state.get("pending_order") or state.get("active_position"):
        evidence = m4.inspect(ex, config, state)
        status = evidence["status"]
    else:
        legacy.account_snapshot(ex, config["symbol"], config.get("leverage", 1), config.get("margin_mode"))
        legacy.symbol_filters(ex, config["symbol"])
        status = "TESTNET_ACCOUNT_AND_MARKET_READABLE"
    return {"status": status, "mode": "testnet", "network_writes": False,
            "mainnet_order_execution": False, "risk": risk,
            "strategy_order_flow": "SELECTED_RESEARCH_STRATEGY_REQUIRES_TESTNET_RISK_APPROVAL",
            "m3_candidates_are_not_orders": True}


def perform(action, config, state_path, state, ex, *, approved=False):
    check_state(state)
    if action == "preflight":
        return preflight(ex, config, state)
    if action in {"dry-run", "entry-testnet"}:
        if state.get("active_position") or state.get("pending_order"):
            blocked("RECONCILE_BEFORE_FURTHER_EXECUTION")
        if action == "entry-testnet":
            # Confirmation is checked BEFORE any network calls.
            if not approved and os.getenv("HUNTER_M5_TESTNET_CONFIRM") != APPROVAL:
                blocked("EXPLICIT_DEMO_TRADE_APPROVAL_REQUIRED")
        result = legacy.execute_once(config, state_path, ex,
                                     allow_write=action == "entry-testnet")
        return {"mode": "testnet", "result": result,
                "mainnet_order_execution": False,
                "requires_reconciliation": result.get("status") ==
                    "ENTRY_SENT_NEEDS_RECONCILIATION"}
    evidence = m4.inspect(ex, config, state)
    if action == "inspect":
        return {"mode": "testnet", **evidence, "state_modified": False}
    if action == "reconcile":
        updated = m4.reconcile(state_path, state, evidence)
        return {"mode": "testnet", **evidence, "state_modified": updated}
    if not approved and os.getenv("HUNTER_M5_TESTNET_CONFIRM") != APPROVAL:
        blocked("EXPLICIT_DEMO_TRADE_APPROVAL_REQUIRED")
    if action == "exit-testnet":
        exit_id = m4.stage_exit(state_path, state, evidence)
        acknowledged = isinstance(m4.send_exit(ex, config, exit_id,
                                                evidence["quantity"], direction=state.get("active_position", {}).get("direction", "LONG")), dict)
        return {"status": "TESTNET_EXIT_SENT_RECONCILIATION_REQUIRED",
                "acknowledged": acknowledged, "mainnet_order_execution": False}
    if action == "cleanup-flat-stop":
        acknowledged = isinstance(m4.cleanup_stop_once(
            ex, config, state_path, state, evidence), dict)
        return {"status": "TESTNET_STOP_CLEANUP_NEEDS_RECONCILIATION",
                "acknowledged": acknowledged, "mainnet_order_execution": False}
    blocked("ACTION_INVALID")


def cli(argv=None):
    parser = argparse.ArgumentParser(description="Private Hunter Testnet M5 pilot")
    parser.add_argument("--config", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--action", choices=ACTIONS, default="status")
    parser.add_argument("--safety-config",
                        default="/etc/hunter-ksa1-identity/public-api.env")
    args = parser.parse_args(argv)
    config_path, state_path = Path(args.config), Path(args.state)
    # Read-only status needs no Binance credentials.
    validate_guards(Path(args.safety_config))
    config = load_config(config_path)
    if args.action in WRITES and os.getenv("HUNTER_M5_TESTNET_CONFIRM") != APPROVAL:
        blocked("EXPLICIT_DEMO_TRADE_APPROVAL_REQUIRED")
    with ExitStack() as stack:
        state = lock_state(state_path, stack)
        check_state(state, allow_halted=args.action == "status")
        if args.action == "status":
            result = {"status": "M5_TESTNET_PILOT_INSTALLED",
                      "mode": "testnet", "pending": bool(state.get("pending_order")),
                      "active": bool(state.get("active_position")),
                      "halted": bool(state.get("halted")),
                      "credential_probe_performed": False, "mainnet_order_execution": False,
                      "automated_trading": False}
        else:
            key, secret = credentials()
            ex = legacy.Exchange("testnet", key, secret)
            stack.callback(ex.close)
            result = perform(args.action, config, state_path, state, ex)
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(cli())
    except (legacy.Halt, BlockingIOError) as exc:
        print("STATUS=BLOCKED_" + str(exc), file=sys.stderr)
        sys.exit(2)
