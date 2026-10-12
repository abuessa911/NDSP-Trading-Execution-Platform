"use client";
import { useState } from "react";
import { Star, Play, Pause } from "lucide-react";
import { marketService, orderService, positionService, signalService, strategyService, tradeService } from "./services";
import { Tx, Async, Chip, DemoBanner, DataGrid, KV, Kpi, LineChart, Meter, Pnl, Section, money, num, useDemo, type Col } from "./ui";
import { useI18n } from "./i18n";
import { replaySeries, strategySketch, timelineSteps, traceNotes } from "./mocks/demo-data";
import PreviewChart from "./PreviewCharts";
import type { Market, Order, Position, Signal, SignalStage, Strategy, Trade } from "./types";

const uniq = <T,>(rows: T[], f: (r: T) => string) => [...new Set(rows.map(f))];

export function MarketsView() {
  const q = useDemo(marketService.list); const { t } = useI18n();
  const [fav, setFav] = useState<Set<string>>(new Set(["BTCUSDT"])); const [onlyFav, setOnlyFav] = useState(false);
  return <><DemoBanner />
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
        <p className="muted"><Tx>{"Watchlist stars live in this tab only; they are not saved. Prices are static demo values and do not tick."}</Tx></p>
        <DataGrid rows={list} cols={cols} label="markets" detailTitle={r => r.symbol} filters={[{ label: "Signal", options: ["Buy", "Sell", "Neutral"], pick: r => r.signal }, { label: "Bot", options: ["Trading", "Watching", "Idle"], pick: r => r.bot }]} empty={{ title: "Nothing here", text: "No markets match. Clear filters or the favorites toggle." }} />
      </Section>;
    }}</Async></>;
}

export function TerminalView() {
  const { t } = useI18n();
  const q = useDemo(marketService.list); const [sym, setSym] = useState("BTCUSDT"); const [tf, setTf] = useState("1h"); const [side, setSide] = useState<"Buy" | "Sell">("Buy");
  return <><DemoBanner what="Chart area and order ticket are placeholders. Buy/Sell cannot submit; no order is created anywhere." />
    <Async q={q} rows={5}>{rows => {
      const m = rows.find(r => r.symbol === sym) ?? rows[0];
      return <div className="terminal">
        <Section title="Markets" className="t-list"><ul className="sym-list">{rows.map(r => <li key={r.id}><button className={r.symbol === sym ? "active" : ""} aria-pressed={r.symbol === sym} onClick={() => setSym(r.symbol)}><span>{r.symbol}</span><Pnl v={r.change24h} money={false} /></button></li>)}</ul></Section>
        <section className="panel t-chart"><div className="row"><div><h2>{m.symbol}</h2><span className="big-price mono">{num(m.price)}</span> <Pnl v={m.change24h} money={false} /></div>
          <div className="seg" role="group" aria-label={t("Timeframe")}>{["1m", "5m", "15m", "30m", "1h", "4h", "1D", "1W"].map(x => <button key={x} aria-pressed={x === tf} className={x === tf ? "on" : ""} onClick={() => setTf(x)}>{x}</button>)}</div></div>
          <PreviewChart values={m.spark.map(value => m.price * (1 + (value - 50) / 1000))} label={`${m.symbol} synthetic illustrative price path`} unit="USDT" />
          <p className="muted"><Tx>{"Future chart integration slot. Timeframe "}</Tx>{tf}<Tx>{" changes the selector only; these are synthetic samples, not historical candles."}</Tx></p>
          <div className="stat-row"><Kpi label="High" value={num(m.price * 1.012)} /><Kpi label="Low" value={num(m.price * 0.981)} /><Kpi label="Volume" value={m.volume} /><Kpi label="Volatility" value={String(m.volatility)} /></div></section>
        <section className="panel t-ticket"><h2><Tx>{"Order ticket"}</Tx></h2><span className="tag"><Tx>{"UNCONNECTED · DEMO UI"}</Tx></span>
          <div className="seg full" role="group" aria-label={t("Side")}><button className={side === "Buy" ? "on gain-bg" : ""} aria-pressed={side === "Buy"} onClick={() => setSide("Buy")}><Tx>{"Buy"}</Tx></button><button className={side === "Sell" ? "on loss-bg" : ""} aria-pressed={side === "Sell"} onClick={() => setSide("Sell")}><Tx>{"Sell"}</Tx></button></div>
          <label className="field"><span><Tx>{"Quantity"}</Tx></span><input disabled placeholder="0.000" /></label>
          <button className="button wide" disabled><Tx>{side}</Tx> {m.symbol}<Tx>{" unavailable"}</Tx></button>
          <p className="muted"><Tx>{"Execution is not implemented. M1 NOT ACCEPTED."}</Tx></p>
          <KV rows={[["Strategy", m.strategy], ["Signal", m.signal], ["Position", m.position], ["Execution allowance", "Blocked (demo)"]]} /></section>
      </div>;
    }}</Async></>;
}

