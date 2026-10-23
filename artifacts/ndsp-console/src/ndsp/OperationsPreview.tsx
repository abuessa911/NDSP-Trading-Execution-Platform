"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "../components/DocumentLink";
import { AlertTriangle, Link2Off, ShieldCheck } from "lucide-react";
import { alertService, analyticsService, auditService, healthService, riskService } from "./services";
import { Tx, Async, Chip, DataGrid, DemoBanner, EmptyState, Kpi, KV, Meter, money, Pnl, Section, useDemo, type Col } from "./ui";
import { useI18n } from "./i18n";
import type { Alert } from "./types";
import PreviewChart from "./PreviewCharts";
import SafetyPreview from "./SafetyPreview";
import { useAuth } from "../components/AuthProvider";
import { BOT_NAME } from "../lib/bot-profile";

export function RiskView() {
  const q = useDemo(riskService.get);
  return <><DemoBanner what="All limits, violations and exposure below are scripted frontend examples. No risk-engine configuration changes." />
    <Async q={q}>{risk => <>
      <div className="kpi-grid"><Kpi label="Account exposure" value={`${risk.exposure}%`} /><Kpi label="Daily loss" value={money(risk.dailyLoss)} tone="warn" sub={`Demo ceiling ${money(risk.maxDailyLoss)}`} /><Kpi label="Remaining capacity" value={`${100 - risk.utilization}%`} /><Kpi label="Open positions" value={`${risk.openPositions} / ${risk.maxPositions}`} /></div>
      <div className="preview-grid"><Section title="Portfolio pressure" aside={<Chip tone="warn"><Tx>{"DEMO WARNING"}</Tx></Chip>}>
        <KV rows={[["Account exposure", `${risk.exposure}%`], ["Daily loss utilization", `${risk.utilization}%`], ["Maximum illustrative leverage", "3×"], ["Stop-loss requirement", "Required in demo policy"]]} />
        <Meter pct={risk.utilization} label="Demo daily loss utilization" />
        <p className="notice"><Tx>{"Actual execution allowance: unavailable. The preview cannot approve or unblock a trade."}</Tx></p>
      </Section><Section title="Attention required"><ul className="timeline-list">{risk.warnings.map(w => <li key={w}><AlertTriangle size={14} aria-hidden /><span><Tx>{w}</Tx></span></li>)}</ul><h3><Tx>{"Blocked illustrative actions"}</Tx></h3><ul>{risk.blocked.map(b => <li key={b}><Tx>{b}</Tx></li>)}</ul></Section></div>
      <div className="panel-grid"><Section title="Symbol exposure">{risk.bySymbol.map(row => <div className="demo-stat-list" key={row.symbol}><div className="row"><strong>{row.symbol}</strong><span>{row.pct}<Tx>{"% of demo exposure"}</Tx></span></div><Meter pct={row.pct} label={row.symbol} /></div>)}</Section>
        <Section title="Strategy exposure">{risk.byStrategy.map(row => <div className="demo-stat-list" key={row.name}><div className="row"><strong>{row.name}</strong><span>{row.pct}%</span></div><Meter pct={row.pct} label={row.name} /></div>)}</Section></div>
    </>}</Async><SafetyPreview /></>;
}

