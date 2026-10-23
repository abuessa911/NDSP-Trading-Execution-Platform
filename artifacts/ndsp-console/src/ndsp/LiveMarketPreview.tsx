"use client";
import { useEffect, useState } from "react";
import { useI18n } from "./i18n";
import { useTradingWorkspace } from "../components/TradingWorkspace";

type Candle = {
  openTimeMs: number; closeTimeMs: number; open: number;
  high: number; low: number; close: number; volume: number;
};
type Result = {
  status: "READ_ONLY_OK"; contract: "HUNTER_CLOSED_CANDLES_PREVIEW_V1";
  source: "BINANCE_PUBLIC_REST"; market: string; symbol: string; interval: string;
  serverTimeMs: number; candles: Candle[]; execution_authorized: false; orders_sent: 0;
};
const intervalMs: Record<string, number> = {
  "5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000,
};
const fmt = (value: number) => value.toLocaleString("en-US", { maximumFractionDigits: 8 });

export default function LiveMarketPreview() {
  const { lang } = useI18n();
  const t = (ar: string, en: string) => lang === "ar" ? ar : en;
  const { workspace, busy } = useTradingWorkspace();
  const [revision, setRevision] = useState(0);
  const [data, setData] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let canceled = false;
    const abort = new AbortController();
    const deadline = setTimeout(() => abort.abort(), 10_000);
    setData(null);
    setError("");
    if (!workspace || busy) { setLoading(false); clearTimeout(deadline); return () => abort.abort(); }
    setLoading(true);
    const { symbol, interval } = workspace;
    void (async () => {
      try {
        // Selection belongs to the authenticated backend, not query parameters.
        const response = await fetch("/api/v1/trading/profile/workspace/candles", {
          cache: "no-store", credentials: "same-origin", signal: abort.signal,
        });
        if (!response.ok) throw new Error("MARKET_UNAVAILABLE");
        const raw: unknown = await response.json();
        if (!raw || typeof raw !== "object") throw new Error("MARKET_RESPONSE_NOT_OBJECT");
        const d = raw as Partial<Result>;
        const candles = Array.isArray(d.candles) ? d.candles.map(c => ({
          ...c, open: Number(c.open), high: Number(c.high), low: Number(c.low),
          close: Number(c.close), volume: Number(c.volume),
        })) : [];
        const last = candles.at(-1);
        const span = intervalMs[interval];
        if (d.status !== "READ_ONLY_OK" || d.contract !== "HUNTER_CLOSED_CANDLES_PREVIEW_V1"
            || d.source !== "BINANCE_PUBLIC_REST" || d.market !== "usdm_futures"
            || d.symbol !== symbol || d.interval !== interval
            || d.orders_sent !== 0 || d.execution_authorized !== false
            || !Number.isSafeInteger(d.serverTimeMs) || !d.serverTimeMs
            || Math.abs(Date.now() - d.serverTimeMs) > 180_000
            || !candles.length || !candles.every((c, i) =>
              Number.isSafeInteger(c.openTimeMs) && Number.isSafeInteger(c.closeTimeMs)
              && c.openTimeMs % span === 0 && c.closeTimeMs === c.openTimeMs + span - 1
              && c.closeTimeMs < d.serverTimeMs!
              && (i === 0 || c.openTimeMs === candles[i - 1].openTimeMs + span)
              && Number.isFinite(c.open) && c.open > 0
              && Number.isFinite(c.high) && c.high > 0 && Number.isFinite(c.low) && c.low > 0
              && Number.isFinite(c.close) && c.close > 0
              && Number.isFinite(c.volume) && c.volume >= 0
              && c.low <= Math.min(c.open, c.close) && c.high >= Math.max(c.open, c.close))
            || !last || d.serverTimeMs - last.closeTimeMs > 2 * span + 1) {
          throw new Error("MARKET_SOURCE_NOT_VERIFIED");
        }
        if (!canceled) setData({ ...d, candles } as Result);
      } catch {
        if (!canceled) setError(t("تعذر التحقق من بيانات السوق. أعد المحاولة.", "Market data verification failed. Retry."));
      } finally { clearTimeout(deadline); if (!canceled) setLoading(false); }
    })();
    return () => { canceled = true; abort.abort(); clearTimeout(deadline); };
  }, [workspace, busy, revision, lang]);

  const matches = !busy && workspace && data?.symbol === workspace.symbol && data?.interval === workspace.interval;
  const last = matches ? data?.candles.at(-1) : null;
  return <section className="panel" aria-label="Verified closed Binance candles">
    <div className="row"><h2>{t("مخرجات السوق الموثقة", "Verified market output")}</h2>
      <button type="button" className="button" disabled={loading || busy || !workspace} onClick={() => setRevision(n => n + 1)}>
        {loading ? t("جار التحديث...", "Loading…") : t("تحديث المخرجات", "Refresh output")}
      </button>
    </div>
    <p className="muted">{workspace ? `${workspace.symbol} · ${workspace.interval} · Binance USD-M` : t("سجّل الدخول وحمّل إعدادات الخادم.", "Sign in and load server settings.")}</p>
    {loading && <p role="status">{t("جار جلب الشموع المغلقة...", "Loading closed candles…")}</p>}
    {error && <p role="alert" className="notice">{error}</p>}
    {last && data && <div aria-live="polite">
      <p>{t("آخر شمعة مغلقة", "Last closed candle")}: {new Date(last.closeTimeMs).toLocaleString(lang === "ar" ? "ar-SA" : "en-US")}</p>
      <div className="row" style={{ gap: 12, flexWrap: "wrap" }}>
        <strong>{t("الإغلاق", "Close")}: {fmt(last.close)} USDT</strong>
        <span>{t("أعلى", "High")}: {fmt(last.high)}</span>
        <span>{t("أدنى", "Low")}: {fmt(last.low)}</span>
        <span>{t("الحجم", "Volume")}: {fmt(last.volume)}</span>
      </div>
    </div>}
    <p className="muted">{t("لا أوامر تداول؛ هذه شموع سوق حقيقية مرتبطة باختيار الخادم.", "No trading orders; real market candles follow the server selection.")}</p>
  </section>;
}