export function PositionsView() {
  const q = useDemo(positionService.list);
  return <><DemoBanner /><Async q={q} rows={4}>{rows => {
    const cols: Col<Position>[] = [
      { key: "symbol", label: "Symbol", value: r => r.symbol, render: r => <strong>{r.symbol}</strong> },
      { key: "side", label: "Side", value: r => r.side, render: r => <Chip tone={r.side === "LONG" ? "ok" : "bad"}>{r.side}</Chip> },
      { key: "size", label: "Size", value: r => r.size, numeric: true, render: r => num(r.size) },
      { key: "entry", label: "Entry", value: r => r.entry, numeric: true, render: r => num(r.entry) },
      { key: "mark", label: "Mark", value: r => r.mark, numeric: true, render: r => num(r.mark) },
      { key: "lev", label: "Leverage", value: r => r.leverage, numeric: true, render: r => `${r.leverage}x` },
      { key: "margin", label: "Margin", value: r => r.margin, numeric: true, render: r => money(r.margin) },
      { key: "pnl", label: "Unrealized P&L", value: r => r.pnl, numeric: true, render: r => <Pnl v={r.pnl} /> },
      { key: "stop", label: "Stop", value: r => r.stop, numeric: true, render: r => (r.stop ? num(r.stop) : "none") },
      { key: "target", label: "Target", value: r => r.target, numeric: true, render: r => num(r.target) },
      { key: "strategy", label: "Strategy", value: r => r.strategy }, { key: "opened", label: "Opened", value: r => r.opened },
      { key: "status", label: "Status", value: r => r.status, render: r => <Chip tone={r.status === "Protected" ? "ok" : "warn"}>{r.status}</Chip> },
    ];
    return <><div className="stat-row"><Kpi label="Open positions" value={String(rows.length)} /><Kpi label="Unrealized P&L" value={money(rows.reduce((a, r) => a + r.pnl, 0))} tone="gain" /><Kpi label="Margin used" value={money(rows.reduce((a, r) => a + r.margin, 0))} /></div>
      <Section title="Positions"><DataGrid rows={rows} cols={cols} label="positions" detailTitle={r => `${r.symbol} ${r.side}`} filters={[{ label: "Side", options: ["LONG", "SHORT"], pick: r => r.side }, { label: "Status", options: uniq(rows, r => r.status), pick: r => r.status }]}
        detailExtra={r => <><p className="muted"><Tx>{"Entry to target range"}</Tx></p><Meter pct={Math.max(0, Math.min(100, ((r.mark - r.entry) / (r.target - r.entry)) * 100))} label="Progress to target" /></>}
        empty={{ title: "Nothing here", text: "No open positions in the demo dataset match this view." }} /></Section></>;
  }}</Async></>;
}

export function OrdersView() {
  const { t } = useI18n();
  const q = useDemo(orderService.list); const [tab, setTab] = useState("All");
  return <><DemoBanner /><Async q={q} rows={4}>{rows => {
    const cols: Col<Order>[] = [
      { key: "id", label: "Order ID", value: r => r.id, render: r => <span className="mono">{r.id}</span> }, { key: "symbol", label: "Symbol", value: r => r.symbol },
      { key: "side", label: "Side", value: r => r.side, render: r => <Chip tone={r.side === "BUY" ? "ok" : "bad"}>{r.side}</Chip> }, { key: "type", label: "Type", value: r => r.type },
      { key: "qty", label: "Quantity", value: r => r.qty, numeric: true, render: r => num(r.qty) }, { key: "price", label: "Price", value: r => r.price, numeric: true, render: r => num(r.price) },
      { key: "filled", label: "Filled", value: r => r.filled, numeric: true, render: r => `${Math.round((r.filled / r.qty) * 100)}%` },
      { key: "status", label: "Status", value: r => r.status, render: r => <Chip tone={r.status === "Filled" ? "ok" : r.status === "Rejected" ? "bad" : r.status === "Open" ? "info" : "mute"}>{r.status}</Chip> },
      { key: "strategy", label: "Strategy", value: r => r.strategy }, { key: "created", label: "Created", value: r => r.created }, { key: "updated", label: "Updated", value: r => r.updated },
    ];
    return <Section title="Orders"><div className="seg" role="tablist" aria-label="Order status">{["All", "Open", "Filled", "Cancelled", "Rejected"].map(s => <button key={s} role="tab" aria-selected={tab === s} className={tab === s ? "on" : ""} onClick={() => setTab(s)}>{t(s)}</button>)}</div>
      <DataGrid rows={tab === "All" ? rows : rows.filter(r => r.status === tab)} cols={cols} label="orders" detailTitle={r => r.id} detailExtra={r => <p className="notice">{r.note}</p>} empty={{ title: "Nothing here", text: "No orders in this state." }} /></Section>;
  }}</Async></>;
}

