import secrets
import csv
import io
from datetime import datetime, timedelta
from typing import Any
from fastapi.responses import StreamingResponse
import os
import subprocess
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, ConfigDict, Field

from app.db.session import get_db
from app.core.config import settings
from app.models.models import User, TradeLog, BinanceApiKey, BotSettings
from app.api.routes import get_current_user
from app.schemas.schemas import ChangePasswordRequest, NdspSignalRequest, LiveSafetyConfirmRequest
from app.services.execution import execute_signal
from app.services.ndsp_decision_interpreter import interpret_ndsp_payload
from app.services.symbols import normalize_symbol
from app.services.risk_service import calculate_daily_pnl, pre_trade_risk_check, live_safety_checklist

try:
    from app.auth.security import verify_password, hash_password as get_password_hash
except Exception:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)


router = APIRouter()


class NdspWebhookSignalRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    user_email: str
    symbol: str | None = None
    side: str | None = None
    notional_usdt: float = 10.0
    confidence: float | None = None
    reason: str = "NDSP webhook signal"
    ndsp_layer: str | None = None
    signal_id: str | None = None
    context: dict[str, Any] | None = None
    decision: dict[str, Any] | None = None
    ndsp_decision: dict[str, Any] | None = None
    execution: dict[str, Any] | None = None
    market_alignment: dict[str, Any] | None = None
    states: dict[str, Any] | None = None
    explanation: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


