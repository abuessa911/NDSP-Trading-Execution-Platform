"use client";
import { useCallback, useEffect, useId, useMemo, useRef, useState, type ReactNode } from "react";
import { AlertTriangle, ArrowDown, ArrowUp, CircleCheck, CircleX, Inbox, RotateCw, Search, X } from "lucide-react";
import { useI18n } from "./i18n";

/** Render-only localization: source records, filter values and identifiers stay unchanged. */
export function Tx({ children }: { children: string }) {
  const { t } = useI18n();
  return <>{t(children)}</>;
}

export function useDemo<T>(fetcher: () => Promise<T>) {
  const [state, set] = useState<{ data: T | null; loading: boolean; error: boolean }>({ data: null, loading: true, error: false });
  const ref = useRef(fetcher); ref.current = fetcher;
  const generation = useRef(0);
  const mounted = useRef(false);
  const load = useCallback(() => {
    const current = ++generation.current;
    set({ data: null, loading: true, error: false });
    ref.current().then(
      data => { if (mounted.current && current === generation.current) set({ data, loading: false, error: false }); },
      () => { if (mounted.current && current === generation.current) set({ data: null, loading: false, error: true }); },
    );
  }, []);
  useEffect(() => {
    mounted.current = true;
    load();
    return () => { mounted.current = false; generation.current++; };
  }, [load]);
  return { ...state, reload: load };
}

export function DemoBanner({ what }: { what?: string }) {
  const { t } = useI18n();
  return <div className="demo-banner" role="note" data-testid="demo-banner">
    <span className="demo-tag">{t("DEMO DATA")}</span><span className="demo-tag">{t("NOT CONNECTED")}</span><span className="demo-tag">{t("READ-ONLY UI PREVIEW")}</span>
    <span className="demo-text">{t(what ?? "Illustrative records from a local frontend dataset. Nothing here is live, persisted or sent to an exchange.")}</span>
  </div>;
}

export function Loading({ rows = 4 }: { rows?: number }) {
  const { t } = useI18n();
  return <div className="skeleton-stack" role="status" aria-label={t("Loading")}>{Array.from({ length: rows }, (_, i) => <div key={i} className="skeleton" style={{ height: i === 0 ? 74 : 44, opacity: 1 - i * 0.12 }} />)}</div>;
}
export function EmptyState({ title, text }: { title: string; text: string }) {
  const { t } = useI18n();
  return <div className="empty-state"><Inbox size={26} aria-hidden /><strong>{t(title)}</strong><p>{t(text)}</p></div>;
}
export function ErrorState({ onRetry }: { onRetry: () => void }) {
  const { t } = useI18n();
  return <div className="error-state" role="alert"><AlertTriangle size={22} aria-hidden /><div><strong>{t("Request failed")}</strong><p>{t("The demo adapter could not return data. Nothing was substituted.")}</p></div><button className="button" onClick={onRetry}><RotateCw size={13} aria-hidden />{t("Retry")}</button></div>;
}

export function Kpi({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "gain" | "loss" | "warn" }) {
  const { t } = useI18n();
  return <div className={`kpi ${tone ?? ""}`}><span className="kpi-label">{t(label)}</span><bdi className="kpi-value" dir="ltr">{t(value)}</bdi>{sub && <span className="kpi-sub">{t(sub)}</span>}</div>;
}

export const money = (n: number, dp = 2) => `${n < 0 ? "-" : ""}$${Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: dp, maximumFractionDigits: dp })}`;
export const signed = (n: number, dp = 2) => `${n > 0 ? "+" : n < 0 ? "-" : ""}${Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: dp, maximumFractionDigits: dp })}`;
export const num = (n: number) => n.toLocaleString("en-US", { maximumFractionDigits: 4 });

export function Pnl({ v, money: m = true }: { v: number; money?: boolean }) {
  return <bdi dir="ltr" className={v > 0 ? "gain" : v < 0 ? "loss" : ""}>{v > 0 ? <ArrowUp size={11} aria-hidden /> : v < 0 ? <ArrowDown size={11} aria-hidden /> : null}{m ? `${v < 0 ? "-" : "+"}${money(Math.abs(v))}` : `${signed(v)}%`}</bdi>;
}

export function Chip({ tone, children }: { tone: "ok" | "warn" | "bad" | "info" | "mute"; children: ReactNode }) {
  const { t } = useI18n();
  const Icon = tone === "ok" ? CircleCheck : tone === "bad" ? CircleX : tone === "warn" ? AlertTriangle : null;
  return <span className={`chip chip-${tone}`}>{Icon && <Icon size={11} aria-hidden />}{typeof children === "string" ? t(children) : children}</span>;
}

