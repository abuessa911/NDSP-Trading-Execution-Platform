"use client";
import Link from "./DocumentLink";
import { useI18n } from "../ndsp/i18n";
import { ownerGuide, userGuide, type GuideChapter } from "./guide-data";
import AdminAccessGate from "./AdminAccessGate";

function ManualBody({ chapters, owner }: { chapters: GuideChapter[]; owner: boolean }) {
  const { lang } = useI18n();
  const translate = (ar: string, en: string) => lang === "ar" ? ar : en;
  return <div className="manual-layout" lang={lang} dir={lang === "ar" ? "rtl" : "ltr"}>
    <aside className="manual-toc panel" aria-label={translate("فهرس الدليل", "Manual contents")}>
      <h2>{translate("فهرس المحتويات", "Contents")}</h2>
      <ol>{chapters.map((chapter, i) => <li key={chapter.id}>
        <a href={"#guide-" + chapter.id}>{chapter.title[lang]}</a>
      </li>)}</ol>
    </aside>
    <div className="manual-body">
      <section className="panel manual-intro">
        <p className="eyebrow">{owner ? translate("دليل المالك · إدارة النظام", "Owner handbook · administration") : translate("دليل المستخدم · جميع الحسابات", "User manual · all accounts")}</p>
        <h2>{owner ? translate("دليل تشغيل وإدارة البوت", "Bot ownership and operations handbook") : translate("دليل استخدام hunter_ksa1 bot", "Using hunter_ksa1 bot")}</h2>
        <p>{owner
          ? translate("دليل الوظائف الموجودة وحدود الأمان وحوكمة التشغيل. قراءة هذا الدليل لا تغيّر الخادم.", "Guide to existing functions, safety boundaries and operation governance. Reading it changes no server settings.")
          : translate("دليل قراءة فقط يشرح الصفحات وخطوات التشغيل وقواعد الاستراتيجيات البحثية، مع التمييز بين الخادم الحقيقي والمحاكاة.", "Guide to pages and controls, distinguishing real backend behavior from demo previews.")}</p>
        <p className="notice">{translate("تنبيه: البوت مستقل عن NDSP. التداول الحقيقي معطل، وبعض الصفحات ما زالت معاينات.", "Important: This bot is independent from NDSP. Live trading is disabled, and some pages remain previews.")}</p>
        <p className="muted">{translate("تغيير اللغة AR / EN في أعلى الموقع يترجم الدليل كله.", "Use AR / EN in the site header to translate the entire guide.")}</p>
      </section>
      {chapters.map((chapter, i) => <section key={chapter.id} id={"guide-" + chapter.id} className="panel manual-chapter">
        <p className="eyebrow">{translate("الفصل", "Chapter")} {i + 1} / {chapters.length}</p>
        <h2>{chapter.title[lang]}</h2>
        <p className="muted">{chapter.lead[lang]}</p>
        <ol>{chapter.items.map((item,j) => <li key={j}>{item[lang]}</li>)}</ol>
        {chapter.href && <Link className="button" href={chapter.href}>{translate("فتح الصفحة المتعلقة بالفصل", "Open related page")}</Link>}
      </section>)}
      <p className="muted manual-final">{translate("نهاية الدليل. أمثلة الواجهة ليست تصريحًا للتداول الحقيقي.", "End of guide. Interface examples do not authorize real trading.")}</p>
    </div>
  </div>;
}
export function UserGuide() { return <ManualBody chapters={userGuide} owner={false} />; }
export function OwnerGuide() { return <AdminAccessGate><ManualBody chapters={ownerGuide} owner /></AdminAccessGate>; }
