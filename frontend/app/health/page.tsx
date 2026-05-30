"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function HealthPage() {
const [health, setHealth] = useState<any>(null);
  const [message, setMessage] = useState("");

  async function loadHealth() {
    setMessage("");
    try {
      const data = await api("/system/health");
      setHealth(data);
    } catch (e: any) {
      setMessage("فشل تحميل صحة النظام: " + e.message);
    }
  }

  useEffect(() => {
    loadHealth();
  }, []);

  function statusBadge(ok: boolean, label: string) {
    return (
      <span className={ok ? "health-badge ok" : "health-badge bad"}>
        {ok ? "✅" : "❌"} {label}
      </span>
    );
  }

  return (
    <main className="container">
      <div className="card">
        <h1>Health Monitor</h1>
        <p>مراقبة حالة النظام والخدمات الأساسية.</p>

        {message && <div className="card">{message}</div>}

        {health && (
          <div className="health-grid">
            <div className="health-box">
              <h3>API</h3>
              {statusBadge(health.api === "ok", health.api)}
            </div>

            <div className="health-box">
              <h3>Database</h3>
              {statusBadge(health.database === "ok", health.database)}
            </div>

            <div className="health-box">
              <h3>Telegram</h3>
              {statusBadge(health.telegram_configured, health.telegram_configured ? "Configured" : "Missing")}
            </div>

            <div className="health-box">
              <h3>Email</h3>
              {statusBadge(health.email_configured, health.email_configured ? "Configured" : "Missing")}
            </div>

            <div className="health-box">
              <h3>Binance Mode</h3>
              <span className="health-badge mode">{health.binance_mode}</span>
            </div>

            <div className="health-box">
              <h3>Docker</h3>
              {statusBadge(health.docker_status === "ok", health.docker_status)}
            </div>

            <div className="health-box">
              <h3>Current User</h3>
              <p>{health.user?.email}</p>
              <p>Admin: {String(health.user?.is_admin)}</p>
              <p>Binance: {String(health.user?.binance_key_configured)}</p>
            </div>
          </div>
        )}

        <button className="btn btn-secondary" onClick={loadHealth}>{"تحديث"}</button>

        <p style={{ marginTop: 22 }}>
          <a href="/">{"العودة للوحة التحكم"}</a>
        </p>
      </div>
    </main>
  );
}
