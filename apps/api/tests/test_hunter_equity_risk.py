"""M2 risk is user-configured; no defaults and no trading calls."""
import sys
from pathlib import Path
from decimal import Decimal
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nex_api.risk_guard import RiskInvalid, daily_loss, percentage, amount


class RiskEquityTests(unittest.TestCase):
    def test_no_default_user_percentage(self):
        with self.assertRaises(RiskInvalid):
            percentage(None)

    def test_user_can_choose_fraction(self):
        self.assertEqual(percentage("0.035"), Decimal("0.035"))

    def test_valid_large_percentage(self):
        self.assertEqual(percentage("75"), Decimal("75"))

    def test_negative_rejected(self):
        with self.assertRaises(RiskInvalid):
            percentage("-1")

    def test_zero_rejected(self):
        with self.assertRaises(RiskInvalid):
            percentage("0")

    def test_excess_over_hundred_rejected(self):
        with self.assertRaises(RiskInvalid):
            percentage("100.0001")

    def test_nan_rejected(self):
        for value in ("NaN", "Infinity", True, float("inf")):
            with self.subTest(value=value), self.assertRaises(RiskInvalid):
                percentage(value)

    def test_excessive_precision_rejected(self):
        with self.assertRaises(RiskInvalid):
            percentage("0.00001")

    def test_equity_nonpositive_rejected(self):
        with self.assertRaises(RiskInvalid):
            daily_loss("0", "100", "3")
        with self.assertRaises(RiskInvalid):
            daily_loss("100", "-1", "3")

    def test_exact_loss_limit_blocks(self):
        result = daily_loss("2000", "1980", "1")
        self.assertTrue(result["new_entries_blocked"])
        self.assertEqual(result["loss_budget"], "20")
        self.assertEqual(result["daily_loss_amount"], "20")

    def test_under_limit_passes_readonly(self):
        result = daily_loss("2000", "1999", "1")
        self.assertFalse(result["new_entries_blocked"])

    def test_profit_does_not_create_negative_loss(self):
        result = daily_loss("2000", "2500", "1")
        self.assertEqual(result["daily_loss_amount"], "0")
        self.assertFalse(result["new_entries_blocked"])

    def test_small_user_defined_limit(self):
        result = daily_loss("1200", "1199", "0.05")
        self.assertTrue(result["new_entries_blocked"])

    def test_uses_equity_not_wallet(self):
        result = daily_loss("1000", "970", "2")
        self.assertTrue(result["new_entries_blocked"])
        self.assertEqual(result["loss_pct_of_opening_equity"], "3")


if __name__ == "__main__":
    unittest.main()
