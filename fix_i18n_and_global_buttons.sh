#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_i18n_buttons_fix_$STAMP"
mkdir -p "$BACKUP_DIR"

cp frontend/app/layout.tsx "$BACKUP_DIR/layout.tsx"
cp frontend/app/globals.css "$BACKUP_DIR/globals.css"
[ -f frontend/app/components/LanguageSwitcher.tsx ] && cp frontend/app/components/LanguageSwitcher.tsx "$BACKUP_DIR/LanguageSwitcher.tsx" || true

mkdir -p frontend/app/components

echo "✅ Backup created: $BACKUP_DIR"

cat > frontend/app/components/GlobalControls.tsx <<'TSX'
"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

type Lang = "ar" | "en";

const AR_TO_EN: Record<string, string> = {
  "الرئيسية": "Home",
  "العودة للرئيسية": "Back Home",
  "العودة للوحة التحكم": "Back to Dashboard",
  "روابط متقدمة": "Advanced Links",

  "تسجيل الدخول": "Login",
  "تسجيل خروج": "Logout",
  "دخول": "Login",
  "حساب جديد": "New Account",
  "إنشاء حساب": "Create Account",
  "الإيميل": "Email",
  "إيميل الحساب الجديد": "New Account Email",
  "كلمة المرور": "Password",
  "كود الدعوة": "Invite Code",
  "مرحباً": "Welcome",
  "مرحبا": "Welcome",

  "لوحة التحكم": "Dashboard",
  "حالة البوت": "Bot Status",
  "إعدادات": "Settings",
  "الإعدادات": "Settings",
  "البوت": "Bot",
  "Settings البوت": "Bot Settings",
  "إعدادات البوت": "Bot Settings",
  "تشغيل البوت": "Enable Bot",
  "الأزواج المسموحة": "Allowed Symbols",
  "أقصى قيمة الصفقة": "Max Order Value",
  "أقصى خسارة يومية": "Max Daily Loss",
  "أقصى عدد صفقات يومياً": "Max Trades Per Day",
  "إدارة المخاطر": "Risk Management",
  "حفظ الإعدادات": "Save Settings",

  "Binance API": "Binance API",
  "مفاتيح Binance": "Binance Keys",
  "مفتاح API": "API Key",
  "Secret Key": "Secret Key",
  "اختبار صفقة": "Test Trade",
  "إيقاف طارئ": "Emergency Stop",
  "التنبيهات": "Alerts",
  "الصفقات": "Trades",
  "عدد الصفقات": "Trades Count",
  "آخر صفقة": "Last Trade",
  "لا توجد صفقات بعد.": "No trades yet.",
  "زوج التداول": "Trading Pair",
  "القيمة": "Value",
  "الكمية": "Amount",
  "السعر": "Price",
  "الوقت": "Time",
  "الوضع": "Mode",
  "سبب الصفقة": "Trade Reason",

  "تم تسجيل الدخول بنجاح": "Logged in successfully",
  "تم تسجيل الخروج": "Logged out",
  "فشل تسجيل الدخول": "Login failed",
  "فشل إنشاء الحساب": "Registration failed",
  "تم إنشاء الحساب وتسجيل الدخول بنجاح": "Account created and logged in successfully",
  "تم حفظ الإعدادات": "Settings saved",
  "فشل حفظ الإعدادات": "Failed to save settings",
  "تم حفظ مفاتيح Binance بشكل مشفر": "Binance keys saved encrypted",
  "فشل حفظ المفاتيح": "Failed to save keys",
  "تم إيقاف البوت فورًا": "Bot stopped immediately",
  "فشل الإيقاف": "Emergency stop failed",
  "تم تنفيذ الإشارة": "Signal executed",
  "فشل تنفيذ الإشارة": "Signal execution failed",

  "Live Safety Center": "Live Safety Center",
  "هذه الصفحة تمنع تفعيل التداول الحقيقي قبل اكتمال شروط الأمان. لا تستخدم Live إلا بعد نجاح Testnet وإضافة مفاتيح Binance بدون صلاحية Withdraw.": "This page prevents enabling live trading before safety requirements are complete. Do not use Live until Testnet succeeds and Binance keys are added without Withdraw permission.",
  "الحالة العامة": "Overall Status",
  "غير جاهز للـ Live": "Not Ready for Live",
  "جاهز للـ Live": "Ready for Live",
  "Checklist": "Checklist",
  "المستخدم نشط": "User is Active",
  "إعدادات البوت موجودة": "Bot Settings Exist",
  "مفاتيح Binance موجودة": "Binance Keys Exist",
  "تم اختبار Testnet": "Testnet Tested",
  "لا توجد صلاحية Withdraw": "No Withdraw Permission",
  "تفعيل التداول الحقيقي": "Enable Live Trading",

  "NDSP Incoming Signals": "NDSP Incoming Signals",
  "هنا تظهر إشارات NDSP التي وصلت فعليًا إلى بوت التداول عبر Webhook.": "This page shows NDSP signals that actually reached the trading bot through the webhook.",
  "فشل تحميل إشارات NDSP": "Failed to load NDSP signals",
  "تحديث": "Refresh",
  "لا توجد إشارات NDSP واردة حتى الآن.": "No incoming NDSP signals yet.",

  "Admin - إدارة الأصدقاء": "Admin - Friends Management",
  "إدارة الأصدقاء": "Friends Management",
  "يمكنك هنا تفعيل أو تعطيل المستخدمين، منح صلاحية Admin، أو حذف حساب مستخدم.": "Here you can enable or disable users, grant Admin access, or delete a user account.",
  "تحديث القائمة": "Refresh List",
  "تعطيل": "Disable",
  "تفعيل": "Enable",
  "تعيين Admin": "Make Admin",
  "حذف": "Delete",
  "فشل تحميل المستخدمين": "Failed to load users",
  "فشل الحذف": "Delete failed",

  "Logs Center": "Logs Center",
  "Payload / Response": "Payload / Response",
  "Reason": "Reason",
  "Rejection / Error": "Rejection / Error",

  "الحالة": "Status",
  "المستخدم": "User",
  "المستخدمين": "Users",
  "موجودة": "Configured",
  "غير موجودة": "Not Configured",
  "نشط": "Active",
  "غير نشط": "Inactive",
  "جاهز": "Ready",
  "غير جاهز": "Not Ready",
  "حفظ": "Save",
  "إلغاء": "Cancel",
  "رجوع": "Back",
  "التالي": "Next",
  "السابق": "Previous",
  "إرسال": "Submit",
  "تنفيذ": "Execute",
  "اختبار": "Test",
  "نجاح": "Success",
  "فشل": "Failed",
  "خطأ": "Error",
  "العربية": "Arabic",
  "English": "English"
};

