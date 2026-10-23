from types import SimpleNamespace as S
import pytest

from nex_api.strategy_risk_decision import decide

IDS = ("trend-ladder", "range-fade", "breakout-scout", "mean-return", "divergence-rsi")

def strategy(sid, signal="NEUTRAL", status="SCANNING", symbol="BTCUSDT", interval="1h", **kwargs):
    return S(id=sid, signal=signal, status=status, symbol=symbol, interval=interval,
             execution_enabled=False, ndsp_verified=False, expires_in_seconds=600,
             last_checked_ms=10000, last_candle_closed_ms=9000, **kwargs)

def risk(state="MONITORING", daily_loss_pct="1.2345", new_entries_blocked=False):
    return S(state=state, configured=True, daily_loss_pct=daily_loss_pct,
             new_entries_blocked=new_entries_blocked,
             opening_equity="1000", current_equity="990")

def rows(**signals):
    return [strategy(x, signal=signals.get(x, "NEUTRAL")) for x in IDS]

def test_no_candidate():
    view = decide(rows(),risk())
    assert view["execution_allowed"] is False
    assert "NO_ACTIONABLE_CANDIDATE" in view["blockers"]
    assert view["candidates"] == []

@pytest.mark.parametrize("strategy_id", IDS)
def test_all_five_strategy_candidates_advisory_only(strategy_id):
    view = decide(rows(**{strategy_id: "LONG_CANDIDATE"}), risk())
    assert view["candidates"][0]["decision"] == "LONG_RESEARCH"
    assert view["candidates"][0]["evidence"] == [strategy_id]
    assert view["mainnet_orders_enabled"] is False
    assert view["ndsp_execution_verified"] is False

def test_conflicting_signals_never_become_order():
    r = rows(**{"trend-ladder":"LONG_CANDIDATE","mean-return":"SHORT_CANDIDATE"})
    view = decide(r,risk())
    assert view["candidates"][0]["decision"] == "CONFLICT"
    assert "CONFLICTING_STRATEGY_SIGNALS" in view["blockers"]
    assert view["execution_allowed"] is False

def test_percent_stays_user_selected_and_no_default():
    v = decide(rows(), risk(daily_loss_pct="0.1125"))
    assert v["risk"]["daily_loss_pct"] == "0.1125"
    assert decide(rows(),S(state="NOT_CONFIGURED", configured=False,
                           new_entries_blocked=True,daily_loss_pct=None))["risk"]["daily_loss_pct"] is None

@pytest.mark.parametrize("state",["NOT_CONFIGURED", "READONLY_ACCOUNT_MISSING",
  "ACCOUNT_CHANGED_REVIEW_REQUIRED", "DAILY_LOSS_LIMIT_REACHED", "UNAVAILABLE"])
def test_risk_status_failclosed(state):
    v=decide(rows(**{"trend-ladder":"LONG_CANDIDATE"}),risk(state=state))
    assert "RISK_EQUITY_NOT_MONITORING" in v["blockers"]
    assert v["execution_allowed"] is False

def test_limit_hit_denies():
    v=decide(rows(),risk(new_entries_blocked=True))
    assert "RISK_BLOCKED" in v["blockers"]

def test_stalled_scanner_ignored():
    seq=rows()
    seq[0]=strategy("trend-ladder","LONG_CANDIDATE",status="STALLED")
    v=decide(seq,risk())
    assert v["active_scanners"]==4
    assert v["stalled_scanners"]==1
    assert v["candidates"] == []

def test_bad_scanner_claim_is_untrusted():
    seq=rows()
    seq[0]=strategy("trend-ladder","LONG_CANDIDATE")
    seq[0].execution_enabled=True
    v=decide(seq,risk())
    assert not v["candidates"]
    assert "SCANNER_EVIDENCE_UNVERIFIED" in v["blockers"]

def test_multiple_symbols_separated():
    seq=rows()
    seq[0].signal="LONG_CANDIDATE"
    seq[1].symbol="ETHUSDT"
    seq[1].signal="SHORT_CANDIDATE"
    v=decide(seq,risk())
    assert [(c["symbol"],c["decision"]) for c in v["candidates"]]==[
        ("BTCUSDT","LONG_RESEARCH"),("ETHUSDT","SHORT_RESEARCH")]

def test_incomplete_inventory_blocked():
    v=decide(rows()[:2],risk())
    assert "STRATEGY_INVENTORY_INCOMPLETE" in v["blockers"]

def test_no_backend_order_import():
    from pathlib import Path
    base=Path(__file__).parent.parent/"nex_api"
    for p in (base/"strategy_risk_decision.py",base/"routes/trade_decision.py"):
        txt=p.read_text()
        assert "signed_post(" not in txt
        assert "hunter_live_executor" not in txt
