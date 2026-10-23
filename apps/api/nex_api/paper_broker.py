"""Durable virtual-money broker. No credentials, exchange writes or real funds.

Fills use verified completed candles, configurable simulated fees/slippage and a
one-position account. This is an operational simulator, not a Binance ledger.
A candle hitting both exits uses the adverse stop first. Gaps through a stop
receive the worse opening price. Same-candle entry lookahead is forbidden.
"""
from __future__ import annotations
from contextlib import contextmanager, closing
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid

from nex_api.binance_closed_candles import INTERVAL_MS

class PaperRejected(ValueError):
    pass

def number(value, *, positive=False):
    if isinstance(value, bool):
        raise PaperRejected("PAPER_INVALID_NUMBER")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise PaperRejected("PAPER_INVALID_NUMBER") from None
    if not result.is_finite() or abs(result) > Decimal("1e15") or (positive and result <= 0):
        raise PaperRejected("PAPER_INVALID_NUMBER")
    return result

def utc_day(now_ms):
    return datetime.fromtimestamp(now_ms / 1000, timezone.utc).date().isoformat()

def json_text(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))

POLICY_FIELDS = frozenset({
    "daily_loss_pct", "trade_risk_pct", "max_margin_pct",
    "stop_distance_pct", "take_profit_distance_pct", "fee_pct", "slippage_pct",
})
PROFILE_FIELDS = ("mode", "symbol", "interval", "execution_method", "leverage", "margin_mode")

def policy_checked(policy, leverage):
    if not isinstance(policy, dict) or set(policy) != POLICY_FIELDS:
        raise PaperRejected("PAPER_POLICY_INCOMPLETE")
    values = {key: number(value) for key, value in policy.items()}
    if (not 0 < values["trade_risk_pct"] <= values["daily_loss_pct"] <= 10
        or not 0 < values["max_margin_pct"] <= 100
        or not 0 < values["stop_distance_pct"] < Decimal(80) / leverage
        or not 0 < values["take_profit_distance_pct"] < 100
        or not 0 <= values["fee_pct"] <= 1
        or not 0 <= values["slippage_pct"] <= 1):
        raise PaperRejected("PAPER_POLICY_INVALID")
    return {key: str(value) for key, value in values.items()}

def profile_checked(profile):
    from nex_api.routes.trading_profile import WorkspaceSettings
    try:
        return WorkspaceSettings.model_validate(profile).model_dump()
    except ValueError:
        raise PaperRejected("PAPER_PROFILE_INVALID") from None

def checked_batch(batch, now_ms):
    if (batch.source != "BINANCE_PUBLIC_REST" or batch.market != "usdm_futures"
        or batch.interval not in INTERVAL_MS or not batch.candles
        or abs(batch.server_time_ms - now_ms) > 30_000):
        raise PaperRejected("PAPER_MARKET_UNVERIFIED")
    span = INTERVAL_MS[batch.interval]
    previous = None
    for row in batch.candles:
        if (row.symbol != batch.symbol or row.interval != batch.interval
            or row.market != batch.market or row.open_time_ms % span
            or row.close_time_ms != row.open_time_ms + span - 1
            or row.close_time_ms >= batch.server_time_ms
            or (previous is not None and row.open_time_ms != previous + span)):
            raise PaperRejected("PAPER_CANDLE_INVALID")
        opened, high, low, close = (number(getattr(row, key), positive=True)
                                     for key in ("open", "high", "low", "close"))
        if low > min(opened, close) or high < max(opened, close) or number(row.volume) < 0:
            raise PaperRejected("PAPER_CANDLE_INVALID")
        previous = row.open_time_ms
    if batch.server_time_ms - batch.candles[-1].close_time_ms > 2 * span + 1:
        raise PaperRejected("PAPER_MARKET_STALE")
    return batch.candles

