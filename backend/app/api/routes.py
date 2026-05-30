from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User, BinanceApiKey, BotSettings, TradeLog
from app.schemas.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    BinanceKeyRequest,
    BotSettingsRequest,
    TestSignalRequest,
)
from app.auth.security import hash_password, verify_password, create_access_token, get_current_user
from app.services.crypto_service import encrypt_text
from app.services.execution import execute_signal
from app.services.risk_service import pre_trade_risk_check
from app.services.notifications import send_telegram, send_email
from app.core.config import settings
from app.exchange.binance_client import get_active_symbols
from app.services.symbols import normalize_market_type, normalize_symbol, serialize_allowed_symbols


router = APIRouter()


@router.post("/auth/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if settings.INVITE_CODE and payload.invite_code != settings.INVITE_CODE:
        raise HTTPException(status_code=403, detail="Invalid invite code")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    bot_settings = BotSettings(user_id=user.id, enabled=False)
    db.add(bot_settings)
    db.commit()

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/auth/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "binance_key_configured": bool(user.api_key),
        "settings_configured": bool(user.settings),
    }


@router.post("/me/binance-key")
def save_binance_key(
    payload: BinanceKeyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    encrypted_key = encrypt_text(payload.api_key)
    encrypted_secret = encrypt_text(payload.api_secret)

    existing = db.query(BinanceApiKey).filter(BinanceApiKey.user_id == user.id).first()

    if existing:
        existing.api_key_encrypted = encrypted_key
        existing.api_secret_encrypted = encrypted_secret
    else:
        existing = BinanceApiKey(
            user_id=user.id,
            api_key_encrypted=encrypted_key,
            api_secret_encrypted=encrypted_secret,
        )
        db.add(existing)

    db.commit()
    return {"status": "saved", "message": "Binance API key encrypted and stored"}


@router.post("/me/settings")
def update_settings(
    payload: BotSettingsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = db.query(BotSettings).filter(BotSettings.user_id == user.id).first()

    if not existing:
        existing = BotSettings(user_id=user.id)
        db.add(existing)

    existing.enabled = payload.enabled
    existing.market_type = normalize_market_type(payload.market_type)
    existing.allowed_symbols = serialize_allowed_symbols(payload.allowed_symbols)
    existing.max_order_usdt = payload.max_order_usdt
    existing.max_daily_loss_usdt = payload.max_daily_loss_usdt
    existing.max_trades_per_day = payload.max_trades_per_day
    existing.stop_loss_pct = payload.stop_loss_pct
    existing.take_profit_pct = payload.take_profit_pct
    existing.prevent_duplicate_positions = payload.prevent_duplicate_positions
    existing.telegram_enabled = payload.telegram_enabled
    existing.email_enabled = payload.email_enabled

    db.commit()

    return {"status": "saved", "settings": payload.model_dump()}


@router.get("/me/settings")
def get_settings(
    user: User = Depends(get_current_user),
):
    if not user.settings:
        return None

    return {
        "enabled": user.settings.enabled,
        "market_type": getattr(user.settings, "market_type", "spot") or "spot",
        "allowed_symbols": user.settings.allowed_symbols,
        "max_order_usdt": user.settings.max_order_usdt,
        "max_daily_loss_usdt": user.settings.max_daily_loss_usdt,
        "max_trades_per_day": user.settings.max_trades_per_day,
        "stop_loss_pct": user.settings.stop_loss_pct,
        "take_profit_pct": user.settings.take_profit_pct,
        "prevent_duplicate_positions": user.settings.prevent_duplicate_positions,
        "live_safety_confirmed": user.settings.live_safety_confirmed,
        "telegram_enabled": user.settings.telegram_enabled,
        "email_enabled": user.settings.email_enabled,
    }


@router.post("/bot/test-signal")
async def test_signal(
    payload: TestSignalRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    ينفذ إشارة يدوية.
    في وضع dryrun لا يتم تنفيذ صفقة حقيقية.
    """
    normalized_symbol = normalize_symbol(payload.symbol)
    pre_trade_risk_check(db, user, normalized_symbol, payload.side)

    trade = await execute_signal(
        db=db,
        user=user,
        symbol=normalized_symbol,
        side=payload.side,
        notional_usdt=payload.notional_usdt,
        reason=payload.reason,
    )

    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "side": trade.side,
        "status": trade.status,
        "mode": trade.mode,
        "reason": trade.reason,
    }


@router.get("/symbols/spot")
def spot_symbols():
    symbols = get_active_symbols("spot", "USDT")
    return {
        "ok": True,
        "market_type": "spot",
        "quote": "USDT",
        "count": len(symbols),
        "symbols": symbols,
    }


@router.get("/symbols/futures")
def futures_symbols():
    symbols = get_active_symbols("futures", "USDT")
    return {
        "ok": True,
        "market_type": "futures",
        "quote": "USDT",
        "count": len(symbols),
        "symbols": symbols,
    }


@router.get("/symbols/summary")
def symbols_summary():
    spot = get_active_symbols("spot", "USDT")
    futures = get_active_symbols("futures", "USDT")
    return {
        "ok": True,
        "quote": "USDT",
        "spot": {
            "market_type": "spot",
            "count": len(spot),
            "symbols": spot,
        },
        "futures": {
            "market_type": "futures",
            "count": len(futures),
            "symbols": futures,
        },
    }


@router.post("/bot/test-alert")
async def test_alert(user: User = Depends(get_current_user)):
    message = f"✅ NDSP Trading Bot test alert for {user.email}"

    telegram_ok = False
    email_ok = False

    if user.settings and user.settings.telegram_enabled:
        telegram_ok = await send_telegram(message)

    if user.settings and user.settings.email_enabled:
        try:
            email_ok = send_email(user.email, "NDSP Test Alert", message)
        except Exception:
            email_ok = False

    return {
        "telegram_sent": telegram_ok,
        "email_sent": email_ok,
    }


@router.get("/trades")
def trades(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(TradeLog)
        .filter(TradeLog.user_id == user.id)
        .order_by(TradeLog.id.desc())
        .limit(100)
        .all()
    )

    return [
        {
            "id": x.id,
            "symbol": x.symbol,
            "side": x.side,
            "amount": x.amount,
            "price": x.price,
            "notional_usdt": x.notional_usdt,
            "pnl_usdt": getattr(x, "pnl_usdt", 0),
            "stop_loss_price": getattr(x, "stop_loss_price", 0),
            "take_profit_price": getattr(x, "take_profit_price", 0),
            "protective_orders_status": getattr(x, "protective_orders_status", "preview"),
            "status": x.status,
            "mode": x.mode,
            "reason": x.reason,
            "created_at": x.created_at,
        }
        for x in rows
    ]


@router.post("/emergency-stop")
def emergency_stop(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    user.settings.enabled = False
    db.commit()

    return {"status": "stopped", "message": "Bot disabled for current user"}
