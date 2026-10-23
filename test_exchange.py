# /opt/hunter_ksa1-bot/test_exchange.py
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")
USE_TESTNET = os.getenv("USE_TESTNET", "true").lower() == "true"

async def test_exchange_connection():
    print("==========================================")
    print("   فحص الاتصال بمنصة التداول (Binance)   ")
    print("==========================================")

    if not API_KEY or not API_SECRET:
        print("⚠️ تنبيه: مفاتيح BINANCE_API_KEY أو BINANCE_API_SECRET غير متوفرة في ملف .env")
        return False

    exchange = None
    try:
        import ccxt.async_support as ccxt

        exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future', # اختيار العقود الآجلة
            }
        })

        if USE_TESTNET:
            # تفعيل وضع التجربة الرسمي المعين داخل مكتبة CCXT
            exchange.enable_demo_trading(True)
            print("🌐 وضع التشغيل: Binance Futures Demo Trading (Native CCXT)")
        else:
            print("🚨 تنبيه: وضع التشغيل: Live (الحساب الحقيقي!)")

        # تحميل الأسواق
        markets = await exchange.load_markets()
        print(f"✅ تم الاتصال بنجاح! تم تحميل {len(markets)} سوق عقود آجل.")

        # جلب الرصيد التجريبي لـ Futures
        balance = await exchange.fetch_balance()
        print("💰 تم جلب رصيد الحساب التجريبي بنجاح!")
        if 'USDT' in balance:
            print(f"💵 رصيد USDT المتاح: {balance['USDT'].get('free', 0)}")

        await exchange.close()
        return True

    except Exception as e:
        print(f"❌ فشل الاتصال بمنصة التداول: {e}")
        if exchange:
            await exchange.close()
        return False

if __name__ == "__main__":
    asyncio.run(test_exchange_connection())
