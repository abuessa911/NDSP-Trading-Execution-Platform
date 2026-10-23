"""Hunter KSA1: isolated USD-M order executor (not mounted on public API).

No default strategy, market, risk budget, credentials, or live enablement.
Intent is durably recorded BEFORE every order write. Ambiguous outcomes lock execution.
Only explicitly approved long-only EMA(20,50) crossing strategy is supported.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlencode
import uuid

import httpx

ORIGINS = {"testnet": "https://demo-fapi.binance.com", "mainnet": "https://fapi.binance.com"}
SYMBOL = re.compile(r"^[A-Z0-9]{5,20}$")
STRATEGY = "ema20_50_long_only"
DAY_TTL = 86400

class Halt(Exception):
    def __init__(self, reason, *, risk_state=None):
        super().__init__(reason)
        self.risk_state = risk_state

def D(value, *, positive=False):
    if isinstance(value, bool):
        raise Halt("INVALID_DECIMAL")
    try:
        v = Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        raise Halt("INVALID_DECIMAL") from None
    if not v.is_finite() or v < 0 or (positive and v == 0):
        raise Halt("INVALID_DECIMAL")
    return v

def pct(value):
    v = D(value, positive=True)
    if v > 100:
        raise Halt("INVALID_PERCENT")
    return v

def quantize_down(value, step):
    value, step = D(value), D(step, positive=True)
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step

def exposure_plan(equity, opening, daily_pct, per_trade_pct, exposure_pct,
                  entry, stop, step, min_qty, min_notional, *, cost_rate="0"):
    equity, opening, entry, stop = (D(x, positive=True) for x in (equity, opening, entry, stop))
    daily_pct, per_trade_pct, exposure_pct = (pct(x) for x in (daily_pct, per_trade_pct, exposure_pct))
    if stop >= entry or per_trade_pct > daily_pct or equity > opening * Decimal("3"):
        raise Halt("RISK_CONFIGURATION_REJECTED")
    used_loss = max(Decimal(0), opening - equity)
    total_budget = opening * daily_pct / 100
    remaining = total_budget - used_loss
    if remaining <= 0:
        raise Halt("DAILY_LOSS_LIMIT_REACHED")
    risk_budget = min(equity * per_trade_pct / 100, remaining)
    costs = D(cost_rate)
    if costs > Decimal("0.05"):
        raise Halt("EXECUTION_COST_UNVERIFIED")
    unit_risk = entry - stop + entry * costs
    q_by_risk = risk_budget / unit_risk
    q_by_exposure = (equity * exposure_pct / 100) / entry
    qty = quantize_down(min(q_by_risk, q_by_exposure), step)
    if qty < D(min_qty, positive=True) or qty * entry < D(min_notional, positive=True):
        raise Halt("ORDER_BELOW_EXCHANGE_MINIMUM")
    if qty * unit_risk > risk_budget or qty * entry > equity * exposure_pct / 100:
        raise Halt("ORDER_EXCEEDS_BUDGET")
    return qty

def ema(values, period):
    values = [D(v, positive=True) for v in values]
    if len(values) < period + 3:
        raise Halt("NOT_ENOUGH_CANDLES")
    smoothing = Decimal(2) / Decimal(period + 1)
    v = sum(values[:period]) / period
    series = [v]
    for p in values[period:]:
        v = (p - v) * smoothing + v
        series.append(v)
    return series

def crossed_up(closes):
    fast = ema(closes, 20)
    slow = ema(closes, 50)
    return fast[-2] <= slow[-2] and fast[-1] > slow[-1]

def crossed_down(closes):
    fast = ema(closes, 20)
    slow = ema(closes, 50)
    return fast[-2] >= slow[-2] and fast[-1] < slow[-1]

def require_config(config):
    required = ("symbol", "strategy", "daily_loss_pct", "trade_risk_pct",
                "max_exposure_pct", "stop_pct", "mode")
    if any(k not in config for k in required):
        raise Halt("CONFIG_INCOMPLETE")
    if config["mode"] not in ORIGINS:
        raise Halt("UNSUPPORTED_MODE")
    from nex_api.strategy_signals import BY_ID
    if config["strategy"] not in BY_ID:
        raise Halt("STRATEGY_NOT_EXPLICITLY_SELECTED")
    if not SYMBOL.fullmatch(str(config["symbol"])):
        raise Halt("INVALID_SYMBOL")
    d, r, exp, stop = (pct(config[k]) for k in ("daily_loss_pct", "trade_risk_pct",
                                             "max_exposure_pct", "stop_pct"))
    leveraged = "leverage" in config
    if leveraged:
        from .hunter_leverage_risk import dec, RiskRejected
        try:
            lev = dec(config["leverage"])
            if lev != lev.to_integral_value() or not 1 <= lev <= 125:
                raise RiskRejected("INVALID_LEVERAGE")
            if r > d or exp > 100:
                raise RiskRejected("INVALID_RISK_POLICY")
            for field in ("fee_rate_each_side", "slippage_rate_each_side",
                          "maintenance_margin_rate"):
                if field not in config:
                    raise RiskRejected("MISSING_" + field.upper())
        except RiskRejected as exc:
            raise Halt(str(exc)) from exc
    elif r > d or stop > 20 or exp > 100:
        raise Halt("RISK_POLICY_INVALID")
    if config["mode"] == "mainnet" and config.get("mainnet_enabled") is not True:
        raise Halt("MAINNET_DISABLED")
    return config

class Exchange:
    """No adjustable remote hosts, redirects or environment proxies."""
    def __init__(self, mode, key, secret, transport=None):
        if not isinstance(mode, str) or mode not in ORIGINS:
            raise Halt("UNSUPPORTED_MODE")
        self.mode = mode
        self._origin = ORIGINS[mode]
        self.key = key
        self.secret = secret
        self.client = httpx.Client(base_url=ORIGINS[mode],
                                   headers={"Accept": "application/json"},
                                   transport=transport, timeout=8, trust_env=False,
                                   follow_redirects=False)
    def close(self):
        self.client.close()
    def _call(self, method, path, params=None, signed=False):
        # Network-boundary enforcement independent of signed_post/delete wrappers.
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            if self.mode != "testnet":
                raise Halt("MAINNET_ORDER_WRITES_NOT_RELEASED")
            allowed = {
                ("POST", "/fapi/v1/order"),
                ("POST", "/fapi/v1/algoOrder"),
                ("DELETE", "/fapi/v1/algoOrder"),
            }
            if (method, path) not in allowed or signed is not True:
                raise Halt("EXCHANGE_WRITE_ROUTE_FORBIDDEN")
            if Path("/run/hunter-ksa1-emergency-stop").exists():
                raise Halt("EMERGENCY_STOP_ACTIVE")
        if self.mode not in ORIGINS or ORIGINS[self.mode] != self._origin:
            raise Halt("EXCHANGE_ORIGIN_CHANGED")
        if str(self.client.base_url).rstrip("/") != self._origin:
            raise Halt("EXCHANGE_ORIGIN_CHANGED")
        public_reads = {"/fapi/v1/time", "/fapi/v1/exchangeInfo",
                        "/fapi/v1/klines", "/fapi/v1/premiumIndex"}
        private_reads = {
            "/fapi/v1/accountConfig", "/fapi/v1/symbolConfig",
            "/fapi/v1/positionSide/dual", "/fapi/v3/account",
            "/fapi/v3/positionRisk", "/fapi/v1/openOrders",
            "/fapi/v1/openAlgoOrders", "/fapi/v1/algoOrder",
            "/fapi/v1/order", "/fapi/v1/leverageBracket", "/fapi/v1/commissionRate",
        }
        if method == "GET":
            if type(signed) is not bool or path not in (private_reads if signed else public_reads):
                raise Halt("EXCHANGE_READ_ROUTE_FORBIDDEN")
        elif method not in ("POST", "DELETE"):
            raise Halt("EXCHANGE_METHOD_FORBIDDEN")
        params = dict(params or {})
        if {"signature", "timestamp", "recvWindow"} & params.keys():
            raise Halt("EXCHANGE_RESERVED_PARAMETER")
        if signed:
            params.update(timestamp=int(time.time()*1000), recvWindow=5000)
            query = urlencode(params)
            params["signature"] = hmac.new(
                self.secret.encode(), query.encode(), hashlib.sha256
            ).hexdigest()
        try:
            resp = self.client.request(method, path,
                    headers={"X-MBX-APIKEY": self.key} if signed else None,
                    params=params if method in ("GET", "DELETE") else None,
                    data=params if method == "POST" else None)
        except httpx.HTTPError:
            raise Halt("EXCHANGE_CONNECTION_AMBIGUOUS") from None
        if resp.status_code != 200:
            if resp.status_code in (418,429):
                raise Halt("EXCHANGE_RATE_LIMITED")
            if resp.status_code in (401,403):
                raise Halt("EXCHANGE_AUTH_REJECTED")
            raise Halt("EXCHANGE_REQUEST_REJECTED")
        try:
            return resp.json()
        except ValueError:
            raise Halt("EXCHANGE_RESPONSE_INVALID") from None
    def get(self, path, **params):
        return self._call("GET", path, params, signed=False)
    def signed_get(self, path, **params):
        return self._call("GET", path, params, signed=True)
    def signed_post(self, path, **params):
        if Path("/run/hunter-ksa1-emergency-stop").exists():
            raise Halt("EMERGENCY_STOP_ACTIVE")
        if self.mode != "testnet":
            raise Halt("MAINNET_ORDER_WRITES_NOT_RELEASED")
        if path not in ("/fapi/v1/algoOrder", "/fapi/v1/order"):
            raise Halt("ORDER_ROUTE_FORBIDDEN")
        return self._call("POST", path, params, signed=True)
    def signed_delete(self, path, **params):
        if Path("/run/hunter-ksa1-emergency-stop").exists():
            raise Halt("EMERGENCY_STOP_ACTIVE")
        if self.mode != "testnet":
            raise Halt("MAINNET_ORDER_WRITES_NOT_RELEASED")
        if path != "/fapi/v1/algoOrder":
            raise Halt("CANCEL_ROUTE_FORBIDDEN")
        if not params.get("clientAlgoId") and not params.get("algoId"):
            raise Halt("CANCEL_ORDER_ID_REQUIRED")
        return self._call("DELETE", path, params, signed=True)

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_state(path, state):
    tmp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex[:8])
    with open(tmp, "x", encoding="utf-8") as f:
        os.chmod(tmp, 0o600)
        json.dump(state, f, separators=(",",":"), sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def day():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def guarded_state(previous, key, equity, day_today, daily_pct):
    fp = hashlib.sha256(key.encode()).hexdigest()
    if previous.get("halted"):
        raise Halt("EXECUTION_HALTED_STICKY")
    if "account" in previous and previous["account"] != fp:
        raise Halt("ACCOUNT_CHANGED_NO_AUTORESET")
    if previous.get("date") == day_today:
        opening = D(previous["opening"], positive=True)
        if pct(previous["daily_pct"]) < pct(daily_pct):
            raise Halt("CANNOT_INCREASE_DAILY_LOSS_LIMIT")
        if previous.get("pending_order"):
            raise Halt("UNRECONCILED_ORDER_REQUIRES_OPERATOR")
        if previous.get("max_loss_hit"):
            raise Halt("DAILY_LOSS_ALREADY_HIT")
    else:
        # Expiration does not clear any unresolved order or sticky halt.
        if previous.get("pending_order"):
            raise Halt("UNRECONCILED_ORDER_REQUIRES_OPERATOR")
        opening = D(equity, positive=True)
    drawdown = max(D(0), opening-D(equity))
    blocked = drawdown >= opening * pct(daily_pct) / 100
    state = dict(previous, account=fp, date=day_today, opening=str(opening),
                 daily_pct=str(daily_pct), last_equity=str(equity),
                 max_loss_hit=blocked)
    if blocked:
        # Caller must persist state before any future order attempt. Mainnet
        # remains read-only regardless of whether this snapshot is persisted.
        raise Halt("DAILY_LOSS_LIMIT_REACHED", risk_state=state)
    return state

def signed_quantity(value):
    if isinstance(value, bool):
        raise Halt("POSITION_INVALID_QUANTITY")
    try:
        quantity = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise Halt("POSITION_INVALID_QUANTITY") from None
    if not quantity.is_finite() or abs(quantity) > Decimal("1e30"):
        raise Halt("POSITION_INVALID_QUANTITY")
    return quantity


def account_settings(ex, *, require_trading=False):
    """Configuration flags belong to accountConfig, not account V3."""
    settings = ex.signed_get("/fapi/v1/accountConfig")
    if not isinstance(settings, dict):
        raise Halt("ACCOUNT_CONFIGURATION_UNVERIFIED")
    if settings.get("dualSidePosition") is not False:
        raise Halt("HEDGE_MODE_NOT_SUPPORTED")
    if settings.get("multiAssetsMargin") is not False:
        raise Halt("ACCOUNT_COLLATERAL_MODE_UNSUPPORTED")
    if require_trading and settings.get("canTrade") is not True:
        raise Halt("ACCOUNT_TRADING_UNAVAILABLE")
    return settings


def symbol_configuration(ex, symbol, required_leverage=1, required_margin_mode=None):
    if not isinstance(symbol, str) or not SYMBOL.fullmatch(symbol) or not symbol.endswith("USDT"):
        raise Halt("INVALID_SYMBOL")
    leverage = D(required_leverage, positive=True)
    if leverage != leverage.to_integral_value() or leverage > 125:
        raise Halt("INVALID_LEVERAGE")
    rows = ex.signed_get("/fapi/v1/symbolConfig", symbol=symbol)
    if not isinstance(rows, list) or len(rows) != 1:
        raise Halt("SYMBOL_CONFIGURATION_UNVERIFIED")
    row = rows[0]
    if not isinstance(row, dict) or row.get("symbol") != symbol:
        raise Halt("SYMBOL_CONFIGURATION_UNVERIFIED")
    if type(row.get("leverage")) is not int or row["leverage"] != leverage:
        raise Halt("ACCOUNT_LEVERAGE_MISMATCH")
    if row.get("marginType") not in ("CROSSED", "ISOLATED") or row.get("isAutoAddMargin") is not False:
        raise Halt("ACCOUNT_MARGIN_MODE_UNVERIFIED")
    if required_margin_mode is not None:
        if not isinstance(required_margin_mode, str):
            raise Halt("ACCOUNT_MARGIN_MODE_MISMATCH")
        expected = {"CROSS": "CROSSED", "CROSSED": "CROSSED", "ISOLATED": "ISOLATED"}.get(required_margin_mode)
        if expected is None or row["marginType"] != expected:
            raise Halt("ACCOUNT_MARGIN_MODE_MISMATCH")
    D(row.get("maxNotionalValue"), positive=True)
    return row


def position_snapshot(ex, symbol, required_leverage=1, required_margin_mode=None):
    """V3 carries amounts; symbolConfig supplies leverage and margin mode.

    An empty V3 array is documented for a symbol with no position/open order.
    The symbol must still have an independently verified configuration.
    """
    symbol_configuration(ex, symbol, required_leverage, required_margin_mode)
    rows = ex.signed_get("/fapi/v3/positionRisk", symbol=symbol)
    if not isinstance(rows, list) or len(rows) > 1:
        raise Halt("POSITION_SNAPSHOT_INVALID")
    if not rows:
        return Decimal(0)
    row = rows[0]
    if (not isinstance(row, dict) or row.get("symbol") != symbol
        or row.get("positionSide") != "BOTH" or row.get("marginAsset") != "USDT"):
        raise Halt("POSITION_MODE_UNSUPPORTED")
    return signed_quantity(row.get("positionAmt"))


def account_snapshot(ex, symbol, required_leverage=1, required_margin_mode=None):
    """Signed read-only snapshot; never changes account leverage or margin."""
    srv = ex.get("/fapi/v1/time")
    if (type(srv) is not dict or type(srv.get("serverTime")) is not int
        or abs(srv["serverTime"] - int(time.time()*1000)) > 1500):
        raise Halt("CLOCK_UNSYNCED")
    account_settings(ex, require_trading=True)
    account = ex.signed_get("/fapi/v3/account")
    if not isinstance(account, dict) or not isinstance(account.get("positions"), list):
        raise Halt("ACCOUNT_POSITION_INVENTORY_UNVERIFIED")
    equity = D(account.get("totalMarginBalance"), positive=True)
    quantity = position_snapshot(ex, symbol, required_leverage, required_margin_mode)
    inventory = {}
    for row in account["positions"]:
        if (not isinstance(row, dict) or not isinstance(row.get("symbol"), str)
            or row["symbol"] in inventory or row.get("positionSide") != "BOTH"):
            raise Halt("ACCOUNT_POSITION_INVENTORY_UNVERIFIED")
        amount = signed_quantity(row.get("positionAmt"))
        if row["symbol"] != symbol and amount != 0:
            raise Halt("UNTRACKED_ACCOUNT_POSITION")
        inventory[row["symbol"]] = amount
    if inventory.get(symbol, Decimal(0)) != quantity:
        raise Halt("ACCOUNT_POSITION_MISMATCH")
    ordinary = ex.signed_get("/fapi/v1/openOrders", symbol=symbol)
    algo = ex.signed_get("/fapi/v1/openAlgoOrders", symbol=symbol, algoType="CONDITIONAL")
    if not isinstance(ordinary, list) or not isinstance(algo, list):
        raise Halt("OPEN_ORDERS_UNAVAILABLE")
    if ordinary or algo:
        raise Halt("EXISTING_ORDERS_REQUIRE_RECONCILIATION")
    return equity, abs(quantity), quantity

def symbol_filters(ex, symbol):
    info = ex.get("/fapi/v1/exchangeInfo")
    if not isinstance(info, dict):
        raise Halt("EXCHANGE_INFO_INVALID")
    matches = [s for s in info.get("symbols", []) if s.get("symbol")==symbol and
               s.get("status")=="TRADING" and s.get("contractType")=="PERPETUAL" and
               s.get("quoteAsset")=="USDT"]
    if len(matches) != 1:
        raise Halt("SYMBOL_NOT_TRADEABLE")
    filt = {f["filterType"]:f for f in matches[0].get("filters", [])}
    try:
        step = D(filt["MARKET_LOT_SIZE"]["stepSize"], positive=True)
        minimum = D(filt["MARKET_LOT_SIZE"]["minQty"], positive=True)
        tick = D(filt["PRICE_FILTER"]["tickSize"], positive=True)
        min_notional = D(filt["MIN_NOTIONAL"]["notional"], positive=True)
    except (KeyError, TypeError):
        raise Halt("UNSUPPORTED_EXCHANGE_FILTERS") from None
    return step, minimum, tick, min_notional

def market_candles(ex, symbol):
    srv_ms = int(ex.get("/fapi/v1/time")["serverTime"])
    rows = ex.get("/fapi/v1/klines", symbol=symbol, interval="15m", limit=120)
    if not isinstance(rows, list) or len(rows)<110:
        raise Halt("CANDLE_SERIES_TOO_SHORT")
    duration = 900000
    candles = []
    previous=None
    for r in rows:
        if not isinstance(r,list) or len(r)<7:
            raise Halt("CANDLE_PAYLOAD_INVALID")
        opened,closed = int(r[0]),int(r[6])
        if closed != opened+duration-1 or opened%duration or (previous is not None and opened != previous+duration):
            raise Halt("CANDLE_SEQUENCE_INVALID")
        previous=opened
        if closed >= srv_ms:
            continue
        candles.append((opened,closed,D(r[4],positive=True)))
    if len(candles)<100 or srv_ms-candles[-1][1]>duration*2:
        raise Halt("CANDLE_STALE_OR_INCOMPLETE")
    return candles

def status_view(config, state):
    return {"mode":config["mode"],"symbol":config["symbol"],
            "strategy":config["strategy"], "halted":bool(state.get("halted",False)),
            "pending_order":bool(state.get("pending_order",False)),
            "last_signal_candle":state.get("last_signal_candle"),
            "mainnet_enabled":bool(config.get("mainnet_enabled",False))}

def execute_once(config, state_path, ex, allow_write=False):
    if allow_write:
        if Path("/run/hunter-ksa1-emergency-stop").exists():
            raise Halt("EMERGENCY_STOP_ACTIVE")
        if getattr(ex, "mode", None) == "mainnet":
            raise Halt("MAINNET_ORDER_WRITES_NOT_RELEASED")
    symbol=config["symbol"]
    equity, position_abs, position_signed=account_snapshot(ex,symbol,config.get("leverage",1),config.get("margin_mode"))
    prev=load_json(state_path) if state_path.is_file() else {}
    try:
        state=guarded_state(prev,ex.key,equity,day(),config["daily_loss_pct"])
    except Halt as error:
        # An observed daily breach stays blocked even if equity later rebounds.
        # Never replace unresolved/foreign state on any other rejected transition.
        if error.risk_state is not None:
            save_state(state_path, error.risk_state)
        raise
    # Persist the original verified daily baseline even if market/planning reads fail.
    save_state(state_path, state)
    candles=market_candles(ex,symbol)
    close_time=candles[-1][1]
    state.setdefault("last_equity",str(equity))
    if state.get("last_signal_candle")==close_time:
        return {"status":"NO_NEW_CANDLE"}
    closes=[c[2] for c in candles]
    signal="ENTER_LONG" if crossed_up(closes) else ("EXIT_LONG" if crossed_down(closes) else "NO_SIGNAL")
    if position_signed < 0:
        if allow_write:
            raise Halt("SHORT_REQUIRES_PROTECTED_DUALSIDE_RECONCILIATION")
        return {"status": "EXISTING_SHORT_REQUIRES_RECONCILIATION", "signal": signal}
    if position_abs>0 and signal!="EXIT_LONG":
        # Cannot permit orphaned or manually created positions without stop reconciliation.
        raise Halt("OPEN_POSITION_NEEDS_OPERATOR_RECONCILIATION")
    if position_abs==0 and signal=="EXIT_LONG":
        signal="NO_SIGNAL"
    if not allow_write:
        # Previewing may persist a risk baseline, but cannot consume an order signal.
        state["last_preview_candle"] = close_time
        save_state(state_path, state)
        return {"status":"NO_SIGNAL"} if signal == "NO_SIGNAL" else {"status":"DRY_RUN","signal":signal}
    if signal=="NO_SIGNAL":
        state["last_signal_candle"] = close_time
        save_state(state_path, state)
        return {"status":"NO_SIGNAL"}
    if signal != "ENTER_LONG":
        raise Halt("EXIT_NEEDS_ORDER_RECONCILIATION")

    # All validation and sizing reads precede a write intention. Rejections
    # here cannot create a phantom pending order or require unsafe state edits.
    step,minimum,tick,min_notional=symbol_filters(ex,symbol)
    mark=ex.get("/fapi/v1/premiumIndex",symbol=symbol)
    mark_price=D(mark.get("markPrice"),positive=True)
    entry=closes[-1]
    if abs(mark_price-entry)/entry>Decimal("0.0075"):
        raise Halt("MARK_PRICE_TOO_FAR_FROM_CLOSED_CANDLE")
    if "leverage" in config:
        from .hunter_leverage_risk import plan, RiskRejected
        try:
            plan(
                equity=equity, opening_equity=state["opening"],
                margin_used=config.get("verified_margin_used", "0"),
                leverage=config["leverage"], entry_price=mark_price,
                stop_margin_pct=config["stop_pct"],
                daily_loss_pct=config["daily_loss_pct"],
                trade_risk_pct=config["trade_risk_pct"],
                max_margin_pct=config["max_exposure_pct"],
                fee_rate_each_side=config["fee_rate_each_side"],
                slippage_rate_each_side=config["slippage_rate_each_side"],
                funding_buffer_rate=config.get("funding_buffer_rate", "0"),
                maintenance_margin_rate=config["maintenance_margin_rate"])
        except RiskRejected as exc:
            raise Halt("LEVERAGE_RISK_REJECTED:" + str(exc)) from exc
        # Account-wide margin, bracket-specific liquidation and UI policy
        # are not yet verified; never place an order on an estimate.
        raise Halt("LEVERAGE_PLAN_REQUIRES_VERIFIED_ACCOUNT_MARGIN_AND_LIQUIDATION")
    stop=quantize_down(mark_price*(1-pct(config["stop_pct"])/100),tick)
    commission = ex.signed_get("/fapi/v1/commissionRate", symbol=symbol)
    if not isinstance(commission, dict) or commission.get("symbol") != symbol:
        raise Halt("EXECUTION_FEE_UNVERIFIED")
    fee = D(commission.get("takerCommissionRate"))
    if fee > Decimal("0.01"):
        raise Halt("EXECUTION_FEE_UNVERIFIED")
    # Both taker fees plus 0.1% per-side slippage and 0.1% funding buffer.
    # These are sizing buffers, not a promise of a maximum realized loss.
    cost_rate = fee * 2 + Decimal("0.003")
    qty=exposure_plan(equity,state["opening"],config["daily_loss_pct"],
                       config["trade_risk_pct"],config["max_exposure_pct"],
                       mark_price,stop,step,minimum,min_notional, cost_rate=cost_rate)

    intent_id="HK1"+uuid.uuid4().hex[:24]
    state["last_signal_candle"] = close_time
    state["pending_order"] = {"id": intent_id, "signal": signal,
        "created": int(time.time()), "quantity": str(qty), "stop_price": str(stop),
        "symbol": symbol, "cost_rate": str(cost_rate)}
    save_state(state_path, state)
    try:
        stop_result=ex.signed_post("/fapi/v1/algoOrder",
            algoType="CONDITIONAL", symbol=symbol,side="SELL",
            positionSide="BOTH",type="STOP_MARKET",
            triggerPrice=str(stop),closePosition="true",workingType="MARK_PRICE",
            clientAlgoId=intent_id+"s")
        if not isinstance(stop_result,dict) or not stop_result.get("algoId"):
            raise Halt("PROTECTIVE_STOP_NOT_CONFIRMED")
        # Verify the actual stop inventory before exposing the account.
        from nex_api.hunter_testnet_reconcile import ensure_stop
        actual_stop = ex.signed_get("/fapi/v1/algoOrder", clientAlgoId=intent_id+"s")
        inventory = ex.signed_get("/fapi/v1/openAlgoOrders", symbol=symbol,
                                   algoType="CONDITIONAL")
        ensure_stop(actual_stop, symbol, intent_id, inventory, expected_trigger=stop)
        fresh_mark = D(ex.get("/fapi/v1/premiumIndex", symbol=symbol).get("markPrice"), positive=True)
        if fresh_mark <= stop or abs(fresh_mark-mark_price)/mark_price > Decimal("0.001"):
            raise Halt("PRICE_CHANGED_BEFORE_PROTECTED_ENTRY")
        # After acceptance, never cancel protective stop on ambiguous entry outcome.
        filled=ex.signed_post("/fapi/v1/order",symbol=symbol,side="BUY",
            positionSide="BOTH",type="MARKET",quantity=str(qty),
            newClientOrderId=intent_id+"e",newOrderRespType="RESULT")
        if not isinstance(filled,dict) or filled.get("status")!="FILLED":
            raise Halt("MARKET_ENTRY_NOT_CONFIRMED")
        # Do not clear pending until runtime reconciliation confirms position
        # AND stop algo state; operator must acknowledge.
        return {"status":"ENTRY_SENT_NEEDS_RECONCILIATION","id":intent_id}
    except Halt:
        state["halted"] = True
        save_state(state_path, state)
        raise

def cli(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",required=True)
    parser.add_argument("--state",required=True)
    parser.add_argument("--mode",choices=["status","dry-run","execute"],default="status")
    args=parser.parse_args(argv)
    path=Path(args.config)
    state_path=Path(args.state)
    if not path.is_file() or path.is_symlink() or os.stat(path).st_mode & 0o077:
        raise Halt("CONFIG_MISSING_OR_INSECURE")
    if state_path.is_symlink():
        raise Halt("STATE_SYMLINK_FORBIDDEN")
    state_path.parent.mkdir(parents=True,exist_ok=True)
    os.chmod(state_path.parent,0o700)
    lock=state_path.with_suffix(".lock")
    with open(lock,"a+b") as f:
        os.chmod(lock,0o600)
        fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        config=require_config(load_json(path))
        if args.mode=="status":
            state=load_json(state_path) if state_path.exists() else {}
            print(json.dumps(status_view(config,state)))
            return 0
        key=os.getenv("HUNTER_EXEC_API_KEY")
        secret=os.getenv("HUNTER_EXEC_API_SECRET")
        if not key or not secret:
            raise Halt("SEPARATE_TRADING_CREDENTIALS_REQUIRED")
        if args.mode=="execute" and config["mode"]=="mainnet":
            raise Halt("MAINNET_ORDER_WRITES_NOT_RELEASED")
        if args.mode=="execute" and os.getenv("HUNTER_LIVE_CONFIRM") != "EXPLICITLY_APPROVED":
            raise Halt("OPERATOR_TESTNET_CONFIRMATION_REQUIRED")
        ex=Exchange(config["mode"],key,secret)
        try:
            output=execute_once(config,state_path,ex,allow_write=args.mode=="execute")
            print(json.dumps(output))
            return 0
        finally:
            ex.close()

if __name__ == "__main__":
    try:
        sys.exit(cli())
    except Halt as exc:
        print("BLOCKED="+str(exc),file=sys.stderr)
        sys.exit(2)
