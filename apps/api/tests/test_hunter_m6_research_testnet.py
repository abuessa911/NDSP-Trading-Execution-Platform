import unittest
from unittest.mock import patch
from decimal import Decimal
from nex_api import hunter_m6_research_testnet as m6

GOOD = {"mode":"testnet", "strategy":"UNSELECTED", "symbol":"BTCUSDT",
        "daily_loss_pct":"2.5", "trade_risk_pct":"0.5",
        "max_exposure_pct":"3", "stop_pct":"1"}
def rows(signal="LONG_CANDIDATE"):
    return [{"id": s.id, "symbol": s.symbol, "interval": s.interval,
             "close": "100", "signal": signal, "closed_candles_verified": True}
            for s in m6.STRATEGIES]

class TestM6RiskReadiness(unittest.TestCase):
    def test_unselected_strategy_does_not_block_readonly_status(self):
        self.assertEqual(m6.config_readiness(GOOD), [])
    def test_user_pct_never_defaulted(self):
        cfg = dict(GOOD)
        cfg.pop("daily_loss_pct")
        self.assertIn("DAILY_LOSS_PCT_USER_SELECTION_REQUIRED",m6.config_readiness(cfg))
    def test_risk_must_be_user_set(self):
        self.assertIn("PRIVATE_CONFIG_MISSING",m6.config_readiness({}))
    def test_mainnet_rejected(self):
        cfg = dict(GOOD,mode="mainnet")
        self.assertIn("TESTNET_MODE_REQUIRED",m6.config_readiness(cfg))
    def test_mainnet_flag_rejected(self):
        cfg = dict(GOOD,mainnet_enabled=True)
        self.assertIn("MAINNET_FLAG_FORBIDDEN",m6.config_readiness(cfg))
    def test_trade_pct_above_daily(self):
        cfg = dict(GOOD,trade_risk_pct="3")
        self.assertIn("PER_TRADE_RISK_EXCEEDS_DAILY_LIMIT",m6.config_readiness(cfg))
    def test_zero_risk_rejected(self):
        cfg = dict(GOOD,stop_pct="0")
        self.assertIn("STOP_PCT_USER_SELECTION_REQUIRED",m6.config_readiness(cfg))
    def test_negative_risk_rejected(self):
        cfg = dict(GOOD,trade_risk_pct="-2")
        self.assertIn("TRADE_RISK_PCT_USER_SELECTION_REQUIRED",m6.config_readiness(cfg))
    def test_nan_risk_rejected(self):
        cfg = dict(GOOD,daily_loss_pct="NaN")
        self.assertIn("DAILY_LOSS_PCT_USER_SELECTION_REQUIRED",m6.config_readiness(cfg))
    def test_status_cannot_trade(self):
        result = m6.plan_candidates(rows(), GOOD)
        self.assertIs(result["mainnet_orders"],False)
        self.assertIs(result["testnet_orders"],False)
        self.assertIs(result["automatic_trading"],False)
    def test_no_testnet_equity_is_a_blocker(self):
        self.assertIn("TESTNET_EQUITY_NOT_VERIFIED",m6.plan_candidates(rows(),GOOD)["blockers"])
    def test_research_not_order(self):
        result = m6.plan_candidates(rows(), GOOD, Decimal("100"), Decimal("100"))
        self.assertTrue(all(x["order_submittable"] is False for x in result["strategies"]))
        self.assertTrue(all("hypothetical_testnet_quantity" not in x for x in result["strategies"]))
    def test_short_not_available(self):
        result = m6.plan_candidates(rows("SHORT_CANDIDATE"), GOOD)
        self.assertTrue(all(x["blocker"]=="SHORT_EXECUTION_NOT_IMPLEMENTED" for x in result["strategies"]))
    def test_insufficient_set(self):
        with self.assertRaises(ValueError): m6.plan_candidates(rows()[:3],GOOD)
    def test_missing_candle_proof(self):
        r=rows()
        r[0]["closed_candles_verified"]=False
        with self.assertRaises(ValueError): m6.plan_candidates(r,GOOD)
    def test_invalid_signal(self):
        r=rows()
        r[0]["signal"]="BUY"
        with self.assertRaises(ValueError): m6.plan_candidates(r,GOOD)
    def test_wrong_ids(self):
        r=rows()
        r[0]["id"]="evil"
        with self.assertRaises(ValueError): m6.plan_candidates(r, GOOD)
    def test_quantity_is_hypothetical(self):
        result=m6.plan_candidates(rows(),GOOD,Decimal("1000"),Decimal("1000"),{
            s.symbol:{"step":"0.01","minimum":"0.01","min_notional":"5"}
            for s in m6.STRATEGIES
        })
        self.assertTrue(all("hypothetical_testnet_quantity" in x for x in result["strategies"]))
        self.assertTrue(all(x["not_a_trade_instruction"] for x in result["strategies"]))
    def test_plan_does_not_require_live_approval(self):
        result=m6.plan_candidates(rows(),GOOD)
        self.assertIn("FOUR_STRATEGIES_NOT_BROKER_APPROVED",result["blockers"])
    def test_neutral_no_quantity(self):
        result=m6.plan_candidates(rows("NEUTRAL"),GOOD)
        self.assertTrue(all("hypothetical_testnet_quantity" not in x for x in result["strategies"]))
    def test_mismatched_symbols_conflict(self):
        r=rows()
        r[1]["symbol"]=r[0]["symbol"]
        r[1]["signal"]="SHORT_CANDIDATE"
        self.assertIn("CONFLICTING_SIGNALS",m6.plan_candidates(r,GOOD)["blockers"])

if __name__=="__main__":
    unittest.main()


class TestM6OpeningEquity(unittest.TestCase):
    def test_original_daily_opening_blocks_after_limit(self):
        filters = {s.symbol: {"step": ".01", "minimum": ".01", "min_notional": "5"}
                   for s in m6.STRATEGIES}
        result = m6.plan_candidates(rows(), GOOD, Decimal("970"), Decimal("1000"), filters)
        self.assertIn("TESTNET_DAILY_RISK_UNVERIFIED", result["blockers"])
        self.assertTrue(all("hypothetical_testnet_quantity" not in item
                            for item in result["strategies"]))

    def test_invalid_opening_never_becomes_current_equity(self):
        for opening in (Decimal("0"), Decimal("-1"), Decimal("NaN")):
            result = m6.plan_candidates(rows(), GOOD, Decimal("1000"), opening)
            self.assertIn("TESTNET_DAILY_RISK_UNVERIFIED", result["blockers"])
