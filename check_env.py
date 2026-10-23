# /opt/hunter_ksa1-bot/check_env.py
import os
from pathlib import Path
from dotenv import load_dotenv

# تحميل ملف .env من المسار الحالي أو جذور المشروع
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

def check_environment():
    print("==========================================")
    print("   فحص متغيرات البيئة لبوت hunter_ksa1   ")
    print("==========================================")

    # 1. فحص متغيرات قاعدة البيانات
    db_url = os.getenv("DATABASE_URL")
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")

    print("\n[ قاعدة البيانات - Database ]")
    if db_url:
        print(f"✅ DATABASE_URL موجودة: {db_url[:15]}... (مخفية للحماية)")
    elif db_host and db_name:
        print(f"✅ بيانات الاتصال المنفصلة موجودة (Host: {db_host}, DB: {db_name})")
    else:
        print("❌ تحذير: لم يتم العثور على DATABASE_URL أو بيانات قاعدة البيانات الأساسية في .env")

    # 2. فحص متغيرات تيليجرام
    print("\n[ إشعارات تيليجرام - Telegram Notifier ]")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if bot_token:
        print(f"✅ TELEGRAM_BOT_TOKEN موجود: {bot_token[:8]}...")
    else:
        print("⚠️ تنبيه: TELEGRAM_BOT_TOKEN غير متوفر (ستتوقف تنبيهات تيليجرام مؤقتاً).")

    if chat_id:
        print(f"✅ TELEGRAM_CHAT_ID موجود: {chat_id}")
    else:
        print("⚠️ تنبيه: TELEGRAM_CHAT_ID غير متوفر.")

    print("\n==========================================")

if __name__ == "__main__":
    check_environment()