const MIXED_TO_EN: Record<string, string> = {
  "Settings البوت": "Bot Settings",
  "Welcome، Welcome": "Welcome",
  "مرحباً، مرحباً": "Welcome",
  "مرحباً، Welcome": "Welcome",
  "Welcome، مرحباً": "Welcome",
  "USDT أقصى قيمة الصفقة": "Max Order Value USDT",
  "USDT أقصى خسارة يومية": "Max Daily Loss USDT"
};

const EN_TO_AR: Record<string, string> = {
  "Home": "الرئيسية",
  "Back Home": "العودة للرئيسية",
  "Back to Dashboard": "العودة للوحة التحكم",
  "Advanced Links": "روابط متقدمة",

  "Login": "تسجيل الدخول",
  "Logout": "تسجيل خروج",
  "New Account": "حساب جديد",
  "Create Account": "إنشاء حساب",
  "Email": "الإيميل",
  "New Account Email": "إيميل الحساب الجديد",
  "Password": "كلمة المرور",
  "Invite Code": "كود الدعوة",
  "Welcome": "مرحباً",

  "Dashboard": "لوحة التحكم",
  "Bot Status": "حالة البوت",
  "Settings": "الإعدادات",
  "Bot Settings": "إعدادات البوت",
  "Enable Bot": "تشغيل البوت",
  "Allowed Symbols": "الأزواج المسموحة",
  "Max Order Value": "أقصى قيمة الصفقة",
  "Max Order Value USDT": "أقصى قيمة الصفقة USDT",
  "Max Daily Loss": "أقصى خسارة يومية",
  "Max Daily Loss USDT": "أقصى خسارة يومية USDT",
  "Max Trades Per Day": "أقصى عدد صفقات يومياً",
  "Risk Management": "إدارة المخاطر",
  "Save Settings": "حفظ الإعدادات",

  "Test Trade": "اختبار صفقة",
  "Emergency Stop": "إيقاف طارئ",
  "Alerts": "التنبيهات",
  "Trades": "الصفقات",
  "Trades Count": "عدد الصفقات",
  "Last Trade": "آخر صفقة",
  "No trades yet.": "لا توجد صفقات بعد.",
  "Trading Pair": "زوج التداول",
  "Value": "القيمة",
  "Amount": "الكمية",
  "Price": "السعر",
  "Time": "الوقت",
  "Mode": "الوضع",
  "Trade Reason": "سبب الصفقة",

  "Overall Status": "الحالة العامة",
  "Not Ready for Live": "غير جاهز للـ Live",
  "Ready for Live": "جاهز للـ Live",
  "User is Active": "المستخدم نشط",
  "Bot Settings Exist": "إعدادات البوت موجودة",
  "Binance Keys Exist": "مفاتيح Binance موجودة",
  "Testnet Tested": "تم اختبار Testnet",
  "No Withdraw Permission": "لا توجد صلاحية Withdraw",
  "Enable Live Trading": "تفعيل التداول الحقيقي",

  "Refresh": "تحديث",
  "Refresh List": "تحديث القائمة",
  "Disable": "تعطيل",
  "Enable": "تفعيل",
  "Make Admin": "تعيين Admin",
  "Delete": "حذف",
  "Status": "الحالة",
  "User": "المستخدم",
  "Users": "المستخدمين",
  "Configured": "موجودة",
  "Not Configured": "غير موجودة",
  "Active": "نشط",
  "Inactive": "غير نشط",
  "Ready": "جاهز",
  "Not Ready": "غير جاهز",
  "Save": "حفظ",
  "Cancel": "إلغاء",
  "Back": "رجوع",
  "Next": "التالي",
  "Previous": "السابق",
  "Submit": "إرسال",
  "Execute": "تنفيذ",
  "Test": "اختبار",
  "Success": "نجاح",
  "Failed": "فشل",
  "Error": "خطأ",
  "Arabic": "العربية"
};

