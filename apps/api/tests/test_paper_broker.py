"""Real SQLite transactions and deterministic candles; zero network access."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal as D
import uuid

import pytest

from nex_api.binance_closed_candles import ClosedCandle, ClosedCandleBatch
from nex_api.paper_broker import PaperBroker, PaperRejected

SPAN = 300000
NOW = 1800000030000
SCOPE = "tenant-a:owner-a"
PROFILE = dict(mode="SPECULATIVE", symbol="BTCUSDT", interval="5m",
               execution_method="MANUAL", leverage=10, margin_mode="ISOLATED")
POLICY = dict(daily_loss_pct="2", trade_risk_pct="1", max_margin_pct="10",
              stop_distance_pct="1", take_profit_distance_pct="2",
              fee_pct="0", slippage_pct="0")


def candle(close_ms, opened="100", high="100", low="100", close="100"):
    return ClosedCandle(symbol="BTCUSDT", market="usdm_futures", interval="5m",
        open_time_ms=close_ms-SPAN+1, close_time_ms=close_ms,
        open=D(opened), high=D(high), low=D(low), close=D(close), volume=D("10"))


def batch(now=NOW, *, latest=None):
    last = now // SPAN * SPAN - 1
    rows = tuple(candle(last-(3-i)*SPAN) for i in range(4))
    if latest:
        rows = rows[:-1] + (candle(last, **latest),)
    return ClosedCandleBatch(market="usdm_futures", symbol="BTCUSDT", interval="5m",
                            server_time_ms=now, candles=rows)


@pytest.fixture
def broker(tmp_path):
    clock = [NOW]
    value = PaperBroker(tmp_path/"private"/"paper.sqlite3", clock=lambda: clock[0])
    value.configure(SCOPE, initial_equity="1000", policy=POLICY,
                    profile=PROFILE, strategy_id="trend-ladder")
    return value, clock


def submit(broker, *, action="OPEN", side="LONG", quantity="1", request_id=None, data=None):
    return broker.submit(SCOPE, data or batch(broker.clock()),
        action=action, side=side, quantity=quantity,
        request_id=request_id or str(uuid.uuid4()), current_profile=PROFILE)


def test_real_ledger_survives_restart_and_is_private(broker):
    value, clock = broker
    submit(value)
    restarted = PaperBroker(value.path, clock=lambda: clock[0])
    assert restarted.view(SCOPE)["position"]["side"] == "LONG"
    assert restarted.path.stat().st_mode & 0o777 == 0o600
    assert restarted.path.parent.stat().st_mode & 0o777 == 0o700
    with pytest.raises(PaperRejected, match="NOT_CONFIGURED"):
        restarted.view("tenant-b:owner-b")


def test_duplicate_request_cannot_fill_twice_or_change_quantity(broker):
    value, _ = broker
    key = str(uuid.uuid4())
    first = submit(value, request_id=key)
    assert submit(value, request_id=key) == first
    assert value.view(SCOPE)["total_orders"] == 1
    with pytest.raises(PaperRejected, match="IDEMPOTENCY_CONFLICT"):
        submit(value, request_id=key, quantity="2")
    assert value.view(SCOPE)["total_orders"] == 1


@pytest.mark.parametrize("side,price", [("LONG", "101"), ("SHORT", "99")])
def test_both_sides_have_real_virtual_pnl_and_close_history(broker, side, price):
    value, clock = broker
    submit(value, side=side)
    clock[0] += SPAN
    data = batch(clock[0], latest=dict(opened=price, high=price, low=price, close=price))
    result = submit(value, action="CLOSE", side=side, data=data)
    assert result["action"] == "CLOSE" and D(result["net_pnl"]) == 1
    view = value.view(SCOPE)
    assert view["position"] is None and D(view["cash"]) == 1001
    assert view["total_orders"] == 2


def test_entry_does_not_read_its_own_already_completed_bar_as_future(broker):
    value, _ = broker
    entry_bar = batch(latest=dict(opened="100", high="110", low="90", close="100"))
    submit(value, data=entry_bar)
    value.cycle(SCOPE, entry_bar)
    assert value.view(SCOPE)["position"] is not None
    assert value.view(SCOPE)["total_orders"] == 1


def test_both_exits_hit_same_future_bar_uses_stop_and_worse_gap(broker):
    value, clock = broker
    submit(value)
    clock[0] += SPAN
    next_bar = batch(clock[0], latest=dict(opened="95", high="110", low="94", close="100"))
    view = value.cycle(SCOPE, next_bar)
    closed = view["orders"][0]
    assert closed["reason"] == "STOP_LOSS" and D(closed["price"]) == 95
    assert D(closed["net_pnl"]) == -5 and view["position"] is None


def test_daily_loss_latches_and_cannot_be_reset_by_capital_or_policy(broker):
    value, clock = broker
    submit(value, quantity="10")
    clock[0] += SPAN
    data = batch(clock[0], latest=dict(opened="95", high="100", low="94", close="95"))
    view = value.cycle(SCOPE, data)
    assert view["daily_hit"] and D(view["cash"]) == 950
    with pytest.raises(PaperRejected):
        submit(value, data=data)
    with pytest.raises(PaperRejected, match="CAPITAL_RESET_FORBIDDEN"):
        value.configure(SCOPE, initial_equity="2000", policy=POLICY, profile=PROFILE, strategy_id="trend-ladder")
    with pytest.raises(PaperRejected, match="DAILY_LIMIT_INCREASE_FORBIDDEN"):
        value.configure(SCOPE, initial_equity="1000", policy=POLICY | {"daily_loss_pct": "3"}, profile=PROFILE, strategy_id="trend-ladder")


def test_protective_exit_is_not_rolled_back_by_manual_close_race(broker):
    value, clock = broker
    submit(value)
    clock[0] += SPAN
    data = batch(clock[0], latest=dict(opened="95", high="100", low="94", close="95"))
    ack = submit(value, action="CLOSE", data=data)
    assert ack["status"] == "ALREADY_FLAT_SIMULATED"
    assert value.view(SCOPE)["position"] is None
    assert D(value.view(SCOPE)["cash"]) == 995


def test_two_simultaneous_open_requests_cannot_overallocate(broker):
    value, _ = broker
    def attempt(_):
        try:
            return submit(value)["action"]
        except PaperRejected:
            return "BLOCKED"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [1, 2]))
    assert sorted(results) == ["BLOCKED", "OPEN"]
    assert value.view(SCOPE)["total_orders"] == 1


def test_virtual_automatic_cycle_has_durable_journal_and_no_duplicate_bar(broker):
    value, clock = broker
    profile = PROFILE | {"execution_method": "AUTOMATIC"}
    value.configure(SCOPE, initial_equity="1000", policy=POLICY, profile=profile, strategy_id="trend-ladder")
    value.set_running(SCOPE, True, profile)
    value.cycle(SCOPE, batch(), current_profile=profile, signal="LONG_CANDIDATE")
    assert value.view(SCOPE)["total_orders"] == 1
    value.cycle(SCOPE, batch(), current_profile=profile, signal="LONG_CANDIDATE")
    assert value.view(SCOPE)["total_orders"] == 1
    changed = profile | {"symbol": "ETHUSDT"}
    result = value.cycle(SCOPE, batch(), current_profile=changed)
    assert result["running"] is False and result["halt_reason"] == "PAPER_WORKSPACE_CHANGED"


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "0", True])
def test_invalid_quantity_cannot_change_paper_state(broker, value):
    value_broker, _ = broker
    with pytest.raises(PaperRejected):
        submit(value_broker, quantity=value)
    assert value_broker.view(SCOPE)["total_orders"] == 0


def test_stale_or_future_market_cannot_fill(broker):
    value, _ = broker
    data = batch()
    for bad in (replace(data, server_time_ms=NOW-60000),
                replace(data, server_time_ms=data.candles[-1].close_time_ms)):
        with pytest.raises(PaperRejected):
            submit(value, data=bad)
    assert value.view(SCOPE)["position"] is None


def test_fees_and_slippage_are_charged_from_virtual_cash(broker):
    value, clock = broker
    policy = POLICY | {"fee_pct": ".04", "slippage_pct": ".01"}
    value.configure(SCOPE, initial_equity="1000", policy=policy, profile=PROFILE, strategy_id="trend-ladder")
    opened = submit(value)
    assert D(opened["price"]) > 100 and D(opened["fee"]) > 0
    closed = submit(value, action="CLOSE")
    assert D(closed["net_pnl"]) < 0
    assert D(value.view(SCOPE)["cash"]) < 1000


def test_stale_strategy_fetch_cannot_open_after_account_reconfiguration(broker):
    value, _ = broker
    auto = PROFILE | {"execution_method": "AUTOMATIC"}
    value.configure(SCOPE, initial_equity="1000", policy=POLICY, profile=auto, strategy_id="trend-ladder")
    value.set_running(SCOPE, True, auto)
    old = value.metadata(SCOPE)["configuration_revision"]
    value.configure(SCOPE, initial_equity="1000", policy=POLICY, profile=auto, strategy_id="mean-return")
    with pytest.raises(PaperRejected, match="CONFIGURATION_CHANGED"):
        value.set_running(SCOPE, True, auto, expected_revision=old)
    value.set_running(SCOPE, True, auto)
    value.cycle(SCOPE, batch(), current_profile=auto, signal="LONG_CANDIDATE", expected_revision=old)
    assert value.view(SCOPE)["position"] is None
    fresh = value.metadata(SCOPE)["configuration_revision"]
    value.cycle(SCOPE, batch(), current_profile=auto, signal="SHORT_CANDIDATE", expected_revision=fresh)
    assert value.view(SCOPE)["position"]["side"] == "SHORT"


def test_delayed_close_intent_cannot_close_a_replacement_position(broker):
    value, _ = broker
    first = submit(value)
    submit(value, action="CLOSE")
    replacement = submit(value, side="SHORT")
    with pytest.raises(PaperRejected, match="POSITION_CHANGED"):
        value.submit(SCOPE, batch(), action="CLOSE", side="LONG", quantity=None,
            request_id=str(uuid.uuid4()), current_profile=PROFILE, expected_position_id=first["id"])
    assert value.view(SCOPE)["position"]["id"] == replacement["id"]
    assert value.view(SCOPE)["total_orders"] == 3
