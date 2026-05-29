#!/usr/bin/env bash
set -e

PROJECT_DIR="/home/nawaf511/ndsp-binance-bot"
BACKUP_DIR="$PROJECT_DIR/backups"
STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

cd "$PROJECT_DIR"

echo "🔄 Creating database backup..."
docker compose exec -T postgres pg_dump -U tradingbot tradingbot > "$BACKUP_DIR/db_$STAMP.sql"

echo "🔄 Backing up env file..."
cp .env "$BACKUP_DIR/env_$STAMP.backup"

echo "🔄 Backing up docker-compose..."
cp docker-compose.yml "$BACKUP_DIR/docker-compose_$STAMP.yml"

echo "🔄 Creating project metadata..."
cat > "$BACKUP_DIR/meta_$STAMP.txt" <<META
NDSP Trading Bot Backup
Created At: $STAMP
Project: $PROJECT_DIR
Files:
- db_$STAMP.sql
- env_$STAMP.backup
- docker-compose_$STAMP.yml
META

echo "✅ Backup completed:"
echo "$BACKUP_DIR"
