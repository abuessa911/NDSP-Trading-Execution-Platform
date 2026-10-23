"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { useAuth } from "./AuthProvider";
import { useI18n } from "../ndsp/i18n";
import { useTradingWorkspace } from "./TradingWorkspace";

type Control = {
  mode: "BINANCE_USDM_PUBLIC_MONITOR";
  state: "STOPPED" | "MONITORING" | "STALLED";
  symbol: string;
  interval: string;
  last_closed_price: string | null;
  last_candle_closed_ms: number | null;
  last_checked_ms: number | null;
  expires_in_seconds: number;
  testnet_key_saved: boolean;
  live_readonly_key_saved: boolean;
  execution_enabled: false;
  order_submission_available: false;
};

const endpoint = "/api/v1/trading/control";

async function parseResponse(response: Response): Promise<unknown> {
  let data: unknown;
  try { data = await response.json(); }
  catch { throw new Error(`HTTP ${response.status}`); }
  if (!response.ok) {
    const reason = typeof data === "object" && data !== null &&
      "reason_code" in data && typeof data.reason_code === "string"
      ? data.reason_code : `HTTP_${response.status}`;
    throw new Error(reason);
  }
  return data;
}

/**
 * This is an authenticated read-only MARKET MONITOR, not a trade engine.
 * Secrets exist only in controlled form state until a TLS same-origin POST.
 * They are never stored in localStorage/sessionStorage or rendered back.
 */
