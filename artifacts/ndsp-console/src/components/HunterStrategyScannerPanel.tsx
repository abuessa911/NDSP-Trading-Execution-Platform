"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "./AuthProvider";
import { useI18n } from "../ndsp/i18n";
import { useTradingWorkspace } from "./TradingWorkspace";

type ScannerStatus = {
  id: string;
  name: string;
  rule: string;
  symbol: string;
  interval: string;
  status: "STOPPED" | "SCANNING" | "STALLED";
  signal: "LONG_CANDIDATE" | "SHORT_CANDIDATE" | "NEUTRAL" | null;
  last_closed_price: string | null;
  last_candle_closed_ms: number | null;
  last_checked_ms: number | null;
  expires_in_seconds: number;
  market_source: "BINANCE_USDM_PUBLIC_CLOSED_CANDLES";
  ndsp_verified: false;
  execution_enabled: false;
};
type ScannerList = { strategies: ScannerStatus[]; order_submission_available: false };
type BotSelection = { powered: boolean; selected_strategy_id: string | null; live_orders_enabled: false };

const ENDPOINT = "/api/v1/trading/strategies";

async function result<T>(response: Response): Promise<T> {
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const code = data && typeof data === "object" && "reason_code" in data &&
      typeof data.reason_code === "string" ? data.reason_code : `HTTP_${response.status}`;
    throw new Error(code);
  }
  return data as T;
}

