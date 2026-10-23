"""Bounded, explicitly started Binance DEMO automation.

Uses the same owner journal, process lock, stop-first entry and non-repeating
receipts as manual execution. No Mainnet capability or automatic recovery of
uncertain writes. A lease runs for one hour; stopping/expiry closes a verified
position and cleans its stop before declaring STOPPED.
"""
from __future__ import annotations

import hashlib
import re
import time
from uuid import uuid4

from nex_api import hunter_live_executor as engine

LEASE_SECONDS = 3600
CREDENTIAL_BUFFER_SECONDS = 900
STATES = {"STOPPED", "RUNNING", "STOPPING", "PAUSED"}


def private_json(path, default):
    from nex_api.testnet_execution import read_private
    return read_private(path, default)


def automation_accounts(service):
    # The caller holds the same process-shared execution lock.
    values = private_json(service.root / "automation-accounts.json", {})
    if len(values) > 20:
        raise engine.Halt("TESTNET_AUTOMATION_ACCOUNT_LIMIT")
    for owner, record in values.items():
        if (not isinstance(record, dict) or
                not re.fullmatch(r"[0-9a-f-]{36}:[0-9a-f-]{36}", str(record.get("scope", ""))) or
                hashlib.sha256(record["scope"].encode()).hexdigest() != owner or
                any(not isinstance(record.get(k), str) or not record[k] or len(record[k]) > 512
                    for k in ("issuer", "subject"))):
            raise engine.Halt("TESTNET_AUTOMATION_INDEX_INVALID")
    return list(values.values())


