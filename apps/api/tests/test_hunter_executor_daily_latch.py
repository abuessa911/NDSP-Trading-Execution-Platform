"""Durable private-executor risk regression; all exchange responses are synthetic."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from nex_api import hunter_live_executor as engine


def config():
    return dict(symbol="BTCUSDT", strategy=engine.STRATEGY, mode="testnet",
                daily_loss_pct="2", trade_risk_pct="1", max_exposure_pct="10", stop_pct="1")


def baseline():
    return dict(account=engine.hashlib.sha256(b"SYNTHETIC").hexdigest(), date=engine.day(),
                opening="1000", daily_pct="2")


def test_observed_daily_breach_is_persisted_and_rebound_cannot_reopen(tmp_path):
    path = tmp_path/"state.json"
    engine.save_state(path, baseline())
    ex = SimpleNamespace(key="SYNTHETIC", mode="testnet")
    with patch.object(engine, "account_snapshot", return_value=(Decimal("970"), 0, 0)):
        with pytest.raises(engine.Halt, match="DAILY_LOSS_LIMIT_REACHED"):
            engine.execute_once(config(), path, ex, allow_write=False)
    saved = engine.load_json(path)
    assert saved.get("max_loss_hit") is True
    assert saved["opening"] == "1000"
    with patch.object(engine, "account_snapshot", return_value=(Decimal("1000"), 0, 0)):
        with pytest.raises(engine.Halt, match="DAILY_LOSS_ALREADY_HIT"):
            engine.execute_once(config(), path, ex, allow_write=False)
    assert engine.load_json(path)["max_loss_hit"] is True


def test_dry_run_does_not_consume_the_actionable_closed_candle(tmp_path):
    path = tmp_path/"state.json"
    ex = SimpleNamespace(key="SYNTHETIC", mode="testnet")
    candles = [(n*900000, (n+1)*900000-1, Decimal("100")) for n in range(120)]
    with (patch.object(engine, "account_snapshot", return_value=(Decimal("1000"), 0, 0)),
          patch.object(engine, "market_candles", return_value=candles),
          patch.object(engine, "crossed_up", return_value=True)):
        first = engine.execute_once(config(), path, ex, allow_write=False)
        second = engine.execute_once(config(), path, ex, allow_write=False)
    assert first == second == {"status": "DRY_RUN", "signal": "ENTER_LONG"}
    saved = engine.load_json(path)
    assert saved.get("last_signal_candle") != candles[-1][1]
    assert saved["last_preview_candle"] == candles[-1][1]
    assert not saved.get("pending_order")


def test_daily_breach_does_not_erase_unresolved_or_foreign_state(tmp_path):
    path = tmp_path/"state.json"
    original = baseline() | {"pending_order": {"id": "unresolved"}}
    engine.save_state(path, original)
    ex = SimpleNamespace(key="SYNTHETIC", mode="testnet")
    with patch.object(engine, "account_snapshot", return_value=(Decimal("970"), 0, 0)):
        with pytest.raises(engine.Halt, match="UNRECONCILED"):
            engine.execute_once(config(), path, ex, allow_write=False)
    assert engine.load_json(path) == original
