#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_protective_preview_$STAMP"
mkdir -p "$BACKUP_DIR"

cp backend/app/models/models.py "$BACKUP_DIR/models.py"
cp backend/app/services/execution.py "$BACKUP_DIR/execution.py"
cp backend/app/api/routes.py "$BACKUP_DIR/routes.py"
cp frontend/app/page.tsx "$BACKUP_DIR/page.tsx"

echo "✅ Backup created: $BACKUP_DIR"

python3 - <<'PY'
from pathlib import Path

p = Path("backend/app/models/models.py")
s = p.read_text()

if "stop_loss_price" not in s:
    s = s.replace(
        '    pnl_usdt: Mapped[float] = mapped_column(Float, default=0.0)\n',
        '    pnl_usdt: Mapped[float] = mapped_column(Float, default=0.0)\n'
        '    stop_loss_price: Mapped[float] = mapped_column(Float, default=0.0)\n'
        '    take_profit_price: Mapped[float] = mapped_column(Float, default=0.0)\n'
        '    protective_orders_status: Mapped[str] = mapped_column(String(50), default="preview")\n'
    )

p.write_text(s)
print("✅ models.py patched")
PY

python3 - <<'PY'
from pathlib import Path

p = Path("backend/app/services/execution.py")
s = p.read_text()

# أضف دالة حساب الحماية
if "def calculate_protective_prices" not in s:
    marker = "async def execute_signal("
    helper = '''
def calculate_protective_prices(user, side: str, entry_price: float) -> tuple[float, float]:
    """
    يحسب أسعار Stop Loss و Take Profit كمرحلة آمنة أولى.
    لا يرسل أوامر حماية فعلية إلى Binance في هذه المرحلة.
    """
    if not user.settings or entry_price <= 0:
        return 0.0, 0.0

    stop_loss_pct = float(getattr(user.settings, "stop_loss_pct", 0) or 0)
    take_profit_pct = float(getattr(user.settings, "take_profit_pct", 0) or 0)

    side = side.upper()

    stop_loss_price = 0.0
    take_profit_price = 0.0

    if side == "BUY":
        if stop_loss_pct > 0:
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        if take_profit_pct > 0:
            take_profit_price = entry_price * (1 + take_profit_pct / 100)

    elif side == "SELL":
        if stop_loss_pct > 0:
            stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
        if take_profit_pct > 0:
            take_profit_price = entry_price * (1 - take_profit_pct / 100)

    return round(stop_loss_price, 8), round(take_profit_price, 8)


'''
    s = s.replace(marker, helper + marker)

# أضف الحساب بعد response
old = '''    amount = float(response.get("amount", 0) or 0)
    price = float(response.get("price", 0) or 0)
    status = response.get("status", "submitted")
'''

new = '''    amount = float(response.get("amount", 0) or 0)
    price = float(response.get("price", 0) or 0)
    status = response.get("status", "submitted")

    stop_loss_price, take_profit_price = calculate_protective_prices(
        user=user,
        side=side,
        entry_price=price,
    )

    protective_orders_status = "preview"
    if stop_loss_price > 0 or take_profit_price > 0:
        protective_orders_status = "preview_calculated"
'''

if "protective_orders_status = \"preview_calculated\"" not in s:
    s = s.replace(old, new)

# أضف الحقول في TradeLog
old = '''        notional_usdt=notional_usdt,
        status=status,
        mode=settings.BINANCE_MODE,
        reason=reason,
        exchange_response=json.dumps(response, ensure_ascii=False),
    )
'''

new = '''        notional_usdt=notional_usdt,
        stop_loss_price=stop_loss_price,
        take_profit_price=take_profit_price,
        protective_orders_status=protective_orders_status,
        status=status,
        mode=settings.BINANCE_MODE,
        reason=reason,
        exchange_response=json.dumps(response, ensure_ascii=False),
    )
'''

if "stop_loss_price=stop_loss_price" not in s:
    s = s.replace(old, new)

# أضف معلومات الحماية في رسالة التنبيه
old = '''        f"Status: {status}\\n"
        f"Reason: {reason}"
    )
'''

