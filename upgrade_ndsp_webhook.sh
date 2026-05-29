#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_ndsp_webhook_$STAMP"
mkdir -p "$BACKUP_DIR"

cp backend/app/core/config.py "$BACKUP_DIR/config.py"
cp backend/app/api/advanced_routes.py "$BACKUP_DIR/advanced_routes.py"
cp frontend/app/ndsp/page.tsx "$BACKUP_DIR/ndsp_page.tsx"
cp .env "$BACKUP_DIR/env.backup"

echo "✅ Backup created: $BACKUP_DIR"

# Add NDSP_WEBHOOK_SECRET to .env if missing
if ! grep -q '^NDSP_WEBHOOK_SECRET=' .env; then
  SECRET="$(python3 - <<'PY'
import secrets
print("ndsp_" + secrets.token_urlsafe(32))
PY
)"
  echo "NDSP_WEBHOOK_SECRET=$SECRET" >> .env
  echo "✅ NDSP_WEBHOOK_SECRET added to .env"
else
  echo "ℹ️ NDSP_WEBHOOK_SECRET already exists"
fi

python3 - <<'PY'
from pathlib import Path

# Patch config
p = Path("backend/app/core/config.py")
s = p.read_text()

if "NDSP_WEBHOOK_SECRET" not in s:
    s = s.replace(
        '    BINANCE_MODE: str = "dryrun"\n',
        '    BINANCE_MODE: str = "dryrun"\n\n'
        '    NDSP_WEBHOOK_SECRET: str | None = None\n'
    )

p.write_text(s)
print("✅ config.py patched")


# Patch advanced_routes
p = Path("backend/app/api/advanced_routes.py")
s = p.read_text()

s = s.replace(
    "from fastapi import APIRouter, Depends, HTTPException",
    "from fastapi import APIRouter, Depends, HTTPException, Header"
)

if "from app.core.config import settings" not in s:
    s = s.replace(
        "from app.db.session import get_db",
        "from app.db.session import get_db\nfrom app.core.config import settings"
    )

if "class NdspWebhookSignalRequest" not in s:
    insert_class = r'''

class NdspWebhookSignalRequest(BaseModel):
    user_email: str
    symbol: str
    side: str
    notional_usdt: float
    reason: str = "NDSP webhook signal"
    ndsp_layer: str | None = None
    signal_id: str | None = None
'''
    s = s.replace("router = APIRouter()\n", "router = APIRouter()\n" + insert_class + "\n")

if '@router.post("/webhooks/ndsp-signal")' not in s:
    endpoint = r'''

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

    target_user = db.query(User).filter(User.email == payload.user_email).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    if not target_user.is_active:
        raise HTTPException(status_code=403, detail="Target user is disabled")

    reason = payload.reason
    if payload.ndsp_layer:
        reason = f"{reason} | NDSP Layer: {payload.ndsp_layer}"
    if payload.signal_id:
        reason = f"{reason} | Signal ID: {payload.signal_id}"

    pre_trade_risk_check(db, target_user, payload.symbol, payload.side)

    trade = await execute_signal(
        db=db,
        user=target_user,
        symbol=payload.symbol,
        side=payload.side,
        notional_usdt=payload.notional_usdt,
        reason=reason,
    )

    return {
        "status": "accepted",
        "trade_id": trade.id,
        "user_email": target_user.email,
        "symbol": trade.symbol,
        "side": trade.side,
        "mode": trade.mode,
        "trade_status": trade.status,
        "reason": trade.reason,
    }
'''
    s += endpoint

p.write_text(s)
print("✅ advanced_routes.py webhook added")
PY

cat > frontend/app/ndsp/page.tsx <<'EOF'
"use client";

import { useState } from "react";
import { api } from "../../lib/api";

export default function NdspSignalPage() {
  const [form, setForm] = useState({
    symbol: "BTC/USDT",
    side: "BUY",
    notional_usdt: 10,
    reason: "NDSP real signal",
    ndsp_layer: "layer-1"
  });

  const [webhookForm, setWebhookForm] = useState({
    user_email: "nawaf@example.com",
    symbol: "BTC/USDT",
    side: "BUY",
    notional_usdt: 10,
    reason: "NDSP webhook test signal",
    ndsp_layer: "layer-1",
    signal_id: "test-signal-001"
  });

  const [message, setMessage] = useState("");

  async function sendSignal() {
    setMessage("");
    try {
      const data = await api("/ndsp/signal", {
        method: "POST",
        body: JSON.stringify(form)
      });
      setMessage(`تم تنفيذ إشارة NDSP: ${data.symbol} ${data.side} ${data.status}`);
    } catch (e: any) {
      setMessage("فشل تنفيذ إشارة NDSP: " + e.message);
    }
  }

  return (
    <main className="container">
      <div className="card">
        <h1>NDSP Signal Bridge</h1>
        <p>هذه الصفحة لاختبار استقبال إشارات NDSP، أما الربط الحقيقي فيكون عبر Webhook آمن.</p>

        <div className="card">
          <h2>اختبار داخلي عبر جلسة المستخدم</h2>

          <label>Symbol</label>
          <input className="input" value={form.symbol} onChange={e => setForm({ ...form, symbol: e.target.value })} />

          <label style={{ display: "block", marginTop: 14 }}>Side</label>
          <select className="input" value={form.side} onChange={e => setForm({ ...form, side: e.target.value })}>
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>

          <label style={{ display: "block", marginTop: 14 }}>Notional USDT</label>
          <input className="input" type="number" value={form.notional_usdt} onChange={e => setForm({ ...form, notional_usdt: Number(e.target.value) })} />

          <label style={{ display: "block", marginTop: 14 }}>NDSP Layer</label>
          <input className="input" value={form.ndsp_layer} onChange={e => setForm({ ...form, ndsp_layer: e.target.value })} />

          <label style={{ display: "block", marginTop: 14 }}>Reason</label>
          <input className="input" value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} />

          <button className="btn btn-primary" style={{ marginTop: 18 }} onClick={sendSignal}>
            إرسال إشارة NDSP داخلية
          </button>
        </div>

        <div className="card">
          <h2>Webhook الحقيقي للربط مع NDSP</h2>

          <p>الرابط:</p>
          <pre style={{ whiteSpace: "pre-wrap" }}>POST https://bot.ndsp.app/api/webhooks/ndsp-signal</pre>

          <p>الهيدر المطلوب:</p>
          <pre style={{ whiteSpace: "pre-wrap" }}>X-NDSP-SECRET: القيمة الموجودة في .env</pre>

          <p>مثال Body:</p>
          <pre style={{ whiteSpace: "pre-wrap", direction: "ltr", textAlign: "left" }}>
{JSON.stringify(webhookForm, null, 2)}
          </pre>

          <p style={{ color: "#fbbf24" }}>
            لا تعرض NDSP_WEBHOOK_SECRET داخل الواجهة. يتم حفظه فقط في ملف .env على السيرفر.
          </p>
        </div>

        {message && <div className="card">{message}</div>}

        <p style={{ marginTop: 22 }}>
          <a href="/">العودة للوحة التحكم</a>
        </p>
      </div>
    </main>
  );
}
