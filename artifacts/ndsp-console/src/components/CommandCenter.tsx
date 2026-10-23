"use client";

import Link from "./DocumentLink";
import { useI18n } from "../ndsp/i18n";
import HealthPanel from "./HealthPanel";
import HunterStrategyScannerPanel from "./HunterStrategyScannerPanel";

export default function CommandCenter() {
  const { lang } = useI18n();
  const ar = lang === "ar";
  return <>
    <section className="panel hunter-operator-intro">
      <h2>{ar ? "تشغيل البوت والاستراتيجيات" : "Bot and strategy controls"}</h2>
      <p>{ar
        ? "زر تشغيل البوت وإيقافه موجود أعلى الصفحة. اختر الأصل والإطار الزمني والنمط، ثم اضغط تأكيد / تطبيق. يمكنك مراجعة الاستراتيجيات أدناه وتشغيل الفحص المرتبط بها."
        : "Use the main bot power control at the top. Choose an asset, interval and trading style, then Confirm / Apply. Review and run the available strategy scanners below."}</p>
      <p className="muted">{ar
        ? "حالة التشغيل تأتي من الخادم. فحوص الاستراتيجيات تستخدم شموعًا مغلقة حقيقية، لكنها ليست أوامر تداول. التداول الحقيقي غير مفعل حتى تتحقق جميع شروط الاتصال والمخاطر."
        : "Power state comes from the server. Strategy scanners use real closed candles but do not submit trades. Real order execution remains unavailable until connection and risk gates pass."}</p>
      <div className="row">
        <Link className="button" href="/strategies/">{ar ? "إدارة الاستراتيجيات" : "Manage strategies"}</Link>
        <Link className="button" href="/settings/">{ar ? "إعدادات الاتصال" : "Connection settings"}</Link>
      </div>
    </section>
    <HunterStrategyScannerPanel />
    <HealthPanel />
  </>;
}
