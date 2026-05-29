"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function SafetyPage() {
  const [status, setStatus] = useState<any>(null);
  const [checklist, setChecklist] = useState<any>(null);
  const [confirmText, setConfirmText] = useState("");
  const [message, setMessage] = useState("");

  async function loadAll() {
    setMessage("");
    try {
      const s = await api("/live-safety/status");
      const c = await api("/live-safety/checklist");
      setStatus(s);
      setChecklist(c);
    } catch (e: any) {
      setMessage("فشل تحميل الحالة: " + e.message);
    }
  }

  async function confirm() {
    setMessage("");
    try {
      await api("/live-safety/confirm", {
        method: "POST",
        body: JSON.stringify({ confirm_text: confirmText })
      });
      setMessage("تم تأكيد مخاطر Live");
      await loadAll();
    } catch (e: any) {
      setMessage("فشل التأكيد: " + e.message);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  return (
    <main className="container">
      <div className="card">
        <h1>Live Safety Center</h1>

        <p style={{ color: "#fbbf24", lineHeight: 1.8 }}>
          هذه الصفحة تمنع تفعيل التداول الحقيقي قبل اكتمال شروط الأمان. لا تستخدم Live إلا بعد نجاح Testnet وإضافة مفاتيح Binance بدون صلاحية Withdraw.
        </p>

        <div className="card">
          <h2>الحالة العامة</h2>
          <span className={checklist?.all_ok ? "badge badge-green" : "badge badge-red"}>
            {checklist?.all_ok ? "جاهز مبدئيًا للـ Live" : "غير جاهز للـ Live"}
          </span>
        </div>

        <div className="card">
          <h2>Checklist</h2>

          <div className="live-checklist">
            {checklist?.checks?.map((item: any) => (
              <div className={item.ok ? "live-check ok" : "live-check bad"} key={item.key}>
                <span>{item.ok ? "✅" : "❌"}</span>
                <strong>{item.label}</strong>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2>تأكيد مخاطر Live</h2>

          <p>اكتب النص التالي حرفيًا:</p>
          <code>{checklist?.required_text || status?.required_text || "I UNDERSTAND LIVE RISK"}</code>

          <input
            className="input"
            style={{ marginTop: 14 }}
            value={confirmText}
            onChange={e => setConfirmText(e.target.value)}
            placeholder="I UNDERSTAND LIVE RISK"
          />

          <button className="btn btn-danger" style={{ marginTop: 18 }} onClick={confirm}>
            تأكيد مخاطر Live
          </button>
        </div>

        {message && <div className="card">{message}</div>}

        <button className="btn btn-secondary" onClick={loadAll}>تحديث</button>

        <p style={{ marginTop: 22 }}>
          <a href="/">العودة للوحة التحكم</a>
        </p>
      </div>
    </main>
  );
}