export function LineChart({ data, height = 140, label, area = true }: { data: number[]; height?: number; label: string; area?: boolean }) {
  const { t } = useI18n();
  if (data.length < 2) return <p className="muted">{t("Insufficient sample data")} · {t(label)}.</p>;
  const min = Math.min(...data), max = Math.max(...data), span = max - min || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * 100},${100 - ((v - min) / span) * 90 - 5}`);
  const up = data[data.length - 1] >= data[0];
  return <svg className={`line-chart ${up ? "up" : "down"}`} viewBox="0 0 100 100" preserveAspectRatio="none" style={{ height, direction: "ltr" }} role="img" aria-label={t(label)}>
    {[25, 50, 75].map(y => <line key={y} x1="0" x2="100" y1={y} y2={y} className="grid" vectorEffect="non-scaling-stroke" />)}
    {area && <polygon points={`0,100 ${pts.join(" ")} 100,100`} className="fill" />}
    <polyline points={pts.join(" ")} className="stroke" fill="none" vectorEffect="non-scaling-stroke" />
  </svg>;
}

export function Bars({ data, label }: { data: number[]; label: string }) {
  const max = Math.max(1, ...data.map(Math.abs));
  return <div className="bars" role="img" aria-label={label}>{data.map((v, i) => <span key={i} className={v >= 0 ? "pos" : "neg"} style={{ height: `${Math.max(6, (Math.abs(v) / max) * 100)}%` }} title={signed(v)} />)}</div>;
}

export function Ring({ pct, label, size = 96, tone }: { pct: number; label: string; size?: number; tone?: "warn" | "bad" }) {
  const r = 42, c = 2 * Math.PI * r; const t = tone ?? (pct >= 85 ? "bad" : pct >= 60 ? "warn" : "ok");
  return <figure className={`ring ring-${t}`} style={{ width: size }}>
    <svg viewBox="0 0 100 100" width={size} height={size} role="img" aria-label={`${label} ${pct}%`}><circle cx="50" cy="50" r={r} className="track" /><circle cx="50" cy="50" r={r} className="arc" strokeDasharray={`${(pct / 100) * c} ${c}`} transform="rotate(-90 50 50)" /><text x="50" y="55" textAnchor="middle">{pct}%</text></svg>
    <figcaption>{label}</figcaption>
  </figure>;
}

export function Meter({ pct, label }: { pct: number; label: string }) {
  const { t } = useI18n();
  const value = Math.max(0, Math.min(100, pct));
  return <div className="meter" role="meter" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100} aria-label={t(label)}><span style={{ transform: `scaleX(${value / 100})` }} /></div>;
}

export function Drawer({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const { t } = useI18n(); const id = useId(); const btn = useRef<HTMLButtonElement>(null);
  const dialog = useRef<HTMLElement>(null);
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null; btn.current?.focus();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key !== "Tab") return;
      const controls = dialog.current?.querySelectorAll<HTMLElement>("button:not([disabled]), a[href], input, select, textarea, [tabindex='0']");
      if (!controls?.length) return;
      const first = controls[0], last = controls[controls.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", key);
    return () => { window.removeEventListener("keydown", key); document.body.style.overflow = overflow; prev?.focus?.(); };
  }, [onClose]);
  return <div className="drawer-scrim" onClick={onClose}><aside ref={dialog} className="drawer" role="dialog" aria-modal="true" aria-labelledby={id} onClick={e => e.stopPropagation()}>
    <header><h2 id={id}>{t(title)}</h2><button ref={btn} className="icon-btn" onClick={onClose} aria-label={t("Close")} data-testid="close-preview-details"><X size={16} /></button></header>
    <div className="drawer-body"><DemoBanner what="Preview details from the demo dataset." />{children}</div>
  </aside></div>;
}

export function KV({ rows }: { rows: [string, ReactNode][] }) {
  const { t } = useI18n();
  return <dl className="kv-list">{rows.map(([k, v]) => <div className="kv-row" key={k}><dt>{t(k)}</dt><dd>{typeof v === "string" ? t(v) : v}</dd></div>)}</dl>;
}

export type Col<T> = { key: string; label: string; value: (r: T) => string | number; render?: (r: T) => ReactNode; numeric?: boolean; hideDetail?: boolean };
export type GridFilter<T> = { label: string; options: string[]; pick: (r: T) => string };

export function DataGrid<T extends { id: string }>({ rows, cols, filters = [], detailTitle, detailExtra, empty, label }: {
  rows: T[]; cols: Col<T>[]; filters?: GridFilter<T>[]; detailTitle: (r: T) => string; detailExtra?: (r: T) => ReactNode; empty: { title: string; text: string }; label: string;
}) {
  const { t } = useI18n();
  const [q, setQ] = useState(""); const [sort, setSort] = useState<{ k: string; dir: 1 | -1 } | null>(null);
  const [fv, setFv] = useState<string[]>(() => filters.map(() => "All")); const [sel, setSel] = useState<T | null>(null);
  const shown = useMemo(() => {
    let r = rows.filter(row => filters.every((f, i) => fv[i] === "All" || f.pick(row) === fv[i]));
    if (q.trim()) { const n = q.trim().toLowerCase(); r = r.filter(row => cols.flatMap(c => [String(c.value(row)), t(String(c.value(row)))]).join(" ").toLowerCase().includes(n)); }
    if (sort) { const c = cols.find(x => x.key === sort.k); if (c) r = [...r].sort((a, b) => { const x = c.value(a), y = c.value(b); return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y))) * sort.dir; }); }
    return r;
  }, [rows, cols, filters, fv, q, sort, t]);
  const onClose = useCallback(() => setSel(null), []);
  return <div className="grid-wrap">
    <div className="filter-bar" role="search">
      <label className="search-field"><Search size={14} aria-hidden /><span className="sr-only">{t("Search")}</span><input type="search" value={q} onChange={e => setQ(e.target.value)} placeholder={`${t("Search")}…`} data-testid={`search-${label}`} /></label>
      {filters.map((f, i) => <label key={f.label} className="field-inline"><span>{t(f.label)}</span><select value={fv[i]} data-testid={`filter-${label}-${i}`} onChange={e => setFv(fv.map((v, j) => j === i ? e.target.value : v))}>{["All", ...f.options].map(o => <option key={o} value={o}>{t(o)}</option>)}</select></label>)}
      <span className="count mono">{shown.length}/{rows.length}</span>
    </div>
    {shown.length === 0 ? <EmptyState {...empty} /> : <div className="table-wrap"><table className="data-table" aria-label={t(label)}>
      <thead><tr>{cols.map(c => <th key={c.key} className={c.numeric ? "num" : ""} aria-sort={sort?.k === c.key ? (sort.dir === 1 ? "ascending" : "descending") : "none"}>
        <button className="th-btn" onClick={() => setSort(s => s?.k === c.key ? (s.dir === 1 ? { k: c.key, dir: -1 } : null) : { k: c.key, dir: 1 })}>{t(c.label)}{sort?.k === c.key && (sort.dir === 1 ? <ArrowUp size={10} aria-hidden /> : <ArrowDown size={10} aria-hidden />)}</button></th>)}<th><span className="sr-only">{t("Details")}</span></th></tr></thead>
      <tbody>{shown.map(r => <tr key={r.id}>{cols.map(c => <td key={c.key} data-label={t(c.label)} className={c.numeric ? "num" : ""}>{c.render ? c.render(r) : typeof c.value(r) === "string" ? t(String(c.value(r))) : c.value(r)}</td>)}
        <td className="act"><button className="button small" data-testid={`details-${r.id}`} onClick={() => setSel(r)} aria-label={`${t("Details")}: ${t(detailTitle(r))}`}>{t("Details")}</button></td></tr>)}</tbody>
    </table></div>}
    {sel && <Drawer title={detailTitle(sel)} onClose={onClose}><KV rows={cols.filter(c => !c.hideDetail).map(c => [t(c.label), c.render ? c.render(sel) : t(String(c.value(sel)))])} />{detailExtra?.(sel)}</Drawer>}
  </div>;
}

export function Section({ title, children, aside, className = "" }: { title: string; children: ReactNode; aside?: ReactNode; className?: string }) {
  const { t } = useI18n();
  return <section className={`panel ${className}`}><div className="row"><h2>{t(title)}</h2>{aside}</div>{children}</section>;
}

export function Async<T>({ q, children, rows }: { q: { data: T | null; loading: boolean; error: boolean; reload: () => void }; children: (d: T) => ReactNode; rows?: number }) {
  if (q.loading) return <Loading rows={rows} />;
  if (q.error || !q.data) return <ErrorState onRetry={q.reload} />;
  return <>{children(q.data)}</>;
}
