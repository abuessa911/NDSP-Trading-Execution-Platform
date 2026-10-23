# /opt/hunter_ksa1-bot/test_system.py
import asyncio
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

# التأكد من تثبيت الحزم المطلوبة تلقائياً
def ensure_packages():
    for pkg, pip_name in [("asyncpg", "asyncpg"), ("aiohttp", "aiohttp")]:
        try:
            __import__(pkg)
        except ImportError:
            print(f"جاري تثبيت الحزمة الناقصة: {pip_name}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--quiet", "--break-system-packages"])

ensure_packages()

import asyncpg
from aiohttp import ClientSession

load_dotenv()

RAW_DATABASE_URL = os.getenv("DATABASE_URL", "")
# تصحيح صيغة الرابط ليتوافق مع asyncpg مباشرة
if "postgresql+asyncpg://" in RAW_DATABASE_URL:
    DATABASE_URL = RAW_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
else:
    DATABASE_URL = RAW_DATABASE_URL

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def test_database():
    print("\n--- [1/2] اختبار الاتصال بقاعدة البيانات وقراءة إعدادات المخاطر ---")
    if not DATABASE_URL:
        print("❌ خطأ: DATABASE_URL غير معرف في ملف .env")
        return False

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ تم الاتصال بقاعدة البيانات بنجاح!")

        row = await conn.fetchrow("SELECT * FROM bot_risk_settings WHERE bot_name = 'hunter_ksa1';")
        if row:
            print(f"✅ تم العثور على إعدادات المخاطر للبوت:")
            print(f"   - مخاطرة الصفقة: {row['risk_per_trade_pct']}%")
            print(f"   - أقصى خسارة يومية: {row['max_daily_loss_pct']}%")
            print(f"   - وقف الخسارة (SL): {row['stop_loss_pct']}%")
            print(f"   - جني الأرباح (TP): {row['take_profit_pct']}%")
        else:
            print("⚠️ تحذير: لم يتم العثور على سجل الإعدادات لـ hunter_ksa1 في الجدول.")

        await conn.close()
        return True
    except Exception as e:
        print(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
        return False

async def test_telegram():
    print("\n--- [2/2] اختبار إرسال تنبيه تجريبي عبر تيليجرام ---")
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ تنبيه: TELEGRAM_BOT_TOKEN أو TELEGRAM_CHAT_ID غير معرّف، تم تخطي اختبار تيليجرام.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": "🚀 *اختبار ناجح - بوت hunter_ksa1*\n\nالنظام متصل وجاهز للتشغيل في بيئة الـ Staging!",
        "parse_mode": "Markdown"
    }

    try:
        async with ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as resp:
                if resp.status == 200:
                    print("✅ تم إرسال رسالة الاختبار عبر تيليجرام بنجاح! تفقد هاتفك.")
                    return True
                else:
                    print(f"❌ فشل إرسال التيليجرام، رمز الاستجابة: {resp.status}")
                    return False
    except Exception as e:
        print(f"❌ خطأ أثناء الاتصال بخادم تيليجرام: {e}")
        return False

async def main():
    print("==========================================")
    print("   بدء الفحص الشامل لنظام hunter_ksa1     ")
    print("==========================================")

    db_ok = await test_database()
    tg_ok = await test_telegram()

    print("\n==========================================")
    if db_ok:
        print("🎉 النظام جاهز ومستعد للانتقال للخطوة التالية!")
    else:
        print("⚠️ يرجى تصحيح أخطاء الاتصال أعلاه قبل المتابعة.")
    print("==========================================")

if __name__ == "__main__":
    asyncio.run(main())
