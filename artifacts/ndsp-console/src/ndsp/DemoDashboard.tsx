"use client";
import Link from "../components/DocumentLink";
import { dashboardService } from "./services";
import { Tx, Async, Chip, DemoBanner, Kpi, Meter, money, Pnl, Section, useDemo } from "./ui";

export default function DemoDashboard() {
  const q = useDemo(dashboardService.snapshot);
  return <div className="page-content"><DemoBanner what="Trading command-center concept. Every financial value, strategy, signal and activity record in this section is synthetic." />
    <Async q={q}>{data => <>
      <div className="kpi-grid"><Kpi label="Balance" value={money(data.account.balance)} sub="Illustrative account" /><Kpi label="Available" value={money(data.account.available)} /><Kpi label="Margin used" value={money(data.account.margin)} /><Kpi label="Unrealized P&L" value={money(data.account.unrealized)} tone="gain" /><Kpi label="Realized P&L" value={money(data.account.realized)} tone="gain" /><Kpi label="Daily P&L" value={money(data.account.daily)} tone="gain" /><Kpi label="Weekly P&L" value={money(data.account.weekly)} tone="gain" /></div>
      <div className="preview-grid"><Section title="Market pulse" aside={<Link className="button small" href="/markets/"><Tx>{"Explore demo markets"}</Tx></Link>}><ul className="signal-list">{data.markets.slice(0, 4).map(market => <li key={market.id}><div className="row"><strong>{market.symbol}</strong><span className="mono">{money(market.price)}</span><Pnl v={market.change24h} money={false} /><Chip tone="info"><Tx>{market.signal}</Tx><Tx>{" · DEMO"}</Tx></Chip></div></li>)}</ul></Section>
        <Section title="Risk attention"><div className="row"><strong><Tx>{"Daily loss capacity used"}</Tx></strong><strong className="warn">{data.risk.utilization}%</strong></div><Meter pct={data.risk.utilization} label="Demo risk utilization" /><p className="notice"><Tx>{data.risk.warnings.join(" · ")}</Tx></p><Link className="button" href="/risk-center/"><Tx>{"Inspect risk preview"}</Tx></Link></Section></div>
      <Section title="Illustrative activity stream"><ol className="timeline-list">{data.signals.slice(0, 4).map(signal => <li key={signal.id}><span className="mono">{signal.time}</span><strong>{signal.symbol}</strong><Chip tone={signal.stage === "Blocked" ? "bad" : "info"}><Tx>{signal.stage}</Tx></Chip><span><Tx>{signal.action}</Tx></span></li>)}</ol><Link className="button" href="/ndsp-decisions/"><Tx>{"Inspect signal lifecycle"}</Tx></Link></Section>
    </>}</Async>
  </div>;
}
