"use client";

import { useEffect, useState } from "react";

export type Lang = "ar" | "en";

export function useLang() {
  const [lang, setLangState] = useState<Lang>("ar");

  useEffect(() => {
    const saved = localStorage.getItem("ndsp_lang") as Lang | null;
    if (saved === "ar" || saved === "en") setLangState(saved);
  }, []);

  function setLang(next: Lang) {
    localStorage.setItem("ndsp_lang", next);
    setLangState(next);
    document.documentElement.lang = next;
    document.documentElement.dir = next === "ar" ? "rtl" : "ltr";
  }

  return { lang, setLang, dir: lang === "ar" ? "rtl" : "ltr" };
}

export function t(lang: Lang, ar: string, en: string) {
  return lang === "ar" ? ar : en;
}

export async function apiJson(path: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : "";
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {})
  };

  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path, {
    ...options,
    headers
  });

  const text = await res.text();
  let data: any = null;

  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!res.ok) {
    const detail = typeof data === "object" ? data?.detail || JSON.stringify(data) : data;
    throw new Error(detail || `HTTP ${res.status}`);
  }

  return data;
}

export function HunterNav({ lang, setLang }: { lang: Lang; setLang: (x: Lang) => void }) {
  const links = [
    ["/", t(lang, "الرئيسية", "Dashboard")],
    ["/account", t(lang, "حسابي", "Account")],
    ["/admin", t(lang, "الإدارة", "Admin")],
    ["/ndsp", "NDSP"],
    ["/webhook-config", "Webhook"],
    ["/safety", "Live Safety"],
    ["/logs", t(lang, "السجلات", "Logs")],
    ["/register", t(lang, "تسجيل", "Register")]
  ];

  function logout() {
    localStorage.removeItem("token");
    window.location.href = "/";
  }

  return (
    <div className="hunter-nav">
      <div className="hunter-brand">
        <strong>NDSP</strong>
        <span>hunter_ksa1</span>
      </div>

      <div className="hunter-links">
        {links.map(([href, label]) => (
          <a key={href} href={href}>{label}</a>
        ))}
      </div>

      <div className="hunter-actions">
        <button className="btn btn-secondary" onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
          {lang === "ar" ? "English" : "العربية"}
        </button>
        <button className="btn btn-danger" onClick={logout}>
          {t(lang, "خروج", "Logout")}
        </button>
      </div>
    </div>
  );
}

export function Badge({ ok, children }: { ok?: boolean; children: any }) {
  return <span className={`hunter-badge ${ok ? "ok" : "danger"}`}>{children}</span>;
}

export function Card({ title, children }: { title?: string; children: any }) {
  return (
    <div className="hunter-card">
      {title && <h2>{title}</h2>}
      {children}
    </div>
  );
}
