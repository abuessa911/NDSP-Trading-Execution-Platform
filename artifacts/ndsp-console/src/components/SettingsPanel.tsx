"use client";

import { useEffect, useState } from "react";
import IdentityPanel from "./IdentityPanel";

const storageKey = "nex-display-preferences";
const zones = ["UTC", "Asia/Riyadh", "Europe/London", "America/New_York", "Asia/Tokyo"];
const locales = ["en-US", "ar-SA"];

export default function SettingsPanel() {
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
    <section className="panel">
      <h2>Display preferences</h2>
      <p className="muted">Local to this browser, not synchronized to your account. Server records remain UTC. These preferences never alter authentication, roles, permissions or trading configuration.</p>
      <form onSubmit={save}>
        <div className="toolbar">
          <label className="field">Display locale<select value={locale} onChange={e => setLocale(e.target.value)}>
            <option value="en-US">English date formatting</option><option value="ar-SA">Arabic date formatting</option>
          </select></label>
          <label className="field">Display timezone<select value={zone} onChange={e => setZone(e.target.value)}>
            {zones.map(value => <option key={value} value={value}>{value}</option>)}
          </select></label>
        </div>
        <p>Current time preview: <time dateTime={now?.toISOString()}>{now ? new Intl.DateTimeFormat(locale, { timeZone: zone, dateStyle: "medium", timeStyle: "long" }).format(now) : "Loading…"}</time></p>
        <button className="button" type="submit">Save display preferences</button>
        <p role="status" className="muted">{message}</p>
      </form>
    </section>
    <section className="panel">
      <h2>Session security</h2>
      <p>The configured provider handles sign-in. NAWAF owns the opaque server-side session; cookies are Secure and HttpOnly, and session actions require CSRF protection. Provider tokens are never stored in this browser.</p>
      <p className="notice">Administrative MFA is unverified. No local security setting can grant administrative access. No password or MFA settings are implemented here.</p>
    </section>
  </>;
}