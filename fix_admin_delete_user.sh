#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

FILE="backend/app/api/advanced_routes.py"
STAMP="$(date +%Y%m%d_%H%M%S)"

cp "$FILE" "$FILE.backup_delete_fix_$STAMP"

python3 - <<'PY'
from pathlib import Path
import re

p = Path("backend/app/api/advanced_routes.py")
s = p.read_text()

# تأكد أن الاستيرادات فيها الجداول المطلوبة
s = s.replace(
    "from app.models.models import User, TradeLog",
    "from app.models.models import User, TradeLog, BinanceApiKey, BotSettings"
)

new_delete = r'''
@router.delete("/admin/users/{target_user_id}")
def admin_delete_user(
    target_user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_admin(user)

    if target_user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete related user data first to avoid foreign key errors
    db.query(TradeLog).filter(TradeLog.user_id == target_user_id).delete(synchronize_session=False)
    db.query(BinanceApiKey).filter(BinanceApiKey.user_id == target_user_id).delete(synchronize_session=False)
    db.query(BotSettings).filter(BotSettings.user_id == target_user_id).delete(synchronize_session=False)

    db.delete(target)
    db.commit()

    return {"status": "deleted", "user_id": target_user_id}
'''

pattern = r'@router\.delete\("/admin/users/\{target_user_id\}"\)\ndef admin_delete_user\([\s\S]*?return \{"status": "deleted"\}'
if re.search(pattern, s):
    s = re.sub(pattern, new_delete.strip(), s)
else:
    # لو ما لقى البلوك القديم، يضيفه في آخر الملف
    if '@router.delete("/admin/users/{target_user_id}")' not in s:
        s += "\n\n" + new_delete

p.write_text(s)
print("✅ admin delete endpoint fixed")
PY

docker compose up -d --build api frontend

echo "✅ انتهى"
echo "افتح صفحة Admin وجرب الحذف مرة ثانية:"
echo "https://bot.ndsp.app/admin"
