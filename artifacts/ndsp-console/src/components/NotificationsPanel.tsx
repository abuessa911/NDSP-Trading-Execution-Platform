"use client";

import { useAuth } from "./AuthProvider";
import { useI18n } from "../ndsp/i18n";

/**
 * Designly foundation for the Bot's authenticated notification center.
 * No client-owned entitlement, bot token, chat ID, payment or execution switch.
 * Transport and per-user outbox must be connected to tenant-scoped server APIs
 * before interactive channel toggles are enabled.
 */
export default function NotificationsPanel() {
  const { state, identity } = useAuth();
  const { lang } = useI18n();
  const ar = lang === "ar";

  if (state === "loading") return <section className="panel" role="status">{ar ? "جارٍ التحقق من جلسة المستخدم…" : "Checking your session…"}</section>;
  if (state !== "authenticated" || !identity) return (
    <section className="panel" role="status">
      <h2>{ar ? "مركز الإشعارات" : "Notification center"}</h2>
      <p>{ar ? "يلزم تسجيل الدخول عبر موفر الهوية المعتمد قبل الوصول إلى إعدادات التنبيهات." : "Sign in with the configured identity provider to access notification preferences."}</p>
    </section>
  );

  return <section className="panel" dir={ar ? "rtl" : "ltr"} aria-labelledby="bot-alert-title">
    <h2 id="bot-alert-title">{ar ? "إشعارات حساب البوت" : "Bot account notifications"}</h2>
    <p className="muted">
      {ar
        ? "إعدادات الإشعارات ستكون خاصة بمستخدمك ومؤسستك. الإرسال بالبريد وتيليجرام غير متاح في مرحلة M1 حتى اعتماد القناة وربطها بالخادم."
        : "Notifications must be scoped to your identity and tenant. Email and Telegram delivery remain unavailable in M1 until the server channel is reviewed and connected."}
    </p>
    <div className="toolbar" role="list" aria-label={ar ? "حالة القنوات" : "Channel status"}>
      <div className="field" role="listitem">
        <strong>{ar ? "داخل التطبيق" : "In-app"}</strong>
        <p className="muted">{ar ? "بانتظار سجل تنبيهات المستخدم المعتمد" : "Awaiting the governed per-user notification ledger"}</p>
      </div>
      <div className="field" role="listitem">
        <strong>{ar ? "البريد الإلكتروني" : "Email"}</strong>
        <p className="muted">{ar ? "غير مفعّل — يتطلب التحقق من ملكية البريد" : "Not enabled — verified email ownership required"}</p>
      </div>
      <div className="field" role="listitem">
        <strong>Telegram</strong>
        <p className="muted">{ar ? "غير مفعّل — يتطلب ربط محادثة خاصة برمز مؤقت" : "Not enabled — private-chat proof with an expiring code is required"}</p>
      </div>
    </div>
    <p className="notice" role="status">
      {ar
        ? "هذه صفحة حالة صادقة وليست محاكاة لإرسال إشعارات. لن تؤدي أي رسالة لاحقًا إلى فتح أو إغلاق صفقة."
        : "This is an explicit availability view, not simulated delivery. Notifications never open or close trades."}
    </p>
  </section>;
}
