#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_health_backup_$STAMP"
mkdir -p "$BACKUP_DIR"

cp backend/app/api/advanced_routes.py "$BACKUP_DIR/advanced_routes.py"
cp frontend/app/page.tsx "$BACKUP_DIR/page.tsx"
cp frontend/app/globals.css "$BACKUP_DIR/globals.css"

echo "✅ Backup created: $BACKUP_DIR"

mkdir -p backups scripts frontend/app/health frontend/app/backups

cat > scripts/backup_now.sh <<'BKEOF'
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
BKEOF

chmod +x scripts/backup_now.sh

python3 - <<'PY'
from pathlib import Path

p = Path("backend/app/api/advanced_routes.py")
s = p.read_text()

if "import os" not in s:
    s = "import os\nimport subprocess\nfrom pathlib import Path\n" + s

if "from app.core.config import settings" not in s:
    s = s.replace(
        "from app.db.session import get_db",
        "from app.db.session import get_db\nfrom app.core.config import settings"
    )

if '@router.get("/system/health")' not in s:
    s += r'''

@router.get("/system/health")
def system_health(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    telegram_ok = bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)
    email_ok = bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD and settings.EMAIL_FROM)

    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    docker_status = "unknown"
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            cwd="/home/nawaf511/ndsp-binance-bot",
            capture_output=True,
            text=True,
            timeout=10,
        )
        docker_status = "ok" if result.returncode == 0 else "error"
    except Exception:
        docker_status = "unavailable"

    return {
        "api": "ok",
        "database": "ok" if db_ok else "error",
        "telegram_configured": telegram_ok,
        "email_configured": email_ok,
        "binance_mode": settings.BINANCE_MODE,
        "docker_status": docker_status,
        "user": {
            "email": user.email,
            "is_admin": getattr(user, "is_admin", False),
            "is_active": user.is_active,
            "binance_key_configured": bool(user.api_key),
        }
    }


@router.get("/system/backups")
def list_backups(
    user: User = Depends(get_current_user),
):
    require_admin(user)

    backup_dir = Path("/home/nawaf511/ndsp-binance-bot/backups")
    backup_dir.mkdir(exist_ok=True)

    files = []
    for f in sorted(backup_dir.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)[:80]:
        files.append({
            "name": f.name,
            "size_bytes": f.stat().st_size,
            "modified_at": f.stat().st_mtime,
        })

    return {"backups": files}


@router.post("/system/backups/run")
def run_backup(
    user: User = Depends(get_current_user),
):
    require_admin(user)

    result = subprocess.run(
        ["/home/nawaf511/ndsp-binance-bot/scripts/backup_now.sh"],
        cwd="/home/nawaf511/ndsp-binance-bot",
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )

    return {
        "status": "backup_completed",
        "stdout": result.stdout,
    }
'''
p.write_text(s)
print("✅ advanced_routes.py patched")
PY

cat > frontend/app/health/page.tsx <<'EOF'
"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function HealthPage() {
  const [health, setHealth] = useState<any>(null);
  const [message, setMessage] = useState("");

  async function loadHealth() {
    setMessage("");
    try {
      const data = await api("/system/health");
      setHealth(data);
    } catch (e: any) {
      setMessage("فشل تحميل صحة النظام: " + e.message);
    }
  }

  useEffect(() => {
    loadHealth();
  }, []);

  function statusBadge(ok: boolean, label: string) {
    return (
      <span className={ok ? "health-badge ok" : "health-badge bad"}>
        {ok ? "✅" : "❌"} {label}
      </span>
    );
  }

  return (
    <main className="container">
      <div className="card">
        <h1>Health Monitor</h1>
        <p>مراقبة حالة النظام والخدمات الأساسية.</p>

        {message && <div className="card">{message}</div>}

        {health && (
          <div className="health-grid">
            <div className="health-box">
              <h3>API</h3>
              {statusBadge(health.api === "ok", health.api)}
            </div>

            <div className="health-box">
              <h3>Database</h3>
              {statusBadge(health.database === "ok", health.database)}
            </div>

            <div className="health-box">
              <h3>Telegram</h3>
              {statusBadge(health.telegram_configured, health.telegram_configured ? "Configured" : "Missing")}
            </div>

            <div className="health-box">
              <h3>Email</h3>
              {statusBadge(health.email_configured, health.email_configured ? "Configured" : "Missing")}
            </div>

            <div className="health-box">
              <h3>Binance Mode</h3>
              <span className="health-badge mode">{health.binance_mode}</span>
            </div>

            <div className="health-box">
              <h3>Docker</h3>
              {statusBadge(health.docker_status === "ok", health.docker_status)}
            </div>

            <div className="health-box">
              <h3>Current User</h3>
              <p>{health.user?.email}</p>
              <p>Admin: {String(health.user?.is_admin)}</p>
              <p>Binance: {String(health.user?.binance_key_configured)}</p>
            </div>
          </div>
        )}

        <button className="btn btn-secondary" onClick={loadHealth}>تحديث</button>

        <p style={{ marginTop: 22 }}>
          <a href="/">العودة للوحة التحكم</a>
        </p>
      </div>
    </main>
  );
}
