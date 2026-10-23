"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useAuth } from "./AuthProvider";
import { useTradingWorkspace } from "./TradingWorkspace";
import { useI18n } from "../ndsp/i18n";

type Preferences = {
  venue: "BINANCE_USDM_FUTURES";
  capital_limit_usdt: string | null;
  trade_risk_pct: string | null;
  daily_loss_pct: string | null;
  leverage: number;
  symbol: string;
  interval: string;
  selected_strategy_id: string | null;
  configured: boolean;
  live_orders_enabled: false;
  execution_ready: false;
};
type Draft = { capital_limit_usdt: string; trade_risk_pct: string; daily_loss_pct: string };
const endpoint = "/api/v1/trading/bot/preferences";
const empty: Draft = { capital_limit_usdt: "", trade_risk_pct: "", daily_loss_pct: "" };

function valid(v: unknown): v is Preferences {
  if (!v || typeof v !== "object") return false;
  const p = v as Partial<Preferences>;
  return p.venue === "BINANCE_USDM_FUTURES" &&
    [p.capital_limit_usdt, p.trade_risk_pct, p.daily_loss_pct].every(x => x === null || typeof x === "string") &&
    typeof p.leverage === "number" && typeof p.symbol === "string" && typeof p.interval === "string" &&
    (p.selected_strategy_id === null || typeof p.selected_strategy_id === "string") &&
    typeof p.configured === "boolean" && p.live_orders_enabled === false && p.execution_ready === false;
}
function errorCode(data: unknown, status: number) {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = data.detail;
    if (detail && typeof detail === "object" && "reason_code" in detail &&
        typeof detail.reason_code === "string") return detail.reason_code;
  }
  return "HTTP_" + status;
}
export default function HunterTradingPreferencesPanel() {
  const { lang } = useI18n();
  const ar = lang === "ar";
  const { state: auth, identity, administratorMfaVerified, getCsrfToken, revalidate } = useAuth();
  const { workspace } = useTradingWorkspace();
  const role = identity?.role ?? "";
  const permitted = auth === "authenticated" && ["OPERATOR", "ADMIN", "SUPER_ADMIN"].includes(role) &&
    (role === "OPERATOR" || administratorMfaVerified);
  const [saved, setSaved] = useState<Preferences | null>(null);
  const [draft, setDraft] = useState<Draft>(empty);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const generation = useRef(0);
  useEffect(() => {
    const current = ++generation.current;
    setSaved(null);
    setDraft(empty);
    setMessage("");
    if (auth !== "authenticated") return;
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch(endpoint, {
          credentials: "same-origin", cache: "no-store", signal: controller.signal,
        });
        if (response.status === 401) { void revalidate(); throw Error("SESSION_REVOKED"); }
        const data: unknown = await response.json();
        if (!response.ok) throw Error(errorCode(data, response.status));
        if (!valid(data)) throw Error("PREFERENCES_RESPONSE_INVALID");
        if (generation.current !== current || controller.signal.aborted) return;
        setSaved(data);
        setDraft({
          capital_limit_usdt: data.capital_limit_usdt ?? "",
          trade_risk_pct: data.trade_risk_pct ?? "",
          daily_loss_pct: data.daily_loss_pct ?? "",
        });
      } catch (error) {
        if (generation.current === current && !controller.signal.aborted)
          setMessage(error instanceof Error ? error.message : "PREFERENCES_UNAVAILABLE");
      }
    })();
    return () => { generation.current++; controller.abort(); };
  }, [auth, identity?.user_id, revalidate]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!permitted || busy || !saved) return;
    const csrf = getCsrfToken();
    if (!csrf) { setMessage("CSRF_TOKEN_REQUIRED"); return; }
    const cap = Number(draft.capital_limit_usdt);
    const trade = Number(draft.trade_risk_pct);
    const day = Number(draft.daily_loss_pct);
    const decimal = /^\d+(?:\.\d{1,4})?$/;
    if (!/^\d+(?:\.\d{1,2})?$/.test(draft.capital_limit_usdt) ||
        !decimal.test(draft.trade_risk_pct) || !decimal.test(draft.daily_loss_pct) ||
        !Number.isFinite(cap) || cap <= 0 || cap > 1_000_000_000 ||
        !Number.isFinite(trade) || !Number.isFinite(day) ||
        trade <= 0 || day <= 0 || day > 100 || trade > day) {
      setMessage(ar ? "راجع المبلغ وحدود الخسارة: مخاطرة الصفقة لا تتجاوز الحد اليومي." :
        "Check capital and risk: trade risk cannot exceed daily loss.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(endpoint, {
        method: "PUT", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json", "X-NEX-CSRF": csrf },
        body: JSON.stringify({ venue: "BINANCE_USDM_FUTURES", ...draft }),
      });
      if (response.status === 401) { void revalidate(); throw Error("SESSION_REVOKED"); }
      const data: unknown = await response.json();
      if (!response.ok) throw Error(errorCode(data, response.status));
      if (!valid(data) || !data.configured ||
          Number(data.capital_limit_usdt) !== cap ||
          Number(data.trade_risk_pct) !== trade ||
          Number(data.daily_loss_pct) !== day) throw Error("PREFERENCES_SAVE_UNCONFIRMED");
      setSaved(data);
      setDraft({
        capital_limit_usdt: data.capital_limit_usdt ?? "",
        trade_risk_pct: data.trade_risk_pct ?? "",
        daily_loss_pct: data.daily_loss_pct ?? "",
      });
      setMessage(ar ? "تم حفظ حدود رأس المال والمخاطر في حسابك على الخادم. التداول الحقيقي لم يُفعّل." :
        "Your capital and risk limits were saved on the server. Live trading remains disabled.");
    } catch (error) {
      setSaved(null);
      setMessage(error instanceof Error ? error.message : "PREFERENCES_SAVE_FAILED");
    } finally { setBusy(false); }
  }
  if (auth !== "authenticated") return null;
  return <section className="panel" aria-label={ar ? "إعدادات التداول الحقيقي" : "Real-money trading settings"}>
    <h2>{ar ? "إعدادات رأس المال والمخاطرة" : "Capital and risk settings"}</h2>
    <p className="notice">{ar
      ? "اختر هذه القيم هنا مرة واحدة، وسيحفظها البوت على الخادم. هذا حفظ للإعدادات فقط؛ تنفيذ الصفقات بأموال حقيقية غير متاح حتى يجتاز محرك الأوامر فحوص السلامة."
      : "Choose and save these values once on the server. Saving preferences never enables real-money orders before the order engine passes its safety checks."}</p>
    <p className="muted">{ar ? "السوق المتاح: عقود Binance USDⓈ-M الآجلة" :
      "Available venue: Binance USDⓈ-M Futures"} · {workspace
      ? `${workspace.symbol} · ${workspace.interval} · ${workspace.leverage}×`
      : (ar ? "إعدادات الأصل والرافعة قيد التحميل" : "Workspace loading")}</p>
    <p className="muted">{ar
      ? "تغيير الأصل أو الفريم أو الرافعة يتم من شريط إعدادات البوت الموحد أعلى الصفحة."
      : "Use the shared settings bar above to choose asset, timeframe, and leverage."}</p>
    <form onSubmit={event => void save(event)}>
      <fieldset disabled={!permitted || !saved || !workspace || busy} style={{ border: 0, padding: 0, margin: 0 }}>
        <div className="row" style={{ flexWrap: "wrap", gap: 12, alignItems: "end" }}>
          <label className="field">{ar ? "رأس المال المسموح للبوت باستخدامه (USDT)" : "Maximum allocated capital (USDT)"}
            <input type="number" min="0.01" max="1000000000" step="0.01" required
              value={draft.capital_limit_usdt}
              onChange={e => setDraft(v => ({ ...v, capital_limit_usdt: e.target.value }))} /></label>
          <label className="field">{ar ? "أقصى مخاطرة للصفقة (%)" : "Maximum trade risk (%)"}
            <input type="number" min="0.0001" max="100" step="0.0001" required
              value={draft.trade_risk_pct}
              onChange={e => setDraft(v => ({ ...v, trade_risk_pct: e.target.value }))} /></label>
          <label className="field">{ar ? "الحد الأقصى للخسارة اليومية (%)" : "Maximum daily loss (%)"}
            <input type="number" min="0.0001" max="100" step="0.0001" required
              value={draft.daily_loss_pct}
              onChange={e => setDraft(v => ({ ...v, daily_loss_pct: e.target.value }))} /></label>
          <button type="submit" className="button">{busy ? (ar ? "جارٍ الحفظ…" : "Saving…") :
            (ar ? "حفظ إعدادات التداول" : "Save trading preferences")}</button>
        </div>
      </fieldset>
    </form>
    <p className="muted" role="status">{message || (saved?.configured
      ? (ar ? "الإعدادات محفوظة على الخادم." : "Preferences saved on server.")
      : (ar ? "لم تحفظ جميع حدود المخاطرة بعد." : "Risk limits have not been fully saved."))}</p>
    <p className="muted">{ar
      ? "لا يمكن رفع حد الخسارة اليومي خلال يوم المخاطرة الجاري. هذه الإعدادات لا تغيّر صلاحيات Binance ولا تسمح بإرسال أوامر حقيقية."
      : "The daily risk limit cannot be increased during the active risk day. These preferences do not change Binance permissions or place real orders."}</p>
  </section>;
}
