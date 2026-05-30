"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function RiskPage() {
const [summary, setSummary] = useState<any>(null);
  const [message, setMessage] = useState("");

  async function loadSummary() {
    try {
      const data = await api("/risk/summary");
      setSummary(data);
    } catch (e: any) {
      setMessage("فشل تحميل المخاطر: " + e.message);
    }
  }

  useEffect(() => {
    loadSummary();
  }, []);

  return (
    <main className="container">
      <div className="card">
        <h1>Risk Center</h1>
        <p>ملخص إدارة المخاطر اليومية.</p>

        {message && <p>{message}</p>}

        {summary && (
          <div className="grid grid-2">
            <div className="card">
              <h3>Daily PnL</h3>
              <strong style={{ fontSize: 34 }}>{summary.daily_pnl_usdt} USDT</strong>
            </div>
            <div className="card">
              <h3>Max Daily Loss</h3>
              <strong>{summary.max_daily_loss_usdt} USDT</strong>
            </div>
            <div className="card">
              <h3>Stop Loss</h3>
              <strong>{summary.stop_loss_pct}%</strong>
            </div>
            <div className="card">
              <h3>Take Profit</h3>
              <strong>{summary.take_profit_pct}%</strong>
            </div>
            <div className="card">
              <h3>Prevent Duplicate</h3>
              <strong>{String(summary.prevent_duplicate_positions)}</strong>
            </div>
            <div className="card">
              <h3>Live Safety</h3>
              <strong>{String(summary.live_safety_confirmed)}</strong>
            </div>
          </div>
        )}

        <button className="btn btn-secondary" onClick={loadSummary}>{"تحديث"}</button>

        <p style={{ marginTop: 22 }}>
          <a href="/">{"العودة للوحة التحكم"}</a>
        </p>
      </div>
    </main>
  );
}