export function AnalyticsView() {
  const q = useDemo(analyticsService.equity);
  const [symbol, setSymbol] = useState("All");
  const [strategy, setStrategy] = useState("All");
  const [range, setRange] = useState("All samples");
  const { t } = useI18n();
  const filtered = useMemo(() => (q.data?.trades ?? []).filter(r => (symbol === "All" || r.symbol === symbol) && (strategy === "All" || r.strategy === strategy) && (range === "All samples" || r.closed.startsWith("Thu"))), [q.data, symbol, strategy, range]);
  return <><DemoBanner /><Async q={q}>{data => {
    const wins = filtered.filter(r => r.pnl > 0), losses = filtered.filter(r => r.pnl < 0);
    const grossWin = wins.reduce((sum, row) => sum + row.pnl, 0), grossLoss = -losses.reduce((sum, row) => sum + row.pnl, 0);
    let peak = data.equity[0], drawdown = 0;
    for (const value of data.equity) { peak = Math.max(peak, value); drawdown = Math.max(drawdown, ((peak - value) / peak) * 100); }
    return <>
      <Section title="Performance filters"><div className="filter-bar">
        <label className="field-inline"><span>{t("Symbol")}</span><select value={symbol} onChange={e => setSymbol(e.target.value)}>{["All", ...new Set(data.trades.map(r => r.symbol))].map(v => <option key={v} value={v}>{t(v)}</option>)}</select></label>
        <label className="field-inline"><span>{t("Strategy")}</span><select value={strategy} onChange={e => setStrategy(e.target.value)}>{["All", ...new Set(data.trades.map(r => r.strategy))].map(v => <option key={v} value={v}>{t(v)}</option>)}</select></label>
        <label className="field-inline"><span>{t("Demo period")}</span><select value={range} onChange={e => setRange(e.target.value)}><option value="All samples">{t("All samples")}</option><option value="Last sample day">{t("Last sample day")}</option></select></label>
      </div></Section>
      {!filtered.length ? <EmptyState title="Nothing here" text="No demo trades match these analytics filters." /> : <div className="kpi-grid"><Kpi label="Realized P&L" value={money(grossWin - grossLoss)} tone={grossWin >= grossLoss ? "gain" : "loss"} /><Kpi label="Win rate" value={`${((wins.length / filtered.length) * 100).toFixed(1)}%`} /><Kpi label="Profit factor" value={grossLoss ? (grossWin / grossLoss).toFixed(2) : "No losing sample"} /><Kpi label="Total trades" value={String(filtered.length)} /></div>}
      <Section title="Illustrative equity curve"><PreviewChart values={data.equity} label="Account equity · synthetic example" /><p className="muted"><Tx>{"The equity curve is a separate fixed account-level example; filters above affect trade-derived metrics only. Maximum sample drawdown: "}</Tx>{drawdown.toFixed(2)}%.</p></Section>
      <Section title="Trade-derived sample statistics"><KV rows={[
        ["Average win", wins.length ? money(grossWin / wins.length) : "No winning samples"], ["Average loss", losses.length ? money(-grossLoss / losses.length) : "No losing samples"],
        ["Loss rate", filtered.length ? `${((losses.length / filtered.length) * 100).toFixed(1)}%` : "No samples"],
        ["Best trade", filtered.length ? money(Math.max(...filtered.map(r => r.pnl))) : "No samples"], ["Worst trade", filtered.length ? money(Math.min(...filtered.map(r => r.pnl))) : "No samples"],
        ["Fees", money(filtered.reduce((sum, r) => sum + r.fees, 0))],
      ]} /></Section>
      <Section title="Daily P&L sample series"><DataGrid rows={data.daily.map((pnl, index) => ({ id: `sample-${index}`, day: `Sample ${index + 1}`, pnl }))} cols={[{ key: "day", label: "Sample day", value: row => row.day }, { key: "pnl", label: "Daily P&L", value: row => row.pnl, render: row => <Pnl v={row.pnl} />, numeric: true }]} label="daily-pnl" detailTitle={row => row.day} empty={{ title: "Nothing here", text: "No sample values." }} /></Section>
    </>;
  }}</Async></>;
}

