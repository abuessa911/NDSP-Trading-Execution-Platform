"use client";
import { useEffect, useState } from "react";
import { Star, Play, Pause } from "lucide-react";
import { marketService, signalService, strategyService } from "./services";
import { Tx, Async, Chip, DemoBanner, DataGrid, KV, Kpi, LineChart, Meter, Pnl, Section, money, num, useDemo, type Col } from "./ui";
import { useI18n } from "./i18n";
import { replaySeries, strategySketch, timelineSteps, traceNotes } from "./mocks/demo-data";
import PreviewChart from "./PreviewCharts";
import LiveMarketPreview from "./LiveMarketPreview";
import HunterControlPanel from "../components/HunterControlPanel";
import TestnetExecutionPanel from "../components/TestnetExecutionPanel";
import HunterStrategyScannerPanel from "../components/HunterStrategyScannerPanel";
import HunterExecutionReviewPanel from "../components/HunterExecutionReviewPanel";
import HunterTradingPreferencesPanel from "../components/HunterTradingPreferencesPanel";
import PaperBrokerPanel from "../components/PaperBrokerPanel";
import type { Market, Signal, SignalStage, Strategy } from "./types";

const uniq = <T,>(rows: T[], f: (r: T) => string) => [...new Set(rows.map(f))];

export function MarketsView() {
  const q = useDemo(marketService.list); const { t } = useI18n();
  const [fav, setFav] = useState<Set<string>>(new Set(["BTCUSDT"])); const [onlyFav, setOnlyFav] = useState(false);
  const [favoritesLoaded, setFavoritesLoaded] = useState(false);
  useEffect(() => {
    try {
      const value = localStorage.getItem("hunter-ksa1-preview-favorites-v1");
      if (value !== null) {
        const saved: unknown = JSON.parse(value);
        if (Array.isArray(saved) && saved.length <= 100 && saved.every(x => typeof x === "string" && /^[A-Z0-9]{2,16}$/.test(x))) {
          setFav(new Set(saved));
        }
      }
    } catch { /* Browser storage is optional for preview favorites. */ }
    setFavoritesLoaded(true);
  }, []);
  useEffect(() => {
    if (!favoritesLoaded) return;
    try { localStorage.setItem("hunter-ksa1-preview-favorites-v1", JSON.stringify([...fav])); }
    catch { /* Preview controls remain available without browser storage. */ }
  }, [fav, favoritesLoaded]);
  return <><LiveMarketPreview /><DemoBanner />
    <Async q={q} rows={6}>{rows => {
      const list = rows.filter(r => !onlyFav || fav.has(r.symbol));
      const cols: Col<Market>[] = [
        { key: "fav", label: "Favorites", value: r => (fav.has(r.symbol) ? 1 : 0), hideDetail: true, render: r => <button className={`icon-btn ${fav.has(r.symbol) ? "on" : ""}`} aria-pressed={fav.has(r.symbol)} aria-label={`${t("Favorites")}: ${r.symbol}`} onClick={() => setFav(s => { const n = new Set(s); n.has(r.symbol) ? n.delete(r.symbol) : n.add(r.symbol); return n; })}><Star size={14} /></button> },
        { key: "symbol", label: "Symbol", value: r => r.symbol, render: r => <strong>{r.symbol}</strong> },
        { key: "price", label: "Price", value: r => r.price, numeric: true, render: r => num(r.price) },
        { key: "chg", label: "24h", value: r => r.change24h, numeric: true, render: r => <Pnl v={r.change24h} money={false} /> },
        { key: "trend", label: "Trend", value: r => r.spark[r.spark.length - 1] - r.spark[0], hideDetail: true, render: r => <div className="mini"><LineChart data={r.spark} height={26} area={false} label={`${r.symbol} trend`} /></div> },
        { key: "vol", label: "Volume", value: r => r.volume, numeric: true },
        { key: "vola", label: "Volatility", value: r => r.volatility, numeric: true, render: r => <span className="vola"><Meter pct={r.volatility} label={`${r.symbol} volatility`} />{r.volatility}</span> },
        { key: "bot", label: "Bot", value: r => r.bot, render: r => <Chip tone={r.bot === "Trading" ? "ok" : r.bot === "Watching" ? "info" : "mute"}>{r.bot}</Chip> },
        { key: "strategy", label: "Strategy", value: r => r.strategy }, { key: "tf", label: "Timeframe", value: r => r.timeframe },
        { key: "signal", label: "Signal", value: r => r.signal, render: r => <Chip tone={r.signal === "Buy" ? "ok" : r.signal === "Sell" ? "bad" : "mute"}>{r.signal}</Chip> },
        { key: "pos", label: "Position", value: r => r.position },
      ];
      return <Section title="Markets" aside={<label className="field-inline check"><input type="checkbox" checked={onlyFav} onChange={e => setOnlyFav(e.target.checked)} /><span>{t("Favorites")}</span></label>}>
        <p className="muted"><Tx>{"Preview favorites are saved in this browser. The table below still contains static demo prices; use the separate read-only live market panel for verified candles."}</Tx></p>
        <DataGrid rows={list} cols={cols} label="markets" detailTitle={r => r.symbol} filters={[{ label: "Signal", options: ["Buy", "Sell", "Neutral"], pick: r => r.signal }, { label: "Bot", options: ["Trading", "Watching", "Idle"], pick: r => r.bot }]} empty={{ title: "Nothing here", text: "No markets match. Clear filters or the favorites toggle." }} />
      </Section>;
    }}</Async></>;
}

