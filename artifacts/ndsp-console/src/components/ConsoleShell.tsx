"use client";

import { Tx } from "../ndsp/ui";
import { useEffect, useRef, useState, type ReactNode } from "react";
import Link from "./DocumentLink";
import { usePathname } from "next/navigation";
import { Activity, ChevronRight, LockKeyhole, Menu, Shield, X } from "lucide-react";
import { useAuth } from "./AuthProvider";
import { adminPages, pageHref, userPages } from "../lib/console-pages";
import { useI18n } from "../ndsp/i18n";
import { BOT_NAME } from "../lib/bot-profile";
import { TradingWorkspaceBar, TradingWorkspaceProvider } from "./TradingWorkspace";
import BotPowerControl from "./BotPowerControl";

const groups: { label: string; slugs: string[] }[] = [
  { label: "OVERVIEW", slugs: ["command-center", "health"] },
  { label: "TRADING", slugs: ["trading", "markets", "positions", "orders", "trade-history"] },
  { label: "STRATEGIES & SIGNALS", slugs: ["strategies", "ndsp-decisions", "execution-trace", "replay-lab"] },
  { label: "RISK & REPORTS", slugs: ["risk-center", "performance", "activity"] },
  { label: "SETTINGS & SUPPORT", slugs: ["binance-connection", "notifications", "settings", "security", "subscription", "user-guide"] },
  { label: "ACCOUNT", slugs: ["account-access", "registration", "audit"] },
];
const unavailableSlugs = new Set(["positions", "orders", "trade-history", "performance", "ndsp-decisions", "execution-trace", "replay-lab", "notifications", "activity"]);

export default function ConsoleShell({ children }: { children: ReactNode }) {
  return <TradingWorkspaceProvider><WorkspaceShell>{children}</WorkspaceShell></TradingWorkspaceProvider>;
}

function WorkspaceShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "/";
  const { lang, setLang, t } = useI18n();
  const { state, identity, busy, act, administratorMfaVerified } = useAuth();
  const adminVisible = state === "authenticated" && administratorMfaVerified && (identity?.role === "ADMIN" || identity?.role === "SUPER_ADMIN");
  const [menuOpen, setMenuOpen] = useState(false);
  const shellRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const header = headerRef.current, shell = shellRef.current;
    if (!header || !shell) return;
    // Header rows wrap on narrow screens and when the language changes.
    // Position the drawer below their actual height so links stay tappable.
    const update = () => {
      const border = parseFloat(getComputedStyle(shell).borderTopWidth) || 0;
      shell.style.setProperty("--console-header-height", Math.ceil(header.getBoundingClientRect().height + border) + "px");
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(header);
    return () => observer.disconnect();
  }, []);
  useEffect(() => { setMenuOpen(false); }, [pathname]);
  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setMenuOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);
  const active = (href: string) => pathname.replace(/\/$/, "") === href.replace(/\/$/, "");

  const bySlug = (s: string) => userPages.find(p => p.slug === s);
  return <div ref={shellRef} className="console-shell console-shell--operator">
    <a className="skip-link" href="#console-content">{t("Skip to content")}</a>
    <aside className="console-nav" id="console-navigation" aria-label={t("Navigation")}>
      <Link href="/dashboard/" className="brand"><span className="brand-mark">H</span><span><strong>{BOT_NAME}</strong><small>{t("Independent trading bot")}</small></span></Link>
      <div className="nav-scope"><span className="scope-dot" /> {t("Account workspace")}</div>
      {groups.map(g => <nav key={g.label} aria-label={t(g.label)}>
        <p className="nav-label">{t(g.label)}</p>
        {g.slugs.filter(slug => slug !== "audit").map(bySlug).filter((p): p is NonNullable<typeof p> => !!p).map(page => {
          const href = pageHref(page);
          return <Link key={page.slug} href={href} className={`nav-link ${active(href) ? "active" : ""}`} aria-current={active(href) ? "page" : undefined}>
            <span>{t(page.title)}</span>
            {page.slug === "audit" ? <LockKeyhole size={13} aria-hidden /> : unavailableSlugs.has(page.slug) ? <span className="nav-hint">{lang === "ar" ? "غير متاح" : "Unavailable"}</span> : <span className="nav-hint real">{lang === "ar" ? "خدمة" : "Service"}</span>}
          </Link>;
        })}
      </nav>)}
      {adminVisible && <nav aria-label="Administrative pages">
        <details className="admin-navigation" open={pathname.startsWith("/admin")}>
          <summary><LockKeyhole size={14} aria-hidden /> {t("Admin")} · {t("MFA GUARDED")}</summary>
          <Link href="/admin/" className={`nav-link ${active("/admin/") ? "active" : ""}`}>{t("Access status")}</Link>
          {adminPages.map(page => <Link key={page.slug} href={pageHref(page, true)} className={`nav-link ${active(pageHref(page, true)) ? "active" : ""}`} aria-current={active(pageHref(page, true)) ? "page" : undefined}>{page.title}<ChevronRight size={12} aria-hidden /></Link>)}
        </details>
      </nav>}
      <div className="nav-footer"><Shield size={17} aria-hidden /><p>{t("Independent from NDSP.")}<br />{t("Read-only exchange checks; order execution disabled.")}</p></div>
    </aside>
    <div className="console-workspace">
      <header ref={headerRef} className="console-top">
        <div className="row">
          <div className="hunter-native-mobile-menu">
            <button type="button" className="button hunter-menu-trigger" aria-label={lang === "ar" ? "فتح القائمة" : "Open navigation"} aria-expanded={menuOpen} aria-controls="hunter-mobile-drawer" onClick={() => setMenuOpen(true)}><Menu size={20} aria-hidden="true" /></button>
            {menuOpen && <button type="button" className="hunter-menu-backdrop" aria-label={lang === "ar" ? "إغلاق القائمة" : "Close navigation"} onClick={() => setMenuOpen(false)} />}
            <div id="hunter-mobile-drawer" className={`hunter-native-menu-body ${menuOpen ? "is-open" : ""}`} dir={lang === "ar" ? "rtl" : "ltr"} aria-label={t("Navigation")} aria-hidden={!menuOpen}>
              <div className="hunter-menu-heading"><strong>{lang === "ar" ? "القائمة الرئيسية" : "Main menu"}</strong><button type="button" className="button" aria-label={lang === "ar" ? "إغلاق القائمة" : "Close navigation"} onClick={() => setMenuOpen(false)}><X size={20} /></button></div>
              {groups.map(g => <nav key={g.label} aria-label={t(g.label)}>
                <p className="nav-label">{lang === "ar" ? ({"OVERVIEW":"نظرة عامة","TRADING":"التداول","STRATEGIES & SIGNALS":"الاستراتيجيات والإشارات","RISK & REPORTS":"المخاطر والتقارير","SETTINGS & SUPPORT":"الإعدادات والدعم","ACCOUNT":"الحساب"} as Record<string,string>)[g.label] : g.label}</p>
                {g.slugs.filter(slug => slug !== "audit").map(bySlug).filter((page): page is NonNullable<typeof page> => !!page).map(page => <Link key={page.slug} href={pageHref(page)} className="nav-link" aria-current={active(pageHref(page)) ? "page" : undefined}>{t(page.title)}</Link>)}
              </nav>)}
              {adminVisible && <Link className="nav-link" href="/admin/">{t("Admin")}</Link>}
            </div>
          </div>
          <span className="top-label"><Activity size={15} aria-hidden /> {BOT_NAME} · {t("Account workspace")}</span>
        </div>
        <div className="row top-actions">
          <div className="seg hunter-native-language" role="group" aria-label={t("Language")}><a href="?lang=ar" data-hunter-lang="ar" className={lang === "ar" ? "on" : ""} aria-current={lang === "ar" ? "true" : undefined} onClick={event => { event.preventDefault(); setLang("ar"); }}>AR · العربية</a><a href="?lang=en" data-hunter-lang="en" className={lang === "en" ? "on" : ""} aria-current={lang === "en" ? "true" : undefined} onClick={event => { event.preventDefault(); setLang("en"); }}>EN · English</a></div>
          <BotPowerControl />
          <span className="acceptance-label"><span className="acceptance-dot" /> {t("Live trading disabled")}</span>
          <div id="hunter-legacy-account" className="hunter-auth-nohydrate hunter-account-status" aria-live="polite"><a className="button small" href="/api/v1/auth/start">{t("Sign in")}</a></div>
          {state === "authenticated" && identity ? <div className="hunter-account-status" role="status" aria-label={t("Account status")}>
            <span className="hunter-account-email" dir="ltr" title={identity.email}>{identity.email}</span>
            <button type="button" className="button small" disabled={busy} onClick={() => void act("logout")}>{t("Sign out")}</button>
          </div> : state === "anonymous" ? <a className="button small" href="/api/v1/auth/start">{t("Sign in")}</a>
            : state !== "loading" ? <Link className="button small" href="/account-access/">{t("Check session")}</Link> : null}
        </div>
      </header>
      <main className="console-main" id="console-content" tabIndex={-1}>
        <TradingWorkspaceBar />
        {children}
        <footer className="console-footer">{BOT_NAME} · {t("Live trading disabled")}</footer>
      </main>
    </div>
  </div>;
}
