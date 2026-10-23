"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "./AuthProvider";
import { useI18n } from "../ndsp/i18n";
import { useTradingWorkspace } from "./TradingWorkspace";

type Policy = Record<"daily_loss_pct" | "trade_risk_pct" | "max_margin_pct" | "stop_distance_pct" | "take_profit_distance_pct" | "fee_pct" | "slippage_pct", string>;
type Fill = { id: string; action: string; status: string; symbol: string; side: string; quantity: string; price: string | null; fee: string; net_pnl: string | null; reason: string; created_ms: number };
type Position = { id: string; symbol: string; interval: string; side: string; quantity: string; entry: string; stop: string; target: string; leverage: number; margin: string };
type View = {
  mode: "PAPER"; configured: boolean; real_orders_enabled: false;
  cash?: string; initial?: string; equity?: string | null; cash_change?: string; unrealized_pnl?: string | null;
  quote_available?: boolean; position: Position | null; daily_opening?: string; daily_hit?: boolean;
  running?: boolean; halt_reason?: string | null; utc_day?: string; strategy_id?: string;
  policy?: Policy; profile?: { symbol: string; interval: string; leverage: number; execution_method: string };
  orders: Fill[]; total_orders: number; market_error?: string;
};
const endpoint = "/api/v1/trading/paper";
const emptyPolicy: Policy = { daily_loss_pct: "", trade_risk_pct: "", max_margin_pct: "", stop_distance_pct: "", take_profit_distance_pct: "", fee_pct: "", slippage_pct: "" };
const rules = ["trend-ladder", "range-fade", "breakout-scout", "mean-return"];
const names = ["Trend Ladder", "Range Fade", "Breakout Scout", "Mean Return"];
function valid(data: unknown): data is View {
  if (!data || typeof data !== "object") return false;
  const value = data as Partial<View>;
  return value.mode === "PAPER" && value.real_orders_enabled === false &&
    typeof value.configured === "boolean" && Array.isArray(value.orders) &&
    Number.isInteger(value.total_orders) && (value.position === null || typeof value.position === "object") &&
    (!value.configured || (typeof value.cash === "string" && typeof value.initial === "string" &&
      !!value.policy && !!value.profile && typeof value.running === "boolean"));
}

