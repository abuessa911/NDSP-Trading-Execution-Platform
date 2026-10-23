"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "./AuthProvider";
import { useI18n } from "../ndsp/i18n";

type Power = {
  status: "STOPPED" | "RUNNING" | "STOPPING" | "DEGRADED";
  issues: string[];
  powered: boolean;
  waiting_for_strategy: boolean;
  selected_strategy_id: string | null;
  monitor: "STOPPED" | "MONITORING" | "STALLED";
  scanners: number;
  paper_running: boolean;
  testnet_automation: string;
  testnet_position_requires_review: boolean;
  live_orders_enabled: false;
  private_ndsp_strategies_connected: false;
};
const endpoint = "/api/v1/trading/bot";

function valid(v: unknown): v is Power {
  if (!v || typeof v !== "object") return false;
  const x = v as Partial<Power>;
  return ["STOPPED", "RUNNING", "STOPPING", "DEGRADED"].includes(x.status ?? "") &&
    Array.isArray(x.issues) && x.issues.every(code => typeof code === "string") &&
    ["STOPPED", "MONITORING", "STALLED"].includes(x.monitor ?? "") &&
    typeof x.powered === "boolean" && typeof x.waiting_for_strategy === "boolean" &&
    (x.selected_strategy_id === null || typeof x.selected_strategy_id === "string") &&
    typeof x.scanners === "number" && typeof x.paper_running === "boolean" &&
    typeof x.testnet_position_requires_review === "boolean" &&
    x.live_orders_enabled === false && x.private_ndsp_strategies_connected === false;
}

