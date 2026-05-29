#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_risk_ui_$STAMP"
mkdir -p "$BACKUP_DIR"

cp backend/app/api/routes.py "$BACKUP_DIR/routes.py"
cp frontend/app/page.tsx "$BACKUP_DIR/page.tsx"
cp frontend/app/globals.css "$BACKUP_DIR/globals.css"

echo "✅ Backup created: $BACKUP_DIR"

python3 - <<'PY'
from pathlib import Path
import re

# Backend: make /bot/test-signal pass risk checks
routes = Path("backend/app/api/routes.py")
s = routes.read_text()

if "from app.services.risk_service import pre_trade_risk_check" not in s:
    s = s.replace(
        "from app.services.execution import execute_signal",
        "from app.services.execution import execute_signal\nfrom app.services.risk_service import pre_trade_risk_check"
    )

old = '''    trade = await execute_signal(
        db=db,
        user=user,
        symbol=payload.symbol,
        side=payload.side,
        notional_usdt=payload.notional_usdt,
        reason=payload.reason,
    )
'''

new = '''    pre_trade_risk_check(db, user, payload.symbol, payload.side)

    trade = await execute_signal(
        db=db,
        user=user,
        symbol=payload.symbol,
        side=payload.side,
        notional_usdt=payload.notional_usdt,
        reason=payload.reason,
    )
'''

if "pre_trade_risk_check(db, user, payload.symbol, payload.side)" not in s:
    s = s.replace(old, new)

routes.write_text(s)
print("✅ Backend risk check added to /bot/test-signal")


# Frontend: add risk fields to Settings UI
page = Path("frontend/app/page.tsx")
s = page.read_text()

# Add fields to default settingsForm
s = s.replace(
'''    max_daily_loss_usdt: 20,
    max_trades_per_day: 3,
    telegram_enabled: true,''',
'''    max_daily_loss_usdt: 20,
    max_trades_per_day: 3,
    stop_loss_pct: 0,
    take_profit_pct: 0,
    prevent_duplicate_positions: true,
    telegram_enabled: true,''')

# Add settings UI block if not already present
if "Stop Loss %" not in s:
    target = '''          <div style={{ marginTop: 14 }}>
            <label>
              <input type="checkbox" checked={settingsForm.telegram_enabled} onChange={e => setSettingsForm({ ...settingsForm, telegram_enabled: e.target.checked })} /> Telegram
            </label>
            <br />
            <label>
              <input type="checkbox" checked={settingsForm.email_enabled} onChange={e => setSettingsForm({ ...settingsForm, email_enabled: e.target.checked })} /> Email
            </label>
          </div>
'''

    insert = '''          <div className="risk-settings-panel">
            <h3>إدارة المخاطر</h3>

            <div className="grid grid-3">
              <div>
                <label>Stop Loss %</label>
                <input
                  className="input"
                  type="number"
                  value={settingsForm.stop_loss_pct || 0}
                  onChange={e => setSettingsForm({ ...settingsForm, stop_loss_pct: Number(e.target.value) })}
                />
              </div>

              <div>
                <label>Take Profit %</label>
                <input
                  className="input"
                  type="number"
                  value={settingsForm.take_profit_pct || 0}
                  onChange={e => setSettingsForm({ ...settingsForm, take_profit_pct: Number(e.target.value) })}
                />
              </div>

              <div>
                <label>منع تكرار الصفقة</label>
                <div className="toggle-box">
                  <input
                    type="checkbox"
                    checked={settingsForm.prevent_duplicate_positions ?? true}
                    onChange={e => setSettingsForm({ ...settingsForm, prevent_duplicate_positions: e.target.checked })}
                  />
                  <span>منع نفس الزوج والاتجاه في نفس اليوم</span>
                </div>
              </div>
            </div>

            <p className="risk-note">
              Stop Loss و Take Profit محفوظة الآن كإعدادات مخاطرة. تنفيذ أوامر حماية فعلية على Binance سيتم في مرحلة OCO/Protective Orders.
            </p>
          </div>

''' + target

    s = s.replace(target, insert)

# Add quick links in dashboard if not exists
if "quick-action-panel" not in s:
    target = '''          <div className="card">
            <h2>آخر صفقة</h2>'''
    replacement = '''          <div className="card quick-action-panel">
            <h2>اختصارات مهمة</h2>
            <div className="grid grid-3">
              <a className="btn btn-secondary" href="/risk">Risk Center</a>
              <a className="btn btn-secondary" href="/safety">Live Safety</a>
              <a className="btn btn-secondary" href="/ndsp">NDSP Signal Bridge</a>
              <a className="btn btn-secondary" href="/account">تغيير كلمة المرور</a>
              <a className="btn btn-secondary" href="/admin">إدارة الأصدقاء</a>
              <a className="btn btn-secondary" href="/docs">Swagger API</a>
            </div>
          </div>

          <div className="card">
            <h2>آخر صفقة</h2>'''
    s = s.replace(target, replacement)

page.write_text(s)
print("✅ Frontend settings UI updated")
PY

cat >> frontend/app/globals.css <<'EOF'

/* Risk Settings UI */
.risk-settings-panel {
  margin-top: 18px;
  background:
    radial-gradient(circle at top left, rgba(239, 68, 68, 0.10), transparent 30%),
    rgba(2, 6, 23, 0.48);
  border: 1px solid rgba(248, 113, 113, 0.16);
  border-radius: 18px;
  padding: 18px;
}

.risk-settings-panel h3 {
  margin-top: 0;
  color: #fecaca;
}

.toggle-box {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 12px;
  padding: 12px;
}

.toggle-box span {
  color: #cbd5e1;
  font-size: 14px;
}

.risk-note {
  margin-bottom: 0;
  color: #fbbf24;
  line-height: 1.7;
  font-size: 14px;
}

.quick-action-panel a.btn {
  text-align: center;
}