export function TradesView() {
  const q = useDemo(tradeService.list);
  return <><DemoBanner /><Async q={q} rows={4}>{rows => {
    const cols: Col<Trade>[] = [
      { key: "symbol", label: "Symbol", value: r => r.symbol }, { key: "dir", label: "Direction", value: r => r.direction },
      { key: "entry", label: "Entry", value: r => r.entry, numeric: true, render: r => num(r.entry) }, { key: "exit", label: "Exit", value: r => r.exit, numeric: true, render: r => num(r.exit) },
      { key: "qty", label: "Quantity", value: r => r.qty, numeric: true }, { key: "pnl", label: "Realized P&L", value: r => r.pnl, numeric: true, render: r => <Pnl v={r.pnl} /> },
      { key: "fees", label: "Fees", value: r => r.fees, numeric: true, render: r => money(r.fees) }, { key: "strategy", label: "Strategy", value: r => r.strategy }, { key: "tf", label: "Timeframe", value: r => r.timeframe },
      { key: "opened", label: "Opened", value: r => r.opened }, { key: "closed", label: "Closed", value: r => r.closed }, { key: "dur", label: "Duration", value: r => r.duration },
      { key: "result", label: "Result", value: r => r.result, render: r => <Chip tone={r.result === "Win" ? "ok" : "bad"}>{r.result}</Chip> },
    ];
    return <Section title="Trade History"><DataGrid rows={rows} cols={cols} label="trades" detailTitle={r => `${r.symbol} ${r.direction}`} empty={{ title: "Nothing here", text: "No closed trades match." }}
      filters={[{ label: "Sample day", options: uniq(rows, r => r.closed.split(" ")[0]), pick: r => r.closed.split(" ")[0] }, { label: "Symbol", options: uniq(rows, r => r.symbol), pick: r => r.symbol }, { label: "Strategy", options: uniq(rows, r => r.strategy), pick: r => r.strategy }, { label: "Result", options: ["Win", "Loss"], pick: r => r.result }, { label: "Direction", options: ["LONG", "SHORT"], pick: r => r.direction }]} /></Section>;
  }}</Async></>;
}

export function StrategiesView() {
  const q = useDemo(strategyService.list); const [sel, setSel] = useState<string | null>(null); const [over, setOver] = useState<Record<string, Strategy["state"]>>({});
  return <><DemoBanner what="State toggles below change this preview only. They do not start, stop or configure any real strategy." />
    <Async q={q} rows={4}>{rows => {
      const cur = rows.find(r => r.id === sel); const st = (s: Strategy) => over[s.id] ?? s.state;
      return <div className="split"><div className="strategy-list">{rows.map(s => <article key={s.id} className={`strategy ${sel === s.id ? "sel" : ""}`}>
        <header><button className="linkish" onClick={() => setSel(s.id)} aria-pressed={sel === s.id}><h3>{s.name}</h3></button><Chip tone={st(s) === "Active" ? "ok" : st(s) === "Paused" ? "warn" : "mute"}>{st(s)}</Chip></header>
        <p className="muted">{s.markets.join(" · ")} · {s.timeframe}</p>
        <div className="stat-row tight"><Kpi label="Win rate" value={`${s.winRate}%`} /><Kpi label="P&L" value={money(s.pnl)} tone={s.pnl >= 0 ? "gain" : "loss"} /><Kpi label="Trades" value={String(s.trades)} /></div>
         <p className="muted"><Tx>{"Risk allocation "}</Tx>{s.risk}%</p><Meter pct={s.risk} label={`${s.name} risk allocation`} />
        <div className="row"><button className="button small" onClick={() => setSel(s.id)}><Tx>{"Details"}</Tx></button>
          <button className="button small" onClick={() => setOver(o => ({ ...o, [s.id]: st(s) === "Active" ? "Paused" : "Active" }))}>{st(s) === "Active" ? <><Pause size={12} aria-hidden /><Tx>{"Preview pause"}</Tx></> : <><Play size={12} aria-hidden /><Tx>{"Preview enable"}</Tx></>}</button></div></article>)}</div>
        <section className="panel" aria-live="polite">{cur ? <><h2>{cur.name}</h2><p><Tx>{cur.note}</Tx></p><KV rows={[["State", st(cur)], ["Markets", cur.markets.join(", ")], ["Timeframe", cur.timeframe], ["Last signal", cur.lastSignal], ["Updated", cur.updated], ["Configuration", "Read-only preview"]]} />
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
  return <><DemoBanner what="Synthetic series, scrubber only. No historical replay runs." /><Section title="Replay Lab">
     <PreviewChart values={replaySeries.slice(0, Math.max(2, Math.round((pos / 100) * replaySeries.length)))} label="Synthetic replay preview" unit="index" />
    <label className="field"><span><Tx>{"Position "}</Tx>{pos}%</span><input type="range" min={5} max={100} value={pos} onChange={e => setPos(Number(e.target.value))} /></label>
    <button className="button" disabled><Tx>{"Start isolated replay unavailable"}</Tx></button></Section></>;
}


