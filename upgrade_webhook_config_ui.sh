#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_webhook_config_$STAMP"
mkdir -p "$BACKUP_DIR"

cp backend/app/api/advanced_routes.py "$BACKUP_DIR/advanced_routes.py"
cp frontend/app/page.tsx "$BACKUP_DIR/page.tsx"
cp frontend/app/globals.css "$BACKUP_DIR/globals.css"

mkdir -p frontend/app/webhook-config

echo "✅ Backup created: $BACKUP_DIR"

python3 - <<'PY'
from pathlib import Path

p = Path("backend/app/api/advanced_routes.py")
s = p.read_text()

if "import secrets" not in s:
    s = "import secrets\n" + s

if '@router.get("/ndsp/webhook-config")' not in s:
    s += r'''

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
            "side": "BUY",
            "notional_usdt": 10,
            "reason": "NDSP webhook signal",
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
'''
p.write_text(s)
print("✅ advanced_routes.py webhook config endpoints added")
PY

cat > frontend/app/webhook-config/page.tsx <<'EOF'
"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function WebhookConfigPage() {
  const [config, setConfig] = useState<any>(null);
  const [newSecret, setNewSecret] = useState("");
  const [message, setMessage] = useState("");
  const [testBody, setTestBody] = useState<any>({
    user_email: "nawaf@example.com",
    symbol: "ETH/USDT",
    side: "BUY",
    notional_usdt: 10,
    reason: "NDSP webhook config page test",
    ndsp_layer: "layer-1",
    signal_id: "webhook-config-test"
  });

  async function loadConfig() {
    setMessage("");
    try {
      const data = await api("/ndsp/webhook-config");
      setConfig(data);
      setTestBody(data.example_body || testBody);
    } catch (e: any) {
      setMessage("فشل تحميل إعدادات Webhook: " + e.message);
    }
  }

  async function rotateSecret() {
    setMessage("");

    const ok = window.confirm(
      "توليد Secret جديد سيجعل أي Secret قديم غير صالح. هل تريد المتابعة؟"
    );

    if (!ok) return;

    try {
      const data = await api("/ndsp/webhook-config/rotate", {
        method: "POST"
      });

      setNewSecret(data.new_secret);
      setMessage("تم توليد Secret جديد. انسخه الآن واحفظه في منظومة NDSP.");
      await loadConfig();
    } catch (e: any) {
      setMessage("فشل توليد Secret جديد: " + e.message);
    }
  }

  async function testWebhook() {
    setMessage("");

    if (!newSecret) {
      setMessage("للاختبار من هذه الصفحة، ولّد Secret جديد أو استخدم curl من السيرفر بالسكرت الموجود في .env.");
      return;
    }

    try {
      const res = await fetch("/api/webhooks/ndsp-signal", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-NDSP-SECRET": newSecret
        },
        body: JSON.stringify({
          ...testBody,
          signal_id: "webhook-config-test-" + Date.now()
        })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(JSON.stringify(data));
      }

      setMessage("تم اختبار Webhook بنجاح: " + JSON.stringify(data));
    } catch (e: any) {
      setMessage("فشل اختبار Webhook: " + e.message);
    }
  }

  useEffect(() => {
    loadConfig();
  }, []);

  return (
    <main className="container">
      <div className="card webhook-config-card">
        <h1>NDSP Webhook Config</h1>
        <p>
          من هنا يتم ربط منظومة NDSP الحقيقية مع بوت التنفيذ عبر Webhook آمن.
        </p>

        {message && <div className="card">{message}</div>}

        {config && (
          <>
            <div className="webhook-grid">
              <div className="webhook-box">
                <span>Webhook URL</span>
                <strong>{config.webhook_url}</strong>
              </div>

              <div className="webhook-box">
                <span>Method</span>
                <strong>{config.method}</strong>
              </div>

              <div className="webhook-box">
                <span>Header</span>
                <strong>{config.header_name}</strong>
              </div>

              <div className="webhook-box">
                <span>Secret Configured</span>
                <strong>{config.configured ? "Yes" : "No"}</strong>
              </div>

              <div className="webhook-box">
                <span>Secret Length</span>
                <strong>{config.secret_length}</strong>
              </div>

              <div className="webhook-box">
                <span>Duplicate Secrets</span>
                <strong>{config.duplicate_count}</strong>
              </div>
            </div>

            <div className="card">
              <h2>Example Body</h2>
              <pre className="webhook-pre">
{JSON.stringify(config.example_body, null, 2)}
              </pre>
            </div>

            <div className="card">
              <h2>توليد Secret جديد</h2>
              <p style={{ color: "#fbbf24" }}>
                بعد التوليد، انسخ Secret فورًا وضعه في منظومة NDSP. لن يتم عرضه مرة أخرى.
              </p>

              <button className="btn btn-danger" onClick={rotateSecret}>
                توليد Secret جديد
              </button>

              {newSecret && (
                <div className="new-secret-box">
                  <span>Secret الجديد</span>
                  <code>{newSecret}</code>
                </div>
              )}
            </div>

            <div className="card">
              <h2>اختبار Webhook من الصفحة</h2>

              <label>User Email</label>
              <input
                className="input"
                value={testBody.user_email}
                onChange={e => setTestBody({ ...testBody, user_email: e.target.value })}
              />

              <label style={{ display: "block", marginTop: 12 }}>Symbol</label>
              <input
                className="input"
                value={testBody.symbol}
                onChange={e => setTestBody({ ...testBody, symbol: e.target.value })}
              />

              <label style={{ display: "block", marginTop: 12 }}>Side</label>
              <select
                className="input"
                value={testBody.side}
                onChange={e => setTestBody({ ...testBody, side: e.target.value })}
              >
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
              </select>

              <label style={{ display: "block", marginTop: 12 }}>Notional USDT</label>
              <input
                className="input"
                type="number"
                value={testBody.notional_usdt}
                onChange={e => setTestBody({ ...testBody, notional_usdt: Number(e.target.value) })}
              />

              <label style={{ display: "block", marginTop: 12 }}>NDSP Layer</label>
              <input
                className="input"
                value={testBody.ndsp_layer}
                onChange={e => setTestBody({ ...testBody, ndsp_layer: e.target.value })}
              />

              <label style={{ display: "block", marginTop: 12 }}>Reason</label>
              <input
                className="input"
                value={testBody.reason}
                onChange={e => setTestBody({ ...testBody, reason: e.target.value })}
              />

              <button className="btn btn-primary" style={{ marginTop: 18 }} onClick={testWebhook}>
                اختبار Webhook
              </button>
            </div>
          </>
        )}

        <p style={{ marginTop: 22 }}>
          <a href="/">العودة للوحة التحكم</a>
        </p>
      </div>
    </main>
  );
}
