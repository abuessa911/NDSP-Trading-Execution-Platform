"use client";

import { useState } from "react";
import { api } from "../../lib/api";

export default function NdspSignalPage() {
  const [form, setForm] = useState({
    symbol: "BTC/USDT",
    side: "BUY",
    notional_usdt: 10,
    reason: "NDSP real signal",
    ndsp_layer: "layer-1"
  });

  const [webhookForm, setWebhookForm] = useState({
    user_email: "nawaf@example.com",
    symbol: "BTC/USDT",
    side: "BUY",
    notional_usdt: 10,
    reason: "NDSP webhook test signal",
    ndsp_layer: "layer-1",
    signal_id: "test-signal-001"
  });

  const [message, setMessage] = useState("");

  async function sendSignal() {
    setMessage("");
    try {
      const data = await api("/ndsp/signal", {
        method: "POST",
        body: JSON.stringify(form)
      });
      setMessage(`تم تنفيذ إشارة NDSP: ${data.symbol} ${data.side} ${data.status}`);
    } catch (e: any) {
      setMessage("فشل تنفيذ إشارة NDSP: " + e.message);
    }
  }

  return (
    <main className="container">
      <div className="card">
        <h1>NDSP Signal Bridge</h1>
        <p>هذه الصفحة لاختبار استقبال إشارات NDSP، أما الربط الحقيقي فيكون عبر Webhook آمن.</p>

        <div className="card">
          <h2>اختبار داخلي عبر جلسة المستخدم</h2>

          <label>Symbol</label>
          <input className="input" value={form.symbol} onChange={e => setForm({ ...form, symbol: e.target.value })} />

          <label style={{ display: "block", marginTop: 14 }}>Side</label>
          <select className="input" value={form.side} onChange={e => setForm({ ...form, side: e.target.value })}>
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>

          <label style={{ display: "block", marginTop: 14 }}>Notional USDT</label>
          <input className="input" type="number" value={form.notional_usdt} onChange={e => setForm({ ...form, notional_usdt: Number(e.target.value) })} />

          <label style={{ display: "block", marginTop: 14 }}>NDSP Layer</label>
          <input className="input" value={form.ndsp_layer} onChange={e => setForm({ ...form, ndsp_layer: e.target.value })} />

          <label style={{ display: "block", marginTop: 14 }}>Reason</label>
          <input className="input" value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} />

          <button className="btn btn-primary" style={{ marginTop: 18 }} onClick={sendSignal}>
            إرسال إشارة NDSP داخلية
          </button>
        </div>

        <div className="card">
          <h2>Webhook الحقيقي للربط مع NDSP</h2>

          <p>الرابط:</p>
          <pre style={{ whiteSpace: "pre-wrap" }}>POST https://bot.ndsp.app/api/webhooks/ndsp-signal</pre>

          <p>الهيدر المطلوب:</p>
          <pre style={{ whiteSpace: "pre-wrap" }}>X-NDSP-SECRET: القيمة الموجودة في .env</pre>

          <p>مثال Body:</p>
          <pre style={{ whiteSpace: "pre-wrap", direction: "ltr", textAlign: "left" }}>
{JSON.stringify(webhookForm, null, 2)}
          </pre>

          <p style={{ color: "#fbbf24" }}>
            لا تعرض NDSP_WEBHOOK_SECRET داخل الواجهة. يتم حفظه فقط في ملف .env على السيرفر.
          </p>
        </div>

        {message && <div className="card">{message}</div>}

        <p style={{ marginTop: 22 }}>
          <a href="/">العودة للوحة التحكم</a>
        </p>
      </div>
    </main>
  );
}
