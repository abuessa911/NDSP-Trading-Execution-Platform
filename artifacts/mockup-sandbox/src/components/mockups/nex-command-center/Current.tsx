import { Activity, ChevronRight, LockKeyhole, Menu, Shield } from "lucide-react";
import "./_group.css";

const userPages = [
  { title: "Command Center", href: "/", active: true },
  { title: "Trading", href: "/trading/", milestone: "LATER" },
  { title: "Strategies", href: "/strategies/", milestone: "LATER" },
  { title: "Positions", href: "/positions/", milestone: "LATER" },
  { title: "Orders", href: "/orders/", milestone: "LATER" },
  { title: "Trade History", href: "/trade-history/", milestone: "LATER" },
  { title: "Performance", href: "/performance/", milestone: "LATER" },
  { title: "Risk Center", href: "/risk-center/", milestone: "LATER" },
  { title: "NDSP Decisions", href: "/ndsp-decisions/", milestone: "LATER" },
  { title: "Execution Trace / Why?", href: "/execution-trace/", milestone: "LATER" },
  { title: "Replay Lab", href: "/replay-lab/", milestone: "LATER" },
  { title: "Binance Connection", href: "/binance-connection/", milestone: "LATER" },
  { title: "Notifications", href: "/notifications/", milestone: "LATER" },
  { title: "Subscription", href: "/subscription/" },
  { title: "Settings", href: "/settings/" },
  { title: "Service Health", href: "/health/" },
  { title: "Audit Access", href: "/audit/" },
];

const adminPages = [
  "Operations Center",
  "Users / Tenants",
  "Subscriptions",
  "Trading Safety",
  "Exchange Health",
  "NDSP Health",
  "Audit",
  "Notifications",
  "Workers / Queues",
  "Incidents",
];

const baseline = [
  ["TRADING_MODE", "paper"],
  ["LIVE_TRADING_ENABLED", "false"],
  ["GLOBAL_KILL_SWITCH", "true"],
  ["BINANCE_ALLOW_WITHDRAW", "false"],
];

function InertLink({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <a className={className} href="#" onClick={(event) => event.preventDefault()}>{children}</a>;
}

export function Current() {
  return (
    <div className="nex-command-center">
      <div className="console-shell">
        <a className="skip-link" href="#console-content">Skip to content</a>
        <aside className="console-nav" id="console-navigation" aria-label="Console navigation">
          <InertLink className="brand">
            <span className="brand-mark">N</span>
            <span><strong>NEX</strong><small>CONTROL CONSOLE</small></span>
          </InertLink>
          <div className="nav-scope"><span className="scope-dot" /> M1 FOUNDATION <span className="mono">01</span></div>
          <nav aria-label="User pages">
            <p className="nav-label">USER CONSOLE</p>
            {userPages.map((page) => <InertLink key={page.title} className={`nav-link ${page.active ? "active" : ""}`}>
              <span>{page.title}</span>
              {page.milestone ? <span className="nav-hint">{page.milestone}</span> : page.title === "Audit Access" ? <LockKeyhole size={13} aria-hidden /> : <ChevronRight size={13} aria-hidden />}
            </InertLink>)}
          </nav>
          <nav aria-label="Administrative pages">
            <details className="admin-navigation">
              <summary><LockKeyhole size={14} aria-hidden /> ADMIN · MFA GUARDED</summary>
              <InertLink className="nav-link">Access status</InertLink>
              {adminPages.map((page) => <InertLink key={page} className="nav-link">{page}<LockKeyhole size={12} aria-hidden /></InertLink>)}
            </details>
          </nav>
          <div className="nav-footer"><Shield size={17} aria-hidden /><p>Independent from NDSP.<br />No exchange or trading access.</p></div>
        </aside>
        <div className="console-workspace">
          <header className="console-top">
            <div className="row">
              <button className="button nav-toggle" type="button" aria-label="Open navigation" aria-expanded="false" aria-controls="console-navigation"><Menu size={18} /></button>
              <span className="top-label"><Activity size={15} aria-hidden /> NEX / FOUNDATION</span>
            </div>
            <span className="acceptance-label"><span className="acceptance-dot" /> M1 NOT ACCEPTED</span>
          </header>
          <main className="console-main" id="console-content" tabIndex={-1}>
            <section aria-label="M1 authentication" className="panel">
              <div className="row">
                <div>
                  <h2>M1 authentication</h2>
                  <p role="status" className="muted">Display-only baseline — authentication service is not connected in this preview.</p>
                </div>
                <div className="row">
                  <button className="button" type="button">Sign in</button>
                  <button className="button" type="button">Administrator MFA sign in</button>
                  <button className="button" type="button">Check session</button>
                </div>
              </div>
              <p className="muted">Administrator access requires fresh, server-verified password + TOTP MFA.</p>
            </section>
            <div className="page-frame">
              <header className="page-heading">
                <p className="eyebrow">NEX CONTROL PLANE</p>
                <h1>Command Center</h1>
                <p className="muted">Identity, service health and M1 safety boundaries.</p>
              </header>
              <div className="page-content">
                <section className="panel">
                  <h2>M1 foundation — acceptance pending</h2>
                  <p className="notice">M1 NOT ACCEPTED. Administrator password + TOTP was verified against the isolated test provider; production/provider readiness and other independent assurance gates remain open. M2 is not authorized.</p>
                  <p className="muted">NEX has its own repository, database, authentication and audit boundary. It does not access or modify NDSP. No trading, exchange credentials or execution engine is present.</p>
                </section>
                <div className="panel-grid">
                  <section className="panel">
                    <div className="row"><h2>Control API health</h2><button className="button" type="button">Refresh health</button></div>
                    <p className="muted" role="status">Display-only baseline — API health has not been queried.</p>
                    <dl className="kv-list">
                      <div className="kv-row"><dt>Liveness</dt><dd>Not queried</dd></div>
                      <div className="kv-row"><dt>Readiness</dt><dd>Not queried</dd></div>
                    </dl>
                    <p className="muted">Public, user-safe health only. Liveness does not prove readiness or M1 acceptance. No exchange, NDSP or worker health is inferred.</p>
                  </section>
                  <section className="panel">
                    <h2>Protected account information</h2>
                    <p className="muted">An active, provisioned application session is required. Account and tenant information are not available while signed out.</p>
                  </section>
                </div>
                <section className="panel">
                  <h2>Required M1 safety baseline</h2>
                  <dl className="kv-list">{baseline.map(([name, value]) =>
                    <div className="kv-row" key={name}><dt className="mono">{name}</dt><dd className="mono">{value}</dd></div>)}</dl>
                  <p className="muted">Required configuration enforced by API startup validation. This is the documented baseline, not a live configuration reading or an editable control.</p>
                </section>
                <section className="panel">
                  <h2>Unavailable beyond M1</h2>
                  <p>Account/NDSP/Binance/risk status, active positions, daily P&amp;L and trading alerts require later milestones. No values are fabricated or displayed as zero.</p>
                  <div className="row">
                    <InertLink className="button">Account settings</InertLink>
                    <InertLink className="button">Entitlements</InertLink>
                    <InertLink className="button">Admin access status</InertLink>
                  </div>
                </section>
              </div>
            </div>
            <footer className="console-footer">NEX MASTER SPEC V1 · M1 only · Later milestones require separate authorization.</footer>
          </main>
        </div>
      </div>
    </div>
  );
}

export default Current;