export default function BotPowerControl() {
  const { lang } = useI18n();
  const ar = lang === "ar";
  const { state: auth, identity, administratorMfaVerified, getCsrfToken, revalidate } = useAuth();
  const allowed = auth === "authenticated" && administratorMfaVerified &&
    (identity?.role === "ADMIN" || identity?.role === "SUPER_ADMIN");
  const subject = identity ? identity.tenant_id + ":" + identity.user_id : null;
  const [power, setPower] = useState<Power | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const epoch = useRef(0);
  const refresh = useCallback(async () => {
    const id = ++epoch.current;
    if (!allowed) { setPower(null); return; }
    try {
      const response = await fetch(endpoint, {
        credentials: "same-origin", cache: "no-store", signal: AbortSignal.timeout(12000),
      });
      if (response.status === 401) {
        if (epoch.current === id) {
          setPower(null);
          setMessage(ar ? "انتهت جلسة الدخول أو أُلغيت. يرجى تسجيل الدخول من جديد." :
            "Your session expired or was revoked. Please sign in again.");
          void revalidate();
        }
        return;
      }
      const data: unknown = await response.json();
      if (!response.ok || !valid(data)) {
        const code = data && typeof data === "object" && "reason_code" in data
          ? String(data.reason_code) : `BOT_STATUS_HTTP_${response.status}`;
        throw Error(code);
      }
      if (epoch.current === id) setPower(data);
    } catch (error) {
      if (epoch.current === id) {
        setPower(null);
        const code = error instanceof Error ? error.message : "BOT_STATE_UNAVAILABLE";
        setMessage((ar ? "تعذر قراءة حالة البوت: " : "Bot status unavailable: ") + code);
      }
    }
  }, [allowed, subject, ar, revalidate]);
  useEffect(() => {
    setPower(null); setMessage("");
    void refresh();
    const timer = window.setInterval(() => void refresh(), 15000);
    return () => { epoch.current++; window.clearInterval(timer); };
  }, [refresh]);

  async function switchPower(action: "start" | "stop") {
    const csrf = getCsrfToken();
    if (!allowed || !csrf || busy || !power) return;
    setBusy(true); setMessage("");
    try {
      const reply = await fetch(endpoint + "/" + action, {
        method: "POST", credentials: "same-origin", cache: "no-store",
        signal: AbortSignal.timeout(30000), headers: { "X-NEX-CSRF": csrf },
      });
      if (reply.status === 401) {
        setPower(null);
        setMessage(ar ? "انتهت جلسة الدخول أو أُلغيت. يرجى تسجيل الدخول من جديد." :
          "Your session expired or was revoked. Please sign in again.");
        void revalidate();
        return;
      }
      const data: unknown = await reply.json();
      if (!reply.ok || !valid(data)) {
        const reason = data && typeof data === "object" && "reason_code" in data
          ? String(data.reason_code) : "BOT_CONTROL_REJECTED";
        throw Error(reason);
      }
      setPower(data);
      setMessage(action === "stop"
        ? (ar ? "أُرسل طلب الإيقاف وتمت قراءة الحالة من الخادم." : "Stop requested; server state verified.")
        : (ar ? "بدأت المراقبة. التداول الحقيقي وربط TDL وNMP لم يُفعّلا." :
          "Monitoring started. Live trading and TDL/NMP integration remain unavailable."));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "BOT_CONTROL_UNAVAILABLE");
      await refresh();
    } finally { setBusy(false); }
  }

  if (!allowed) return null;
  const status = power?.status;
  // Status DEGRADED can be caused only by an unrelated unavailable Testnet
  // inspection. Do not turn the off button into a misleading "Safe stop".
  const operating = !!power && (
    power.powered || power.monitor !== "STOPPED" || power.scanners > 0 ||
    power.paper_running || ["RUNNING", "STOPPING"].includes(power.testnet_automation)
  );
  const label = status === "STOPPING" ? (ar ? "جارٍ الإيقاف" : "Stopping")
    : status === "DEGRADED" ? (ar ? "فحص خدمة مساندة غير مكتمل" : "Auxiliary health unverified")
    : operating ? (ar ? "يعمل" : "Running")
    : status === "STOPPED" ? (ar ? "متوقف" : "Stopped")
    : (ar ? "الحالة غير متاحة" : "Unavailable");
  const issuesText = power?.issues.map(code => code === "TESTNET_STATUS_UNAVAILABLE"
    ? (ar ? "تعذر التحقق من خدمة التنفيذ المنفصلة" : "Separate execution service could not be checked")
    : code).join(ar ? "، " : ", ");
  return <div className="hunter-bot-power" aria-label={ar ? "التحكم الرئيسي بالبوت" : "Main bot control"}>
    <span role="status" aria-live="polite">{ar ? "حالة البوت" : "Bot"}: <strong>{label}</strong></span>
    <button type="button" className="button small hunter-bot-power-action"
      aria-label={!power ? (ar ? "إعادة فحص البوت" : "Retry bot status")
        : operating ? (ar ? "إيقاف البوت" : "Stop bot")
        : (ar ? "تشغيل البوت" : "Start bot")}
      disabled={busy || status === "STOPPING"}
      onClick={() => !power ? void refresh() : void switchPower(operating ? "stop" : "start")}>
      {!power ? (ar ? "إعادة الفحص" : "Retry")
        : operating ? (ar ? "إيقاف البوت" : "Stop bot")
        : (ar ? "تشغيل البوت" : "Start bot")}
    </button>
    {power && power.issues.length > 0 && <small className="hunter-bot-status-issues" role="status">
      {ar ? "تنبيه حالة الخدمات: " : "Service check warning: "}{issuesText}
    </small>}
    {power?.testnet_position_requires_review && <small role="status">{ar ? "مركز تجريبي يحتاج مراجعة" : "Demo position requires review"}</small>}
    <small className="muted">{ar ? "زر التشغيل يدير أتمتة الفحص على الخادم؛ لا يفتح أوامر مالية قبل اجتياز بوابات التنفيذ." : "Power controls server-side scanner automation, not unauthorized order execution."}</small>
    {message && <small role="status">{message}</small>}
  </div>;
}
