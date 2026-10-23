"use client";

import { useI18n } from "./i18n";
import LiveMarketPreview from "./LiveMarketPreview";
import HunterControlPanel from "../components/HunterControlPanel";
import HunterStrategyScannerPanel from "../components/HunterStrategyScannerPanel";
import HunterExecutionReviewPanel from "../components/HunterExecutionReviewPanel";
import HunterEquityRiskPanel from "../components/HunterEquityRiskPanel";

// No seeded P&L, simulated positions, pretend orders or fictional NDSP decisions
// are exposed through production user routes. Unverified sources remain unavailable.
const unavailable: Record<string, [string, string]> = {
  positions: ["لم يكتمل ربط سجل المراكز الحقيقية بمصدر موثق.", "Verified real-position data is not connected yet."],
  orders: ["سجل الأوامر الفعلية غير مرتبط بمصدر تنفيذ موثق.", "Actual orders are not connected to a verified execution source."],
  "trade-history": ["سجل الصفقات المنفذة غير متاح حتى اعتماد مصدر التسوية.", "Trade history awaits a verified reconciliation source."],
  performance: ["لن نعرض أرباحًا أو نسب نجاح قبل توفر سجل صفقات موثق.", "Real performance requires verifiable trades, fees and P&L."],
  "ndsp-decisions": ["قرارات NDSP غير متاحة حتى اعتماد العقد والتحقق من المصدر.", "NDSP decisions require a verified source and approved contract."],
  "execution-trace": ["سجل تفسير التنفيذ غير متاح حتى تتوفر أدلة قرارات وأوامر فعلية.", "Execution trace needs real decision and order evidence."],
  "replay-lab": ["إعادة التشغيل غير متاحة دون بيانات تاريخية موثقة.", "Replay is unavailable without verified historical data."],
  notifications: ["سجل التنبيهات لم يُربط بخدمة إرسال موثقة.", "Notification history has no verified delivery source yet."],
  activity: ["سجل نشاط المستخدم الحقيقي غير متاح من هذا القسم.", "Real account activity is not available from this section."],
};
function Unavailable({ section }: { section: string }) {
  const { lang } = useI18n();
  const ar = lang === "ar";
  const note = unavailable[section] ?? ["بيانات المصدر غير متاحة.", "Source data unavailable."];
  return <section className="panel" role="status">
    <h2>{ar ? "غير متاح — مصدر غير موثق" : "Unavailable — no verified source"}</h2>
    <p>{note[ar ? 0 : 1]}</p>
    <p className="muted">{ar
      ? "لا تُعرض بيانات افتراضية بديلة، ولا يُفترض وجود تداول حقيقي عند غياب التأكيد."
      : "No fabricated substitute is displayed. Live execution is never inferred from unavailable data."}</p>
  </section>;
}
export default function PreviewWorkspace({ section }: { section: string }) {
  switch (section) {
    case "markets": return <LiveMarketPreview />;
    case "trading": return <><HunterControlPanel /><HunterStrategyScannerPanel /><HunterExecutionReviewPanel /><LiveMarketPreview /></>;
    case "strategies": return <HunterStrategyScannerPanel />;
    case "risk-center": return <HunterEquityRiskPanel />;
    case "binance-connection": return <HunterEquityRiskPanel />;
    default: return <Unavailable section={section} />;
  }
}