export function AlertsView() {
  const { t } = useI18n();
  const q = useDemo(alertService.list);
  const [ack, setAck] = useState<Set<string>>(new Set());
  const [read, setRead] = useState<Set<string>>(new Set());
  const [tab, setTab] = useState("All");
  const [alertsLoaded, setAlertsLoaded] = useState(false);
  useEffect(() => {
    try {
      const value = localStorage.getItem("hunter-ksa1-preview-alert-flags-v1");
      if (value) {
        const parsed: unknown = JSON.parse(value);
        if (parsed && typeof parsed === "object") {
          const flags = parsed as Record<string, unknown>;
          const safeIds = (items: unknown): items is string[] =>
            Array.isArray(items) && items.length <= 500 &&
            items.every(item => typeof item === "string" && item.length > 0 && item.length <= 80);
          if (safeIds(flags.read)) setRead(new Set(flags.read));
          if (safeIds(flags.ack)) setAck(new Set(flags.ack));
        }
      }
    } catch { /* Browser storage is optional for preview actions. */ }
    setAlertsLoaded(true);
  }, []);
  useEffect(() => {
    if (!alertsLoaded) return;
    try {
      localStorage.setItem("hunter-ksa1-preview-alert-flags-v1",
        JSON.stringify({ read: [...read], ack: [...ack] }));
    } catch { /* Read and acknowledged preview states still work in this tab. */ }
  }, [read, ack, alertsLoaded]);
  const cols: Col<Alert>[] = [
    { key: "time", label: "Time", value: row => row.time },
    { key: "severity", label: "Severity", value: row => row.severity, render: row => <Chip tone={row.severity === "Critical" ? "bad" : row.severity === "Warning" ? "warn" : "info"}>{row.severity}</Chip> },
    { key: "category", label: "Category", value: row => row.category }, { key: "title", label: "Alert", value: row => row.title },
    { key: "subject", label: "Subject", value: row => row.subject },
    { key: "status", label: "Status", value: row => ack.has(row.id) ? "Acknowledged" : read.has(row.id) ? "Read" : "Unread" },
  ];
  return <><DemoBanner what="Read and acknowledgment actions are saved in this browser as preview only. No alert is acknowledged in any backend." />
    <Async q={q}>{rows => <Section title="Alert center"><div className="seg" role="group" aria-label={t("Alert status")}>{["All", "Unread", "Read", "Acknowledged"].map(value => <button key={value} className={value === tab ? "on" : ""} aria-pressed={value === tab} onClick={() => setTab(value)}>{t(value)}</button>)}</div>
      <DataGrid rows={rows.filter(row => tab === "All" || (tab === "Acknowledged" ? ack.has(row.id) : tab === "Read" ? read.has(row.id) && !ack.has(row.id) : !read.has(row.id) && !ack.has(row.id)))} cols={cols} label="alerts" detailTitle={row => row.title}
        filters={[{ label: "Severity", options: ["Information", "Warning", "Critical"], pick: row => row.severity }, { label: "Category", options: ["Trading", "Risk", "Strategy", "Exchange", "System", "Security"], pick: row => row.category }]}
        detailExtra={row => <><p className={row.severity === "Critical" ? "notice" : "inline-note"}>{t(row.message)}</p><div className="demo-actions"><button className="button" onClick={() => setRead(value => new Set(value).add(row.id))}>{t("Mark read in preview")}</button><button className="button" disabled={ack.has(row.id)} onClick={() => setAck(value => new Set(value).add(row.id))}>{t("Acknowledge in preview")}</button></div></>}
        empty={{ title: "Nothing here", text: "No demo alerts match this status or filter. Preview acknowledgment is saved in this browser only." }} />
    </Section>}</Async></>;
}

export function ExchangeView() {
  const [state, setState] = useState("Disconnected");
  return <><DemoBanner what="Binance configuration presentation only. No credential fields collect or store values; no connection is attempted." />
    <Section title="Exchange boundary" aside={<Link2Off size={18} aria-hidden />}><p className="notice"><Tx>{"Actual exchange access: NOT CONNECTED. Binance integration is outside M1."}</Tx></p>
      <label className="field"><span><Tx>{"Inspect a demo connection state"}</Tx></span><select value={state} onChange={e => setState(e.target.value)}><option value="Disconnected"><Tx>{"Disconnected"}</Tx></option><option value="Degraded"><Tx>{"Degraded"}</Tx></option><option value="Connected example"><Tx>{"Connected example"}</Tx></option></select></label>
      <KV rows={[["Exchange", "Binance · UI placeholder"], ["Illustrative state", `${state} — DEMO ONLY`], ["Mode", "Testnet presentation · not configured"], ["API status", "Not queried"], ["Credentials", "Not supplied · never collected by this preview"], ["Permissions", "Illustrative trade permission; withdrawal always unavailable"], ["Last verification", "No real verification performed"]]} />
      <Link className="button" href="/markets/"><Tx>{"Open read-only market panel"}</Tx></Link>
    </Section></>;
}