def _payload_dict(payload: BaseModel | dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return payload.model_dump(mode="python", exclude_none=True)


def _payload_symbol(payload_data: dict[str, Any]) -> str:
    meta = payload_data.get("meta") if isinstance(payload_data.get("meta"), dict) else {}
    symbol = payload_data.get("symbol") or meta.get("symbol_id") or meta.get("symbol")
    if not symbol:
        raise HTTPException(status_code=400, detail="NDSP payload symbol is required")
    return normalize_symbol(str(symbol))


def _payload_reason(payload_data: dict[str, Any], default_reason: str) -> str:
    reason = payload_data.get("reason") or default_reason
    ndsp_layer = payload_data.get("ndsp_layer")
    signal_id = payload_data.get("signal_id")
    if ndsp_layer:
        reason = f"{reason} | NDSP Layer: {ndsp_layer}"
    if signal_id:
        reason = f"{reason} | Signal ID: {signal_id}"
    return reason


def require_admin(user: User):
    if not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin only")



class CleanupLogsRequest(BaseModel):
    older_than_days: int = Field(default=30, ge=1, le=3650)
    rejected_only: bool = False


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None


@router.post("/me/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    user.password_hash = get_password_hash(payload.new_password)
    db.commit()

    return {"status": "changed"}


@router.get("/admin/users")
def admin_users(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_admin(user)

    rows = db.query(User).order_by(User.id.desc()).all()

    return [
        {
            "id": x.id,
            "email": x.email,
            "is_active": x.is_active,
            "is_admin": getattr(x, "is_admin", False),
            "created_at": x.created_at,
            "binance_key_configured": bool(x.api_key),
            "settings_configured": bool(x.settings),
        }
        for x in rows
    ]


@router.patch("/admin/users/{target_user_id}")
def admin_update_user(
    target_user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_admin(user)

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.is_active is not None:
        target.is_active = payload.is_active

    if payload.is_admin is not None:
        target.is_admin = payload.is_admin

    db.commit()

    return {"status": "updated"}


@router.get("/risk/daily-pnl")
def daily_pnl(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pnl = calculate_daily_pnl(db, user)

    return {
        "daily_pnl_usdt": pnl,
        "source": "bot_trade_logs",
        "note": "PnL is calculated from bot trade logs. Exchange-level PnL integration can be added next."
    }


@router.post("/live-safety/confirm")
def confirm_live_safety(
    payload: LiveSafetyConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.confirm_text.strip() != "I UNDERSTAND LIVE RISK":
        raise HTTPException(
            status_code=400,
            detail='Type exactly: I UNDERSTAND LIVE RISK'
        )

    if not user.settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    user.settings.live_safety_confirmed = True
    db.commit()

    return {"status": "confirmed"}


@router.get("/live-safety/status")
def live_safety_status(user: User = Depends(get_current_user)):
    return {
        "confirmed": bool(user.settings and user.settings.live_safety_confirmed),
        "required_text": "I UNDERSTAND LIVE RISK"
    }


@router.post("/ndsp/signal")
async def ndsp_signal(
    payload: NdspSignalRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payload_data = _payload_dict(payload)
    interpretation = interpret_ndsp_payload(payload_data)
    normalized_symbol = _payload_symbol(payload_data)

    if interpretation["action"] == "NO_TRADE":
        return {
            "status": "no_trade",
            "symbol": normalized_symbol,
            "side": "NO_TRADE",
            "action": "NO_TRADE",
            "reason": interpretation["reason"],
            "interpretation": interpretation,
        }

    action = interpretation["action"]
    pre_trade_risk_check(db, user, normalized_symbol, action)

    trade = await execute_signal(
        db=db,
        user=user,
        symbol=normalized_symbol,
        side=action,
        notional_usdt=float(payload_data.get("notional_usdt") or 10.0),
        reason=_payload_reason(payload_data, interpretation["reason"]),
    )

    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "side": trade.side,
        "action": action,
        "status": trade.status,
        "mode": trade.mode,
        "reason": trade.reason,
        "interpretation": interpretation,
    }


@router.get("/risk/summary")
def risk_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = user.settings

    return {
        "bot_enabled": bool(settings and settings.enabled),
        "daily_pnl_usdt": calculate_daily_pnl(db, user),
        "max_daily_loss_usdt": settings.max_daily_loss_usdt if settings else None,
        "stop_loss_pct": settings.stop_loss_pct if settings else None,
        "take_profit_pct": settings.take_profit_pct if settings else None,
        "prevent_duplicate_positions": settings.prevent_duplicate_positions if settings else None,
        "live_safety_confirmed": bool(settings and settings.live_safety_confirmed),
    }


@router.delete("/admin/users/{target_user_id}")
def admin_delete_user(
    target_user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_admin(user)

    if target_user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete related user data first to avoid foreign key errors
    db.query(TradeLog).filter(TradeLog.user_id == target_user_id).delete(synchronize_session=False)
    db.query(BinanceApiKey).filter(BinanceApiKey.user_id == target_user_id).delete(synchronize_session=False)
    db.query(BotSettings).filter(BotSettings.user_id == target_user_id).delete(synchronize_session=False)

    db.delete(target)
    db.commit()

    return {"status": "deleted", "user_id": target_user_id}


@router.post("/webhooks/ndsp-signal")
async def ndsp_webhook_signal(
    payload: NdspWebhookSignalRequest,
    x_ndsp_secret: str | None = Header(default=None, alias="X-NDSP-SECRET"),
    db: Session = Depends(get_db),
):
    if not settings.NDSP_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="NDSP webhook secret is not configured")

    if x_ndsp_secret != settings.NDSP_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid NDSP webhook secret")

    payload_data = _payload_dict(payload)
    target_user = db.query(User).filter(User.email == payload.user_email).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    if not target_user.is_active:
        raise HTTPException(status_code=403, detail="Target user is disabled")

    interpretation = interpret_ndsp_payload(payload_data)
    normalized_symbol = _payload_symbol(payload_data)

    if interpretation["action"] == "NO_TRADE":
        return {
            "status": "no_trade",
            "user_email": target_user.email,
            "symbol": normalized_symbol,
            "side": "NO_TRADE",
            "action": "NO_TRADE",
            "reason": interpretation["reason"],
            "interpretation": interpretation,
        }

    action = interpretation["action"]
    pre_trade_risk_check(db, target_user, normalized_symbol, action)

    trade = await execute_signal(
        db=db,
        user=target_user,
        symbol=normalized_symbol,
        side=action,
        notional_usdt=float(payload_data.get("notional_usdt") or 10.0),
        reason=_payload_reason(payload_data, interpretation["reason"]),
    )

    return {
        "status": "accepted",
        "trade_id": trade.id,
        "user_email": target_user.email,
        "symbol": trade.symbol,
        "side": trade.side,
        "action": action,
        "mode": trade.mode,
        "trade_status": trade.status,
        "reason": trade.reason,
        "interpretation": interpretation,
    }


@router.get("/live-safety/checklist")
def live_safety_checklist_endpoint(user: User = Depends(get_current_user)):
    checks = live_safety_checklist(user)
    return {
        "all_ok": all(x["ok"] for x in checks),
        "checks": checks,
        "required_text": "I UNDERSTAND LIVE RISK"
    }


@router.get("/system/health")
def system_health(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    telegram_ok = bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)
    email_ok = bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD and settings.EMAIL_FROM)

    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    docker_status = "unknown"
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            cwd="/home/nawaf511/ndsp-binance-bot",
            capture_output=True,
            text=True,
            timeout=10,
        )
        docker_status = "ok" if result.returncode == 0 else "error"
    except Exception:
        docker_status = "unavailable"

    return {
        "api": "ok",
        "database": "ok" if db_ok else "error",
        "telegram_configured": telegram_ok,
        "email_configured": email_ok,
        "binance_mode": settings.BINANCE_MODE,
        "docker_status": docker_status,
        "user": {
            "email": user.email,
            "is_admin": getattr(user, "is_admin", False),
            "is_active": user.is_active,
            "binance_key_configured": bool(user.api_key),
        }
    }


@router.get("/system/backups")
def list_backups(
    user: User = Depends(get_current_user),
):
    require_admin(user)

    backup_dir = Path("/home/nawaf511/ndsp-binance-bot/backups")
    backup_dir.mkdir(exist_ok=True)

    files = []
    for f in sorted(backup_dir.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)[:80]:
        files.append({
            "name": f.name,
            "size_bytes": f.stat().st_size,
            "modified_at": f.stat().st_mtime,
        })

    return {"backups": files}


@router.post("/system/backups/run")
def run_backup(
    user: User = Depends(get_current_user),
):
    require_admin(user)

    result = subprocess.run(
        ["/home/nawaf511/ndsp-binance-bot/scripts/backup_now.sh"],
        cwd="/home/nawaf511/ndsp-binance-bot",
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )

    return {
        "status": "backup_completed",
        "stdout": result.stdout,
    }


@router.get("/system/logs/rejections")
def rejected_trades_log(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(TradeLog)
        .filter(TradeLog.user_id == user.id)
        .filter(TradeLog.status.in_(["rejected", "failed", "error"]))
        .order_by(TradeLog.id.desc())
        .limit(150)
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
            "status": x.status,
            "mode": x.mode,
            "reason": x.reason,
            "exchange_response": x.exchange_response,
            "created_at": x.created_at,
        }
        for x in rows
    ]


@router.get("/system/logs/trades")
def trades_log_extended(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(TradeLog)
        .filter(TradeLog.user_id == user.id)
        .order_by(TradeLog.id.desc())
        .limit(200)
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
            "exchange_response": x.exchange_response,
            "created_at": x.created_at,
        }
        for x in rows
    ]


@router.get("/system/logs/summary")
def logs_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(TradeLog)
        .filter(TradeLog.user_id == user.id)
        .order_by(TradeLog.id.desc())
        .limit(500)
        .all()
    )

    total = len(rows)
    rejected = len([x for x in rows if x.status in ["rejected", "failed", "error"]])
    closed = len([x for x in rows if x.status == "closed"])
    simulated = len([x for x in rows if x.status == "simulated"])

    return {
        "total": total,
        "closed": closed,
        "simulated": simulated,
        "rejected_or_failed": rejected,
        "latest_status": rows[0].status if rows else None,
        "latest_reason": rows[0].reason if rows else None,
    }


@router.get("/system/logs/export.csv")
def export_trades_csv(
    rejected_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(TradeLog).filter(TradeLog.user_id == user.id)

    if rejected_only:
        query = query.filter(TradeLog.status.in_(["rejected", "failed", "error"]))

    rows = query.order_by(TradeLog.id.desc()).limit(5000).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "id",
        "symbol",
        "side",
        "amount",
        "price",
        "notional_usdt",
        "pnl_usdt",
        "stop_loss_price",
        "take_profit_price",
        "protective_orders_status",
        "status",
        "mode",
        "reason",
        "created_at",
    ])

    for x in rows:
        writer.writerow([
            x.id,
            x.symbol,
            x.side,
            x.amount,
            x.price,
            x.notional_usdt,
            getattr(x, "pnl_usdt", 0),
            getattr(x, "stop_loss_price", 0),
            getattr(x, "take_profit_price", 0),
            getattr(x, "protective_orders_status", "preview"),
            x.status,
            x.mode,
            x.reason,
            x.created_at,
        ])

    output.seek(0)

    filename = "rejected_trades.csv" if rejected_only else "trades.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/system/logs/cleanup")
