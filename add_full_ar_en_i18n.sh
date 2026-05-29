#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_i18n_ar_en_$STAMP"
mkdir -p "$BACKUP_DIR"

cp frontend/app/layout.tsx "$BACKUP_DIR/layout.tsx"
cp frontend/app/globals.css "$BACKUP_DIR/globals.css"

echo "✅ Backup created: $BACKUP_DIR"

mkdir -p frontend/app/components

cat > frontend/app/components/LanguageSwitcher.tsx <<'TSX'
"use client";

import { useEffect, useState } from "react";

type Lang = "ar" | "en";

const AR_TO_EN: Record<string, string> = {
  "الرئيسية": "Home",
  "لوحة التحكم": "Dashboard",
  "العودة للرئيسية": "Back to Home",
  "العودة للوحة التحكم": "Back to Dashboard",

  "تسجيل الدخول": "Login",
  "تسجيل خروج": "Logout",
  "دخول": "Login",
  "حساب جديد": "New Account",
  "إنشاء حساب": "Create Account",
  "الإيميل": "Email",
  "إيميل الحساب الجديد": "New Account Email",
  "كلمة المرور": "Password",
  "كود الدعوة": "Invite Code",
  "مرحبا": "Welcome",

  "تم تسجيل الدخول بنجاح": "Logged in successfully",
  "تم تسجيل الخروج": "Logged out",
  "فشل تسجيل الدخول": "Login failed",
  "فشل إنشاء الحساب": "Registration failed",
  "تم إنشاء الحساب وتسجيل الدخول بنجاح": "Account created and logged in successfully",

  "حالة البوت": "Bot Status",
  "إعدادات": "Settings",
  "الإعدادات": "Settings",
  "Binance API": "Binance API",
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
  "تم حفظ الإعدادات": "Settings saved",
  "فشل حفظ الإعدادات": "Failed to save settings",
  "تم حفظ مفاتيح Binance بشكل مشفر": "Binance keys saved encrypted",
  "فشل حفظ المفاتيح": "Failed to save keys",
  "تم إيقاف البوت فورًا": "Bot stopped immediately",
  "فشل الإيقاف": "Emergency stop failed",
  "تم تنفيذ الإشارة": "Signal executed",
  "فشل تنفيذ الإشارة": "Signal execution failed",

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
  "مستخدم نشط": "Active User",
  "المستخدم نشط": "User Active",

  "Live Safety Center": "Live Safety Center",
  "هذه الصفحة تمنع تفعيل التداول الحقيقي قبل اكتمال شروط الأمان. لا تستخدم Live إلا بعد نجاح Testnet وإضافة مفاتيح Binance بدون صلاحية Withdraw.": "This page prevents enabling live trading before safety requirements are complete. Do not use Live until Testnet succeeds and Binance keys are added without Withdraw permission.",
  "الحالة العامة": "Overall Status",
  "غير جاهز للـ Live": "Not Ready for Live",
  "جاهز للـ Live": "Ready for Live",
  "Checklist": "Checklist",
  "المستخدم نشط": "User is active",
  "إعدادات البوت موجودة": "Bot settings exist",
  "مفاتيح Binance موجودة": "Binance keys exist",
  "تم اختبار Testnet": "Testnet has been tested",
  "لا توجد صلاحية Withdraw": "No Withdraw permission",
  "تفعيل التداول الحقيقي": "Enable Live Trading",

  "NDSP Incoming Signals": "NDSP Incoming Signals",
  "هنا تظهر إشارات NDSP التي وصلت فعليًا إلى بوت التداول عبر Webhook.": "This page shows NDSP signals that actually reached the trading bot through the webhook.",
  "فشل تحميل إشارات NDSP": "Failed to load NDSP signals",
  "تحديث": "Refresh",
  "لا توجد إشارات NDSP واردة حتى الآن.": "No incoming NDSP signals yet.",
  "العودة للوحة التحكم": "Back to Dashboard",

  "Logs Center": "Logs Center",
  "Live Logs": "Live Logs",
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
  "خطأ": "Error"
};

const EN_TO_AR = Object.fromEntries(
  Object.entries(AR_TO_EN).map(([ar, en]) => [en, ar])
);

function translateText(value: string, lang: Lang): string {
  const clean = value.trim();
  if (!clean) return value;

  const dict = lang === "en" ? AR_TO_EN : EN_TO_AR;

  if (dict[clean]) {
    return value.replace(clean, dict[clean]);
  }

  let output = value;

  Object.entries(dict)
    .sort((a, b) => b[0].length - a[0].length)
    .forEach(([from, to]) => {
      if (from && output.includes(from)) {
        output = output.split(from).join(to);
      }
    });

  return output;
}

