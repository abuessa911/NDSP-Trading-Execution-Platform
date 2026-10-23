"use client";

import { useEffect, useState } from "react";
import IdentityPanel from "./IdentityPanel";
import HunterControlPanel from "./HunterControlPanel";
import HunterEquityRiskPanel from "./HunterEquityRiskPanel";
import HunterTradingPreferencesPanel from "./HunterTradingPreferencesPanel";
import { Tx } from "../ndsp/ui";
import { useI18n } from "../ndsp/i18n";

const storageKey = "nex-display-preferences";
const zones = ["UTC", "Asia/Riyadh", "Europe/London", "America/New_York", "Asia/Tokyo"];
const locales = ["en-US", "ar-SA"];

export default function SettingsPanel() {
  const { t } = useI18n();
  const [locale, setLocale] = useState("en-US");
  const [zone, setZone] = useState("UTC");
  const [message, setMessage] = useState("");
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) ?? "null");
      if (saved && locales.includes(saved.locale) && zones.includes(saved.zone)) {
        setLocale(saved.locale);
        setZone(saved.zone);
      }
    } catch { setMessage("Saved display preferences could not be loaded."); }
  }, []);

  function save(event: React.FormEvent) {
    event.preventDefault();
    try {
      localStorage.setItem(storageKey, JSON.stringify({ locale, zone }));
      setNow(new Date());
      setMessage("Display preferences saved on this browser.");
    } catch { setMessage("Display preferences could not be saved. Browser storage may be disabled."); }
  }

  return <>
    <IdentityPanel />
    <HunterControlPanel />
    <HunterTradingPreferencesPanel />
    <HunterEquityRiskPanel />
    <section className="panel">
      <h2><Tx>{"Display preferences"}</Tx></h2>
      <p className="muted"><Tx>{"Local to this browser, not synchronized to your account. Server records remain UTC. These preferences never alter authentication, roles, permissions or trading configuration."}</Tx></p>
      <form onSubmit={save}>
        <div className="toolbar">
          <label className="field"><Tx>{"Display locale"}</Tx><select value={locale} onChange={e => setLocale(e.target.value)}>
            <option value="en-US"><Tx>{"English date formatting"}</Tx></option><option value="ar-SA"><Tx>{"Arabic date formatting"}</Tx></option>
          </select></label>
          <label className="field"><Tx>{"Display timezone"}</Tx><select value={zone} onChange={e => setZone(e.target.value)}>
            {zones.map(value => <option key={value} value={value}>{value}</option>)}
          </select></label>
        </div>
        <p>{t("Current time preview")}: <time dateTime={now?.toISOString()}>{now ? new Intl.DateTimeFormat(locale, { timeZone: zone, dateStyle: "medium", timeStyle: "long" }).format(now) : "Loading…"}</time></p>
        <button className="button" type="submit"><Tx>{"Save display preferences"}</Tx></button>
        <p role="status" className="muted">{t(message)}</p>
      </form>
    </section>
    <section className="panel">
      <h2><Tx>{"Session security"}</Tx></h2>
      <p><Tx>{"The configured provider handles sign-in. NAWAF owns the opaque server-side session; cookies are Secure and HttpOnly, and session actions require CSRF protection. Provider tokens are never stored in this browser."}</Tx></p>
      <p className="notice"><Tx>{"Administrative MFA is unverified. No local security setting can grant administrative access. No password or MFA settings are implemented here."}</Tx></p>
    </section>
  </>;
}