def cleanup_logs(
    payload: CleanupLogsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cutoff = datetime.utcnow() - timedelta(days=payload.older_than_days)

    query = (
        db.query(TradeLog)
        .filter(TradeLog.user_id == user.id)
        .filter(TradeLog.created_at < cutoff)
    )

    if payload.rejected_only:
        query = query.filter(TradeLog.status.in_(["rejected", "failed", "error"]))

    count = query.count()
    query.delete(synchronize_session=False)
    db.commit()

    return {
        "status": "cleaned",
        "deleted": count,
        "older_than_days": payload.older_than_days,
        "rejected_only": payload.rejected_only,
    }


@router.get("/ndsp/webhook-config")
def ndsp_webhook_config(
    user: User = Depends(get_current_user),
):
    require_admin(user)

    env_path = Path("/home/nawaf511/ndsp-binance-bot/.env")
    duplicate_count = 0

    if env_path.exists():
        duplicate_count = sum(
            1 for line in env_path.read_text().splitlines()
            if line.startswith("NDSP_WEBHOOK_SECRET=")
        )

    current_secret = settings.NDSP_WEBHOOK_SECRET or ""

    return {
        "webhook_url": "https://bot.ndsp.app/api/webhooks/ndsp-signal",
        "configured": bool(current_secret),
        "secret_length": len(current_secret),
        "duplicate_count": duplicate_count,
        "header_name": "X-NDSP-SECRET",
        "method": "POST",
        "example_body": {
            "user_email": user.email,
            "symbol": "ETH/USDT",
            "notional_usdt": 10,
            "reason": "NDSP webhook signal",
            "decision": {
                "direction": "bullish",
                "confidence": 85,
                "grade": "A",
                "quality_label": "Valid",
                "execution_allowed": True
            },
            "execution": {
                "allowed": True,
                "mode": "decision_support_only"
            },
            "market_alignment": {
                "signal": "CONTINUATION_SIGNAL"
            },
            "states": {
                "risk_state": "normal",
                "system_state": "live"
            },
            "explanation": {
                "guidance": "Decision support context only; not a primary execution signal."
            },
            "ndsp_layer": "layer-1",
            "signal_id": "ndsp-signal-001"
        }
    }


@router.post("/ndsp/webhook-config/rotate")
def rotate_ndsp_webhook_secret(
    user: User = Depends(get_current_user),
):
    require_admin(user)

    env_path = Path("/home/nawaf511/ndsp-binance-bot/.env")
    lines = []

    if env_path.exists():
        lines = env_path.read_text().splitlines()

    lines = [
        line for line in lines
        if not line.startswith("NDSP_WEBHOOK_SECRET=")
    ]

    new_secret = "ndsp_" + secrets.token_urlsafe(48)
    lines.append(f"NDSP_WEBHOOK_SECRET={new_secret}")

    env_path.write_text("\n".join(lines) + "\n")

    # Update runtime settings immediately without waiting for container restart
    settings.NDSP_WEBHOOK_SECRET = new_secret

    return {
        "status": "rotated",
        "new_secret": new_secret,
        "warning": "Copy this secret now. It will be shown only in this response."
    }