const previewBotSettingsKey = "hunter-ksa1-bot-preview-preferences-v1";
const previewMarkets = ["BTCUSDT", "ETHUSDT", "SOLUSDT"];
const previewTimeframes = ["5m", "15m", "1h", "4h"];

export function BotSettingsView() {
  const [name, setName] = useState(BOT_NAME), [market, setMarket] = useState("BTCUSDT"), [timeframe, setTimeframe] = useState("1h");
  const [risk, setRisk] = useState("1"), [notify, setNotify] = useState(true);
  const [saveMessage, setSaveMessage] = useState("");
  const { t } = useI18n();
  useEffect(() => {
    try {
      const raw = localStorage.getItem(previewBotSettingsKey);
      if (!raw) return;
      const saved: unknown = JSON.parse(raw);
      if (!saved || typeof saved !== "object") return;
      const item = saved as Record<string, unknown>;
      if (item.version !== 1) return;
      if (typeof item.name === "string" && item.name.length > 0 && item.name.length <= 60) setName(item.name);
      if (typeof item.market === "string" && previewMarkets.includes(item.market)) setMarket(item.market);
      if (typeof item.timeframe === "string" && previewTimeframes.includes(item.timeframe)) setTimeframe(item.timeframe);
      if (typeof item.risk === "string" && Number.isFinite(Number(item.risk)) && Number(item.risk) >= 0.1 && Number(item.risk) <= 5) setRisk(item.risk);
      if (typeof item.notify === "boolean") setNotify(item.notify);
    } catch {
      setSaveMessage("Preview preferences could not be loaded from this browser.");
    }
  }, []);
  function savePreview() {
    const positionRisk = Number(risk);
    if (!name.trim() || name.length > 60 || !Number.isFinite(positionRisk) || positionRisk < 0.1 || positionRisk > 5) {
      setSaveMessage("Enter a valid preview name and position risk between 0.1% and 5%.");
      return;
    }
    try {
      localStorage.setItem(previewBotSettingsKey, JSON.stringify({
        version: 1, name: name.trim(), market, timeframe, risk: String(positionRisk), notify,
      }));
      setSaveMessage("Preview preferences saved in this browser only. No trading configuration changed.");
    } catch {
      setSaveMessage("Could not save preview preferences in this browser.");
    }
  }
  function resetPreview() {
    setName(BOT_NAME); setMarket("BTCUSDT"); setTimeframe("1h"); setRisk("1"); setNotify(true);
    try {
      localStorage.removeItem(previewBotSettingsKey);
      setSaveMessage("Preview preferences reset in this browser.");
    } catch {
      setSaveMessage("Could not clear preview preferences in this browser.");
    }
  }
  return <><DemoBanner what="These sample bot preferences are stored in this browser only when you save them. They never change the server bot, trading strategy, margin, or exchange settings." /><Section title="Bot settings preview">
    <div className="preview-grid"><label className="field"><span><Tx>{"Demo bot name"}</Tx></span><input value={name} maxLength={60} onChange={e => setName(e.target.value)} /></label>
      <label className="field"><span><Tx>{"Default market"}</Tx></span><select value={market} onChange={e => setMarket(e.target.value)}>{["BTCUSDT", "ETHUSDT", "SOLUSDT"].map(v => <option key={v}>{v}</option>)}</select></label>
      <label className="field"><span><Tx>{"Timeframe"}</Tx></span><select value={timeframe} onChange={e => setTimeframe(e.target.value)}>{["5m", "15m", "1h", "4h"].map(v => <option key={v}>{v}</option>)}</select></label>
      <label className="field"><span><Tx>{"Illustrative position risk (%)"}</Tx></span><input type="number" min="0.1" max="5" step="0.1" value={risk} onChange={e => setRisk(e.target.value)} /></label></div>
    <label className="field-inline check"><input type="checkbox" checked={notify} onChange={e => setNotify(e.target.checked)} /><span><Tx>{"Show preview notifications preference"}</Tx></span></label>
    <p className="inline-note"><Tx>{"No real bot exists in M1. Timezone, operating mode and safety limits are not changed by these drafts."}</Tx></p>
    <div className="demo-actions"><button type="button" className="button" onClick={resetPreview}><Tx>{"Reset draft"}</Tx></button><button type="button" className="button" onClick={savePreview}><Tx>{"Save preview preferences"}</Tx></button></div>
    <p className="muted" role="status">{t(saveMessage)}</p>
  </Section></>;
}