class PaperBroker:
    def __init__(self, path, *, clock=None):
        self.path = Path(path)
        self.clock = clock or (lambda: int(time.time() * 1000))
        parent = self.path.parent
        if parent.exists():
            if parent.is_symlink() or parent.stat().st_uid != os.geteuid() or parent.stat().st_mode & 0o077:
                raise PaperRejected("PAPER_DIRECTORY_INSECURE")
        else:
            parent.mkdir(mode=0o700, parents=True)
        if self.path.is_symlink():
            raise PaperRejected("PAPER_LEDGER_SYMLINK")
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if info.st_uid != os.geteuid() or info.st_mode & 0o077:
                raise PaperRejected("PAPER_LEDGER_INSECURE")
        finally:
            os.close(fd)
        with closing(self.connect()) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS paper_accounts (
                    scope TEXT PRIMARY KEY, state TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS paper_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    scope TEXT NOT NULL, request_id TEXT NOT NULL,
                    request_hash TEXT NOT NULL, payload TEXT NOT NULL,
                    UNIQUE(scope, request_id)
                );
                CREATE INDEX IF NOT EXISTS paper_events_scope ON paper_events(scope, seq);
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=5000")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _load(self, db, scope):
        if not re.fullmatch(r"[A-Za-z0-9:_-]{1,120}", scope):
            raise PaperRejected("PAPER_SCOPE_INVALID")
        row = db.execute("SELECT state FROM paper_accounts WHERE scope=?", (scope,)).fetchone()
        if row is None:
            raise PaperRejected("PAPER_ACCOUNT_NOT_CONFIGURED")
        try:
            state = json.loads(row["state"])
            number(state["cash"])
            number(state["opening"], positive=True)
            profile = profile_checked(state["profile"])
            policy_checked(state["policy"], profile["leverage"])
            if type(state["running"]) is not bool or type(state["daily_hit"]) is not bool:
                raise ValueError()
            # Old ledgers gain a stable configuration identity without resetting funds.
            state.setdefault("configuration_revision", hashlib.sha256(json_text({
                key: state[key] for key in ("profile", "policy", "strategy_id")
            }).encode()).hexdigest())
            return state
        except (ValueError, TypeError, KeyError):
            raise PaperRejected("PAPER_LEDGER_INVALID") from None

    def _save(self, db, scope, state):
        db.execute("UPDATE paper_accounts SET state=? WHERE scope=?", (json_text(state), scope))

    def _event(self, db, scope, request_id, fingerprint, payload):
        db.execute("INSERT INTO paper_events(scope,request_id,request_hash,payload) VALUES (?,?,?,?)",
                   (scope, request_id, fingerprint, json_text(payload)))

    def _existing(self, db, scope, request_id, fingerprint):
        try:
            uuid.UUID(request_id)
        except (ValueError, AttributeError, TypeError):
            raise PaperRejected("PAPER_REQUEST_ID_INVALID") from None
        row = db.execute("SELECT request_hash,payload FROM paper_events WHERE scope=? AND request_id=?",
                         (scope, request_id)).fetchone()
        if row:
            if row["request_hash"] != fingerprint:
                raise PaperRejected("PAPER_IDEMPOTENCY_CONFLICT")
            return json.loads(row["payload"])
        return None

    def configure(self, scope, *, initial_equity, policy, profile, strategy_id):
        from nex_api.strategy_signals import BY_ID
        initial = number(initial_equity, positive=True)
        selected = profile_checked(profile)
        rules = policy_checked(policy, selected["leverage"])
        if strategy_id not in BY_ID:
            raise PaperRejected("PAPER_STRATEGY_INVALID")
        now = self.clock()
        with self.transaction() as db:
            exists = db.execute("SELECT 1 FROM paper_accounts WHERE scope=?", (scope,)).fetchone()
            if exists:
                state = self._load(db, scope)
                if state["position"]:
                    raise PaperRejected("PAPER_CONFIG_REQUIRES_FLAT_ACCOUNT")
                if initial != number(state["initial"]):
                    raise PaperRejected("PAPER_CAPITAL_RESET_FORBIDDEN")
                if utc_day(now) == state["day"] and number(rules["daily_loss_pct"]) > number(state["policy"]["daily_loss_pct"]):
                    raise PaperRejected("PAPER_DAILY_LIMIT_INCREASE_FORBIDDEN")
                state.update(policy=rules, profile=selected, strategy_id=strategy_id,
                             running=False, halt_reason=None, last_signal=None, configuration_revision=str(uuid.uuid4()))
                self._save(db, scope, state)
            else:
                if not re.fullmatch(r"[A-Za-z0-9:_-]{1,120}", scope):
                    raise PaperRejected("PAPER_SCOPE_INVALID")
                state = dict(initial=str(initial), cash=str(initial), opening=str(initial),
                    day=utc_day(now), daily_hit=False, running=False, halt_reason=None,
                    position=None, policy=rules, profile=selected, strategy_id=strategy_id,
                    last_signal=None, created_ms=now, configuration_revision=str(uuid.uuid4()))
                db.execute("INSERT INTO paper_accounts(scope,state) VALUES (?,?)", (scope, json_text(state)))
        return self.view(scope)

    def metadata(self, scope):
        with closing(self.connect()) as db:
            return self._load(db, scope)

    def active_scopes(self):
        with closing(self.connect()) as db:
            rows = db.execute("SELECT scope,state FROM paper_accounts").fetchall()
        # A malformed account must not prevent protective checks for others.
        active = []
        for row in rows:
            try:
                state = json.loads(row["state"])
                if state.get("running") or state.get("position"):
                    active.append(row["scope"])
            except (ValueError, AttributeError):
                continue
        return active

    def _equity(self, state, price=None):
        pnl = Decimal(0)
        position = state["position"]
        if position:
            if price is None:
                raise PaperRejected("PAPER_POSITION_QUOTE_REQUIRED")
            sign = 1 if position["side"] == "LONG" else -1
            pnl = number(position["quantity"]) * (price - number(position["entry"])) * sign
        return number(state["cash"]) + pnl

    def _daily(self, state, equity):
        day = utc_day(self.clock())
        if day < state["day"]:
            raise PaperRejected("PAPER_CLOCK_MOVED_BACKWARDS")
        if day != state["day"]:
            # First observed virtual account valuation of each UTC day.
            state.update(day=day, daily_hit=equity <= 0)
            if equity > 0:
                state["opening"] = str(equity)
        if equity <= 0 or number(state["opening"]) - equity >= number(state["opening"]) * number(state["policy"]["daily_loss_pct"]) / 100:
            state.update(daily_hit=True, running=False)

    def _close(self, db, scope, state, price, reason, request_id, fingerprint, candle_ms):
        position = state["position"]
        if not position:
            raise PaperRejected("PAPER_POSITION_MISSING")
        sign = 1 if position["side"] == "LONG" else -1
        policy = position["policy"]
        fill = price * (1 - sign * number(policy["slippage_pct"]) / 100)
        quantity = number(position["quantity"])
        gross = quantity * (fill - number(position["entry"])) * sign
        fee = quantity * fill * number(policy["fee_pct"]) / 100
        state["cash"] = str(number(state["cash"]) + gross - fee)
        payload = dict(id=request_id, action="CLOSE", status="FILLED_SIMULATED",
            symbol=position["symbol"], side=position["side"], quantity=str(quantity),
            price=str(fill), fee=str(fee), net_pnl=str(gross - fee - number(position["entry_fee"])),
            reason=reason, candle_closed_ms=candle_ms, created_ms=self.clock())
        self._event(db, scope, request_id, fingerprint, payload)
        state["position"] = None
        return payload

    def _advance(self, db, scope, state, batch):
        candles = checked_batch(batch, self.clock())
        position = state["position"]
        if position:
            if batch.symbol != position["symbol"] or batch.interval != position["interval"]:
                raise PaperRejected("PAPER_POSITION_MARKET_MISMATCH")
            pending = [c for c in candles if c.close_time_ms > position["last_candle_ms"]]
            if pending and pending[0].open_time_ms > position["last_candle_ms"] + 1:
                state.update(running=False, halt_reason="PAPER_CANDLE_HISTORY_GAP")
            else:
                for candle in pending:
                    stop, target = number(position["stop"]), number(position["target"])
                    long = position["side"] == "LONG"
                    stop_hit = candle.low <= stop if long else candle.high >= stop
                    target_hit = candle.high >= target if long else candle.low <= target
                    if stop_hit or target_hit:
                        reason = "STOP_LOSS" if stop_hit else "TAKE_PROFIT"
                        price = (min(candle.open, stop) if long else max(candle.open, stop)) if stop_hit else target
                        event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "paper-exit:" + scope + ":" + position["id"] + ":" + str(candle.close_time_ms)))
                        self._close(db, scope, state, price, reason, event_id, "protective-exit", candle.close_time_ms)
                        break
                    position["last_candle_ms"] = candle.close_time_ms
        mark = candles[-1].close
        self._daily(state, self._equity(state, mark))
        return mark

    def cycle(self, scope, batch, *, current_profile=None, signal=None, expected_revision=None):
        with self.transaction() as db:
            state = self._load(db, scope)
            mark = self._advance(db, scope, state, batch)
            same_configuration = expected_revision is None or expected_revision == state["configuration_revision"]
            if same_configuration and current_profile is not None and profile_checked(current_profile) != state["profile"]:
                state.update(running=False, halt_reason="PAPER_WORKSPACE_CHANGED")
            if same_configuration and current_profile is not None and state["running"] and not state["position"] and not state["daily_hit"] and not state["halt_reason"]:
                token = str(batch.candles[-1].close_time_ms)
                if state["last_signal"] != token:
                    state["last_signal"] = token
                    if signal in ("LONG_CANDIDATE", "SHORT_CANDIDATE"):
                        side = "LONG" if signal == "LONG_CANDIDATE" else "SHORT"
                        key = str(uuid.uuid5(uuid.NAMESPACE_URL, "paper-auto:" + scope + ":" +
                            state["profile"]["symbol"] + ":" + state["profile"]["interval"] + ":" +
                            state["strategy_id"] + ":" + token))
                        try:
                            if self._existing(db, scope, key, "automatic-entry") is None:
                                payload = self._open(db, scope, state, batch, side, None, key)
                                self._event(db, scope, key, "automatic-entry", payload)
                        except PaperRejected as error:
                            state.update(running=False, halt_reason=str(error))
            self._save(db, scope, state)
        return self.view(scope, mark)

    def _open(self, db, scope, state, batch, side, quantity, request_id):
        if side not in ("LONG", "SHORT"):
            raise PaperRejected("PAPER_SIDE_INVALID")
        candles = checked_batch(batch, self.clock())
        if batch.symbol != state["profile"]["symbol"] or batch.interval != state["profile"]["interval"]:
            raise PaperRejected("PAPER_WORKSPACE_MARKET_MISMATCH")
        if state["position"] or state["daily_hit"] or state["halt_reason"]:
            raise PaperRejected("PAPER_ENTRY_BLOCKED")
        equity = self._equity(state)
        self._daily(state, equity)
        if state["daily_hit"]:
            raise PaperRejected("PAPER_DAILY_LOSS_LIMIT_REACHED")
        policy, leverage = state["policy"], state["profile"]["leverage"]
        sign = 1 if side == "LONG" else -1
        fill = candles[-1].close * (1 + sign * number(policy["slippage_pct"]) / 100)
        distance = number(policy["stop_distance_pct"]) / 100
        fee_rate = number(policy["fee_pct"]) / 100
        remaining = number(state["opening"]) * number(policy["daily_loss_pct"]) / 100 - max(Decimal(0), number(state["opening"]) - equity)
        budget = min(equity * number(policy["trade_risk_pct"]) / 100, remaining)
        maximum_notional = equity * number(policy["max_margin_pct"]) / 100 * leverage
        risk_per_unit = fill * (distance + 2 * fee_rate + 2 * number(policy["slippage_pct"]) / 100)
        if quantity is None:
            qty = min(budget / risk_per_unit, maximum_notional / fill).quantize(Decimal(".00000001"), rounding=ROUND_DOWN)
        else:
            qty = number(quantity, positive=True)
        if qty <= 0 or qty * risk_per_unit > budget or qty * fill > maximum_notional:
            raise PaperRejected("PAPER_ORDER_EXCEEDS_POLICY")
        fee = qty * fill * fee_rate
        if qty * fill / leverage + fee > equity:
            raise PaperRejected("PAPER_INSUFFICIENT_MARGIN")
        stop = fill * (1 - sign * distance)
        target = fill * (1 + sign * number(policy["take_profit_distance_pct"]) / 100)
        if min(stop, target) <= 0:
            raise PaperRejected("PAPER_EXIT_PRICE_INVALID")
        state["cash"] = str(number(state["cash"]) - fee)
        state["position"] = dict(id=request_id, symbol=batch.symbol, interval=batch.interval,
            side=side, quantity=str(qty), entry=str(fill), stop=str(stop), target=str(target),
            leverage=leverage, margin=str(qty * fill / leverage), entry_fee=str(fee),
            last_candle_ms=candles[-1].close_time_ms, opened_ms=self.clock(), policy=dict(policy))
        payload = dict(id=request_id, action="OPEN", status="FILLED_SIMULATED", symbol=batch.symbol,
            side=side, quantity=str(qty), price=str(fill), fee=str(fee), net_pnl=None,
            reason="VIRTUAL_ENTRY", candle_closed_ms=candles[-1].close_time_ms, created_ms=self.clock())
        return payload

    def submit(self, scope, batch, *, action, side, quantity, request_id, current_profile,
               expected_revision=None, expected_position_id=None):
        intent = dict(action=action, side=side, quantity=quantity)
        if expected_position_id is not None:
            intent["position_id"] = expected_position_id
        fingerprint = hashlib.sha256(json_text(intent).encode()).hexdigest()
        with self.transaction() as db:
            previous = self._existing(db, scope, request_id, fingerprint)
            if previous is not None:
                return previous
            state = self._load(db, scope)
            if action == "OPEN":
                if expected_revision is not None and expected_revision != state["configuration_revision"]:
                    raise PaperRejected("PAPER_CONFIGURATION_CHANGED")
                if profile_checked(current_profile) != state["profile"]:
                    raise PaperRejected("PAPER_WORKSPACE_CHANGED")
                if state["running"] or state["profile"]["execution_method"] != "MANUAL":
                    raise PaperRejected("PAPER_MANUAL_MODE_REQUIRED")
                self._daily(state, self._equity(state))
                payload = self._open(db, scope, state, batch, side, quantity, request_id)
                self._event(db, scope, request_id, fingerprint, payload)
            elif action == "CLOSE":
                # Bind this close to its intended virtual position, never a later one.
                if expected_position_id is not None:
                    if state["position"] and state["position"]["id"] != expected_position_id:
                        raise PaperRejected("PAPER_POSITION_CHANGED")
                    original = db.execute("SELECT payload FROM paper_events WHERE scope=? AND request_id=?",
                                          (scope, expected_position_id)).fetchone()
                    if original is None or json.loads(original["payload"]).get("action") != "OPEN":
                        raise PaperRejected("PAPER_POSITION_MISSING")
                # Closing remains available after a policy stop or workspace change.
                self._advance(db, scope, state, batch)
                if not state["position"]:
                    payload = dict(id=request_id, action="CLOSE_ACK", status="ALREADY_FLAT_SIMULATED",
                        symbol=batch.symbol, side=side, quantity="0", price=None, fee="0",
                        net_pnl=None, reason="PROTECTIVE_EXIT_ALREADY_APPLIED",
                        candle_closed_ms=batch.candles[-1].close_time_ms, created_ms=self.clock())
                    self._event(db, scope, request_id, fingerprint, payload)
                else:
                    payload = self._close(db, scope, state, batch.candles[-1].close,
                        "MANUAL_CLOSE", request_id, fingerprint, batch.candles[-1].close_time_ms)
                self._daily(state, self._equity(state))
            else:
                raise PaperRejected("PAPER_ACTION_INVALID")
            self._save(db, scope, state)
        return payload

    def set_running(self, scope, enabled, current_profile=None, *, expected_revision=None):
        if type(enabled) is not bool:
            raise PaperRejected("PAPER_RUNNING_INVALID")
        with self.transaction() as db:
            state = self._load(db, scope)
            if enabled:
                if expected_revision is not None and expected_revision != state["configuration_revision"]:
                    raise PaperRejected("PAPER_CONFIGURATION_CHANGED")
                if (profile_checked(current_profile) != state["profile"]
                    or state["profile"]["execution_method"] != "AUTOMATIC"
                    or state["daily_hit"] or state["halt_reason"]):
                    raise PaperRejected("PAPER_AUTOMATIC_NOT_READY")
            state["running"] = enabled
            self._save(db, scope, state)
        return {"running": enabled, "mode": "PAPER", "real_orders_enabled": False}

    def view(self, scope, mark=None):
        with closing(self.connect()) as db:
            state = self._load(db, scope)
            rows = db.execute("SELECT payload FROM paper_events WHERE scope=? AND json_extract(payload,'$.action') IN ('OPEN','CLOSE') ORDER BY seq DESC LIMIT 100", (scope,)).fetchall()
            total = db.execute("SELECT count(*) FROM paper_events WHERE scope=? AND json_extract(payload,'$.action') IN ('OPEN','CLOSE')", (scope,)).fetchone()[0]
        equity = self._equity(state, mark) if not state["position"] or mark is not None else None
        return dict(mode="PAPER", real_orders_enabled=False, configured=True,
            cash=state["cash"], initial=state["initial"], equity=str(equity) if equity is not None else None,
            cash_change=str(number(state["cash"]) - number(state["initial"])),
            unrealized_pnl=str(equity - number(state["cash"])) if equity is not None else None,
            quote_available=not state["position"] or mark is not None, position=state["position"],
            daily_opening=state["opening"], daily_hit=state["daily_hit"], utc_day=state["day"],
            running=state["running"], halt_reason=state["halt_reason"], policy=state["policy"],
            profile=state["profile"], strategy_id=state["strategy_id"],
            orders=[json.loads(row["payload"]) for row in rows], total_orders=total,
            fill_model="COMPLETED_CANDLE_VIRTUAL_ONLY_STOP_FIRST_ON_AMBIGUITY")
