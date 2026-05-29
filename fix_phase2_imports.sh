#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

echo "🔧 Fixing Phase 2 imports..."

python3 - <<'PY'
from pathlib import Path

p = Path("backend/app/api/advanced_routes.py")

if not p.exists():
    raise SystemExit("❌ advanced_routes.py not found")

s = p.read_text()

# التصحيح الأهم: المشروع عندك يستخدم execution.py وليس trading_service.py
s = s.replace(
    "from app.services.trading_service import execute_signal",
    "from app.services.execution import execute_signal"
)

# تصحيح fallback لتشفير كلمة المرور إذا احتاج
s = s.replace(
    "from app.core.security import verify_password, get_password_hash",
    "from app.auth.security import verify_password, hash_password as get_password_hash"
)

p.write_text(s)
print("✅ advanced_routes.py fixed")
PY

echo "🔄 Rebuilding API and Frontend..."
docker compose up -d --build api frontend

echo "⏳ Waiting 5 seconds..."
sleep 5

echo "📌 Containers:"
docker compose ps

echo "📌 API logs:"
docker compose logs --tail=60 api

echo "✅ Done"
