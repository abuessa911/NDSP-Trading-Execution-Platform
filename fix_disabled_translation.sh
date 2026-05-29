#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_disabled_translation_$STAMP"
mkdir -p "$BACKUP_DIR"

cp frontend/app/components/GlobalControls.tsx "$BACKUP_DIR/GlobalControls.tsx"

python3 - <<'PY'
from pathlib import Path

p = Path("frontend/app/components/GlobalControls.tsx")
s = p.read_text()

# Add full-word translations before partial words
replacements = {
    '"تعطيل": "Disable",': '"معطل": "Disabled",\n  "تعطيل": "Disable",',
    '"تفعيل": "Enable",': '"مفعل": "Enabled",\n  "تفعيل": "Enable",',
    '"Disable": "تعطيل",': '"Disabled": "معطل",\n  "Disable": "تعطيل",',
    '"Enable": "تفعيل",': '"Enabled": "مفعل",\n  "Enable": "تفعيل",',
}

for old, new in replacements.items():
    if old in s and new not in s:
        s = s.replace(old, new)

# Add extra hard cleanup for mixed leftovers
old_line = '.replaceAll("Welcome، Welcome", lang === "en" ? "Welcome" : "مرحباً");'
new_line = '''.replaceAll("Welcome، Welcome", lang === "en" ? "Welcome" : "مرحباً")
    .replaceAll("تعطيلd", lang === "en" ? "Disabled" : "معطل")
    .replaceAll("تفعيلd", lang === "en" ? "Enabled" : "مفعل")
    .replaceAll("معطلd", lang === "en" ? "Disabled" : "معطل")
    .replaceAll("مفعلd", lang === "en" ? "Enabled" : "مفعل");'''

if old_line in s and "تعطيلd" not in s:
    s = s.replace(old_line, new_line)

p.write_text(s)
print("✅ Disabled/Enabled translation fixed")
PY

docker compose up -d --build frontend

echo "✅ انتهى"
echo "افتح الموقع واعمل Refresh قوي"
