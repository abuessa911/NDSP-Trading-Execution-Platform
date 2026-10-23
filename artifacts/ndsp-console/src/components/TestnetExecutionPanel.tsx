"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "./AuthProvider";
import { useI18n } from "../ndsp/i18n";

type Config = { symbol: string; margin_mode: string; daily_loss_pct: string; trade_risk_pct: string; max_exposure_pct: string; stop_pct: string };
type Action = "preflight" | "dry-run" | "entry" | "inspect" | "reconcile" | "exit" | "cleanup" | "recover";
type Receipt = { request_id: string; action: Action; status: "CONFIRMED" | "REJECTED" | "UNCERTAIN"; reason: string | null; result: Record<string, unknown> | null; created_ms: number };
type Automation = { state: "STOPPED" | "RUNNING" | "STOPPING" | "PAUSED"; expires_at: number | null; last_checked_ms: number | null; last_result: string | null; reason: string | null };
type View = { automation: Automation; venue: "BINANCE_USDM_TESTNET"; mainnet_orders_enabled: false; configured: boolean; revision: string | null; config: Config | null; credentials_saved: boolean; active_position: { id: string; quantity: string } | null; pending_order: { id: string; signal: string } | null; halted: boolean; daily_loss_hit: boolean; opening_equity: string | null; last_equity: string | null; receipts: Receipt[] };
type Command = { request_id: string; revision: string; action: Action; position_id: string | null; confirmation: "BINANCE_DEMO_ONLY" };
const endpoint = "/api/v1/trading/testnet";
const defaults: Config = { symbol: "BTCUSDT", margin_mode: "CROSS", daily_loss_pct: "2", trade_risk_pct: "0.5", max_exposure_pct: "10", stop_pct: "1" };
function valid(value: unknown): value is View {
  if (!value || typeof value !== "object") return false;
  const v = value as Partial<View>;
  return v.venue === "BINANCE_USDM_TESTNET" && v.mainnet_orders_enabled === false &&
    typeof v.configured === "boolean" && Array.isArray(v.receipts) && !!v.automation &&
    ["STOPPED", "RUNNING", "STOPPING", "PAUSED"].includes(v.automation.state) &&
    typeof v.halted === "boolean" && (!v.configured || (!!v.config && typeof v.revision === "string"));
}

