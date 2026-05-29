#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_protective_orders_$STAMP"
mkdir -p "$BACKUP_DIR"

cp backend/app/services/execution.py "$BACKUP_DIR/execution.py"
cp frontend/app/logs/page.tsx "$BACKUP_DIR/logs_page.tsx" 2>/dev/null || true
cp frontend/app/page.tsx "$BACKUP_DIR/page.tsx"

echo "✅ Backup created: $BACKUP_DIR"

cat > /tmp/protective_patch.py <<'PY'
from pathlib import Path

p = Path("backend/app/services/execution.py")
s = p.read_text()

if "async def place_protective_orders_testnet" not in s:
    helper = r'''
async def place_protective_orders_testnet(exchange, symbol: str, side: str, amount: float, stop_loss_price: float, take_profit_price: float) -> dict:
    """
    محاولة آمنة لوضع أوامر حماية على Binance Testnet فقط.
    لا تعمل في live.
    ملاحظة: Spot OCO قد يفشل حسب دعم testnet/الزوج/الرصيد. الفشل يتم تسجيله ولا يوقف الصفقة الأصلية.
    """
    result = {
        "attempted": False,
        "stop_loss_order": None,
        "take_profit_order": None,
        "errors": []
    }

    if settings.BINANCE_MODE != "testnet":
        result["errors"].append("Protective orders are allowed only in testnet in this phase")
        return result

    if amount <= 0:
        result["errors"].append("Amount is zero")
        return result

    side = side.upper()
    protective_side = "SELL" if side == "BUY" else "BUY"

    result["attempted"] = True

    # Take Profit: limit order
    if take_profit_price and take_profit_price > 0:
        try:
            tp = await exchange.create_order(
                symbol=symbol,
                type="limit",
                side=protective_side.lower(),
                amount=amount,
                price=take_profit_price,
                params={"timeInForce": "GTC"},
            )
            result["take_profit_order"] = tp
        except Exception as exc:
            result["errors"].append(f"take_profit_failed: {repr(exc)}")

    # Stop Loss: stop-limit style if supported by exchange/testnet
    if stop_loss_price and stop_loss_price > 0:
        try:
            if protective_side == "SELL":
                stop_limit_price = stop_loss_price * 0.999
            else:
                stop_limit_price = stop_loss_price * 1.001

            sl = await exchange.create_order(
                symbol=symbol,
                type="stop_loss_limit",
                side=protective_side.lower(),
                amount=amount,
                price=round(stop_limit_price, 8),
                params={
                    "stopPrice": stop_loss_price,
                    "timeInForce": "GTC",
                },
            )
            result["stop_loss_order"] = sl
        except Exception as exc:
            result["errors"].append(f"stop_loss_failed: {repr(exc)}")

    return result

'''
    s = s.replace("async def execute_signal(", helper + "\nasync def execute_signal(")

# بعد حساب protective_orders_status نضيف نتيجة أوامر الحماية
old = '''    protective_orders_status = "preview"
    if stop_loss_price > 0 or take_profit_price > 0:
        protective_orders_status = "preview_calculated"
'''
new = '''    protective_orders_status = "preview"
    protective_orders_result = None

    if stop_loss_price > 0 or take_profit_price > 0:
        protective_orders_status = "preview_calculated"

        if settings.BINANCE_MODE == "testnet" and status in ["closed", "filled"]:
            protective_orders_result = await place_protective_orders_testnet(
                exchange=exchange,
                symbol=symbol,
                side=side,
                amount=amount,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
            )

            if protective_orders_result and protective_orders_result.get("attempted"):
                if protective_orders_result.get("errors"):
                    protective_orders_status = "testnet_failed"
                else:
                    protective_orders_status = "testnet_submitted"
'''
if "protective_orders_result = None" not in s:
    s = s.replace(old, new)

# exchange_response يتضمن نتيجة أوامر الحماية
old = '''        exchange_response=json.dumps(response, ensure_ascii=False),
'''
new = '''        exchange_response=json.dumps({
            "entry_order": response,
            "protective_orders": protective_orders_result,
        }, ensure_ascii=False),
'''
if '"entry_order": response' not in s:
    s = s.replace(old, new)

# رسالة التنبيه أوضح
if "Protective Orders Result" not in s:
    s = s.replace(
'''        f"Protective Status: {protective_orders_status}\\n"
        f"Reason: {reason}"
''',
'''        f"Protective Status: {protective_orders_status}\\n"
        f"Protective Orders Result: {protective_orders_result}\\n"
        f"Reason: {reason}"
'''
    )

p.write_text(s)
print("✅ execution.py protective orders patched")
PY

python3 /tmp/protective_patch.py

echo "🔄 Rebuilding API..."
docker compose up -d --build api

echo "⏳ Waiting..."
sleep 5

echo "📌 API logs:"
docker compose logs --tail=80 api

echo "✅ Protective Orders Testnet upgrade completed"
echo "افتح الإعدادات وضع Stop Loss و Take Profit أكبر من صفر، ثم اختبر إشارة جديدة."