export default function HunterControlPanel() {
  const { lang } = useI18n();
  const ar = lang === "ar";
  const { state: auth, identity, getCsrfToken } = useAuth();
  const { workspace, busy: workspaceBusy } = useTradingWorkspace();
  const generation = useRef(0), identityEpoch = useRef(0), saving = useRef(false);
  const currentOwner = identity ? identity.tenant_id + ":" + identity.user_id : null;
  const [control, setControl] = useState<Control | null>(null);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [key, setKey] = useState("");
  const [secret, setSecret] = useState("");
  const [liveKey, setLiveKey] = useState("");
  const [liveSecret, setLiveSecret] = useState("");
  const canOperate = auth === "authenticated" &&
    ["OPERATOR", "ADMIN", "SUPER_ADMIN"].includes(identity?.role ?? "");

  useEffect(() => {
    identityEpoch.current++; generation.current++;
    setKey(""); setSecret(""); setLiveKey(""); setLiveSecret(""); setFeedback(""); setControl(null);
    return () => { identityEpoch.current++; generation.current++; };
  }, [auth, currentOwner]);

  const refresh = useCallback(async () => {
    const current = ++generation.current;
    if (auth !== "authenticated") { setControl(null); return; }
    try {
      const response = await fetch(endpoint, { credentials: "same-origin", cache: "no-store", signal: AbortSignal.timeout(12000) });
      const data = await parseResponse(response);
      const value = data as Partial<Control> | null;
      if (!value || value.execution_enabled !== false || value.order_submission_available !== false
          || !["STOPPED", "MONITORING", "STALLED"].includes(value.state ?? "")) throw new Error("INVALID_CONTROL");
      if (current === generation.current) setControl(value as Control);
    } catch {
      if (current !== generation.current) return;
      setControl(null);
      setFeedback(ar ? "تعذر قراءة حالة المراقبة من الخادم." : "Server monitor status unavailable.");
    }
  }, [auth, currentOwner, ar, workspace]);

  useEffect(() => {
    setControl(null);
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30000);
    return () => { generation.current++; window.clearInterval(timer); };
  }, [refresh]);

  async function mutate(path: string, method: "POST" | "DELETE", body?: object) {
    const csrf = getCsrfToken();
    if (!csrf || !canOperate || saving.current) {
      setFeedback(ar ? "تحتاج جلسة مشغّل مصادقًا عليها." : "Authenticated operator session required.");
      return;
    }
    const ownerEpoch = identityEpoch.current;
    saving.current = true;
    setLoading(true);
    setFeedback("");
    try {
      const response = await fetch(`${endpoint}${path}`, {
        method,
        credentials: "same-origin",
        cache: "no-store",
        signal: AbortSignal.timeout(30000),
        headers: { "X-NEX-CSRF": csrf, ...(body ? { "Content-Type": "application/json" } : {}) },
        body: body ? JSON.stringify(body) : undefined,
      });
      await parseResponse(response);
      if (ownerEpoch !== identityEpoch.current) return;
      setFeedback(ar ? "تم استلام الأمر وتأكيده من الخادم." : "Server operation confirmed.");
      await refresh();
    } catch (error) {
      if (ownerEpoch === identityEpoch.current) setFeedback(error instanceof Error ? error.message : "Request failed");
    } finally {
      saving.current = false;
      setLoading(false);
    }
  }

  async function verifyCredentials(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await mutate("/testnet/connect", "POST", { api_key: key, api_secret: secret });
    } finally {
      // Do not persist or cache exchange secrets in browser storage.
      setKey("");
      setSecret("");
    }
  }

  async function verifyLiveCredentials(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await mutate("/live/connect", "POST", { api_key: liveKey, api_secret: liveSecret });
    } finally {
      setLiveKey("");
      setLiveSecret("");
    }
  }

  const stateText = control?.state === "MONITORING"
    ? (ar ? "مراقبة فعلية — بيانات سوق فقط" : "Monitoring real market data")
    : control?.state === "STALLED"
      ? (ar ? "المراقبة متوقفة مؤقتًا أو فقدت الاتصال" : "Monitor stalled / disconnected")
      : (ar ? "متوقف" : "Stopped");

  return (
    <section className="panel" aria-label="Hunter server trading controls">
      <h2>{ar ? "التحكم الفعلي بالخادم — Hunter KSA1" : "Hunter KSA1 server controls"}</h2>
      <p className="notice">
        {ar
          ? "المرحلة الحالية: مراقبة شموع Binance المغلقة، وربط حساب Binance الحقيقي للقراءة فقط أو مفاتيح Testnet. زر التشغيل لا ينفذ صفقات ولا يحرّك أموالًا."
          : "Current phase: Binance closed-candle monitoring, plus Binance mainnet read-only or TESTNET account validation. Start does NOT place orders or move funds."}
      </p>
      <div className="stat-row">
        <div><strong>{ar ? "الحالة" : "Status"}:</strong> {control ? stateText : (ar ? "غير متاح" : "Unavailable")}</div>
        <div><strong>{ar ? "السوق" : "Market"}:</strong> {control?.state !== "STOPPED" && control ? control.symbol : workspace?.symbol ?? "—"} / {control?.state !== "STOPPED" && control ? control.interval : workspace?.interval ?? "—"}</div>
        <div><strong>{ar ? "التنفيذ" : "Execution"}:</strong> {ar ? "مراقبة فقط؛ تنفيذ Demo في القسم المستقل" : "Monitor only; Demo execution has separate controls"}</div>
      </div>
      {control?.last_closed_price && (
        <p aria-live="polite">
          {ar ? "آخر إغلاق مؤكد" : "Last verified closed candle"}:
          {" "}<bdi dir="ltr">{control.last_closed_price} USDT</bdi>
          {control.last_candle_closed_ms ? ` (${new Date(control.last_candle_closed_ms).toLocaleString()})` : ""}
        </p>
      )}
      {control?.state === "MONITORING" && (
        <p className="muted">{ar ? "تتوقف تلقائيًا بعد 15 دقيقة، ويمكن إعادة تشغيلها." : "Automatically expires after 15 minutes; restart as needed."}</p>
      )}
      <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
        <button type="button" className="button" disabled={!canOperate || loading || !control || !workspace || workspaceBusy || control.state === "MONITORING"}
          onClick={() => void mutate("/start", "POST")}>
          {ar ? "تشغيل مراقبة السوق" : "Start market monitor"}
        </button>
        <button type="button" className="button" disabled={!canOperate || loading || !control || control.state === "STOPPED"}
          onClick={() => void mutate("/stop", "POST")}>
          {ar ? "إيقاف المراقبة" : "Stop monitor"}
        </button>
        <button type="button" className="button" disabled={loading || auth !== "authenticated"} onClick={() => void refresh()}>
          {ar ? "تحديث الحالة" : "Refresh status"}
        </button>
      </div>
      <hr />
      <h3>{ar ? "فحص ربط Binance USD-M Futures Testnet" : "Binance USD-M Futures Testnet connection"}</h3>
      <p className="muted">
        {ar ? "تُرسل المفاتيح مباشرة للخادم المشفر وتُخزن في Redis مشفرة لمدة 24 ساعة فقط بعد نجاح الفحص. لا تستخدم مفاتيح حسابك الحقيقي."
          : "Testnet keys are sent to your server and stored encrypted in Redis for 24h after validation. Do not enter live account keys."}
      </p>
      <p><strong>{ar ? "حالة المفاتيح" : "Credential status"}:</strong>{" "}
        {control?.testnet_key_saved
          ? (ar ? "متحقق منها ومحفوظة مشفرة" : "Verified and encrypted on server")
          : (ar ? "لا توجد مفاتيح محفوظة" : "No verified keys stored")}
      </p>
      <form onSubmit={event => { void verifyCredentials(event); }} autoComplete="off">
        <label className="field">
          <span>Testnet API Key</span>
          <input type="password" value={key} autoComplete="off" required minLength={10}
            onChange={event => setKey(event.target.value)} disabled={!canOperate || loading} />
        </label>
        <label className="field">
          <span>Testnet API Secret</span>
          <input type="password" value={secret} autoComplete="off" required
            onChange={event => setSecret(event.target.value)} disabled={!canOperate || loading} />
        </label>
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <button type="submit" className="button" disabled={!canOperate || loading}>
            {ar ? "فحص وحفظ مفاتيح Testnet" : "Verify and save testnet credentials"}
          </button>
          <button type="button" className="button" disabled={!canOperate || loading || !control?.testnet_key_saved}
            onClick={() => void mutate("/testnet/connect", "DELETE")}>
            {ar ? "حذف المفاتيح من الخادم" : "Delete server credentials"}
          </button>
        </div>
      </form>
      <hr />
      <h3>{ar ? "ربط حساب Binance الحقيقي — قراءة فقط" : "Binance real account — read only"}</h3>
      <p className="notice">
        {ar
          ? "هذه مفاتيح Binance الحقيقية وليست Testnet. يتم فحص صلاحيات المفتاح عبر Binance: يجب أن يكون للقراءة فقط، ومقيدًا بعنوان IP، ودون تداول أو سحب أو تحويل. لا يتم إرسال أي أمر تداول. لا تدخل مفتاحًا يملك صلاحيات تنفيذ."
          : "Real Binance mainnet keys, not Testnet. Binance must verify read-only permissions and an IP allowlist, with trading, withdrawals and transfers disabled. No order is submitted. Never enter a trading-enabled key."}
      </p>
      <p><strong>{ar ? "حالة حساب Binance الحقيقي" : "Real Binance account status"}:</strong>{" "}
        {control?.live_readonly_key_saved
          ? (ar ? "تم التحقق من مفتاح قراءة فقط وحفظه مشفرًا على الخادم (ساعة واحدة)" : "Verified read-only, encrypted server-side for one hour")
          : (ar ? "غير مربوط" : "Not connected")}
      </p>
      <form onSubmit={event => { void verifyLiveCredentials(event); }} autoComplete="off">
        <label className="field">
          <span>{ar ? "مفتاح Binance الحقيقي (للقراءة فقط)" : "Real Binance read-only API Key"}</span>
          <input type="password" value={liveKey} autoComplete="off" required minLength={10}
            onChange={event => setLiveKey(event.target.value)} disabled={!canOperate || loading} />
        </label>
        <label className="field">
          <span>{ar ? "سر API الحقيقي" : "Real Binance API Secret"}</span>
          <input type="password" value={liveSecret} autoComplete="off" required
            onChange={event => setLiveSecret(event.target.value)} disabled={!canOperate || loading} />
        </label>
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <button type="submit" className="button" disabled={!canOperate || loading}>
            {ar ? "ربط الحساب الحقيقي والتحقق من الصلاحيات" : "Verify and link real read-only account"}
          </button>
          <button type="button" className="button"
            disabled={!canOperate || loading || !control?.live_readonly_key_saved}
            onClick={() => void mutate("/live/connect", "DELETE")}>
            {ar ? "فصل الحساب الحقيقي وحذف المفتاح" : "Disconnect and delete real key"}
          </button>
        </div>
      </form>
      <p role="status" className="muted">{feedback}</p>
      {!canOperate && <p className="notice">{ar ? "يلزم تسجيل الدخول بصلاحية مشغّل؛ قد تتطلب الإدارة تحقق MFA." : "Sign in as an operator; administrators may require MFA."}</p>}
    </section>
  );
}
