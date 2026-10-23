# apps/api/nex_api/risk_engine.py
import logging
from datetime import datetime

logger = logging.getLogger("hunter_ksa1.risk")

class DynamicRiskEngine:
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self.risk_per_trade_pct = 0.5
        self.max_daily_loss_pct = 2.0
        self.max_exposure_pct = 10.0
        self.stop_loss_pct = 1.0
        self.take_profit_pct = 2.0

        self.daily_starting_balance = 0.0
        self.current_daily_loss = 0.0
        self.last_reset_day = datetime.utcnow().day

    async def load_settings_from_db(self):
        if not self.db_pool:
            return
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT risk_per_trade_pct, max_daily_loss_pct, max_exposure_pct, stop_loss_pct, take_profit_pct FROM bot_risk_settings WHERE bot_name = 'hunter_ksa1';"
                )
                if row:
                    self.risk_per_trade_pct = float(row['risk_per_trade_pct'])
                    self.max_daily_loss_pct = float(row['max_daily_loss_pct'])
                    self.max_exposure_pct = float(row['max_exposure_pct'])
                    self.stop_loss_pct = float(row['stop_loss_pct'])
                    self.take_profit_pct = float(row['take_profit_pct'])
        except Exception as e:
            logger.error(f"خطأ أثناء قراءة إعدادات المخاطر من قاعدة البيانات: {e}")

    def calculate_trade_params(self, account_balance: float, entry_price: float, is_long: bool) -> dict:
        risk_amount = account_balance * (self.risk_per_trade_pct / 100.0)

        if is_long:
            sl_price = entry_price * (1 - (self.stop_loss_pct / 100.0))
            tp_price = entry_price * (1 + (self.take_profit_pct / 100.0))
        else:
            sl_price = entry_price * (1 + (self.stop_loss_pct / 100.0))
            tp_price = entry_price * (1 - (self.take_profit_pct / 100.0))

        price_risk = abs(entry_price - sl_price)
        qty = (risk_amount / price_risk) if price_risk > 0 else 0.0

        return {
            "quantity": round(qty, 3),
            "stop_loss": round(sl_price, 4),
            "take_profit": round(tp_price, 4)
        }
