#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

echo "===== PROJECT TREE ====="
find backend/app -maxdepth 4 -type f | sort

echo ""
echo "===== ROUTES ====="
sed -n '1,260p' backend/app/api/routes.py || true

echo ""
echo "===== MODELS FILES ====="
find backend/app -type f \( -name "*model*" -o -name "models.py" \) -print -exec sed -n '1,260p' {} \;

echo ""
echo "===== SCHEMAS FILES ====="
find backend/app -type f \( -name "*schema*" -o -name "schemas.py" \) -print -exec sed -n '1,260p' {} \;

echo ""
echo "===== DB SESSION ====="
sed -n '1,220p' backend/app/db/session.py || true

echo ""
echo "===== CONFIG ====="
sed -n '1,220p' backend/app/core/config.py || true

echo ""
echo "===== FRONTEND PAGE ====="
sed -n '1,360p' frontend/app/page.tsx || true

echo ""
echo "===== COMPOSE ====="
cat docker-compose.yml
