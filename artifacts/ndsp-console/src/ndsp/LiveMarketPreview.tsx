"use client";
import { useState } from "react";

type Candle = { openTimeMs: number; closeTimeMs: number; open: number; high: number; low: number; close: number; volume: number };
type Result = {
  status: "READ_ONLY_OK"; contract: "HUNTER_CLOSED_CANDLES_PREVIEW_V1";
  source: "BINANCE_PUBLIC_REST"; market: string; symbol: string; interval: string;
  serverTimeMs: number; candles: Candle[]; execution_authorized: false; orders_sent: 0;
};

const choices = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "APTUSDT"] as const;

export default function LiveMarketPreview() {
  const [market, setMarket] = useState("spot");
  const [symbol, setSymbol] = useState<string>("BTCUSDT");
  const [interval, setInterval] = useState("5m");
  const [data, setData] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function refresh() {
    if (loading) return;
    setLoading(true);
    setData(null);
    setError("");
    try {
      const params = new URLSearchParams({ market, symbol, interval });
      const response = await fetch("/preview/market/closed-candles?" + params.toString(), {
        // The entire bot is protected with same-origin HTTP Basic authentication.
        // "omit" drops the browser's login from this fetch and causes HTTP 401.
        cache: "no-store", credentials: "same-origin", signal: AbortSignal.timeout(10000),
      });
      if (!response.ok) throw new Error("خدمة الشموع الحقيقية غير متاحة.");
      const raw: unknown = await response.json();
      if (!raw || typeof raw !== "object") throw new Error("استجابة غير صالحة.");
      const d = raw as Partial<Result>;
      if (d.status !== "READ_ONLY_OK" || d.contract !== "HUNTER_CLOSED_CANDLES_PREVIEW_V1"
          || d.source !== "BINANCE_PUBLIC_REST" || d.market !== market
          || d.symbol !== symbol || d.interval !== interval
          || d.orders_sent !== 0 || d.execution_authorized !== false
          || !Array.isArray(d.candles) || !d.candles.length
          || !d.candles.every(c => Number.isFinite(c.close) && c.close > 0
                                 && Number.isSafeInteger(c.closeTimeMs))) {
        throw new Error("بيانات أو هوية المصدر غير موثوقة.");
      }
      setData(d as Result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "تعذر الحصول على بيانات السوق.");
    } finally {
      setLoading(false);
    }
  }
  const last = data?.candles.at(-1);
  return <section className="panel" aria-label="Real public Binance CLOSED candles read-only">
    <h2>Binance — شموع السوق المغلقة (قراءة فقط)</h2>
    <p className="muted">بيانات عامة حقيقية، لا مفاتيح ولا أوامر تداول. لا تُستخدم هذه القراءة لإصدار توصية أو تنفيذ صفقة.</p>
    <div className="row" style={{ flexWrap: "wrap", gap: 12 }}>
      <label className="field">السوق
        <select value={market} onChange={e => { setMarket(e.target.value); setData(null); }}>
          <option value="spot">فوري</option><option value="usdm_futures">عقود USD-M — بيانات فقط</option>
        </select>
      </label>
      <label className="field">الرمز
        <select value={symbol} onChange={e => { setSymbol(e.target.value); setData(null); }}>
          {choices.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </label>
      <label className="field">الفاصل
        <select value={interval} onChange={e => { setInterval(e.target.value); setData(null); }}>
          <option value="5m">5m</option><option value="15m">15m</option>
        </select>
      </label>
      <button type="button" className="button" disabled={loading} onClick={refresh}>
        {loading ? "جارٍ التحقق..." : "جلب آخر الشموع المغلقة"}
      </button>
    </div>
    {error && <p role="alert" className="notice">{error} لن نعرض بيانات قديمة كأنها حية.</p>}
    {last && data && <div aria-live="polite">
      <p className="muted">آخر إغلاق: {new Date(last.closeTimeMs).toLocaleString("ar-SA")} — Binance public REST.</p>
      <div className="row">
        <strong>الإغلاق: {last.close.toLocaleString("en-US", { maximumFractionDigits: 8 })} USDT</strong>
        <span>أعلى: {last.high.toLocaleString("en-US")}</span>
        <span>أدنى: {last.low.toLocaleString("en-US")}</span>
      </div>
      <p className="muted">لا أوامر تداول ولا رصيد مرتبط. الجدول التجريبي أدناه منفصل تمامًا عن هذه البيانات الحقيقية.</p>
    </div>}
  </section>;
}
