"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useAuth } from "./AuthProvider";
import { useI18n } from "../ndsp/i18n";

type BinanceBalances = {
  spot_usdt: string | null;
  futures_usdt: string;
  total_usdt: string | null;
  valuation_complete: boolean;
  unpriced_assets_count: number;
  execution_enabled: false;
  valuation_basis: string;
};

type RiskSnapshot = {
  daily_loss_pct: string | null;
  configured: boolean;
  account_connected: boolean;
  state: "NOT_CONFIGURED" | "READONLY_ACCOUNT_MISSING" |
    "ACCOUNT_CHANGED_REVIEW_REQUIRED" | "ACCOUNT_UNAVAILABLE" |
    "MONITORING" | "DAILY_LOSS_LIMIT_REACHED";
  opening_equity: string | null;
  current_equity: string | null;
  daily_loss_amount: string | null;
  loss_budget: string | null;
  loss_pct_of_opening_equity: string | null;
  new_entries_blocked: boolean;
  execution_enabled: false;
  order_gate_attached: false;
};

function failureCode(value: unknown, status: number) {
  if (value && typeof value === "object" && "reason_code" in value &&
      typeof value.reason_code === "string") return value.reason_code;
  return `HTTP_${status}`;
}

export default function HunterEquityRiskPanel() {
  const { lang } = useI18n();
  const ar = lang === "ar";
  const { state, identity, getCsrfToken } = useAuth();
  const [snapshot, setSnapshot] = useState<RiskSnapshot | null>(null);
  const [balances, setBalances] = useState<BinanceBalances | null>(null);
  const [balanceStatus, setBalanceStatus] = useState("");
  const [chosen, setChosen] = useState("");
  const [ed25519Key, setEd25519Key] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connectionMessage, setConnectionMessage] = useState("");

  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const operator = state === "authenticated" &&
    ["OPERATOR", "ADMIN", "SUPER_ADMIN"].includes(identity?.role ?? "");

  const refreshBalances = useCallback(async () => {
    if (state !== "authenticated") {
      setBalances(null);
      setBalanceStatus("");
      return;
    }

    try {
      const response = await fetch(
        "/api/v1/trading/ed25519/balances",
        { credentials: "same-origin", cache: "no-store" }
      );
      if (!response.ok) {
        throw new Error(`BALANCES_HTTP_${response.status}`);
      }
      const data = await response.json() as BinanceBalances;
      if (data.execution_enabled !== false) {
        throw new Error("UNEXPECTED_EXECUTION_STATUS");
      }
      setBalances(data);
      setBalanceStatus("");
    } catch (error) {
      setBalances(null);
      setBalanceStatus(
        error instanceof Error ? error.message : "BALANCES_UNAVAILABLE"
      );
    }
  }, [state]);

  const refresh = useCallback(async () => {
    if (state !== "authenticated") { setSnapshot(null); return; }
    try {
      const response = await fetch("/api/v1/trading/risk", {
        credentials: "same-origin", cache: "no-store",
      });
      const data: unknown = await response.json();
      if (!response.ok) throw new Error(failureCode(data, response.status));
      const value = data as RiskSnapshot;
      if (value.execution_enabled !== false || value.order_gate_attached !== false)
        throw new Error("UNEXPECTED_EXECUTION_STATUS");
      setSnapshot(value);
    } catch (error) {
      setSnapshot(null);
      setMessage(error instanceof Error ? error.message : "RISK_STATUS_UNAVAILABLE");
    }
  }, [state]);

  useEffect(() => {
    void refresh();
    void refreshBalances();
  }, [refresh, refreshBalances]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !operator) return;
    const csrf = getCsrfToken();
    if (!csrf) { setMessage("CSRF_TOKEN_REQUIRED"); return; }
    const pct = Number(chosen);
    if (!Number.isFinite(pct) || pct <= 0 || pct > 100 ||
        !/^(?:\d+)(?:\.\d{1,4})?$/.test(chosen)) {
      setMessage(ar ? "اختر نسبة صحيحة بين أكبر من صفر وحتى 100." : "Enter a valid percentage above zero and at most 100.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch("/api/v1/trading/risk", {
        method: "PUT", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json", "X-NEX-CSRF": csrf },
        body: JSON.stringify({ daily_loss_pct: chosen }),
      });
      const data: unknown = await response.json();
      if (!response.ok) throw new Error(failureCode(data, response.status));
      setMessage(ar ? "تم حفظ نسبة الخسارة على الخادم." : "Daily loss policy saved on server.");
      setChosen("");
      await refresh();
      await refreshBalances();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "RISK_UPDATE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function connectEd25519(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!operator || connecting || !ed25519Key.trim()) return;

    const csrf = getCsrfToken();
    if (!csrf) {
      setConnectionMessage("CSRF_TOKEN_REQUIRED");
      return;
    }

    setConnecting(true);
    setConnectionMessage("");

    try {
      const response = await fetch(
        "/api/v1/trading/ed25519/connect",
        {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            "Content-Type": "application/json",
            "X-NEX-CSRF": csrf,
          },
          body: JSON.stringify({ api_key: ed25519Key.trim() }),
        }
      );

      if (!response.ok) {
        throw new Error(`ED25519_CONNECT_HTTP_${response.status}`);
      }

      setEd25519Key("");
      setConnectionMessage(
        ar ? "تم ربط Binance للقراءة فقط." :
             "Binance read-only connection saved."
      );
      await refresh();
      await refreshBalances();
    } catch (error) {
      setConnectionMessage(
        error instanceof Error ? error.message : "ED25519_CONNECT_FAILED"
      );
    } finally {
      setConnecting(false);
    }
  }

  return (
    <section className="panel" aria-label="Verified account-equity daily risk">
      <h2>{ar ? "نسبة الخسارة اليومية من حقوق ملكية الحساب" : "Daily equity-based loss percentage"}</h2>
      <p className="notice">
        {ar
          ? "المستخدم يحدد النسبة، ولا توجد قيمة مفروضة مسبقًا. عرض الرصيد الحقيقي يعتمد على مفتاح Binance للقراءة فقط. هذا فحص مخاطر فعلي، لكن محرك الأوامر الحقيقي لم يُربط بعد ولا يتم تنفيذ أي صفقة من هذه الصفحة."
          : "The user selects the percentage; no default is imposed. Real equity requires a Binance read-only connection. This is a real risk monitor, not yet attached to a live order executor."}
      </p>
      {operator && (
        <form onSubmit={connectEd25519}>
          <label htmlFor="hunter-ed25519-api-key">
            {ar ? "Binance API Key (Ed25519)" : "Binance API Key (Ed25519)"}
          </label>
          <input
            id="hunter-ed25519-api-key"
            type="password"
            autoComplete="off"
            value={ed25519Key}
            onChange={(event) => setEd25519Key(event.target.value)}
            minLength={10}
            maxLength={256}
            required
          />
          <button type="submit" disabled={connecting}>
            {connecting
              ? (ar ? "جارٍ التحقق..." : "Connecting...")
              : (ar ? "ربط Binance للقراءة فقط" : "Connect read-only")}
          </button>
          <p role="status">{connectionMessage}</p>
          <p>
            {ar
              ? "الاتصال للقراءة فقط. لا تُرسل أوامر تداول، ولا يُشترط تقييد IP."
              : "Read-only connector. No orders; IP restriction is not required."}
          </p>
        </form>
      )}
      <div className="stat-row" aria-label="Binance balances">
        <div>
          <strong>Spot (USDT): </strong>
          <bdi dir="ltr">{balances?.spot_usdt ?? "—"}</bdi>
        </div>
        <div>
          <strong>Futures (USDT): </strong>
          <bdi dir="ltr">{balances?.futures_usdt ?? "—"}</bdi>
        </div>
        <div>
          <strong>{ar ? "الإجمالي (USDT)" : "Total (USDT)"}: </strong>
          <bdi dir="ltr">{balances?.total_usdt ?? "—"}</bdi>
        </div>
      </div>
      {balances && !balances.valuation_complete && (
        <p role="status" className="notice">
          {ar
            ? `تقييم Spot غير مكتمل: ${balances.unpriced_assets_count} أصول بلا سعر متاح. تم إخفاء الإجمالي.`
            : `Spot valuation incomplete: ${balances.unpriced_assets_count} unpriced assets. Total hidden.`}
        </p>
      )}
      {balances && (
        <p className="muted">
          {ar
            ? "التقييم تقريبي بأسعار السوق الأخيرة، وليس قيمة تنفيذ مضمونة. لا توجد أوامر تداول."
            : "Indicative last-market-price valuation; no orders are submitted."}
        </p>
      )}
      {!balances && state === "authenticated" && (
        <p role="status" className="muted">{balanceStatus}</p>
      )}
      <p><strong>{ar ? "الحد المحفوظ" : "Saved limit"}:</strong>{" "}
        <bdi dir="ltr">{snapshot?.daily_loss_pct ? `${snapshot.daily_loss_pct}%` : (ar ? "غير محدد" : "Not set")}</bdi>
      </p>
      <p><strong>{ar ? "الحالة" : "Status"}:</strong>{" "}{snapshot?.state ?? (ar ? "غير متاح" : "Unavailable")}</p>
      {snapshot?.opening_equity && (
        <div className="stat-row" aria-live="polite">
          <div><strong>{ar ? "أول Equity موثّق اليوم (UTC)" : "First observed UTC-day equity"}:</strong>{" "}
            <bdi dir="ltr">{snapshot.opening_equity} USDT</bdi></div>
          <div><strong>{ar ? "Equity الحالي" : "Current equity"}:</strong>{" "}
            <bdi dir="ltr">{snapshot.current_equity} USDT</bdi></div>
          <div><strong>{ar ? "خسارة اليوم" : "Today's loss"}:</strong>{" "}
            <bdi dir="ltr">{snapshot.daily_loss_amount} USDT</bdi></div>
          <div><strong>{ar ? "حد الخسارة" : "Daily loss budget"}:</strong>{" "}
            <bdi dir="ltr">{snapshot.loss_budget} USDT</bdi></div>
        </div>
      )}
      {snapshot?.new_entries_blocked && (
        <p className="notice">
          {ar ? "القرار التحليلي: ممنوع فتح صفقات جديدة حتى تتحقق سياسة المخاطر. هذا لا يعني أن التنفيذ متصل." :
            "Risk analysis blocks new entries. This screen is not connected to order execution."}
        </p>
      )}
      <form onSubmit={event => { void submit(event); }}>
        <label className="field">
          <span>{ar ? "أدخل الحد الذي تختاره (%)" : "Your chosen daily loss limit (%)"}</span>
          <input type="number" inputMode="decimal" min="0.0001" max="100" step="0.0001"
            placeholder={ar ? "بدون نسبة افتراضية" : "No default"}
            value={chosen} onChange={event => setChosen(event.target.value)}
            disabled={busy || !operator} required />
        </label>
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <button className="button" type="submit" disabled={busy || !operator}>
            {ar ? "حفظ حد الخسارة على الخادم" : "Save server daily limit"}
          </button>
          <button className="button" type="button" disabled={busy || state !== "authenticated"}
            onClick={() => { void refresh(); }}>
            {ar ? "تحديث Equity" : "Refresh equity"}
          </button>
        </div>
      </form>
      <p role="status" className="muted">{message}</p>
      <p className="muted">
        {ar ? "لا يُسمح بزيادة الحد داخل يوم المخاطرة النشط؛ يخضع الرفع لبدء يوم UTC جديد وقبل تثبيت رصيد البداية. الإيقاف بعد تجاوز الحد يبقى ثابتًا حتى اليوم التالي."
          : "The daily limit cannot be raised during an active risk day. Breaches remain latched until the next UTC day."}
      </p>
    </section>
  );
}
