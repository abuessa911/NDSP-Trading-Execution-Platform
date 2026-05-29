#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_phase2_$STAMP"
mkdir -p "$BACKUP_DIR"

echo "✅ Backup: $BACKUP_DIR"

cp backend/app/models/models.py "$BACKUP_DIR/models.py"
cp backend/app/schemas/schemas.py "$BACKUP_DIR/schemas.py"
cp backend/app/api/routes.py "$BACKUP_DIR/routes.py"
cp backend/app/main.py "$BACKUP_DIR/main.py"
cp frontend/app/page.tsx "$BACKUP_DIR/page.tsx"

python3 - <<'PY'
from pathlib import Path
import re

models = Path("backend/app/models/models.py")
s = models.read_text()

if "is_admin" not in s:
    s = s.replace(
        '    is_active: Mapped[bool] = mapped_column(Boolean, default=True)\n',
        '    is_active: Mapped[bool] = mapped_column(Boolean, default=True)\n'
        '    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)\n'
    )

if "stop_loss_pct" not in s:
    s = s.replace(
        '    max_trades_per_day: Mapped[int] = mapped_column(Integer, default=3)\n',
        '    max_trades_per_day: Mapped[int] = mapped_column(Integer, default=3)\n'
        '    stop_loss_pct: Mapped[float] = mapped_column(Float, default=0.0)\n'
        '    take_profit_pct: Mapped[float] = mapped_column(Float, default=0.0)\n'
        '    prevent_duplicate_positions: Mapped[bool] = mapped_column(Boolean, default=True)\n'
        '    live_safety_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)\n'
    )

if "pnl_usdt" not in s:
    s = s.replace(
        '    notional_usdt: Mapped[float] = mapped_column(Float, default=0)\n',
        '    notional_usdt: Mapped[float] = mapped_column(Float, default=0)\n'
        '    pnl_usdt: Mapped[float] = mapped_column(Float, default=0.0)\n'
    )

models.write_text(s)
print("✅ models.py patched")


schemas = Path("backend/app/schemas/schemas.py")
s = schemas.read_text()

if "stop_loss_pct" not in s:
    s = s.replace(
        '    max_trades_per_day: int = 3\n',
        '    max_trades_per_day: int = 3\n'
        '    stop_loss_pct: float = 0.0\n'
        '    take_profit_pct: float = 0.0\n'
        '    prevent_duplicate_positions: bool = True\n'
    )

if "ChangePasswordRequest" not in s:
    s += '''

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class NdspSignalRequest(BaseModel):
    symbol: str
    side: str
    notional_usdt: float
    reason: str = "NDSP signal"
    ndsp_layer: str | None = None


class LiveSafetyConfirmRequest(BaseModel):
    confirm_text: str
'''

schemas.write_text(s)
print("✅ schemas.py patched")


routes = Path("backend/app/api/routes.py")
s = routes.read_text()

if "stop_loss_pct = payload.stop_loss_pct" not in s:
    s = s.replace(
        '    existing.max_trades_per_day = payload.max_trades_per_day\n',
        '    existing.max_trades_per_day = payload.max_trades_per_day\n'
        '    existing.stop_loss_pct = payload.stop_loss_pct\n'
        '    existing.take_profit_pct = payload.take_profit_pct\n'
        '    existing.prevent_duplicate_positions = payload.prevent_duplicate_positions\n'
    )

if '"stop_loss_pct": user.settings.stop_loss_pct' not in s:
    s = s.replace(
        '        "max_trades_per_day": user.settings.max_trades_per_day,\n',
        '        "max_trades_per_day": user.settings.max_trades_per_day,\n'
        '        "stop_loss_pct": user.settings.stop_loss_pct,\n'
        '        "take_profit_pct": user.settings.take_profit_pct,\n'
        '        "prevent_duplicate_positions": user.settings.prevent_duplicate_positions,\n'
        '        "live_safety_confirmed": user.settings.live_safety_confirmed,\n'
    )

routes.write_text(s)
print("✅ routes.py patched")
PY

cat > backend/app/services/risk_service.py <<'EOF'
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import User, TradeLog
from app.core.config import settings


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


def ensure_live_safety(user: User):
    if settings.BINANCE_MODE == "live":
        if not user.settings or not user.settings.live_safety_confirmed:
            raise HTTPException(
                status_code=403,
                detail="Live safety is not confirmed. Confirm live safety before live trading."
            )


def ensure_no_duplicate_trade(db: Session, user: User, symbol: str, side: str):
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
    if not user.settings or not user.settings.enabled:
        raise HTTPException(status_code=403, detail="Bot is disabled")

    ensure_live_safety(user)
    ensure_daily_loss_limit(db, user)
    ensure_no_duplicate_trade(db, user, symbol, side)
