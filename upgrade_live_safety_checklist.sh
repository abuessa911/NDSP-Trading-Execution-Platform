#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_live_safety_$STAMP"
mkdir -p "$BACKUP_DIR"

cp backend/app/services/risk_service.py "$BACKUP_DIR/risk_service.py"
cp backend/app/api/advanced_routes.py "$BACKUP_DIR/advanced_routes.py"
cp frontend/app/safety/page.tsx "$BACKUP_DIR/safety_page.tsx"

echo "✅ Backup created: $BACKUP_DIR"

cat > backend/app/services/risk_service.py <<'PYEOF'
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
PYEOF

python3 - <<'PY'
from pathlib import Path

p = Path("backend/app/api/advanced_routes.py")
s = p.read_text()

if "live_safety_checklist" not in s:
    s = s.replace(
        "from app.services.risk_service import calculate_daily_pnl, pre_trade_risk_check",
        "from app.services.risk_service import calculate_daily_pnl, pre_trade_risk_check, live_safety_checklist"
    )

if '@router.get("/live-safety/checklist")' not in s:
    s += '''

@router.get("/live-safety/checklist")
def live_safety_checklist_endpoint(user: User = Depends(get_current_user)):
    checks = live_safety_checklist(user)
    return {
        "all_ok": all(x["ok"] for x in checks),
        "checks": checks,
        "required_text": "I UNDERSTAND LIVE RISK"
    }
'''

p.write_text(s)
print("✅ advanced_routes.py patched")
PY

cat > frontend/app/safety/page.tsx <<'EOF'
"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function SafetyPage() {
  const [status, setStatus] = useState<any>(null);
  const [checklist, setChecklist] = useState<any>(null);
  const [confirmText, setConfirmText] = useState("");
  const [message, setMessage] = useState("");

  async function loadAll() {
    setMessage("");
    try {
      const s = await api("/live-safety/status");
      const c = await api("/live-safety/checklist");
      setStatus(s);
      setChecklist(c);
    } catch (e: any) {
      setMessage("فشل تحميل الحالة: " + e.message);
    }
  }

  async function confirm() {
    setMessage("");
    try {
      await api("/live-safety/confirm", {
        method: "POST",
        body: JSON.stringify({ confirm_text: confirmText })
      });
      setMessage("تم تأكيد مخاطر Live");
      await loadAll();
    } catch (e: any) {
      setMessage("فشل التأكيد: " + e.message);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  return (
    <main className="container">
      <div className="card">
        <h1>Live Safety Center</h1>

        <p style={{ color: "#fbbf24", lineHeight: 1.8 }}>
          هذه الصفحة تمنع تفعيل التداول الحقيقي قبل اكتمال شروط الأمان. لا تستخدم Live إلا بعد نجاح Testnet وإضافة مفاتيح Binance بدون صلاحية Withdraw.
        </p>

        <div className="card">
          <h2>الحالة العامة</h2>
          <span className={checklist?.all_ok ? "badge badge-green" : "badge badge-red"}>
            {checklist?.all_ok ? "جاهز مبدئيًا للـ Live" : "غير جاهز للـ Live"}
          </span>
        </div>

        <div className="card">
          <h2>Checklist</h2>

          <div className="live-checklist">
            {checklist?.checks?.map((item: any) => (
              <div className={item.ok ? "live-check ok" : "live-check bad"} key={item.key}>
                <span>{item.ok ? "✅" : "❌"}</span>
                <strong>{item.label}</strong>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2>تأكيد مخاطر Live</h2>

          <p>اكتب النص التالي حرفيًا:</p>
          <code>{checklist?.required_text || status?.required_text || "I UNDERSTAND LIVE RISK"}</code>

          <input
            className="input"
            style={{ marginTop: 14 }}
            value={confirmText}
            onChange={e => setConfirmText(e.target.value)}
            placeholder="I UNDERSTAND LIVE RISK"
          />

          <button className="btn btn-danger" style={{ marginTop: 18 }} onClick={confirm}>
            تأكيد مخاطر Live
          </button>
        </div>

        {message && <div className="card">{message}</div>}

        <button className="btn btn-secondary" onClick={loadAll}>تحديث</button>

        <p style={{ marginTop: 22 }}>
          <a href="/">العودة للوحة التحكم</a>
        </p>
      </div>
    </main>
  );
}