function translate(value: string, lang: Lang): string {
  let output = value;

  if (lang === "en") {
    for (const [from, to] of Object.entries(MIXED_TO_EN)) {
      output = output.split(from).join(to);
    }

    for (const [from, to] of Object.entries(AR_TO_EN).sort((a, b) => b[0].length - a[0].length)) {
      output = output.split(from).join(to);
    }

    return output;
  }

  for (const [from, to] of Object.entries(EN_TO_AR).sort((a, b) => b[0].length - a[0].length)) {
    output = output.split(from).join(to);
  }

  return output;
}

function applyLanguage(lang: Lang) {
  const skipTags = new Set(["SCRIPT", "STYLE", "CODE", "PRE", "TEXTAREA"]);

  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  document.body.classList.toggle("lang-ar", lang === "ar");
  document.body.classList.toggle("lang-en", lang === "en");

  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent) return NodeFilter.FILTER_REJECT;
      if (skipTags.has(parent.tagName)) return NodeFilter.FILTER_REJECT;
      if (parent.closest("[data-no-translate]")) return NodeFilter.FILTER_REJECT;
      if (!node.textContent || !node.textContent.trim()) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }
  });

  const nodes: Text[] = [];
  while (walker.nextNode()) nodes.push(walker.currentNode as Text);

  for (const node of nodes) {
    const parent = node.parentElement as HTMLElement | null;
    if (!parent) continue;

    if (!parent.dataset.sourceText) {
      parent.dataset.sourceText = node.textContent || "";
    }

    const source = parent.dataset.sourceText || node.textContent || "";
    node.textContent = translate(source, lang);
  }

  document.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>("input, textarea").forEach((el) => {
    if (el.closest("[data-no-translate]")) return;

    if (el.placeholder) {
      if (!el.dataset.sourcePlaceholder) el.dataset.sourcePlaceholder = el.placeholder;
      el.placeholder = translate(el.dataset.sourcePlaceholder || el.placeholder, lang);
    }
  });
}

