"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { previewArabic } from "./preview-copy";

export type Lang = "en" | "ar";
const ar: Record<string, string> = {
  ...previewArabic,
  "DEMO": "تجريبي", "DEMO ONLY": "للعرض التجريبي فقط", "Demo ceiling": "الحد التجريبي",
  "Sample": "عينة", "trend": "الاتجاه", "volatility": "التقلب",
  "Versions, assignments and paper/shadow/live readiness.": "الإصدارات والتخصيصات وجاهزية التداول الورقي والظل والتداول المباشر.",
  "Telegram/email setup, history and preferences.": "إعداد تيليجرام والبريد الإلكتروني والسجل والتفضيلات.",
  "Users / Tenants": "المستخدمون / المستأجرون", "Workers / Queues": "المهام الخلفية / قوائم الانتظار",
  "STOPPED": "متوقف", "BLOCKED": "محظور", "STATIC PREVIEW": "معاينة ثابتة",
  "MFA GUARDED": "محمي بالتحقق متعدد العوامل", "synthetic sample sequence": "تسلسل عينات اصطناعية",
  "synthetic samples": "عينات اصطناعية", "Insufficient sample data": "بيانات العينة غير كافية",
  "DEFERRED": "مؤجل", "Stage": "المرحلة",
  "24h": "24 ساعة",
  "Chart area and order ticket are placeholders. Buy/Sell cannot submit; no order is created anywhere.": "منطقة الرسم وتذكرة الأمر للعرض فقط. لا يمكن للشراء أو البيع إرسال أي أمر، ولا يُنشأ أي أمر في أي مكان.",
  "Read/acknowledgment actions only change this local preview. No alert is acknowledged in any backend.": "إجراءات القراءة والإقرار تغيّر هذه المعاينة المحلية فقط. لا يُسجَّل أي إقرار بتنبيه في الخادم.",
  "LINKUSDT long has no protective stop configured.": "مركز الشراء لرمز LINKUSDT بلا وقف خسارة وقائي مُعدّ.",
  "LINKUSDT has no stop": "لا يوجد وقف خسارة لرمز LINKUSDT",
  "DOGEUSDT entries: symbol limit": "دخول DOGEUSDT: حدّ الرمز",
  "2 active": "نشط: 2",
  "markets": "الأسواق", "positions": "المراكز", "orders": "الأوامر", "trades": "الصفقات",
  "alerts": "التنبيهات", "activity": "النشاط", "daily-pnl": "الربح والخسارة اليومية",
  "Command Center": "مركز القيادة", "Markets": "الأسواق", "Trading": "التداول", "Strategies": "الاستراتيجيات", "Positions": "المراكز", "Orders": "الأوامر",
  "Trade History": "سجل الصفقات", "Performance": "الأداء", "Risk Center": "مركز المخاطر", "NDSP Decisions": "قرارات NDSP", "Execution Trace / Why?": "تتبع التنفيذ / لماذا؟",
  "Replay Lab": "مختبر الإعادة", "Binance Connection": "اتصال بينانس", "Notifications": "التنبيهات", "Subscription": "الاشتراك", "Settings": "الإعدادات", "Service Health": "صحة الخدمة",
  "Audit Access": "الوصول للتدقيق", "Security": "الأمان", "Skip to content": "تخطي إلى المحتوى", "Search": "بحث", "All": "الكل", "Open": "مفتوح", "Filled": "منفذ", "Cancelled": "ملغى", "Rejected": "مرفوض",
  "DEMO DATA": "بيانات تجريبية", "NOT CONNECTED": "غير متصل", "READ-ONLY UI PREVIEW": "معاينة واجهة للقراءة فقط", "M1 NOT ACCEPTED": "M1 غير مقبول",
  "Simulation": "محاكاة", "Testnet": "شبكة اختبار", "Live": "مباشر", "Bot": "الروبوت", "Exchange": "المنصة", "Risk": "المخاطر", "Market data": "بيانات السوق", "Mode": "الوضع",
  "Balance": "الرصيد", "Available": "المتاح", "Margin used": "الهامش المستخدم", "Unrealized P&L": "الربح غير المحقق", "Realized P&L": "الربح المحقق", "Daily P&L": "ربح اليوم", "Weekly P&L": "ربح الأسبوع",
  "Close": "إغلاق", "Details": "التفاصيل", "Retry": "إعادة المحاولة", "Language": "اللغة", "Admin": "الإدارة", "Navigation": "التنقل", "Open navigation": "فتح القائمة", "Close navigation": "إغلاق القائمة",
  "Nothing here": "لا يوجد شيء", "Loading": "جار التحميل", "Symbol": "الرمز", "Side": "الاتجاه", "Status": "الحالة", "Strategy": "الاستراتيجية", "Price": "السعر", "Alerts": "التنبيهات", "Unread": "غير مقروء", "Acknowledged": "تم الإقرار",
  "Favorites": "المفضلة", "Real M1 data": "بيانات M1 الحقيقية", "Preview": "معاينة", "Demo preview": "معاينة تجريبية",
  "COMMAND": "القيادة", "BOOK": "المحفظة", "INTELLIGENCE": "التحليل", "CONTROL": "التحكم", "ACCOUNT": "الحساب",
  "Timeframe": "الإطار الزمني", "Signal": "الإشارة", "Position": "المركز", "Quantity": "الكمية", "Size": "الحجم", "Entry": "الدخول", "Exit": "الخروج", "Mark": "السعر الحالي",
  "Leverage": "الرافعة", "Stop": "وقف الخسارة", "Target": "الهدف", "Opened": "وقت الفتح", "Direction": "الاتجاه", "Time": "الوقت", "Order ID": "معرّف الأمر", "Type": "النوع",
  "Created": "الإنشاء", "Updated": "التحديث", "Severity": "الخطورة", "Category": "الفئة", "Subject": "الموضوع", "Alert": "تنبيه", "Volume": "الحجم", "Volatility": "التقلب", "Trend": "الاتجاه",
  "Win rate": "نسبة الفوز", "Total trades": "إجمالي الصفقات", "Trades": "الصفقات", "Result": "النتيجة", "Duration": "المدة", "Fees": "الرسوم", "Sample day": "يوم تجريبي",
  "Watching": "مراقبة", "Idle": "خامل", "Buy": "شراء", "Sell": "بيع", "Neutral": "محايد", "Read": "مقروء",
  "Market pulse": "حركة الأسواق", "Risk attention": "تنبيهات المخاطر", "Account exposure": "تعرّض الحساب", "Daily loss": "الخسارة اليومية", "Remaining capacity": "السعة المتبقية", "Open positions": "المراكز المفتوحة",
  "Activity Preview": "معاينة النشاط", "Event": "الحدث", "Actor": "الجهة",
};
type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (s: string) => string };
const I18n = createContext<Ctx>({ lang: "en", setLang: () => {}, t: s => s });

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  useEffect(() => { try { const v = localStorage.getItem("nex-lang"); if (v === "ar") setLangState("ar"); } catch { /* ignore */ } }, []);
  useEffect(() => { document.documentElement.lang = lang; document.documentElement.dir = lang === "ar" ? "rtl" : "ltr"; }, [lang]);
  const setLang = useCallback((l: Lang) => { setLangState(l); try { localStorage.setItem("nex-lang", l); } catch { /* ignore */ } }, []);
  const t = useCallback((s: string) => {
    if (lang === "en") return s;
    const core = s.trim();
    const exact = ar[core];
    if (exact) return s.replace(core, exact);
    // Translate presentation fragments without changing the underlying values.
    if (/ · | — /.test(core)) return core.split(/( · | — )/).map(part => ar[part] ?? part).join("");
    const sample = /^Sample (\d+)$/.exec(core);
    if (sample) return `${ar.Sample} ${sample[1]}`;
    const ceiling = /^Demo ceiling (.+)$/.exec(core);
    if (ceiling) return `${ar["Demo ceiling"]} ${ceiling[1]}`;
    const marketLabel = /^([A-Z0-9]+) (trend|volatility)$/.exec(core);
    if (marketLabel) return `${marketLabel[1]} ${ar[marketLabel[2]]}`;
    const pricePath = /^([A-Z0-9]+) synthetic illustrative price path$/.exec(core);
    if (pricePath) return `مسار سعري توضيحي اصطناعي لـ ${pricePath[1]}`;
    const allocation = /^(.+) risk allocation$/.exec(core);
    if (allocation) return `تخصيص المخاطر لـ ${allocation[1]}`;
    return s;
  }, [lang]);
  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <I18n.Provider value={value}>{children}</I18n.Provider>;
}
export const useI18n = () => useContext(I18n);