export default function PaperBrokerPanel({ view = "control" }: { view?: "control" | "positions" | "orders" | "history" | "performance" }) {
  const { lang, t } = useI18n();
  const ar = lang === "ar";
  const { state: auth, identity, getCsrfToken } = useAuth();
  const { workspace, busy: workspaceBusy } = useTradingWorkspace();
  const [data, setData] = useState<View | null>(null);
  const [dataOwner, setDataOwner] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [initial, setInitial] = useState("");
  const [policy, setPolicy] = useState<Policy>(emptyPolicy);
  const [strategy, setStrategy] = useState("");
  const [quantity, setQuantity] = useState("");
  const [pending, setPending] = useState<{ request_id: string; action: "OPEN" | "CLOSE"; side: "LONG" | "SHORT"; quantity: string | null; position_id: string | null } | null>(null);
  const sequence = useRef(0), saving = useRef(false), seeded = useRef(false), identityEpoch = useRef(0);
  const canOperate = auth === "authenticated" && ["OPERATOR", "ADMIN", "SUPER_ADMIN"].includes(identity?.role ?? "");
  const shown = auth === "authenticated" && dataOwner === identity?.user_id ? data : null;

  const refresh = useCallback(async () => {
    const current = ++sequence.current;
    if (auth !== "authenticated") { setData(null); return; }
    const controller = new AbortController();
    const deadline = setTimeout(() => controller.abort(), 10_000);
    try {
      const response = await fetch(endpoint, { credentials: "same-origin", cache: "no-store", signal: controller.signal });
      const value: unknown = await response.json();
      if (!response.ok || !valid(value)) throw Error("PAPER_SERVICE_UNAVAILABLE");
      if (sequence.current !== current) return;
      setData(value); setDataOwner(identity?.user_id ?? null);
      if (value.configured && !seeded.current) {
        seeded.current = true;
        setInitial(value.initial!); setPolicy(value.policy!); setStrategy(value.strategy_id ?? "");
      }
    } catch {
      if (sequence.current === current) { setData(null); setMessage(ar ? "خدمة المحاكاة غير متاحة؛ لا تُعرض بيانات نموذجية بدل السجل." : "Simulator unavailable; no sample ledger is substituted."); }
    } finally { clearTimeout(deadline); }
  }, [auth, identity?.user_id, ar]);

  useEffect(() => {
    identityEpoch.current++; seeded.current = false; setPending(null); setData(null); setDataOwner(null);
    setInitial(""); setPolicy(emptyPolicy); setStrategy(""); setMessage("");
    return () => { identityEpoch.current++; sequence.current++; };
  }, [auth, identity?.user_id]);
  useEffect(() => {
    void refresh();
    if (auth !== "authenticated") return;
    const timer = setInterval(() => void refresh(), 30_000);
    return () => { sequence.current++; clearInterval(timer); };
  }, [refresh, auth, workspace]);

  async function mutate(path: string, method: "POST" | "PUT", body?: object) {
    const csrf = getCsrfToken();
    if (!canOperate || !csrf || saving.current) return false;
    const ownerEpoch = identityEpoch.current;
    saving.current = true; setBusy(true); setMessage("");
    const controller = new AbortController();
    const deadline = setTimeout(() => controller.abort(), 12_000);
    try {
      const response = await fetch(endpoint + path, {
        method, credentials: "same-origin", cache: "no-store", signal: controller.signal,
        headers: { "X-NEX-CSRF": csrf, ...(body ? { "Content-Type": "application/json" } : {}) },
        body: body ? JSON.stringify(body) : undefined,
      });
      const value = await response.json();
      if (ownerEpoch !== identityEpoch.current) return false;
      if (!response.ok) {
        if (response.status >= 400 && response.status < 500) setPending(null);
        throw Error(typeof value?.reason_code === "string" ? value.reason_code : "PAPER_OPERATION_REJECTED");
      }
      if (path === "/orders") {
        if (!body || !("request_id" in body) || value?.id !== body.request_id ||
            !["FILLED_SIMULATED", "ALREADY_FLAT_SIMULATED"].includes(value?.status)) throw Error("PAPER_ORDER_UNCONFIRMED");
        setPending(null);
      } else if (value?.real_orders_enabled !== false) throw Error("PAPER_RESPONSE_INVALID");
      setMessage(ar ? "أكد الخادم عملية المحاكاة؛ لم تُرسل صفقة للبورصة." : "Server confirmed the virtual operation; no exchange order was sent.");
      await refresh();
      return true;
    } catch (error) {
      if (ownerEpoch === identityEpoch.current) setMessage(error instanceof Error ? error.message : "PAPER_OPERATION_UNCONFIRMED");
      return false;
    } finally { clearTimeout(deadline); saving.current = false; setBusy(false); }
  }

  function submit(action: "OPEN" | "CLOSE", side: "LONG" | "SHORT") {
    if (busy || pending || !canOperate) return;
    const body = { request_id: crypto.randomUUID(), action, side, quantity: action === "OPEN" ? quantity : null, position_id: action === "CLOSE" ? shown?.position?.id ?? null : null };
    setPending(body); void mutate("/orders", "POST", body);
  }
  const manual = workspace?.execution_method === "MANUAL" && shown?.profile?.execution_method === "MANUAL";
  const fills = (shown?.orders ?? []).filter(row => view !== "history" || row.action === "CLOSE");
  const position = shown?.position;
  const title = view === "positions" ? (ar ? "المراكز الافتراضية" : "Virtual positions")
    : view === "orders" ? (ar ? "سجل أوامر المحاكاة" : "Simulation order ledger")
    : view === "history" ? (ar ? "الصفقات الافتراضية المغلقة" : "Closed virtual trades")
    : view === "performance" ? (ar ? "الأداء الفعلي للمحاكاة" : "Recorded simulation performance")
    : (ar ? "محرك المحاكاة — أموال افتراضية" : "Paper broker — virtual funds");
  const fields: [keyof Policy, string, string, number][] = [
    ["daily_loss_pct", "حد الخسارة اليومي ٪", "Daily loss limit %", 10],
    ["trade_risk_pct", "مخاطرة الصفقة ٪", "Trade risk %", 10],
    ["max_margin_pct", "الحد الأقصى للهامش ٪", "Maximum margin %", 100],
    ["stop_distance_pct", "مسافة الوقف من السعر ٪", "Stop distance from price %", 79],
    ["take_profit_distance_pct", "مسافة الهدف من السعر ٪", "Target distance from price %", 99.9999],
    ["fee_pct", "رسوم المحاكاة لكل جانب ٪", "Simulated fee each side %", 1],
    ["slippage_pct", "انزلاق المحاكاة لكل جانب ٪", "Simulated slippage each side %", 1],
  ];

  return <section className="panel" aria-label={ar ? "وسيط المحاكاة" : "Paper broker"}>
    <h2>{title}</h2>
    <p className="notice">{ar ? "هذا سجل تشغيل محفوظ بأموال افتراضية فقط، مستقل عن رصيد Binance. يستخدم شموعًا حقيقية مغلقة وأسعار تعبئة محاكاة؛ ولا يرسل أوامر حقيقية أو Testnet." : "A durable virtual-money account, independent of Binance balances. Real completed candles drive simulated fills. No real or Testnet orders are submitted."}</p>
    {!shown && <p role="status">{auth === "authenticated" ? (ar ? "تعذر تحميل سجل المحاكاة." : "Simulation ledger unavailable.") : (ar ? "سجّل الدخول لعرض سجلك الخاص." : "Sign in to view your own ledger.")}</p>}
    {shown && !shown.configured && <p>{ar ? "لا يوجد حساب افتراضي مهيأ. لن تُختلق أرصدة أو مراكز أو صفقات." : "No virtual account has been configured. No balances, positions or fills are invented."}</p>}
    {shown?.configured && <>
      <div className="stat-row">
        <div>{ar ? "الرصيد النقدي الافتراضي" : "Virtual cash"}: <bdi>{shown.cash}</bdi></div>
        <div>{ar ? "قيمة الحساب الافتراضي" : "Virtual equity"}: <bdi>{shown.equity ?? "—"}</bdi></div>
        <div>{ar ? "التغير النقدي مع الرسوم" : "Cash change including fees"}: <bdi>{shown.cash_change}</bdi></div>
        <div>{ar ? "الربح غير المحقق" : "Unrealized P&L"}: <bdi>{shown.unrealized_pnl ?? "—"}</bdi></div>
      </div>
      <p>{shown.profile?.symbol} · {shown.profile?.interval} · {shown.profile?.leverage}x · {shown.utc_day} UTC</p>
      <p>{ar ? "حالة الإدخالات الآلية" : "Automatic entries"}: {shown.running ? (ar ? "تعمل داخل المحاكاة" : "Running in simulation") : (ar ? "متوقفة" : "Stopped")}</p>
      {shown.daily_hit && <p role="alert">{ar ? "بلغ الحساب الافتراضي حد الخسارة اليومي؛ الإدخالات الجديدة ممنوعة." : "The virtual daily loss limit was reached; new entries are blocked."}</p>}
      {(shown.halt_reason || shown.market_error) && <p role="alert">{shown.halt_reason ?? shown.market_error}</p>}
      {position && <div style={{ overflowX: "auto" }}>
        <table><thead><tr>{[ar ? "الأصل" : "Asset", ar ? "الاتجاه" : "Side", ar ? "الكمية" : "Quantity", ar ? "الدخول" : "Entry", ar ? "الوقف" : "Stop", ar ? "الهدف" : "Target"].map(label => <th key={label}>{label}</th>)}</tr></thead>
          <tbody><tr><td>{position.symbol}</td><td>{position.side}</td><td>{position.quantity}</td><td>{position.entry}</td><td>{position.stop}</td><td>{position.target}</td></tr></tbody></table>
      </div>}
      {!position && <p>{ar ? "لا يوجد مركز افتراضي مفتوح." : "No virtual position is open."}</p>}
    </>}
    {view === "control" && canOperate && shown && <details open={!shown.configured}>
      <summary>{ar ? "تهيئة حساب المحاكاة وحدوده" : "Configure simulation account and limits"}</summary>
      <form onSubmit={event => { event.preventDefault(); void mutate("/account", "PUT", {
        initial_equity: shown.configured ? shown.initial : initial, policy, strategy_id: strategy,
      }); }}>
        <fieldset disabled={busy || !!pending || !workspace?.persisted || workspaceBusy} style={{ border: 0, padding: 0 }}>
          <div className="row" style={{ gap: 12, flexWrap: "wrap" }}>
            <label className="field">{ar ? "رأس مال افتراضي" : "Virtual initial capital"}<input aria-label={ar ? "رأس مال افتراضي" : "Virtual initial capital"} type="number" min=".00000001" step="any" required value={initial} disabled={shown.configured} onChange={event => setInitial(event.target.value)} /></label>
            <label className="field">{ar ? "قاعدة المحاكاة" : "Simulation rule"}<select aria-label={ar ? "قاعدة المحاكاة" : "Simulation rule"} required value={strategy} onChange={event => setStrategy(event.target.value)}><option value="">{ar ? "اختر قاعدة" : "Select a rule"}</option>{rules.map((id, index) => <option key={id} value={id}>{t(names[index])}</option>)}</select></label>
            {fields.map(([key, arabic, english, max]) => <label className="field" key={key}>{ar ? arabic : english}<input aria-label={ar ? arabic : english} type="number" required min={key === "fee_pct" || key === "slippage_pct" ? 0 : ".00000001"} max={max} step="any" value={policy[key]} onChange={event => setPolicy(previous => ({ ...previous, [key]: event.target.value }))} /></label>)}
          </div>
          <button className="button" type="submit">{ar ? "حفظ إعدادات المحاكاة" : "Save simulation settings"}</button>
        </fieldset>
      </form>
      <p className="muted">{ar ? "أكد الشريط الموحد أولًا. لا يُعاد ضبط رأس المال أو محو الخسائر عند تحديث الإعدادات. حد اليوم لا يمكن رفعه خلال يوم UTC نفسه." : "Confirm shared settings first. Saving does not reset virtual capital or erase losses. The daily limit cannot be increased during the same UTC day."}</p>
    </details>}
    {view === "control" && canOperate && shown?.configured && <div>
      <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
        <label className="field">{ar ? "كمية الأمر الافتراضي" : "Virtual order quantity"}<input aria-label={ar ? "كمية الأمر الافتراضي" : "Virtual order quantity"} type="number" min=".00000001" step="any" value={quantity} onChange={event => setQuantity(event.target.value)} disabled={busy || !!pending} /></label>
        <button type="button" className="button" disabled={busy || !!pending || !manual || !!position || shown.daily_hit || !quantity} onClick={() => submit("OPEN", "LONG")}>{ar ? "شراء افتراضي" : "Virtual buy"}</button>
        <button type="button" className="button" disabled={busy || !!pending || !manual || !!position || shown.daily_hit || !quantity} onClick={() => submit("OPEN", "SHORT")}>{ar ? "بيع افتراضي" : "Virtual short"}</button>
        <button type="button" className="button" disabled={busy || !!pending || !position} onClick={() => submit("CLOSE", position?.side === "SHORT" ? "SHORT" : "LONG")}>{ar ? "إغلاق المركز الافتراضي" : "Close virtual position"}</button>
        <button type="button" className="button" disabled={busy || !!pending || shown.running || workspace?.execution_method !== "AUTOMATIC" || shown.daily_hit} onClick={() => void mutate("/start", "POST")}>{ar ? "تشغيل المحاكاة الآلية" : "Start automatic simulation"}</button>
        <button type="button" className="button" disabled={busy || !shown.running} onClick={() => void mutate("/stop", "POST")}>{ar ? "إيقاف الإدخالات الآلية" : "Stop automatic entries"}</button>
      </div>
      <p className="muted">{ar ? "الإيقاف يمنع إدخالات جديدة؛ يستمر فحص الوقف والهدف للمركز الافتراضي المفتوح." : "Stopping prevents new entries; protective checks continue for an existing virtual position."}</p>
    </div>}
    {pending && <div role="alert"><p>{ar ? "لم يصل تأكيد نهائي للأمر. أعد المحاولة بالمعرف نفسه لتجنب تكراره." : "Order confirmation is pending. Retry the same request ID to prevent duplication."}</p><button type="button" className="button" disabled={busy} onClick={() => void mutate("/orders", "POST", pending)}>{ar ? "إعادة طلب التأكيد" : "Retry confirmation"}</button></div>}
    {shown?.configured && view !== "positions" && <div style={{ overflowX: "auto" }}>
      <h3>{ar ? "التعبئات الافتراضية المحفوظة" : "Recorded virtual fills"}</h3>
      <table><thead><tr>{[ar ? "الوقت" : "Time", ar ? "الأصل" : "Asset", ar ? "العملية" : "Action", ar ? "الكمية" : "Quantity", ar ? "السعر" : "Price", ar ? "الرسوم" : "Fees", ar ? "صافي الصفقة" : "Trade net P&L"].map(label => <th key={label}>{label}</th>)}</tr></thead>
        <tbody>{fills.map(row => <tr key={row.id}><td>{new Date(row.created_ms).toLocaleString(ar ? "ar-SA" : "en-US")}</td><td>{row.symbol}</td><td>{row.action} / {row.side}</td><td>{row.quantity}</td><td>{row.price ?? "—"}</td><td>{row.fee}</td><td>{row.net_pnl ?? "—"}</td></tr>)}</tbody></table>
      {!fills.length && <p>{ar ? "لا توجد تعبئات افتراضية محفوظة." : "No virtual fills have been recorded."}</p>}
      <p>{ar ? "إجمالي الأوامر الافتراضية" : "Total virtual fills"}: {shown.total_orders} · {ar ? "تُعرض آخر 100 تعبئة" : "Latest 100 fills shown"}</p>
    </div>}
    <button type="button" className="button" disabled={busy || auth !== "authenticated"} onClick={() => void refresh()}>{ar ? "تحديث سجل المحاكاة" : "Refresh simulation ledger"}</button>
    <p role="status" aria-live="polite">{message}</p>
  </section>;
}
