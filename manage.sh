#!/usr/bin/env bash
set -e

PROJECT_DIR="/home/nawaf511/ndsp-binance-bot"
cd "$PROJECT_DIR"

case "$1" in
  status)
    docker compose ps
    ;;

  restart)
    docker compose up -d --build
    ;;

  api-restart)
    docker compose up -d --build api
    ;;

  frontend-restart)
    docker compose up -d --build frontend
    ;;

  logs)
    docker compose logs --tail=120 api frontend
    ;;

  api-logs)
    docker compose logs --tail=160 api
    ;;

  frontend-logs)
    docker compose logs --tail=160 frontend
    ;;

  health)
    echo "API:"
    curl -s http://127.0.0.1:8000/
    echo
    echo
    echo "Frontend:"
    curl -I http://127.0.0.1:3010 | head
    echo
    echo "HTTPS:"
    curl -I https://bot.ndsp.app | head
    ;;

  mode)
    docker compose exec -T api python - <<'PY'
from app.core.config import settings
print("BINANCE_MODE:", settings.BINANCE_MODE)
PY
    ;;

  backup)
    if [ -x scripts/backup_now.sh ]; then
      ./scripts/backup_now.sh
    else
      echo "❌ scripts/backup_now.sh غير موجود"
      exit 1
    fi
    ;;

  db-users)
    docker compose exec -T postgres psql -U tradingbot -d tradingbot -c "SELECT id,email,is_admin,is_active,created_at FROM users ORDER BY id;"
    ;;

  safety)
    echo "Live Safety Checklist from API:"
    TOKEN_MESSAGE="افتح من الواجهة: https://bot.ndsp.app/safety"
    echo "$TOKEN_MESSAGE"
    ;;

  webhook-secret-check)
    if grep -q '^NDSP_WEBHOOK_SECRET=' .env; then
      SECRET="$(grep '^NDSP_WEBHOOK_SECRET=' .env | head -n 1 | cut -d= -f2-)"
      echo "NDSP_WEBHOOK_SECRET set: yes"
      echo "Length: ${#SECRET}"
      echo "Duplicates:"
      grep -c '^NDSP_WEBHOOK_SECRET=' .env
    else
      echo "NDSP_WEBHOOK_SECRET set: no"
    fi
    ;;

  webhook-test)
    SECRET="$(grep '^NDSP_WEBHOOK_SECRET=' .env | head -n 1 | cut -d= -f2-)"

    if [ -z "$SECRET" ]; then
      echo "❌ NDSP_WEBHOOK_SECRET غير موجود في .env"
      exit 1
    fi

    SIGNAL_ID="manage-webhook-$(date +%s)"

    cat > /tmp/ndsp_webhook_test.json <<JSON
{
  "user_email": "nawaf@example.com",
  "symbol": "ETH/USDT",
  "side": "SELL",
  "notional_usdt": 10,
  "reason": "manage.sh webhook test",
  "ndsp_layer": "layer-1",
  "signal_id": "$SIGNAL_ID"
}
JSON

    curl --http1.1 -s -X POST "https://bot.ndsp.app/api/webhooks/ndsp-signal" \
      -H "Content-Type: application/json" \
      -H "X-NDSP-SECRET: ${SECRET}" \
      --data-binary @/tmp/ndsp_webhook_test.json

    echo
    ;;

  local-webhook-test)
    SECRET="$(grep '^NDSP_WEBHOOK_SECRET=' .env | head -n 1 | cut -d= -f2-)"

    if [ -z "$SECRET" ]; then
      echo "❌ NDSP_WEBHOOK_SECRET غير موجود في .env"
      exit 1
    fi

    SIGNAL_ID="local-webhook-$(date +%s)"

    cat > /tmp/ndsp_webhook_test.json <<JSON
{
  "user_email": "nawaf@example.com",
  "symbol": "ETH/USDT",
  "side": "SELL",
  "notional_usdt": 10,
  "reason": "manage.sh local webhook test",
  "ndsp_layer": "layer-1",
  "signal_id": "$SIGNAL_ID"
}
JSON

    curl -s -X POST "http://127.0.0.1:8000/webhooks/ndsp-signal" \
      -H "Content-Type: application/json" \
      -H "X-NDSP-SECRET: ${SECRET}" \
      --data-binary @/tmp/ndsp_webhook_test.json

    echo
    ;;

  *)
    echo "NDSP Trading Bot Manager"
    echo
    echo "Usage:"
    echo "  ./manage.sh status               حالة الحاويات"
    echo "  ./manage.sh health               فحص API/Frontend/HTTPS"
    echo "  ./manage.sh restart              إعادة بناء وتشغيل الكل"
    echo "  ./manage.sh api-restart          إعادة بناء API فقط"
    echo "  ./manage.sh frontend-restart     إعادة بناء الواجهة فقط"
    echo "  ./manage.sh logs                 لوج API والواجهة"
    echo "  ./manage.sh api-logs             لوج API"
    echo "  ./manage.sh frontend-logs        لوج الواجهة"
    echo "  ./manage.sh backup               إنشاء نسخة احتياطية"
    echo "  ./manage.sh mode                 عرض BINANCE_MODE"
    echo "  ./manage.sh db-users             عرض المستخدمين"
    echo "  ./manage.sh webhook-secret-check فحص سكرت NDSP"
    echo "  ./manage.sh webhook-test         اختبار Webhook عبر HTTPS"
    echo "  ./manage.sh local-webhook-test   اختبار Webhook داخلي"
    ;;
esac
