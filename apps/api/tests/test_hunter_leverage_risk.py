import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from nex_api.hunter_leverage_risk import plan,RiskRejected
BASE=dict(equity=1000,opening_equity=1000,margin_used=0,leverage=10,entry_price=100,
          stop_margin_pct=70,daily_loss_pct=10,trade_risk_pct=10,max_margin_pct=10,
          fee_rate_each_side="0.0005",slippage_rate_each_side="0.001",
          maintenance_margin_rate="0.005")
def test_plan():
    p=plan(**BASE)
    assert float(p["margin"])<=100
    assert float(p["estimated_loss_including_costs"])<=100
    assert float(p["long_stop_price_unrounded"])==93
def test_daily_limit():
    with pytest.raises(RiskRejected,match="DAILY_LOSS"):
        plan(**{**BASE,"equity":900})
def test_liquidation():
    with pytest.raises(RiskRejected,match="LIQUIDATION"):
        plan(**{**BASE,"maintenance_margin_rate":"0.02"})
def test_missing_maintenance():
    x=BASE.copy();del x["maintenance_margin_rate"]
    with pytest.raises(RiskRejected,match="MAINTENANCE"):
        plan(**x)
def test_existing_margin():
    assert float(plan(**{**BASE,"margin_used":90})["margin"])<=10
def test_bad_leverage():
    with pytest.raises(RiskRejected):
        plan(**{**BASE,"leverage":0})