/** Authenticated, per-user, server-backed closed-candle scanner. NO orders. */
export default function HunterStrategyScannerPanel() {
  const { lang, t } = useI18n();
  const ar = lang === "ar";
  const { state: auth, identity, administratorMfaVerified, getCsrfToken, revalidate } = useAuth();
  const { workspace } = useTradingWorkspace();
  const canChoose = auth === "authenticated" && administratorMfaVerified &&
    ["ADMIN", "SUPER_ADMIN"].includes(identity?.role ?? "");
  const generation = useRef(0);
  const [strategies, setStrategies] = useState<ScannerStatus[]>([]);
  const [bot, setBot] = useState<BotSelection | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(async () => {
    const current = ++generation.current;
    if (auth !== "authenticated") {
      setStrategies([]); setBot(null); setLoaded(false); return;
    }
    try {
      const [strategiesReply, botReply] = await Promise.all([
        fetch(ENDPOINT, { credentials: "same-origin", cache: "no-store" }),
        fetch("/api/v1/trading/bot", { credentials: "same-origin", cache: "no-store" }),
      ]);
      if (strategiesReply.status === 401 || botReply.status === 401) {
        void revalidate();
        throw new Error("SESSION_REVOKED");
      }
      const [data, selection] = await Promise.all([
        result<ScannerList>(strategiesReply), result<BotSelection>(botReply),
      ]);
      if (!Array.isArray(data.strategies) || data.order_submission_available !== false ||
          typeof selection.powered !== "boolean" ||
          selection.live_orders_enabled !== false ||
          !(selection.selected_strategy_id === null || typeof selection.selected_strategy_id === "string")) {
        throw new Error("INVALID_STRATEGY_SELECTION_RESPONSE");
      }
      if (current !== generation.current) return;
      setStrategies(data.strategies);
      setBot(selection);
      setLoaded(true);
      setNotice("");
    } catch (error) {
      if (current !== generation.current) return;
      setStrategies([]); setBot(null); setLoaded(false);
      setNotice(error instanceof Error && error.message === "SESSION_REVOKED"
        ? (ar ? "انتهت جلسة الدخول؛ سجل الدخول مجددًا." : "Session expired; please sign in again.")
        : (ar ? "تعذر قراءة الاستراتيجيات من الخادم." : "Cannot read strategy selection."));
    }
  }, [auth, identity?.user_id, ar, workspace, revalidate]);

  useEffect(() => {
    setStrategies([]); setBot(null); setLoaded(false);
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30_000);
    return () => { generation.current++; window.clearInterval(timer); };
  }, [refresh]);

  async function choose(s: ScannerStatus) {
    const csrf = getCsrfToken();
    if (!canChoose || !csrf || busy) {
      setNotice(ar ? "اختيار الاستراتيجية يتطلب جلسة مدير موثقة." : "Administrator MFA session required.");
      return;
    }
    setBusy(s.id);
    setNotice("");
    try {
      const reply = await fetch(`/api/v1/trading/bot/strategy/${encodeURIComponent(s.id)}/select`, {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "X-NEX-CSRF": csrf },
      });
      if (reply.status === 401) {
        void revalidate();
        throw new Error("SESSION_REVOKED");
      }
      const selected = await result<BotSelection>(reply);
      if (selected.selected_strategy_id !== s.id || selected.live_orders_enabled !== false)
        throw new Error("STRATEGY_SELECTION_UNCONFIRMED");
      await refresh();
      setNotice(selected.powered
        ? (ar ? "تم اختيار الاستراتيجية وبدء متابعتها. لا تُرسل أوامر تداول." :
          "Strategy selected and monitored. No trading orders are submitted.")
        : (ar ? "تم حفظ الاستراتيجية المختارة. شغّل البوت من الزر الرئيسي لبدء متابعتها." :
          "Strategy selected. Use the main bot switch to begin monitoring."));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "STRATEGY_SELECTION_FAILED");
    } finally {
      setBusy(null);
    }
  }

  return <section className="panel" aria-label="Hunter strategy selection">
    <h2>{ar ? "اختيار الاستراتيجية" : "Choose a strategy"}</h2>
    <p className="notice">{ar
      ? "اختر استراتيجية واحدة لتكون المعتمدة لدى البوت. زر تشغيل/إيقاف البوت الرئيسي مستقل. المتابعة الحالية بحثية ولا تُرسل أوامر تداول حقيقية."
      : "Select one strategy for the bot. The main bot power button is independent. Monitoring remains research-only and never places live orders."}</p>
    {loaded && !bot?.powered && <p className="muted" role="status">{ar
      ? "البوت متوقف: اختر الاستراتيجية الآن، ثم شغّله من الزر الرئيسي."
      : "Bot is stopped: choose a strategy, then turn it on using the main button."}</p>}
    {!loaded && <p className="muted">{auth === "authenticated"
      ? (ar ? "تعذر تحميل اختيارات الاستراتيجيات." : "Strategy selection unavailable.")
      : (ar ? "سجّل الدخول لعرض الاختيارات." : "Sign in to choose a strategy.")}</p>}
    {loaded && <div className="strategy-list">{strategies.map(s => {
      const selected = bot?.selected_strategy_id === s.id;
      return <article className="strategy" key={s.id}>
        <header><h3>{t(s.name)}</h3><strong>{selected ? (ar ? "مختارة" : "Selected") : (ar ? "غير مختارة" : "Not selected")}</strong></header>
        <p className="muted">{t(s.rule)}</p>
        <p className="muted">{s.status === "STOPPED"
          ? (workspace ? `${workspace.symbol} · ${workspace.interval}` : "—")
          : `${s.symbol} · ${s.interval}`}</p>
        <p>{ar ? "إشارة بحثية" : "Research candidate"}: <strong>{ar ? (s.signal === "LONG_CANDIDATE" ? "مرشح شراء" : s.signal === "SHORT_CANDIDATE" ? "مرشح بيع" : s.signal === "NEUTRAL" ? "محايد" : "—") : s.signal ?? "—"}</strong></p>
        <p className="muted">{ar ? "إغلاق مؤكد" : "Verified close"}: {s.last_closed_price ?? "—"} · {ar ? "الانتهاء بعد" : "Expires in"} {s.expires_in_seconds}s</p>
        <div className="row">
          <button type="button" className="button small" disabled={!canChoose || selected || busy !== null}
            aria-pressed={selected} onClick={() => void choose(s)}>
            {busy === s.id ? (ar ? "جارٍ الاختيار…" : "Selecting…")
              : selected ? (ar ? "مختارة" : "Selected")
              : (ar ? "اختيار الاستراتيجية" : "Select strategy")}
          </button>
        </div>
      </article>;
    })}</div>}
    <p role="status" className="muted">{notice}</p>
    <p className="muted">{ar
      ? "المتابعة البحثية الحالية مدتها 15 دقيقة لكل تفعيل؛ يظل اختيارك محفوظًا عند إيقاف البوت. إشارات NDSP لا تُجيز تنفيذ الصفقات."
      : "Each research monitoring run lasts 15 minutes; the strategy choice survives power-off. NDSP signals do not authorize execution."}</p>
  </section>;
}
