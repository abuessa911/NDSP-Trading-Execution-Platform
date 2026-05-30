from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.exchange.binance_client import is_symbol_supported
from app.models.models import TradeLog, User
from app.services.symbols import (
    SPECIAL_ALLOWED_SYMBOLS,
    is_usdt_pair,
    normalize_market_type,
    normalize_symbol,
    parse_allowed_symbols,
)


def allowed_symbols_list(raw: str) -> list[str]:
    return parse_allowed_symbols(raw)


def count_trades_today(db: Session, user_id: int) -> int:
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(func.count(TradeLog.id))
        .filter(TradeLog.user_id == user_id, TradeLog.created_at >= start)
        .scalar()
        or 0
    )


def is_symbol_allowed(symbol: str, raw_allowed_symbols: str, market_type: str = "spot") -> tuple[bool, str]:
    normalized_symbol = normalize_symbol(symbol)
    selected_market_type = normalize_market_type(market_type)
    allowed = parse_allowed_symbols(raw_allowed_symbols)

    if not normalized_symbol:
        return False, "Symbol is required"

    special = next((item for item in allowed if item in SPECIAL_ALLOWED_SYMBOLS), None)

    if special:
        if not is_usdt_pair(normalized_symbol):
            return False, f"Symbol {normalized_symbol} is not a USDT pair"

        if special == "ALL_SPOT_USDT":
            market_types = ["spot"]
        elif special == "ALL_FUTURES_USDT":
            market_types = ["futures"]
        else:
            market_types = [selected_market_type]

        for symbol_market_type in market_types:
            if is_symbol_supported(normalized_symbol, symbol_market_type):
                return True, "allowed"

        markets = "/".join(market_types)
        return False, f"Symbol {normalized_symbol} is not an active Binance {markets} USDT symbol"

    if normalized_symbol not in allowed:
        return False, f"Symbol {normalized_symbol} is not allowed"

    return True, "allowed"


def validate_trade(db: Session, user: User, symbol: str, side: str, notional_usdt: float) -> tuple[bool, str]:
    user_settings = user.settings
    normalized_symbol = normalize_symbol(symbol)

    if not user_settings or not user_settings.enabled:
        return False, "Bot is disabled for this user"

    market_type = getattr(user_settings, "market_type", "spot") or "spot"

    allowed, reason = is_symbol_allowed(
        normalized_symbol,
        user_settings.allowed_symbols,
        market_type,
    )

    if not allowed:
        return False, reason

    if side.upper() not in ["BUY", "SELL"]:
        return False, "Invalid side"

    if notional_usdt <= 0:
        return False, "Invalid order value"

    if notional_usdt > user_settings.max_order_usdt:
        return False, "Order exceeds max_order_usdt"

    if count_trades_today(db, user.id) >= user_settings.max_trades_per_day:
        return False, "Max trades per day reached"

    return True, "OK"