new = '''        f"Status: {status}\\n"
        f"Stop Loss Preview: {stop_loss_price}\\n"
        f"Take Profit Preview: {take_profit_price}\\n"
        f"Protective Status: {protective_orders_status}\\n"
        f"Reason: {reason}"
    )
'''

if "Stop Loss Preview" not in s:
    s = s.replace(old, new)

p.write_text(s)
print("✅ execution.py patched")
PY

python3 - <<'PY'
from pathlib import Path

p = Path("backend/app/api/routes.py")
s = p.read_text()

old = '''            "notional_usdt": x.notional_usdt,
            "status": x.status,
            "mode": x.mode,
            "reason": x.reason,
            "created_at": x.created_at,
'''

new = '''            "notional_usdt": x.notional_usdt,
            "pnl_usdt": getattr(x, "pnl_usdt", 0),
            "stop_loss_price": getattr(x, "stop_loss_price", 0),
            "take_profit_price": getattr(x, "take_profit_price", 0),
            "protective_orders_status": getattr(x, "protective_orders_status", "preview"),
            "status": x.status,
            "mode": x.mode,
            "reason": x.reason,
            "created_at": x.created_at,
'''

if "stop_loss_price" not in s:
    s = s.replace(old, new)

p.write_text(s)
print("✅ routes.py patched")
PY

python3 - <<'PY'
from pathlib import Path

p = Path("frontend/app/page.tsx")
s = p.read_text()

# LastTradeCard: أضف Stop Loss / Take Profit لو لم تكن موجودة
if "Stop Loss Preview" not in s:
    s = s.replace(
'''          <div className="trade-detail-item">
            <span>الوضع</span>
            <strong>{trade.mode}</strong>
          </div>
        </div>

        <div className="trade-reason">''',
'''          <div className="trade-detail-item">
            <span>الوضع</span>
            <strong>{trade.mode}</strong>
          </div>

          <div className="trade-detail-item">
            <span>Stop Loss Preview</span>
            <strong>{trade.stop_loss_price || 0}</strong>
          </div>

          <div className="trade-detail-item">
            <span>Take Profit Preview</span>
            <strong>{trade.take_profit_price || 0}</strong>
          </div>

          <div className="trade-detail-item">
            <span>Protective Status</span>
            <strong>{trade.protective_orders_status || "preview"}</strong>
          </div>
        </div>

        <div className="trade-reason">'''
    )

# Trades table: أضف أعمدة
if "<th>SL</th>" not in s:
    s = s.replace(
'''                  <th>Status</th>
                  <th>Mode</th>
                  <th>Time</th>''',
'''                  <th>SL</th>
                  <th>TP</th>
                  <th>Protective</th>
                  <th>Status</th>
                  <th>Mode</th>
                  <th>Time</th>'''
    )

    s = s.replace(
'''                    <td>{t.status}</td>
                    <td>{t.mode}</td>
                    <td>{t.created_at}</td>''',
'''                    <td>{t.stop_loss_price || 0}</td>
                    <td>{t.take_profit_price || 0}</td>
                    <td>{t.protective_orders_status || "preview"}</td>
                    <td>{t.status}</td>
                    <td>{t.mode}</td>
                    <td>{t.created_at}</td>'''
    )

p.write_text(s)
print("✅ frontend page patched")
PY

echo "🔄 Rebuilding..."
docker compose up -d --build api frontend

echo "🔄 Running DB migration..."
docker compose exec -T api python - <<'PY'
from sqlalchemy import text
from app.db.session import engine

sql = [
    "ALTER TABLE trade_logs ADD COLUMN IF NOT EXISTS stop_loss_price DOUBLE PRECISION DEFAULT 0",
    "ALTER TABLE trade_logs ADD COLUMN IF NOT EXISTS take_profit_price DOUBLE PRECISION DEFAULT 0",
    "ALTER TABLE trade_logs ADD COLUMN IF NOT EXISTS protective_orders_status VARCHAR(50) DEFAULT 'preview'"
]

with engine.begin() as conn:
    for q in sql:
        conn.execute(text(q))

print("✅ protective preview migration done")
PY

echo "✅ Protective Preview upgrade completed"
echo "افتح https://bot.ndsp.app"
echo "ثم الإعدادات: ضع Stop Loss % و Take Profit %"
echo "ثم جرب إشارة جديدة من NDSP أو Test Signal"
