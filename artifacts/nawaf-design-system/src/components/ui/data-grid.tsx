import { useCallback, useMemo, useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, Search } from "lucide-react";
import { Button } from "./button";
import { DetailDrawer } from "./detail-drawer";
import { KV } from "./kv";
import { EmptyState } from "./states";

// Source: DataGrid, Col, GridFilter in ndsp-console/src/ndsp/ui.tsx.
// Preserved: search, select filters ("All" sentinel), 3-state sort (asc, desc, none), aria-sort, details drawer, stacked mobile layout.
// Adaptations: i18n singleton replaced by caller-owned `t` (identity default) and `labels`; DemoBanner replaced by `drawerBanner`.
export type Col<T> = { key: string; label: string; value: (r: T) => string | number; render?: (r: T) => ReactNode; numeric?: boolean; hideDetail?: boolean };
export type GridFilter<T> = { label: string; options: string[]; pick: (r: T) => string };

export function DataGrid<T extends { id: string }>({ rows, cols, filters = [], detailTitle, detailExtra, empty, label, t = (s: string) => s, labels, drawerBanner }: {
  rows: T[]; cols: Col<T>[]; filters?: GridFilter<T>[]; detailTitle: (r: T) => string; detailExtra?: (r: T) => ReactNode; empty: { title: string; text: string }; label: string;
  t?: (s: string) => string; labels?: { search?: string; details?: string; close?: string }; drawerBanner?: ReactNode;
}) {
  const search = labels?.search ?? "Search", details = labels?.details ?? "Details";
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<{ k: string; dir: 1 | -1 } | null>(null);
  const [fv, setFv] = useState<string[]>(() => filters.map(() => "All"));
  const [sel, setSel] = useState<T | null>(null);
  const shown = useMemo(() => {
    let r = rows.filter((row) => filters.every((f, i) => fv[i] === "All" || f.pick(row) === fv[i]));
    if (q.trim()) { const n = q.trim().toLowerCase(); r = r.filter((row) => cols.map((c) => String(c.value(row))).join(" ").toLowerCase().includes(n)); }
    if (sort) { const c = cols.find((x) => x.key === sort.k); if (c) r = [...r].sort((a, b) => { const x = c.value(a), y = c.value(b); return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y))) * sort.dir; }); }
    return r;
  }, [rows, cols, filters, fv, q, sort]);
  const onClose = useCallback(() => setSel(null), []);
  return (
    <div className="nawaf-grid-wrap">
      <div className="nawaf-filter-bar" role="search">
        <label className="nawaf-search-field"><Search className="size-ds-search-icon" aria-hidden /><span className="nawaf-sr-only">{search}</span><input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={`${search}…`} data-testid={`search-${label}`} /></label>
        {filters.map((f, i) => (
          <label key={f.label} className="nawaf-field-inline"><span>{t(f.label)}</span>
            <select value={fv[i]} data-testid={`filter-${label}-${i}`} onChange={(e) => setFv(fv.map((v, j) => (j === i ? e.target.value : v)))}>{["All", ...f.options].map((o) => <option key={o} value={o}>{t(o)}</option>)}</select>
          </label>
        ))}
        <span className="nawaf-count" dir="ltr">{shown.length}/{rows.length}</span>
      </div>
      {shown.length === 0 ? <EmptyState {...empty} /> : (
        <div className="nawaf-table-wrap"><table className="nawaf-data-table" aria-label={label}>
          <thead><tr>{cols.map((c) => (
            <th key={c.key} className={c.numeric ? "num" : ""} aria-sort={sort?.k === c.key ? (sort.dir === 1 ? "ascending" : "descending") : "none"}>
              <button type="button" className="nawaf-th-btn" onClick={() => setSort((s) => (s?.k === c.key ? (s.dir === 1 ? { k: c.key, dir: -1 } : null) : { k: c.key, dir: 1 }))}>{t(c.label)}{sort?.k === c.key && (sort.dir === 1 ? <ArrowUp aria-hidden /> : <ArrowDown aria-hidden />)}</button>
            </th>))}<th><span className="nawaf-sr-only">{details}</span></th></tr></thead>
          <tbody>{shown.map((r) => (
            <tr key={r.id}>{cols.map((c) => <td key={c.key} data-label={t(c.label)} className={c.numeric ? "num" : ""}>{c.render ? c.render(r) : c.value(r)}</td>)}
              <td className="nawaf-act"><Button variant="outline" size="sm" data-testid={`details-${r.id}`} onClick={() => setSel(r)} aria-label={`${details}: ${detailTitle(r)}`}>{details}</Button></td></tr>))}</tbody>
        </table></div>
      )}
      {sel && <DetailDrawer title={detailTitle(sel)} onClose={onClose} closeLabel={labels?.close} banner={drawerBanner}><KV rows={cols.filter((c) => !c.hideDetail).map((c) => [t(c.label), c.render ? c.render(sel) : String(c.value(sel))])} />{detailExtra?.(sel)}</DetailDrawer>}
    </div>
  );
}