function walkAndTranslate(root: ParentNode, lang: Lang) {
  const skipTags = new Set(["SCRIPT", "STYLE", "CODE", "PRE", "TEXTAREA"]);

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent) return NodeFilter.FILTER_REJECT;
      if (skipTags.has(parent.tagName)) return NodeFilter.FILTER_REJECT;
      if (parent.closest("[data-no-translate]")) return NodeFilter.FILTER_REJECT;
      if (!node.textContent || !node.textContent.trim()) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }
  });

  const textNodes: Text[] = [];
  while (walker.nextNode()) {
    textNodes.push(walker.currentNode as Text);
  }

  for (const node of textNodes) {
    const parent = node.parentElement;
    if (!parent) continue;

    const key = "originalText";
    const anyParent = parent as HTMLElement & { dataset: DOMStringMap };

    if (!anyParent.dataset[key]) {
      anyParent.dataset[key] = node.textContent || "";
    }

    const original = anyParent.dataset[key] || node.textContent || "";
    node.textContent = translateText(original, lang);
  }

  const elements = Array.from(
    document.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLButtonElement>(
      "input, textarea, button"
    )
  );

  for (const el of elements) {
    if (el.closest("[data-no-translate]")) continue;

    if ("placeholder" in el && el.placeholder) {
      if (!el.dataset.originalPlaceholder) {
        el.dataset.originalPlaceholder = el.placeholder;
      }
      el.placeholder = translateText(el.dataset.originalPlaceholder || el.placeholder, lang);
    }

    if (el.title) {
      if (!el.dataset.originalTitle) {
        el.dataset.originalTitle = el.title;
      }
      el.title = translateText(el.dataset.originalTitle || el.title, lang);
    }
  }
}

export default function LanguageSwitcher() {
  const [lang, setLang] = useState<Lang>("ar");

  useEffect(() => {
    const saved = (localStorage.getItem("ndsp_lang") as Lang | null) || "ar";
    setLang(saved);
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;

    localStorage.setItem("ndsp_lang", lang);

    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.body.classList.toggle("lang-en", lang === "en");
    document.body.classList.toggle("lang-ar", lang === "ar");

    const run = () => walkAndTranslate(document.body, lang);
    run();

    const observer = new MutationObserver(() => {
      window.requestAnimationFrame(run);
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true
    });

    return () => observer.disconnect();
  }, [lang]);

  return (
    <button
      className="global-language-switcher"
      data-no-translate
      onClick={() => setLang(lang === "ar" ? "en" : "ar")}
      aria-label="Language switcher"
    >
      <span>{lang === "ar" ? "EN" : "AR"}</span>
      <b>{lang === "ar" ? "English" : "العربية"}</b>
    </button>
  );
}
TSX

python3 - <<'PY'
from pathlib import Path

p = Path("frontend/app/layout.tsx")
s = p.read_text()

if 'LanguageSwitcher' not in s:
    s = s.replace(
        'import "./globals.css";',
        'import "./globals.css";\nimport LanguageSwitcher from "./components/LanguageSwitcher";'
    )

if "<LanguageSwitcher />" not in s:
    s = s.replace(
        "{children}",
        '''<LanguageSwitcher />
        {children}'''
    )

p.write_text(s)
print("✅ LanguageSwitcher added to layout")
PY

cat >> frontend/app/globals.css <<'EOF'

/* Global Arabic / English switcher */
.global-language-switcher {
  position: fixed;
  top: 18px;
  right: 18px;
  z-index: 10000;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(59, 130, 246, 0.35);
  border-radius: 999px;
  padding: 10px 14px;
  color: #e0f2fe;
  background:
    linear-gradient(135deg, rgba(59, 130, 246, 0.28), rgba(15, 23, 42, 0.92)),
    rgba(2, 6, 23, 0.9);
  box-shadow:
    0 12px 30px rgba(0, 0, 0, 0.32),
    0 0 22px rgba(59, 130, 246, 0.16);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  cursor: pointer;
  font-weight: 900;
}

.global-language-switcher span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 26px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.2);
  color: #bfdbfe;
  font-size: 13px;
}

.global-language-switcher b {
  font-size: 14px;
}

.global-language-switcher:hover {
  transform: translateY(-1px);
  border-color: rgba(147, 197, 253, 0.68);
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

body.lang-en .global-home-button {
  left: 18px;
  right: auto;
}

body.lang-en .global-language-switcher {
  right: 18px;
  left: auto;
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
  .global-language-switcher {
    top: auto;
    right: 14px;
    bottom: 138px;
    padding: 10px 12px;
  }

  .global-language-switcher b {
    font-size: 13px;
  }

  body.lang-en .global-language-switcher {
    right: 14px;
    left: auto;
  }
}
