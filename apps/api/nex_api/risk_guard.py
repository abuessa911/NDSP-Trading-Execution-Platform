"""Pure account-equity daily-loss policy. No network, credentials or orders."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation


class RiskInvalid(ValueError):
    pass


def amount(value, positive=False):
    if isinstance(value, bool):
        raise RiskInvalid("INVALID_DECIMAL")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise RiskInvalid("INVALID_DECIMAL") from None
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise RiskInvalid("INVALID_DECIMAL")
    return result


def percentage(value):
    number = amount(value, positive=True)
    if number > 100 or number.as_tuple().exponent < -4:
        raise RiskInvalid("INVALID_PERCENT")
    return number


def daily_loss(opening_equity, current_equity, user_daily_loss_pct):
    """Opening/current are total account equity, including unrealized PnL.
    Never use available wallet balance or profit-only PnL as equity.
    """
    opening = amount(opening_equity, positive=True)
    current = amount(current_equity)
    limit = percentage(user_daily_loss_pct)
    loss = max(Decimal(0), opening - current)
    loss_limit = opening * limit / Decimal(100)
    return {
        "opening_equity": str(opening),
        "current_equity": str(current),
        "daily_loss_amount": str(loss),
        "loss_budget": str(loss_limit),
        "loss_pct_of_opening_equity": str(loss * 100 / opening),
        "new_entries_blocked": loss >= loss_limit,
    }
