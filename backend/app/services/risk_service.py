from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import User, TradeLog
from app.core.config import settings
from app.services.symbols import normalize_symbol


def today_bounds():
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


def calculate_daily_pnl(db: Session, user: User) -> float:
    start, end = today_bounds()
    rows = (
        db.query(TradeLog)
        .filter(TradeLog.user_id == user.id)
        .filter(TradeLog.created_at >= start)
        .filter(TradeLog.created_at < end)
        .all()
    )
    return float(sum(float(getattr(x, "pnl_usdt", 0) or 0) for x in rows))


def live_safety_checklist(user: User) -> list[dict]:
    user_settings = user.settings

    checks = [
        {
            "key": "user_active",
            "label": "المستخدم نشط",
            "ok": bool(user.is_active),
        },
        {
            "key": "bot_settings",
            "label": "إعدادات البوت موجودة",
            "ok": bool(user_settings),
        },
        {
            "key": "bot_enabled",
            "label": "البوت مفعّل للمستخدم",
            "ok": bool(user_settings and user_settings.enabled),
        },
        {
            "key": "binance_api",
            "label": "Binance API مضاف",
            "ok": bool(user.api_key),
        },
        {
            "key": "stop_loss",
            "label": "Stop Loss أكبر من 0",
            "ok": bool(user_settings and float(user_settings.stop_loss_pct or 0) > 0),
        },
        {
            "key": "take_profit",
            "label": "Take Profit أكبر من 0",
            "ok": bool(user_settings and float(user_settings.take_profit_pct or 0) > 0),
        },
        {
            "key": "max_daily_loss",
            "label": "Max Daily Loss محدد",
            "ok": bool(user_settings and float(user_settings.max_daily_loss_usdt or 0) > 0),
        },
        {
            "key": "max_trades_per_day",
            "label": "Max Trades Per Day محدد",
            "ok": bool(user_settings and int(user_settings.max_trades_per_day or 0) > 0),
        },
        {
            "key": "prevent_duplicate",
            "label": "منع تكرار الصفقات مفعّل",
            "ok": bool(user_settings and user_settings.prevent_duplicate_positions),
        },
        {
            "key": "telegram_configured",
            "label": "Telegram مضبوط",
            "ok": bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID),
        },
        {
            "key": "email_configured",
            "label": "Email SMTP مضبوط",
            "ok": bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD and settings.EMAIL_FROM),
        },
        {
            "key": "live_safety_confirmed",
            "label": "تم تأكيد مخاطر Live",
            "ok": bool(user_settings and user_settings.live_safety_confirmed),
        },
    ]

    return checks


def ensure_live_safety(user: User):
    if settings.BINANCE_MODE != "live":
        return

    checks = live_safety_checklist(user)
    failed = [x for x in checks if not x["ok"]]

    if failed:
        labels = ", ".join(x["label"] for x in failed)
        raise HTTPException(
            status_code=403,
            detail=f"Live trading blocked. Missing safety checks: {labels}"
        )


def ensure_no_duplicate_trade(db: Session, user: User, symbol: str, side: str):
    symbol = normalize_symbol(symbol)
    side = side.upper()
    if not user.settings or not user.settings.prevent_duplicate_positions:
        return

    start, end = today_bounds()

    existing = (
        db.query(TradeLog)
        .filter(TradeLog.user_id == user.id)
        .filter(TradeLog.symbol == symbol)
        .filter(TradeLog.side == side)
        .filter(TradeLog.created_at >= start)
        .filter(TradeLog.created_at < end)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate trade blocked: {symbol} {side} already exists today."
        )


def ensure_daily_loss_limit(db: Session, user: User):
    if not user.settings:
        return

    pnl = calculate_daily_pnl(db, user)
    max_loss = float(user.settings.max_daily_loss_usdt or 0)

    if max_loss > 0 and pnl <= -abs(max_loss):
        raise HTTPException(
            status_code=403,
            detail=f"Daily loss limit reached. PnL={pnl}, limit={max_loss}"
        )


def pre_trade_risk_check(db: Session, user: User, symbol: str, side: str):
    symbol = normalize_symbol(symbol)
    side = side.upper()
    if not user.settings or not user.settings.enabled:
        raise HTTPException(status_code=403, detail="Bot is disabled")

    ensure_live_safety(user)
    ensure_daily_loss_limit(db, user)
    ensure_no_duplicate_trade(db, user, symbol, side)
