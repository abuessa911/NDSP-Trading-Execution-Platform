import Link from "next/link";
import HealthPanel from "./HealthPanel";
import IdentityPanel from "./IdentityPanel";
import DemoDashboard from "../ndsp/DemoDashboard";

const baseline = [
  ["TRADING_MODE", "paper"], ["LIVE_TRADING_ENABLED", "false"],
  ["GLOBAL_KILL_SWITCH", "true"], ["BINANCE_ALLOW_WITHDRAW", "false"],
];

export default function CommandCenter() {
  return <>
    <section className="panel">
      <h2>M1 foundation — acceptance pending</h2>
      <p className="notice">M1 NOT ACCEPTED. Administrator password + TOTP was verified against the isolated test provider; production/provider readiness and other independent assurance gates remain open. M2 is not authorized.</p>
      <p className="muted">NAWAF has its own repository, database, authentication and audit boundary. It does not access or modify NDSP. No trading, exchange credentials or execution engine is present.</p>
    </section>
    <DemoDashboard />
    <div className="row"><h2>Real M1 foundation</h2><span className="tag">REAL API DATA · NOT A DEMO</span></div>
    <div className="panel-grid"><HealthPanel /><IdentityPanel /></div>
    <section className="panel">
      <h2>Required M1 safety baseline</h2>
      <dl className="kv-list">{baseline.map(([name, value]) =>
        <div className="kv-row" key={name}><dt className="mono">{name}</dt><dd className="mono">{value}</dd></div>)}</dl>
      <p className="muted">Required configuration enforced by API startup validation. This is the documented baseline, not a live configuration reading or an editable control.</p>
    </section>
    <section className="panel">
      <h2>Unavailable beyond M1</h2>
      <p>Real trading, NDSP access, Binance access and execution require separately approved milestones. Financial values in the UI-preview section are synthetic; they do not represent a connected account or live activity.</p>
      <div className="row"><Link className="button" href="/settings/">Account settings</Link><Link className="button" href="/subscription/">Entitlements</Link><Link className="button" href="/admin/">Admin access status</Link></div>
    </section>
  </>;
}