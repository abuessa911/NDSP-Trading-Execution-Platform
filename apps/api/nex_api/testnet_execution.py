"""Durable, owner-scoped Binance DEMO execution service.

No Mainnet capability, subprocesses, process-wide credential environment, or
caller-supplied paths/URLs. A process-shared lock covers credentials, write-ahead
intent, receipts and reconciliation. An uncertain receipt is never resubmitted.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
import time
from uuid import UUID, uuid4

from nex_api import hunter_live_executor as engine
from nex_api import hunter_m5_testnet_pilot as pilot
from nex_api import hunter_testnet_reconcile as reconcile
from nex_api.testnet_automation import AutomationSession, automation_accounts
from nex_api.strategy_signals import BY_ID

ACTIONS = {"preflight", "dry-run", "entry", "inspect", "reconcile", "exit", "cleanup", "recover"}
MUTATIONS = {"entry", "exit", "cleanup"}
PRESET = {"mode": "testnet", "mainnet_enabled": False, "symbol": "BTCUSDT",
          "strategy": "trend-ladder", "daily_loss_pct": "2",
          "trade_risk_pct": "0.5", "max_exposure_pct": "10",
          "stop_pct": "1", "margin_mode": "CROSS"}
SYMBOLS = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LINKUSDT"}


def reject(code):
    raise engine.Halt(code)


def private_directory(path):
    if path.is_symlink():
        reject("TESTNET_STATE_SYMLINK")
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.stat()
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        reject("TESTNET_STATE_PERMISSIONS")


def read_private(path, default):
    if path.exists() or path.is_symlink():
        pilot.private_file(path)
        value = engine.load_json(path)
        if not isinstance(value, dict):
            reject("TESTNET_STATE_INVALID")
        return value
    return default


def valid_config(value):
    if set(value) != set(PRESET) or value.get("mode") != "testnet" or value.get("mainnet_enabled") is not False:
        reject("TESTNET_CONFIG_INVALID")
    if value.get("symbol") not in SYMBOLS or value.get("margin_mode") not in {"CROSS", "ISOLATED"}:
        reject("TESTNET_CONFIG_INVALID")
    if value["strategy"] not in BY_ID or value["symbol"] != BY_ID[value["strategy"]].symbol:
        reject("STRATEGY_MARKET_INTERVAL_MISMATCH")
    return reconcile.checked_config(dict(value))


class TestnetExecution:
    def __init__(self, directory, *, exchange_factory=None):
        self.root = Path(directory)
        # The service's systemd StateDirectory parent already exists.
        private_directory(self.root)
        self.exchange_factory = exchange_factory or engine.Exchange

    def automation_accounts(self):
        if not (self.root / "automation-accounts.json").exists():
            return []
        path = self.root / "execution.lock"
        pilot.private_file(path)
        with path.open("rb") as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                reject("TESTNET_OPERATION_IN_PROGRESS")
            return automation_accounts(self)

    @contextmanager
    def session(self, scope):
        if not isinstance(scope, str) or not re.fullmatch(r"[0-9a-f-]{36}:[0-9a-f-]{36}", scope):
            reject("TESTNET_SCOPE_INVALID")
        owner = hashlib.sha256(scope.encode()).hexdigest()
        lock_path = self.root / "execution.lock"
        if lock_path.is_symlink():
            reject("TESTNET_STATE_SYMLINK")
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "r+b") as lock:
            if os.fstat(lock.fileno()).st_uid != os.geteuid():
                reject("TESTNET_STATE_PERMISSIONS")
            os.fchmod(lock.fileno(), 0o600)
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                reject("TESTNET_OPERATION_IN_PROGRESS")
            directory = self.root / owner
            private_directory(directory)
            yield ExecutionSession(self, directory, owner, scope)


class ExecutionSession(AutomationSession):
    def __init__(self, service, directory, owner, scope):
        self.service, self.directory, self.owner = service, directory, owner
        self.scope = scope
        self.state_path = directory / "state.json"
        self.config_path = directory / "config.json"
        self.receipts_path = directory / "receipts.json"

    def state(self):
        value = read_private(self.state_path, {})
        reconcile.checked_ids(value)
        return value

    def metadata(self):
        return read_private(self.config_path, {})

    def config(self):
        value = read_private(self.config_path, {})
        if not value:
            reject("TESTNET_SETUP_REQUIRED")
        return valid_config(value.get("config", {}))

    def view(self):
        state, meta = self.state(), self.metadata()
        automation = self.automation()
        config = self.config() if self.config_path.exists() else None
        receipts = read_private(self.receipts_path, {})
        recent = list(receipts.values())[-30:]
        return {"venue": "BINANCE_USDM_TESTNET", "mainnet_orders_enabled": False,
                "configured": config is not None, "config": config,
                "revision": meta.get("revision"), "interval": BY_ID[config["strategy"]].interval if config else None, "leverage": 1,
                "strategy": config["strategy"] if config else None, "automated_trading": automation["state"] == "RUNNING",
                "automation": automation,
                "active_position": state.get("active_position"),
                "pending_order": state.get("pending_order"),
                "halted": bool(state.get("halted")), "daily_loss_hit": bool(state.get("max_loss_hit")),
                "risk_day": state.get("date"), "opening_equity": state.get("opening"),
                "last_equity": state.get("last_equity"), "receipts": recent}

    def configure(self, config):
        if self.automation()["state"] in {"RUNNING", "STOPPING"}:
            reject("TESTNET_STOP_AUTOMATION_BEFORE_CONFIGURE")
        config = valid_config(config)
        state = self.state()
        if state.get("pending_order") or state.get("active_position") or state.get("halted"):
            reject("TESTNET_RECONCILE_BEFORE_CONFIGURE")
        if state.get("date") == engine.day() and state.get("daily_pct") is not None:
            if engine.pct(config["daily_loss_pct"]) > engine.pct(state["daily_pct"]):
                reject("CANNOT_INCREASE_DAILY_LOSS_LIMIT")
        engine.save_state(self.config_path, {"config": config, "revision": str(uuid4())})
        return self.view()

    def credential_change(self, api_key=None):
        state = self.state()
        # Re-saving the SAME key permits renewal without orphaning protection.
        fingerprint = hashlib.sha256(api_key.encode()).hexdigest() if api_key else None
        if self.automation()["state"] in {"RUNNING", "STOPPING"}:
            if not fingerprint or fingerprint != state.get("account"):
                reject("TESTNET_STOP_AUTOMATION_BEFORE_CREDENTIAL_CHANGE")
        if (state.get("pending_order") or state.get("active_position")) and fingerprint != state.get("account"):
            reject("TESTNET_CREDENTIAL_CHANGE_WITH_OPEN_TRADE")
        if fingerprint and state.get("account") not in (None, fingerprint):
            reject("TESTNET_ACCOUNT_KEY_ROTATION_REQUIRES_REVIEW")

    def bind(self, api_key):
        fingerprint = hashlib.sha256(api_key.encode()).hexdigest()
        index_path = self.service.root / "key-owners.json"
        index = read_private(index_path, {})
        if fingerprint in index and index[fingerprint] != self.owner:
            reject("TESTNET_KEY_BOUND_TO_ANOTHER_OWNER")
        self.credential_change(api_key)
        if fingerprint not in index:
            index[fingerprint] = self.owner
            engine.save_state(index_path, index)

    def operate(self, action, request_id, revision, key, secret, *, position_id=None):
        if action not in ACTIONS:
            reject("TESTNET_ACTION_INVALID")
        if str(UUID(request_id)) != request_id:
            reject("TESTNET_REQUEST_ID_INVALID")
        payload = {"action": action, "revision": revision, "position_id": position_id}
        receipts = read_private(self.receipts_path, {})
        previous = receipts.get(request_id)
        if previous:
            if previous["request"] != payload:
                reject("TESTNET_REQUEST_ID_CONFLICT")
            # Includes errors/uncertain writes: returning a receipt never sends again.
            return previous
        if len(receipts) >= 10000:
            reject("TESTNET_RECEIPT_ARCHIVE_REQUIRED")
        config = self.config()
        if revision != self.metadata().get("revision"):
            reject("TESTNET_CONFIGURATION_CHANGED")
        state = self.state()
        self.bind(key)
        if action == "exit" and (state.get("active_position") or {}).get("id") != position_id:
            reject("TESTNET_POSITION_CONFIRM_REQUIRED")
        receipt = {"request_id": request_id, "request": payload, "action": action,
                   "status": "UNCERTAIN", "reason": "TESTNET_OPERATION_INTERRUPTED",
                   "created_ms": int(time.time()*1000), "result": None}
        receipts[request_id] = receipt
        engine.save_state(self.receipts_path, receipts)
        ex = None
        try:
            ex = self.service.exchange_factory("testnet", key, secret)
            # No per-process environment mutation. Approval is local to this call.
            mapped = {"entry": "entry-testnet", "exit": "exit-testnet",
                      "cleanup": "cleanup-flat-stop"}.get(action, action)
            if action == "recover":
                pending = state.get("pending_order") or {}
                if (not state.get("halted") or pending.get("signal") != "ENTER_LONG" or
                        pending.get("id") != position_id or state.get("active_position")):
                    reject("TESTNET_RECOVERY_CONFIRM_REQUIRED")
                # An uncertain BUY is never repeated. Clear the halt only after
                # signed proof of the intended filled entry and protective stop.
                reviewed = dict(state, halted=False)
                evidence = reconcile.inspect(ex, config, reviewed)
                if evidence["status"] != "ENTRY_PROTECTED_CONFIRMED":
                    reject("TESTNET_RECOVERY_NOT_PROVEN")
                reconcile.reconcile(self.state_path, reviewed, evidence)
                result = {"status": "TESTNET_ENTRY_RECOVERED_FROM_SIGNED_EVIDENCE",
                          "mainnet_order_execution": False, "network_writes": False}
            else:
                result = pilot.perform(mapped, config, self.state_path, state, ex, approved=True)
            receipt.update(status="CONFIRMED", reason=None, result=result)
        except engine.Halt as error:
            # Only internal reason codes, never exchange bodies, credentials or URLs.
            reason = str(error)
            if not re.fullmatch(r"[A-Z0-9_:.-]{1,160}", reason):
                reason = "TESTNET_OPERATION_REJECTED"
            current = self.state()
            staged = (current.get("pending_order") != state.get("pending_order") or
                      current.get("stop_cleanup_attempted") != state.get("stop_cleanup_attempted"))
            uncertain = staged and action in MUTATIONS
            receipt.update(status="UNCERTAIN" if uncertain else "REJECTED", reason=reason)
        except Exception:
            # A crash/transport error after staging must never cause a repeat write.
            receipt.update(reason="TESTNET_OPERATION_UNCERTAIN" if action in MUTATIONS else "TESTNET_READ_UNAVAILABLE")
            if action not in MUTATIONS:
                receipt["status"] = "REJECTED"
        finally:
            if ex is not None:
                ex.close()
        engine.save_state(self.receipts_path, receipts)
        return receipt
