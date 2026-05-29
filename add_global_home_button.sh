#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_global_home_button_$STAMP"
mkdir -p "$BACKUP_DIR"

cp frontend/app/layout.tsx "$BACKUP_DIR/layout.tsx"
cp frontend/app/globals.css "$BACKUP_DIR/globals.css"

echo "✅ Backup created: $BACKUP_DIR"

python3 - <<'PY'
from pathlib import Path

p = Path("frontend/app/layout.tsx")
s = p.read_text()

if "global-home-button" not in s:
    # Wrap body children with global home button.
    s = s.replace(
        "{children}",
        '''<a className="global-home-button" href="/" aria-label="العودة للرئيسية">
          <span>⌂</span>
          <b>الرئيسية</b>
        </a>
        {children}'''
    )

p.write_text(s)
print("✅ Global home button added to layout.tsx")
PY

cat >> frontend/app/globals.css <<'EOF'

/* Global Home Button */
.global-home-button {
  position: fixed;
  top: 18px;
  left: 18px;
  z-index: 9999;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 11px 15px;
  border-radius: 999px;
  text-decoration: none;
  color: #eafff1;
  background:
    linear-gradient(135deg, rgba(34, 197, 94, 0.28), rgba(15, 23, 42, 0.92)),
    rgba(2, 6, 23, 0.88);
  border: 1px solid rgba(34, 197, 94, 0.38);
  box-shadow:
    0 12px 30px rgba(0, 0, 0, 0.32),
    0 0 22px rgba(34, 197, 94, 0.14);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  font-weight: 900;
}

.global-home-button span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.18);
  color: #86efac;
  font-size: 16px;
}

.global-home-button b {
  font-size: 14px;
  letter-spacing: 0.2px;
}

.global-home-button:hover {
  transform: translateY(-1px);
  border-color: rgba(134, 239, 172, 0.65);
  box-shadow:
    0 16px 38px rgba(0, 0, 0, 0.38),
    0 0 28px rgba(34, 197, 94, 0.22);
}

@media (max-width: 700px) {
  .global-home-button {
    top: auto;
    left: 14px;
    bottom: 82px;
    padding: 10px 13px;
  }

  .global-home-button b {
    font-size: 13px;
  }
}
