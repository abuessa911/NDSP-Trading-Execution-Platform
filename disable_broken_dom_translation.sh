#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_disable_broken_i18n_$STAMP"
mkdir -p "$BACKUP_DIR"

cp frontend/app/components/GlobalControls.tsx "$BACKUP_DIR/GlobalControls.tsx"

cat > frontend/app/components/GlobalControls.tsx <<'TSX'
"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

type Lang = "ar" | "en";

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
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.body.classList.toggle("lang-ar", lang === "ar");
    document.body.classList.toggle("lang-en", lang === "en");
  }, [lang]);

  return (
    <div className="global-controls-fixed" data-no-translate>
      {!isHome && (
        <a className="home-pill-fixed" href="/">
          <span>⌂</span>
          <b>{lang === "ar" ? "الرئيسية" : "Home"}</b>
        </a>
      )}

      <button className="lang-pill-fixed" onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
        <span>{lang === "ar" ? "EN" : "AR"}</span>
        <b>{lang === "ar" ? "English" : "العربية"}</b>
      </button>
    </div>
  );
}
TSX

docker compose up -d --build frontend

echo "✅ Broken DOM translation disabled"
echo "✅ Language button remains safe"