export default function TestnetExecutionPanel() {
  const { lang } = useI18n(), ar = lang === "ar";
  const { state: auth, identity, getCsrfToken } = useAuth();
  const [data, setData] = useState<View | null>(null), [owner, setOwner] = useState<string | null>(null);
  const [config, setConfig] = useState<Config>(defaults), [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false), [message, setMessage] = useState("");
  const [pending, setPending] = useState<Command | null>(null);
  const epoch = useRef(0), sequence = useRef(0), saving = useRef(false), seeded = useRef(false);
  const canOperate = auth === "authenticated" && ["OPERATOR", "ADMIN", "SUPER_ADMIN"].includes(identity?.role ?? "");
  const currentOwner = identity ? identity.tenant_id + ":" + identity.user_id : null;
  const shown = auth === "authenticated" && owner === currentOwner ? data : null;
  function outcome(result: Record<string, unknown> | null) {
    const nested = result?.result;
    const code = typeof nested === "object" && nested !== null && "status" in nested
      ? String(nested.status) : String(result?.status ?? "");
    const text: Record<string, [string, string]> = {
      TESTNET_ACCOUNT_AND_MARKET_READABLE: ["فحص الحساب والسوق ناجح", "Account and market checks passed"],
      DRY_RUN: ["توجد إشارة؛ لم يُرسل أمر", "Signal found; no order submitted"],
      NO_SIGNAL: ["لا توجد إشارة دخول في آخر شمعة مغلقة", "No entry signal on the last closed candle"],
      NO_NEW_CANDLE: ["لم تغلق شمعة جديدة بعد", "No new closed candle yet"],
      ENTRY_SENT_NEEDS_RECONCILIATION: ["أُرسل الدخول التجريبي؛ نفّذ التسوية", "Demo entry sent; reconcile the journal"],
      ENTRY_PROTECTED_CONFIRMED: ["الدخول ووقف الحماية مثبتان", "Entry and protective stop verified"],
      ACTIVE_PROTECTED_CONFIRMED: ["المركز محمي بوقف مثبت", "Position and protective stop verified"],
      TESTNET_EXIT_SENT_RECONCILIATION_REQUIRED: ["أُرسل الإغلاق؛ افحص الوقف ثم سوِّ السجل", "Exit sent; inspect the stop and reconcile"],
      EXIT_FILLED_STOP_STILL_ACTIVE: ["المركز مغلق؛ نفّذ تنظيف الوقف", "Position closed; clean the remaining stop"],
      TESTNET_STOP_CLEANUP_NEEDS_RECONCILIATION: ["أُرسل تنظيف الوقف؛ نفّذ التسوية", "Stop cleanup sent; reconcile the journal"],
      EXIT_FLAT_STOP_GONE: ["الإغلاق مكتمل ولا يوجد وقف معلّق", "Exit complete; no remaining stop"],
      NO_TRACKED_TRADE: ["لا توجد صفقة مسجلة مفتوحة", "No tracked open trade"],
      STOP_FILLED_FLAT_CONFIRMED: ["وقف الحماية أغلق المركز وتم إثبات الإغلاق", "Protective stop closed the position; closure verified"],
      TESTNET_AUTOMATION_STARTED: ["بدأ تشغيل الديمو الآلي", "Demo automation started"],
      TESTNET_ENTRY_RECOVERED_FROM_SIGNED_EVIDENCE: ["استُعيد الدخول من إثباتات الحساب دون تكرار أمر", "Entry recovered from signed evidence without repeating an order"],
    };
    return text[code]?.[ar ? 0 : 1] ?? (ar ? "سُجلت نتيجة العملية على الخادم" : "Operation result recorded on server");
  }
  function reason(code: string) {
    const messages: Record<string, [string, string]> = {
      TESTNET_RENEW_CREDENTIALS_BEFORE_AUTOMATION: ["جدد حفظ مفاتيح Demo قبل بدء الساعة الآلية", "Renew saved Demo credentials before starting automation"],
      TESTNET_AUTOMATION_UNCERTAIN_REQUIRES_REVIEW: ["نتيجة أمر غير مؤكدة؛ أُوقف التشغيل للمراجعة دون إعادة الأمر", "An order outcome is uncertain; automation paused without repeating it"],
      TESTNET_STOP_AUTOMATION_BEFORE_MANUAL_ACTION: ["أوقف التشغيل الآلي قبل التنفيذ اليدوي", "Stop automation before manual execution"],
      TESTNET_AUTOMATION_LEASE_ENDED: ["انتهت مدة التشغيل؛ يتوقف الدخول ويُغلق المركز المثبت", "Lease ended; entries stopped and a verified position is being closed"],
      TESTNET_OPERATOR_STOP_REQUESTED: ["طُلب الإيقاف وإغلاق المركز التجريبي", "Stop and Demo position closure requested"],
      TESTNET_OWNER_AUTHORIZATION_ENDED: ["انتهت صلاحية التشغيل؛ يتوقف الدخول ويُغلق المركز المثبت", "Operator authorization ended; entries stopped and a verified position is being closed"],
      TESTNET_CREDENTIALS_UNAVAILABLE: ["مفاتيح Demo غير متاحة؛ أُوقف التشغيل للمراجعة", "Demo credentials unavailable; automation paused for review"],
      ACCOUNT_LEVERAGE_MISMATCH: ["اجعل رافعة الأصل في حساب Binance Demo تساوي 1× ثم أعد الفحص", "Set this symbol to 1× in Binance Demo, then run preflight again"],
      ACCOUNT_MARGIN_MODE_MISMATCH: ["طابق نوع الهامش في حساب Demo مع الإعداد المحفوظ", "Match the Demo account margin type to the saved setup"],
      ORDER_BELOW_EXCHANGE_MINIMUM: ["الحجم المحسوب أقل من حد البورصة؛ راجع رصيد Demo وحد التعرض", "Calculated quantity is below the exchange minimum; review Demo balance and exposure"],
      SEPARATE_BINANCE_DEMO_CREDENTIALS_REQUIRED: ["أدخل مفاتيح Binance Demo في نموذج الربط", "Save Binance Demo keys in the connection form"],
      DAILY_LOSS_ALREADY_HIT: ["بلغ الحساب حد الخسارة اليومية؛ الإدخالات متوقفة", "Daily loss limit reached; entries are blocked"],
      DAILY_LOSS_LIMIT_REACHED: ["بلغ الحساب حد الخسارة اليومية؛ الإدخالات متوقفة", "Daily loss limit reached; entries are blocked"],
      RECONCILE_BEFORE_FURTHER_EXECUTION: ["سوِّ الصفقة المسجلة قبل إرسال دخول آخر", "Reconcile the tracked trade before another entry"],
    };
    return messages[code]?.[ar ? 0 : 1] ?? code;
  }
  const refresh = useCallback(async () => {
    const turn = ++sequence.current;
    if (auth !== "authenticated") return;
    try {
      const response = await fetch(endpoint, { credentials: "same-origin", cache: "no-store", signal: AbortSignal.timeout(12000) });
      const value: unknown = await response.json();
      if (!response.ok || !valid(value)) throw Error("TESTNET_SERVICE_UNAVAILABLE");
      if (turn !== sequence.current) return;
      setData(value); setOwner(currentOwner);
      if (!seeded.current && value.config) { seeded.current = true; setConfig(Object.fromEntries(Object.keys(defaults).map(key => [key, value.config![key as keyof Config]])) as Config); }
    } catch {
      if (turn === sequence.current) { setData(null); setMessage(ar ? "تعذر قراءة سجل Testnet." : "Testnet journal unavailable."); }
    }
  }, [auth, currentOwner, ar]);
  useEffect(() => {
    epoch.current++; sequence.current++; seeded.current = false;
    setData(null); setOwner(null); setConfig(defaults); setConfirmed(false); setPending(null); setMessage("");
    return () => { epoch.current++; sequence.current++; };
  }, [auth, currentOwner]);
  useEffect(() => {
    void refresh();
    if (auth !== "authenticated") return;
    const timer = setInterval(() => void refresh(), 30000);
    return () => { sequence.current++; clearInterval(timer); };
  }, [refresh, auth]);

  async function send(path: string, method: "POST" | "PUT", body: object) {
    const csrf = getCsrfToken(), ownerEpoch = epoch.current;
    const stopping = path === "/automation" && "enabled" in body && body.enabled === false;
    if (!csrf || !canOperate || saving.current || (!confirmed && !stopping)) return;
    saving.current = true; setBusy(true); setMessage("");
    try {
      const response = await fetch(endpoint + path, { method, credentials: "same-origin", cache: "no-store",
        signal: AbortSignal.timeout(90000), headers: { "Content-Type": "application/json", "X-NEX-CSRF": csrf },
        body: JSON.stringify(body) });
      const value = await response.json();
      if (ownerEpoch !== epoch.current) return;
      if (!response.ok) throw Error(typeof value.reason_code === "string" ? value.reason_code : "TESTNET_REQUEST_REJECTED");
      if (method === "POST") {
        if (!value || value.request_id !== (body as Command).request_id ||
            !["CONFIRMED", "REJECTED", "UNCERTAIN"].includes(value.status)) throw Error("TESTNET_ACK_UNVERIFIED");
        setPending(null);
        setMessage((value.status === "CONFIRMED" ? (ar ? "مؤكد: " : "Confirmed: ") : value.status + ": ") + (value.reason ? reason(value.reason) : outcome(value.result)));
      } else if (path === "/automation") {
        setMessage(ar ? "حُفظ طلب التشغيل الآلي؛ الحالة أدناه من الخادم." : "Automation request saved; server status is shown below.");
      } else { seeded.current = false; setMessage(ar ? "حُفظ إعداد Testnet." : "Testnet configuration saved."); }
      await refresh();
    } catch (error) {
      if (ownerEpoch === epoch.current) setMessage(error instanceof Error ? error.message : "TESTNET_REQUEST_UNCERTAIN");
    } finally {
      saving.current = false;
      setBusy(false);
    }
  }
  function action(value: Action) {
    if (!shown?.revision || pending) return;
    const command: Command = { request_id: crypto.randomUUID(), revision: shown.revision,
      action: value, position_id: value === "exit" ? shown.active_position?.id ?? null : value === "recover" ? shown.pending_order?.id ?? null : null,
      confirmation: "BINANCE_DEMO_ONLY" };
    setPending(command);
    void send("/actions", "POST", command);
  }
  const labels: Record<Action, string> = ar
    ? { preflight: "فحص الحساب والحماية", "dry-run": "معاينة الإشارة دون أمر", entry: "تنفيذ إشارة الدخول على Testnet", inspect: "فحص المركز والوقف", reconcile: "تسوية السجل", exit: "إغلاق مركز Testnet", cleanup: "تنظيف الوقف بعد الإغلاق", recover: "التحقق من دخول غامض واستعادته" }
    : { preflight: "Preflight account", "dry-run": "Preview signal", entry: "Execute Testnet entry signal", inspect: "Inspect position and stop", reconcile: "Reconcile journal", exit: "Close Testnet position", cleanup: "Clean stop after exit", recover: "Verify and recover uncertain entry" };
  const fields: [keyof Config, string][] = ar
    ? [["daily_loss_pct", "الخسارة اليومية %"], ["trade_risk_pct", "مخاطرة الصفقة %"], ["max_exposure_pct", "أقصى تعرض %"], ["stop_pct", "مسافة الوقف %"]]
    : [["daily_loss_pct", "Daily loss %"], ["trade_risk_pct", "Trade risk %"], ["max_exposure_pct", "Max exposure %"], ["stop_pct", "Stop distance %"]];
  const locked = busy || !!pending || !canOperate;
  const autoBusy = shown?.automation.state === "RUNNING" || shown?.automation.state === "STOPPING";
  const autoLabels = ar ? { STOPPED: "متوقف", RUNNING: "تشغيل آلي", STOPPING: "إيقاف وإغلاق المركز", PAUSED: "موقوف للمراجعة" }
    : { STOPPED: "Stopped", RUNNING: "Automatic", STOPPING: "Stopping and closing", PAUSED: "Paused for review" };
  const heartbeatStale = autoBusy && (!shown?.automation.last_checked_ms || Date.now() - shown.automation.last_checked_ms > 90000);
  return <section className="panel" aria-label="Binance Testnet execution" style={{ minWidth: 0, maxWidth: "100%", overflowWrap: "anywhere" }}>
    <h2>{ar ? "تنفيذ Binance التجريبي من الواجهة" : "Binance Demo execution"}</h2>
    <p className="notice">{ar
      ? "أوامر إلى Binance Testnet بأموال تجريبية فقط. يستخدم هذا القسم إعدادًا مستقلًا: EMA20/50 شراء فقط، فريم 15 دقيقة ورافعة 1×. القيم المعروضة للاختبار. التداول بأموال حقيقية غير مفعّل."
      : "Binance Testnet orders using demo funds. Independent pilot settings: EMA20/50 long only, 15-minute candles, 1× leverage. Displayed values are for testing. Real-money execution is disabled."}</p>
    <p>{ar ? "المفاتيح" : "Keys"}: {shown?.credentials_saved ? (ar ? "محفوظة مشفرة" : "Saved encrypted") : (ar ? "أدخل مفاتيح Demo في نموذج الربط أعلاه ثم حدّث" : "Save Demo keys in the connection form above, then refresh")}</p>
    <label className="field"><span>{ar ? "الأصل" : "Symbol"}</span>
      <select value={config.symbol} disabled={locked || autoBusy} onChange={e => setConfig({ ...config, symbol: e.target.value })}>
        {["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT"].map(s => <option key={s}>{s}</option>)}
      </select></label>
    <label className="field"><span>{ar ? "الهامش المطلوب في حساب Demo" : "Required Demo account margin"}</span>
      <select value={config.margin_mode} disabled={locked || autoBusy} onChange={e => setConfig({ ...config, margin_mode: e.target.value })}>
        <option value="CROSS">CROSS</option><option value="ISOLATED">ISOLATED</option>
      </select></label>
    {fields.map(([key, label]) => <label className="field" key={key}><span>{label}</span>
      <input type="number" min="0.001" max="100" step="any" value={config[key]} disabled={locked || autoBusy}
        onChange={e => setConfig({ ...config, [key]: e.target.value })} /></label>)}
    <label className="row"><input type="checkbox" checked={confirmed} disabled={busy}
      onChange={e => setConfirmed(e.target.checked)} />{ar ? "أؤكد أن هذه العمليات لحساب Binance Demo فقط" : "I confirm Binance Demo operations only"}</label>
    <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
      <button className="button" disabled={locked || autoBusy || !confirmed || !!shown?.active_position || !!shown?.pending_order || !!shown?.halted}
        onClick={() => void send("/configuration", "PUT", { ...config, confirmation: "BINANCE_DEMO_ONLY" })}>
        {ar ? "حفظ إعداد Testnet" : "Save Testnet setup"}</button>
      <button className="button" disabled={busy || auth !== "authenticated"} onClick={() => void refresh()}>{ar ? "تحديث سجل Testnet" : "Refresh Testnet journal"}</button>
    </div>
    {shown?.configured && <>
      <p>{ar ? "الإعداد المحفوظ" : "Saved setup"}: {shown.config?.symbol} / 15m / 1× / {shown.config?.margin_mode}</p>

      <div className="notice" aria-label={ar ? "تشغيل الديمو الآلي" : "Demo automation"}>
        <h3>{ar ? "التداول الآلي على Demo" : "Automatic Demo trading"}</h3>
        <p>{ar ? "تشغيل مستقل لمدة ساعة: دخول عند تقاطع EMA20/50 الصاعد وإغلاق عند التقاطع الهابط أو حد الخسارة اليومية. عند الإيقاف أو انتهاء الساعة يُغلق المركز المثبت ويُنظف الوقف. يستمر على الخادم بعد إغلاق الصفحة." : "One-hour independent run: enter on an EMA20/50 upward cross; exit on a downward cross or the daily loss limit. Stop or expiry closes a verified position and cleans its stop. Continues on the server after closing this page."}</p>
        <p role="status">{ar ? "الحالة" : "State"}: {autoLabels[shown.automation.state]}
          {heartbeatStale ? (ar ? " — بانتظار إثبات نبضة الخادم؛ لا يُعد التشغيل مؤكدًا" : " — awaiting server heartbeat; execution health unverified") : ""}
        </p>
        <p>{ar ? "آخر فحص" : "Last check"}: {shown.automation.last_checked_ms ? new Date(shown.automation.last_checked_ms).toLocaleTimeString(ar ? "ar-SA" : "en-US") : "—"}
          {" · "}{ar ? "نهاية الساعة" : "Lease end"}: {shown.automation.expires_at ? new Date(shown.automation.expires_at * 1000).toLocaleTimeString(ar ? "ar-SA" : "en-US") : "—"}</p>
        {shown.automation.reason && <p role="alert">{reason(shown.automation.reason)}</p>}
        {shown.automation.last_result && <p>{outcome({ status: shown.automation.last_result })}</p>}
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <button className="button" disabled={locked || autoBusy || !confirmed || !shown.credentials_saved || shown.halted || !!shown.active_position || !!shown.pending_order}
            onClick={() => void send("/automation", "PUT", { enabled: true, revision: shown.revision, confirmation: "BINANCE_DEMO_ONLY" })}>
            {ar ? "تشغيل الديمو آليًا لمدة ساعة" : "Run Demo automatically for one hour"}</button>
          <button className="button" disabled={locked || shown.automation.state === "STOPPED"}
            onClick={() => void send("/automation", "PUT", { enabled: false, revision: shown.revision, confirmation: "BINANCE_DEMO_ONLY" })}>
            {ar ? "إيقاف الديمو وإغلاق مركزه" : "Stop Demo and close its position"}</button>
        </div>
      </div>
      <p>{ar ? "المركز" : "Position"}: {shown.active_position?.quantity ?? "—"} · {ar ? "أمر قيد التسوية" : "Pending reconciliation"}: {shown.pending_order?.signal ?? "—"}</p>
      {(shown.halted || shown.daily_loss_hit) && <p role="alert">{ar ? "الإدخالات موقوفة للحماية؛ راجع سجل العملية." : "Entries halted for protection; review the operation journal."}</p>}
      <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
        {(Object.keys(labels) as Action[]).map(value => <button className="button" key={value}
          disabled={locked || !confirmed || !shown.credentials_saved || (autoBusy && !["inspect", "preflight"].includes(value)) ||
            (value === "entry" && (!!shown.active_position || !!shown.pending_order || shown.halted || shown.daily_loss_hit)) ||
            (value === "exit" && (!shown.active_position || !!shown.pending_order)) ||
            (value === "recover" && (!shown.halted || shown.pending_order?.signal !== "ENTER_LONG"))}
          onClick={() => action(value)}>{labels[value]}</button>)}
      </div>
      <div className="table-wrap"><table className="table"><thead><tr><th>{ar ? "العملية" : "Action"}</th><th>{ar ? "الحالة" : "Status"}</th><th>{ar ? "النتيجة" : "Result"}</th></tr></thead>
        <tbody>{[...shown.receipts].reverse().map(row => <tr key={row.request_id}><td>{labels[row.action] ?? row.action}</td><td>{row.status}</td><td><bdi dir="ltr">{row.reason ? reason(row.reason) : outcome(row.result)}</bdi></td></tr>)}</tbody></table></div>
    </>}
    {pending && <div className="notice"><p>{ar ? "لم يثبت وصول التأكيد. إعادة الاستعلام تستخدم نفس معرّف الطلب ولا تنشئ أمرًا ثانيًا." : "Acknowledgement unverified. Retry uses the same request ID and cannot place a duplicate."}</p>
      <button className="button" disabled={busy || !confirmed || !canOperate} onClick={() => void send("/actions", "POST", pending)}>{ar ? "استعادة تأكيد الطلب نفسه" : "Recover same request receipt"}</button></div>}
    <p role="status">{message}</p>
  </section>;
}