export default function GlobalControls() {
  const pathname = usePathname();
  const [lang, setLang] = useState<Lang>("ar");

  const isHome = pathname === "/";

  useEffect(() => {
    const saved = (localStorage.getItem("ndsp_lang") as Lang | null) || "ar";
    setLang(saved);
  }, []);

  useEffect(() => {
    localStorage.setItem("ndsp_lang", lang);

    const run = () => applyLanguage(lang);
    run();

    const observer = new MutationObserver(() => {
      requestAnimationFrame(run);
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true
    });

    return () => observer.disconnect();
  }, [lang, pathname]);

  return (
    <div className="global-controls" data-no-translate>
      {!isHome && (
        <a className="global-home-button" href="/" aria-label="Home">
          <span>⌂</span>
          <b>{lang === "ar" ? "الرئيسية" : "Home"}</b>
        </a>
      )}

      <button
        className="global-language-switcher"
        onClick={() => setLang(lang === "ar" ? "en" : "ar")}
        aria-label="Language"
      >
        <span>{lang === "ar" ? "EN" : "AR"}</span>
        <b>{lang === "ar" ? "English" : "العربية"}</b>
      </button>
    </div>
  );
}
TSX

python3 - <<'PY'
from pathlib import Path
import re

p = Path("frontend/app/layout.tsx")
s = p.read_text()

# Remove old LanguageSwitcher import
s = re.sub(r'import\s+LanguageSwitcher\s+from\s+["\']\.\/components\/LanguageSwitcher["\'];\n?', '', s)

# Remove old GlobalControls import if duplicated
s = re.sub(r'import\s+GlobalControls\s+from\s+["\']\.\/components\/GlobalControls["\'];\n?', '', s)

# Add clean import
s = s.replace('import "./globals.css";', 'import "./globals.css";\nimport GlobalControls from "./components/GlobalControls";')

# Remove old inserted controls
s = s.replace("<LanguageSwitcher />", "")

# Remove old home anchor block
s = re.sub(
    r'<a\s+className="global-home-button"[\s\S]*?</a>\s*',
    '',
    s
)

# Add GlobalControls once before children
if "<GlobalControls />" not in s:
    s = s.replace("{children}", "<GlobalControls />\n        {children}")

p.write_text(s)
print("✅ layout cleaned and GlobalControls installed")
PY

cat >> frontend/app/globals.css <<'EOF'

/* I18N + Global Controls Fix */
.global-controls {
  pointer-events: none;
}

.global-home-button,
.global-language-switcher {
  pointer-events: auto;
  position: fixed;
  top: 14px;
  z-index: 10000;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  border-radius: 999px;
  padding: 9px 14px;
  text-decoration: none;
  font-weight: 900;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.global-home-button {
  left: 14px;
  color: #eafff1;
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.30), rgba(15, 23, 42, 0.92));
  border: 1px solid rgba(34, 197, 94, 0.40);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.34), 0 0 22px rgba(34, 197, 94, 0.14);
}

.global-language-switcher {
  right: 14px;
  color: #e0f2fe;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.30), rgba(15, 23, 42, 0.92));
  border: 1px solid rgba(59, 130, 246, 0.40);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.34), 0 0 22px rgba(59, 130, 246, 0.14);
  cursor: pointer;
}

.global-home-button span,
.global-language-switcher span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 26px;
  border-radius: 999px;
  font-size: 13px;
}

.global-home-button span {
  background: rgba(34, 197, 94, 0.18);
  color: #86efac;
}

.global-language-switcher span {
  background: rgba(59, 130, 246, 0.20);
  color: #bfdbfe;
}

.global-home-button b,
.global-language-switcher b {
  font-size: 14px;
}

body.lang-en {
  direction: ltr;
  text-align: left;
}

body.lang-en input,
body.lang-en textarea {
  direction: ltr;
  text-align: left;
}

body.lang-en .card,
body.lang-en .auth-card,
body.lang-en .ndsp-signal-item {
  text-align: left;
}

body.lang-ar {
  direction: rtl;
  text-align: right;
}

body.lang-ar input,
body.lang-ar textarea {
  direction: rtl;
  text-align: right;
}

@media (max-width: 700px) {
  .global-home-button,
  .global-language-switcher {
    top: 10px;
    padding: 8px 11px;
    min-height: 38px;
  }

  .global-home-button {
    left: 10px;
  }

  .global-language-switcher {
    right: 10px;
  }

  .global-home-button b,
  .global-language-switcher b {
    font-size: 12px;
  }
}