export function FutureHealthView() {
  const q = useDemo(healthService.nodes);
  return <><DemoBanner what="Future system topology examples only. They are NOT the real health result shown above." /><Async q={q}>{nodes => <Section title="Future topology preview"><div className="preview-grid">{nodes.map(node => <article className="demo-focus" key={node.id}><div className="row"><h3><Tx>{node.name}</Tx></h3><Chip tone={node.status === "Operational" ? "info" : node.status === "Down" ? "bad" : "warn"}><Tx>{node.status}</Tx><Tx>{" · DEMO"}</Tx></Chip></div><strong className="mono"><Tx>{node.metric}</Tx></strong><p className="muted"><Tx>{node.detail}</Tx><Tx>{" · synthetic"}</Tx></p></article>)}</div></Section>}</Async></>;
}

export function SecurityView() {
  const { state, identity, administratorMfaVerified, revalidate } = useAuth();
  return <><Section title="Server-authoritative account security" aside={<ShieldCheck size={20} aria-hidden />}>
    <span className="tag"><Tx>{"REAL M1 SESSION STATE"}</Tx></span>
    <KV rows={[["Session", state], ["Role", identity?.role ?? "Not available while signed out"], ["Administrator MFA", administratorMfaVerified ? "Verified by the server" : "Not verified"], ["Password authority", "External OIDC provider; this console never stores passwords"], ["API security", "Existing same-origin session and CSRF boundary"], ["Session inventory", "Not exposed by the current M1 API"]]} />
    <button className="button" onClick={() => void revalidate()}><Tx>{"Check current session"}</Tx></button>
  </Section><Section title="Recent login and security activity"><EmptyState title="Not available" text="The M1 user API does not expose session lists, password configuration or recent login events. No synthetic account-security records are substituted." /><Link className="button" href="/admin/audit/"><Tx>{"Open MFA-protected administrator audit"}</Tx></Link></Section></>;
}

export function ActivityView() {
  const q = useDemo(auditService.list);
  return <><DemoBanner what="Synthetic activity records only. This is NOT the real administrator audit, login history or immutable evidence." /><Async q={q}>{rows => <Section title="Activity Preview">
    <DataGrid rows={rows} label="activity" detailTitle={row => row.event}
      cols={[{ key: "time", label: "Time", value: row => row.time }, { key: "event", label: "Event", value: row => row.event }, { key: "category", label: "Category", value: row => row.category }, { key: "severity", label: "Severity", value: row => row.severity, render: row => <Chip tone={row.severity === "Warning" ? "warn" : "info"}>{row.severity}</Chip> }, { key: "actor", label: "Actor", value: row => row.actor }]}
      filters={[{ label: "Category", options: ["Signal", "Risk", "Strategy", "Security"], pick: row => row.category }, { label: "Severity", options: ["Information", "Warning", "Critical"], pick: row => row.severity }]}
      detailExtra={() => <p className="notice"><Tx>{"Illustrative event from the central mock dataset. Real audit evidence remains tenant-scoped and MFA-protected."}</Tx></p>}
      empty={{ title: "Nothing here", text: "No synthetic activity matches the filters." }} />
  </Section>}</Async></>;
}