class AutomationSession:
    def automation(self):
        value = private_json(self.directory / "automation.json", {})
        if not value:
            return {"state": "STOPPED", "expires_at": None, "last_checked_ms": None,
                    "last_result": None, "reason": None, "revision": None}
        if (value.get("state") not in STATES or
                type(value.get("expires_at")) is not int or
                value["expires_at"] < 0 or
                not isinstance(value.get("revision"), str) or
                (value.get("last_checked_ms") is not None and
                 type(value["last_checked_ms"]) is not int)):
            raise engine.Halt("TESTNET_AUTOMATION_STATE_INVALID")
        return value

    def save_automation(self, value):
        engine.save_state(self.directory / "automation.json", value)
        return value

    def pause_automation(self, reason):
        value = self.automation()
        # A disabled account is never accidentally reactivated by error handling.
        if value["state"] in {"RUNNING", "STOPPING"}:
            value.update(state="PAUSED", reason=reason, last_checked_ms=int(time.time()*1000))
            self.save_automation(value)
        return value

    def set_automation(self, enabled, revision, key=None, secret=None, *,
                       credentials_ttl=0, authority=None):
        if revision != self.metadata().get("revision"):
            raise engine.Halt("TESTNET_CONFIGURATION_CHANGED")
        current = self.automation()
        if not enabled:
            if current["state"] != "STOPPED":
                current.update(state="STOPPING", reason="TESTNET_OPERATOR_STOP_REQUESTED")
                self.save_automation(current)
            return self.view()
        if current["state"] == "RUNNING":
            # Replaying START does not renew/extend authorization.
            return self.view()
        if current["state"] == "STOPPING":
            raise engine.Halt("TESTNET_AUTOMATION_STOPPING")
        config, state = self.config(), self.state()
        if state.get("halted") or state.get("pending_order") or state.get("active_position"):
            raise engine.Halt("TESTNET_AUTOMATION_REQUIRES_FLAT_RECONCILED_ACCOUNT")
        if credentials_ttl < LEASE_SECONDS + CREDENTIAL_BUFFER_SECONDS:
            raise engine.Halt("TESTNET_RENEW_CREDENTIALS_BEFORE_AUTOMATION")
        if (not isinstance(authority, dict) or
                any(not isinstance(authority.get(k), str) or not authority[k] or
                    len(authority[k]) > 512 for k in ("issuer", "subject"))):
            raise engine.Halt("TESTNET_AUTOMATION_AUTHORITY_REQUIRED")
        self.bind(key)
        checked = self.operate("preflight", str(uuid4()), revision, key, secret)
        if checked["status"] != "CONFIRMED":
            raise engine.Halt(checked.get("reason") or "TESTNET_PREFLIGHT_REQUIRED")
        ex = self.service.exchange_factory("testnet", key, secret)
        try:
            equity, quantity, _ = engine.account_snapshot(ex, config["symbol"], 1, config["margin_mode"])
            if quantity != 0:
                raise engine.Halt("TESTNET_AUTOMATION_REQUIRES_FLAT_RECONCILED_ACCOUNT")
            baseline = engine.guarded_state(state, key, equity, engine.day(), config["daily_loss_pct"])
            engine.save_state(self.state_path, baseline)
        finally:
            ex.close()
        index_path = self.service.root / "automation-accounts.json"
        index = private_json(index_path, {})
        if self.owner not in index and len(index) >= 20:
            raise engine.Halt("TESTNET_AUTOMATION_ACCOUNT_LIMIT")
        index[self.owner] = {"scope": self.scope, **{k: authority[k] for k in ("issuer", "subject")}}
        engine.save_state(index_path, index)
        self.save_automation({"state": "RUNNING", "expires_at": int(time.time()) + LEASE_SECONDS,
            "last_checked_ms": None, "last_result": "TESTNET_AUTOMATION_STARTED",
            "reason": None, "revision": revision, "started_ms": int(time.time()*1000)})
        return self.view()

    def automation_cycle(self, key, secret, *, credentials_ttl, owner_allowed=True):
        auto = self.automation()
        if auto["state"] not in {"RUNNING", "STOPPING"}:
            return auto
        if auto["revision"] != self.metadata().get("revision"):
            return self.pause_automation("TESTNET_CONFIGURATION_CHANGED")
        auto["last_checked_ms"] = int(time.time()*1000)
        if (not owner_allowed or time.time() >= auto["expires_at"] or
                credentials_ttl <= CREDENTIAL_BUFFER_SECONDS):
            auto.update(state="STOPPING", reason=("TESTNET_OWNER_AUTHORIZATION_ENDED"
                if not owner_allowed else "TESTNET_AUTOMATION_LEASE_ENDED"))
        self.save_automation(auto)
        try:
            state = self.state()
            receipts = private_json(self.receipts_path, {})
            if any(r.get("status") == "UNCERTAIN" and r.get("action") in {"entry", "exit", "cleanup"}
                   and r.get("created_ms", 0) >= auto.get("started_ms", 0)
                   for r in receipts.values()):
                raise engine.Halt("TESTNET_AUTOMATION_UNCERTAIN_REQUIRES_REVIEW")
            if state.get("halted"):
                raise engine.Halt("HALTED_REQUIRES_OPERATOR_REVIEW")
            if credentials_ttl <= 0 or not key or not secret:
                raise engine.Halt("TESTNET_CREDENTIALS_UNAVAILABLE")
            if state.get("pending_order") or state.get("active_position"):
                receipt = self._automatic_action("inspect", key, secret)
                if receipt["status"] != "CONFIRMED":
                    return self.automation()
                status = receipt["result"]["status"]
                if status in {"ENTRY_PROTECTED_CONFIRMED", "STOP_FILLED_FLAT_CONFIRMED",
                              "EXIT_FLAT_STOP_GONE"}:
                    receipt = self._automatic_action("reconcile", key, secret)
                    if receipt["status"] == "CONFIRMED":
                        latest = self.state()
                        if auto["state"] == "STOPPING" and not (
                                latest.get("active_position") or latest.get("pending_order")):
                            auto = self.automation()
                            auto.update(state="STOPPED", last_result="EXIT_FLAT_STOP_GONE")
                            self.save_automation(auto)
                elif status == "EXIT_FILLED_STOP_STILL_ACTIVE":
                    self._automatic_action("cleanup", key, secret)
                elif status == "ACTIVE_PROTECTED_CONFIRMED":
                    if auto["state"] == "STOPPING" or self._automatic_exit_signal(key, secret):
                        self._automatic_action("exit", key, secret,
                                               position_id=state["active_position"]["id"])
                else:
                    raise engine.Halt("TESTNET_AUTOMATION_EVIDENCE_UNRECOGNIZED")
            elif auto["state"] == "STOPPING":
                ex = self.service.exchange_factory("testnet", key, secret)
                try:
                    _, quantity, _ = engine.account_snapshot(ex, self.config()["symbol"], 1,
                                                           self.config()["margin_mode"])
                    if quantity != 0:
                        raise engine.Halt("TESTNET_UNTRACKED_POSITION_REQUIRES_REVIEW")
                finally:
                    ex.close()
                auto.update(state="STOPPED", last_result="NO_TRACKED_TRADE")
                self.save_automation(auto)
            else:
                self._automatic_action("entry", key, secret)
        except engine.Halt as error:
            reason = str(error)
            if not re.fullmatch(r"[A-Z0-9_:.-]{1,160}", reason):
                reason = "TESTNET_AUTOMATION_CHECK_FAILED"
            self.pause_automation(reason)
        except Exception:
            self.pause_automation("TESTNET_AUTOMATION_CHECK_FAILED")
        return self.automation()

    def _automatic_action(self, action, key, secret, *, position_id=None):
        auto = self.automation()
        receipt = self.operate(action, str(uuid4()), auto["revision"], key, secret,
                               position_id=position_id)
        if receipt["status"] != "CONFIRMED":
            self.pause_automation(receipt.get("reason") or "TESTNET_AUTOMATION_UNCERTAIN")
        else:
            result = receipt.get("result") or {}
            result = result.get("result", result)
            auto.update(last_result=result.get("status", "TESTNET_OPERATION_CONFIRMED"))
            self.save_automation(auto)
        return receipt

    def _automatic_exit_signal(self, key, secret):
        state, config = self.state(), self.config()
        if state.get("max_loss_hit"):
            return True
        ex = self.service.exchange_factory("testnet", key, secret)
        try:
            engine.account_settings(ex)
            snapshot = ex.signed_get("/fapi/v3/account")
            if not isinstance(snapshot, dict):
                raise engine.Halt("TESTNET_EQUITY_UNVERIFIED")
            equity = engine.D(snapshot.get("totalMarginBalance"), positive=True)
            try:
                updated = engine.guarded_state(state, key, equity, engine.day(),
                                               config["daily_loss_pct"])
                engine.save_state(self.state_path, updated)
            except engine.Halt as error:
                if error.risk_state is not None:
                    engine.save_state(self.state_path, error.risk_state)
                if str(error) in {"DAILY_LOSS_LIMIT_REACHED", "DAILY_LOSS_ALREADY_HIT"}:
                    return True
                raise
            candles = engine.market_candles(ex, config["symbol"])
            return engine.crossed_down([row[2] for row in candles])
        finally:
            ex.close()
