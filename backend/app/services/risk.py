from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import User, TradeLog


def allowed_symbols_list(raw: str) -> list[str]:
    return [x.strip().upper() for x in raw.split(",") if x.strip()]


def count_trades_today(db: Session, user_id: int) -> int:
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(func.count(TradeLog.id))
        .filter(TradeLog.user_id == user_id, TradeLog.created_at >= start)
        .scalar()
        or 0
    )


def validate_trade(db: Session, user: User, symbol: str, side: str, notional_usdt: float) -> tuple[bool, str]:
    settings = user.settings

    if not settings or not settings.enabled:
        return False, "Bot is disabled for this user"

    if symbol.upper() not in allowed_symbols_list(settings.allowed_symbols):
        return False, f"Symbol {symbol} is not allowed"

    if side.upper() not in ["BUY", "SELL"]:
        return False, "Invalid side"

    if notional_usdt <= 0:
        return False, "Order notional must be positive"

    if notional_usdt > settings.max_order_usdt:
        return False, f"Order notional exceeds max_order_usdt={settings.max_order_usdt}"

    trades_today = count_trades_today(db, user.id)
    if trades_today >= settings.max_trades_per_day:
        return False, "Max trades per day reached"

    return True, "Risk validation passed"
