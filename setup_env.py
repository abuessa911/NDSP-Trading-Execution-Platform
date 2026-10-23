# /opt/hunter_ksa1-bot/setup_env.py
import os
from pathlib import Path

def setup_environment():
    env_path = Path(__file__).resolve().parent / ".env"

    print("==========================================")
    print("   إعداد وتحديث متغيرات البيئة لبوت hunter_ksa1")
    print("==========================================")
    print("يرجى إدخال البيانات التالية (اضغط Enter لتخطي أي قيمة اختياريّة):\n")

    # استقبال المدخلات من المستخدم
    db_url = input("أدخل رابط قاعدة البيانات (DATABASE_URL) [مثال: postgresql://user:pass@localhost:5432/dbname]: ").strip()
    bot_token = input("أدخل توكن بوت تيليجرام (TELEGRAM_BOT_TOKEN): ").strip()
    chat_id = input("أدخل معرف محادثة تيليجرام (TELEGRAM_CHAT_ID): ").strip()

    # قراءة المتغيرات القديمة إن وجدت لتجنب مسحها
    env_lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            env_lines = f.readlines()

    # تحويل المحتوى إلى قاموس لتحديثه
    env_dict = {}
    for line in env_lines:
        if "=" in line and not line.strip().startswith("#"):
            key, val = line.strip().split("=", 1)
            env_dict[key.strip()] = val.strip().strip('"').strip("'")

    # تحديث القيم الجديدة إذا تم إدخالها
    if db_url:
        env_dict["DATABASE_URL"] = db_url
    if bot_token:
        env_dict["TELEGRAM_BOT_TOKEN"] = bot_token
    if chat_id:
        env_dict["TELEGRAM_CHAT_ID"] = chat_id

    # كتابة القيم المحدثة داخل ملف .env
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("# Generated automatically by setup_env.py\n")
        for key, val in env_dict.items():
            f.write(f'{key}="{val}"\n')

    print("\n==========================================")
    print("✅ تم حفظ وتحديث ملف .env بنجاح!")
    print("==========================================")

if __name__ == "__main__":
    setup_environment()
