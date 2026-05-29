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