export function TerminalView() {
  const { lang } = useI18n();
  return <><HunterControlPanel /><HunterTradingPreferencesPanel /><TestnetExecutionPanel /><HunterStrategyScannerPanel /><HunterExecutionReviewPanel /><LiveMarketPreview /><PaperBrokerPanel />
    <section className="panel">
      <h2>{lang === "ar" ? "إرسال الأوامر" : "Order submission"}</h2>
      <p className="notice">{lang === "ar"
        ? "التنفيذ الحي غير مفعّل. إعدادات الأصل والفريم والنمط والرافعة تُؤكَّد من الشريط الموحد أعلاه."
        : "Live execution is disabled. Confirm asset, timeframe, style and leverage in the shared settings above."}</p>
      <p className="muted">{lang === "ar" ? "أزرار المحاكاة تسجل أوامر افتراضية فقط؛ لا ترسل أوامر للبورصة." : "Simulation buttons record virtual orders only; no orders are sent to an exchange."}</p>
    </section>
  </>;
}

export function PositionsView() {
  return <PaperBrokerPanel view="positions" />;
}

export function OrdersView() {
  return <PaperBrokerPanel view="orders" />;
}

export function TradesView() {
  return <PaperBrokerPanel view="history" />;
}

function strategyUpdateLabel(value: string, lang: "ar" | "en"): string {
  if (lang !== "ar") return value;
  const match = /^(\d+)([mh]) ago$/.exec(value);
  if (!match) return value;
  const count = Number(match[1]);
  const digits = count.toLocaleString("ar-SA");
  if (match[2] === "m") return count === 1 ? "قبل دقيقة" : count === 2 ? "قبل دقيقتين" : `قبل ${digits} ${count >= 3 && count <= 10 ? "دقائق" : "دقيقة"}`;
  return count === 1 ? "قبل ساعة" : count === 2 ? "قبل ساعتين" : `قبل ${digits} ${count >= 3 && count <= 10 ? "ساعات" : "ساعة"}`;
}
function strategySignalLabel(value: string, t: (s: string) => string): string {
  const match = /^(Buy|Sell) ([A-Z0-9]+) · (\d{2}:\d{2})$/.exec(value);
  return match ? `${t(match[1])} ${match[2]} · ${match[3]}` : t(value);
}

export function StrategiesView() {
  const { lang, t } = useI18n();
  const q = useDemo(strategyService.list); const [sel, setSel] = useState<string | null>(null);
  return <><HunterStrategyScannerPanel /><DemoBanner what="Historical strategy metrics and signals below remain synthetic examples; only the scanner above reads live closed candles." />
    <Async q={q} rows={4}>{rows => {
      const cur = rows.find(r => r.id === sel); const st = (s: Strategy) => s.state;
      return <div className="split"><div className="strategy-list">{rows.map(s => <article key={s.id} className={`strategy ${sel === s.id ? "sel" : ""}`}>
        <header><button className="linkish" onClick={() => setSel(s.id)} aria-pressed={sel === s.id}><h3>{t(s.name)}</h3></button><Chip tone={st(s) === "Active" ? "ok" : st(s) === "Paused" ? "warn" : "mute"}>{st(s)}</Chip></header>
        <p className="muted"><bdi dir="ltr">{s.markets.join(" · ")} · {s.timeframe}</bdi></p>
        <div className="stat-row tight"><Kpi label="Win rate" value={`${s.winRate}%`} /><Kpi label="P&L" value={money(s.pnl)} tone={s.pnl >= 0 ? "gain" : "loss"} /><Kpi label="Trades" value={String(s.trades)} /></div>
        <p className="muted">{t("Risk allocation")}: <bdi dir="ltr">{s.risk}%</bdi></p>
        <Meter pct={s.risk} label={`${t("Risk allocation")} — ${t(s.name)}`} />
        <div className="row"><button className="button small" onClick={() => setSel(s.id)}><Tx>{"Details"}</Tx></button>
</div></article>)}</div>
        <section className="panel" aria-live="polite">{cur ? <><h2>{t(cur.name)}</h2><p><Tx>{cur.note}</Tx></p><KV rows={[["State", t(st(cur))], ["Markets", cur.markets.join(", ")], ["Timeframe", cur.timeframe], ["Last signal", strategySignalLabel(cur.lastSignal, t)], ["Updated", strategyUpdateLabel(cur.updated, lang)], ["Configuration", t("Read-only preview")]]} />
           <LineChart data={strategySketch.map(v => v * (cur.pnl >= 0 ? 1 : -1))} height={90} label="Synthetic performance sketch, not reported strategy returns" /></> : <p className="muted"><Tx>{"Select a strategy to inspect its overview."}</Tx></p>}</section></div>;
    }}</Async></>;
}

