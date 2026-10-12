"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, ChevronRight, Languages, LockKeyhole, Menu, Shield, X } from "lucide-react";
import { adminPages, pageHref, userPages } from "../lib/console-pages";
import { useI18n } from "../ndsp/i18n";
import AuthControls from "./AuthControls";
import { BOT_NAME } from "../lib/bot-profile";

const groups: { label: string; slugs: string[] }[] = [
  { label: "COMMAND", slugs: ["command-center", "markets", "trading"] },
  { label: "BOOK", slugs: ["positions", "orders", "trade-history", "performance"] },
  { label: "INTELLIGENCE", slugs: ["strategies", "ndsp-decisions", "execution-trace", "replay-lab"] },
  { label: "CONTROL", slugs: ["risk-center", "binance-connection", "notifications"] },
  { label: "ACCOUNT", slugs: ["settings", "security", "subscription", "health", "activity", "audit"] },
];
const modes = ["Simulation", "Testnet", "Live"] as const;
const realSlugs = new Set(["security", "subscription"]);
const mixedSlugs = new Set(["command-center", "settings", "health"]);

export default function ConsoleShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "/";
  const { lang, setLang, t } = useI18n();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<(typeof modes)[number]>("Simulation");
  const active = (href: string) => pathname.replace(/\/$/, "") === href.replace(/\/$/, "");
  const close = () => setOpen(false);
  const bySlug = (s: string) => userPages.find(p => p.slug === s);
  return <div className="console-shell console-shell--operator" data-mode={mode.toLowerCase()}>
    <a className="skip-link" href="#console-content">{t("Skip to content")}</a>
    <aside className={`console-nav ${open ? "is-open" : ""}`} id="console-navigation" aria-label={t("Navigation")}>
      <Link href="/" className="brand" onClick={close}><span className="brand-mark">N</span><span><strong>NAWAF</strong><small>{BOT_NAME}</small></span></Link>
      <div className="nav-scope"><span className="scope-dot" /> {t("M1 FOUNDATION")} <span className="mono">01</span></div>
      {groups.map(g => <nav key={g.label} aria-label={t(g.label)}>
        <p className="nav-label">{t(g.label)}</p>
        {g.slugs.map(bySlug).filter((p): p is NonNullable<typeof p> => !!p).map(page => {
          const href = pageHref(page);
          return <Link key={page.slug} href={href} className={`nav-link ${active(href) ? "active" : ""}`} aria-current={active(href) ? "page" : undefined} onClick={close}>
            <span>{t(page.title)}</span>
            {page.slug === "audit" ? <LockKeyhole size={13} aria-hidden /> : realSlugs.has(page.slug) ? <span className="nav-hint real">M1</span> : mixedSlugs.has(page.slug) ? <span className="nav-hint">M1 / UI</span> : <span className="nav-hint demo">DEMO</span>}
          </Link>;
        })}
      </nav>)}
      <nav aria-label="Administrative pages">
        <details className="admin-navigation" open={pathname.startsWith("/admin")}>
          <summary><LockKeyhole size={14} aria-hidden /> {t("Admin")} · {t("MFA GUARDED")}</summary>
          <Link href="/admin/" className={`nav-link ${active("/admin/") ? "active" : ""}`} onClick={close}>{t("Access status")}</Link>
          {adminPages.map(page => <Link key={page.slug} href={pageHref(page, true)} className={`nav-link ${active(pageHref(page, true)) ? "active" : ""}`} aria-current={active(pageHref(page, true)) ? "page" : undefined} onClick={close}>{page.title}<ChevronRight size={12} aria-hidden /></Link>)}
        </details>
      </nav>
      <div className="nav-footer"><Shield size={17} aria-hidden /><p>{t("Independent from NDSP.")}<br />{t("No exchange or trading access.")}</p></div>
    </aside>
    {open && <button className="nav-scrim" aria-label={t("Close navigation")} onClick={close} />}
    <div className="console-workspace">
      <header className="console-top">
        <div className="row">
          <button className="button nav-toggle" type="button" aria-label={open ? t("Close navigation") : t("Open navigation")} aria-expanded={open} aria-controls="console-navigation" onClick={() => setOpen(!open)}>{open ? <X size={18} /> : <Menu size={18} />}</button>
          <span className="top-label"><Activity size={15} aria-hidden /> {t("NAWAF / FOUNDATION")}</span>
        </div>
        <div className="row top-actions">
          <button className="button small" type="button" onClick={() => setLang(lang === "en" ? "ar" : "en")} aria-label={t("Language")} data-testid="toggle-language"><Languages size={13} aria-hidden />{lang === "en" ? "العربية" : "English"}</button>
          <span className="acceptance-label"><span className="acceptance-dot" /> {t("M1 NOT ACCEPTED")}</span>
        </div>
      </header>
      <div className="system-strip" role="region" aria-label="Preview system state">
        <span className="demo-tag">{t("DEMO DATA")}</span>
        <div className="mode-switch" role="group" aria-label={`${t("Mode")} · ${t("Preview")}`}>
          {modes.map(m => <button key={m} type="button" aria-pressed={m === mode} className={`mode-${m.toLowerCase()} ${m === mode ? "on" : ""}`} onClick={() => setMode(m)}>{t(m)}</button>)}
        </div>
        <span className="strip-note">{mode === "Live" ? t("LIVE APPEARANCE PREVIEW — NOT ENABLED. ") : ""}{t("Mode selector changes appearance only. No trading mode is applied.")}</span>
        <div className="workspace-safety" aria-label={t("Execution safety boundaries")}><span>{t("Bot")}: {t("STOPPED")}</span><span>{t("Exchange")}: {t("NOT CONNECTED")}</span><span>{t("Risk")}: {t("BLOCKED")}</span><span>{t("Market data")}: {t("STATIC PREVIEW")}</span></div>
      </div>
      <main className="console-main" id="console-content" tabIndex={-1}>
        <AuthControls />
        {children}
        <footer className="console-footer">{t("NAWAF · MASTER SPEC V1 · M1 only · Later milestones require separate authorization.")}</footer>
      </main>
    </div>
  </div>;
}
