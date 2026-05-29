#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

PAGE="frontend/app/page.tsx"
CSS="frontend/app/globals.css"

if [ ! -f "$PAGE" ]; then
  echo "❌ لم أجد الملف: $PAGE"
  exit 1
fi

if [ ! -f "$CSS" ]; then
  echo "❌ لم أجد الملف: $CSS"
  exit 1
fi

cp "$PAGE" "$PAGE.backup_one_signature_$(date +%Y%m%d_%H%M%S)"
cp "$CSS" "$CSS.backup_one_signature_$(date +%Y%m%d_%H%M%S)"

python3 - <<'PY'
from pathlib import Path
import re

p = Path("frontend/app/page.tsx")
s = p.read_text()

# حذف البادج الداخلي: Signature: hunter_ksa1
s = re.sub(
    r'\s*<div className="signature-pill">\s*Signature:\s*hunter_ksa1\s*</div>',
    '',
    s,
    flags=re.S
)

# حذف أي نسخة داخلية أخرى محتملة بنفس النص
s = re.sub(
    r'\s*<div[^>]*>\s*Signature:\s*hunter_ksa1\s*</div>',
    '',
    s,
    flags=re.S
)

p.write_text(s)
print("✅ Removed duplicated inner signature")
PY

# إضافة CSS لإخفاء التوقيع الداخلي إذا بقي بأي شكل
cat >> "$CSS" <<'EOF'

/* Keep only one visible hunter_ksa1 signature */
.signature-pill {
  display: none !important;
}

.auth-brand .signature-pill {
  display: none !important;
}

.center-signature-badge {
  margin-top: 18px;
  margin-bottom: 28px;
}