const stages: SignalStage[] = ["Detected", "Validating", "Approved", "Executed", "Completed"];
function Lifecycle({ stage }: { stage: SignalStage }) {
  const { t } = useI18n();
  const path = stage === "Blocked" ? ["Detected", "Validating", "Blocked"] : stage === "Expired" ? ["Detected", "Validating", "Expired"] : stages;
  const at = stage === "Executed" ? 3 : path.indexOf(stage);
  return <ol className="lifecycle" aria-label={`${t("Stage")} ${t(stage)}`}>{path.map((p, i) => <li key={p} className={`${i <= at ? "done" : ""} ${p === stage || (stage === "Executed" && i === 3) ? "now" : ""} ${p === "Blocked" ? "stop" : ""}`}><span className="dot" />{t(p)}</li>)}</ol>;
}
export function SignalsView() {
  const q = useDemo(signalService.list); const [sel, setSel] = useState<Signal | null>(null);
  return <><DemoBanner what="Decisions and signals are illustrative. No NDSP contract is read or verified in this preview." /><Async q={q} rows={4}>{rows =>
    <div className="split"><Section title="NDSP Decisions"><ul className="signal-list">{rows.map(s => <li key={s.id}><button className={sel?.id === s.id ? "active" : ""} onClick={() => setSel(s)}><span className="mono">{s.time}</span><strong>{s.symbol}</strong><Chip tone={s.direction === "Buy" ? "ok" : "bad"}>{s.direction}</Chip><span className="muted">{s.strategy} · {s.timeframe}</span><Chip tone={s.stage === "Blocked" ? "bad" : s.stage === "Expired" ? "mute" : s.stage === "Completed" || s.stage === "Executed" ? "ok" : "info"}>{s.stage}</Chip></button></li>)}</ul></Section>
      <section className="panel" aria-live="polite">{sel ? <><h2>{sel.symbol} <Tx>{sel.direction}</Tx></h2><Lifecycle stage={sel.stage} /><KV rows={[["Market price", num(sel.price)], ["Strategy", sel.strategy], ["Resulting action", sel.action]]} /><h3><Tx>{"Supporting evidence"}</Tx></h3><ul>{sel.evidence.map(e => <li key={e}><Tx>{e}</Tx></li>)}</ul></> : <p className="muted"><Tx>{"Select a signal to see its lifecycle and evidence."}</Tx></p>}</section></div>}</Async></>;
}

export function TraceView() {
  const q = useDemo(signalService.list); const [i, setI] = useState(0);
  return <><DemoBanner what="A hand-written example trace. No real decision, order or fill is being explained." /><Async q={q} rows={3}>{() =>
    <Section title="Execution Trace / Why?"><ol className="trace">{timelineSteps.map((s, n) => <li key={s} className={n <= i ? "done" : ""}><button onClick={() => setI(n)} aria-current={n === i ? "step" : undefined}><span className="dot" /><Tx>{s}</Tx></button></li>)}</ol>
       <p className="notice" aria-live="polite"><strong><Tx>{timelineSteps[i]}</Tx>.</strong> <Tx>{traceNotes[i]}</Tx></p></Section>}</Async></>;
}

export function ReplayView() {
  const [pos, setPos] = useState(40);
  const [playing, setPlaying] = useState(false);
  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => setPos(p => Math.min(100, p + 5)), 350);
    return () => window.clearInterval(timer);
  }, [playing]);
  useEffect(() => { if (pos >= 100 && playing) setPlaying(false); }, [pos, playing]);
  return <><DemoBanner what="Synthetic sample playback only. No historical candles, trades, or real replay engine are used." /><Section title="Replay Lab">
    <PreviewChart values={replaySeries.slice(0, Math.max(2, Math.round((pos / 100) * replaySeries.length)))} label="Synthetic replay preview" unit="index" />
    <label className="field"><span><Tx>{"Position "}</Tx>{pos}%</span><input type="range" min={5} max={100} value={pos} onChange={e => { setPos(Number(e.target.value)); setPlaying(false); }} /></label>
    <button type="button" className="button" aria-pressed={playing} onClick={() => { if (pos >= 100) setPos(5); setPlaying(p => !p); }}>
      <Tx>{playing ? "Pause synthetic playback" : "Play synthetic sample"}</Tx>
    </button></Section></>;
}


