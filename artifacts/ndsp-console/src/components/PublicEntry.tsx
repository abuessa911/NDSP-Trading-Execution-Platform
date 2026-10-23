"use client";
import { useEffect, useState } from "react";
import { useI18n, type Lang } from "../ndsp/i18n";

function usePublicLocale() {
  const [lang, setLocal] = useState<Lang>("ar");
  const [ready, setReady] = useState(false);
  const { setLang } = useI18n();
  useEffect(() => {
    let saved: string | null = null;
    try {
      const param = new URLSearchParams(window.location.search).get("lang");
      saved = param === "ar" || param === "en" ? param : window.localStorage.getItem("nex-lang");
    } catch { /* Browser storage may be disabled. */ }
    const chosen: Lang = saved === "en" ? "en" : "ar";
    setLocal(chosen);
    setLang(chosen);
    setReady(true);
  }, [setLang]);
  function choose(next: Lang) { setLocal(next); setLang(next); }
  return { lang, choose, ready };
}

function LocaleSelector({ lang, choose }: { lang: Lang; choose: (v: Lang) => void }) {
  return <div className="hunter-locale-selector" role="group" aria-label={lang === "ar" ? "لغة العرض" : "Display language"}>
    <button type="button" lang="ar" aria-pressed={lang === "ar"} onClick={() => choose("ar")}>العربية</button>
    <button type="button" lang="en" aria-pressed={lang === "en"} onClick={() => choose("en")}>English</button>
  </div>;
}

export default function PublicWelcome() {
  const { lang, choose } = usePublicLocale();
  const [authError, setAuthError] = useState<string | null>(null);
  useEffect(() => {
    const current = new URL(window.location.href);
    const error = current.searchParams.get("auth_error");
    if (!error) return;
    if (/^[A-Z0-9_]{1,60}$/.test(error)) setAuthError(error);
    current.searchParams.delete("auth_error");
    window.history.replaceState(null, "", current.pathname + current.search + current.hash);
  }, []);
  const ar = lang === "ar";
  const auth = `/api/v1/auth/start?lang=${lang}`;
  const register = `/registration/?lang=${lang}`;
  return <main className="hunter-public hunter-landing" dir={ar ? "rtl" : "ltr"}>
    <nav className="hunter-nav">
      <div className="hunter-brand"><span className="hunter-shield" aria-hidden="true">◆</span><div><strong>HUNTER KSA1</strong><small>{ar ? "منصة التداول الآلي" : "Automated trading platform"}</small></div></div>
      <div className="hunter-nav-actions"><LocaleSelector lang={lang} choose={choose}/></div>
    </nav>
    <section className="hunter-hero">
      {authError && <p className="hunter-auth-error-banner" role="alert">{ar
        ? `تعذّر إكمال تسجيل الدخول بأمان. رمز التشخيص: ${authError}. أعد المحاولة، وإذا استمرت المشكلة أبلغ الدعم بهذا الرمز.`
        : `Secure sign-in could not be completed. Diagnostic code: ${authError}. Retry, or share this code with support.`}</p>}
      <span className="hunter-version">HUNTER KSA1</span>
      <h1>{ar ? <>منصة واحدة. تحكم أوضح.<br/>قرارات تداول مدروسة.</> : <>One platform. Clear control.<br/>Informed trading decisions.</>}</h1>
      <p>{ar ? "راقب الاستراتيجيات، إشارات السوق، وحالة إدارة المخاطر في واجهة موحدة. التداول الورقي متاح للتجربة، ولا يعني جاهزية التداول الحقيقي." : "Monitor strategies, market signals, and risk controls in one place. Paper trading is for testing and does not imply live-trading readiness."}</p>
      <div className="hunter-hero-actions"><a className="hunter-primary-link" href={auth}>{ar ? "تسجيل الدخول ←" : "Sign in →"}</a><a className="hunter-secondary-link" href={register}>{ar ? "إنشاء حساب" : "Create account"}</a></div>
    </section>
    <section className="hunter-feature-grid">
      {(ar ? [["الاستراتيجيات","متابعة حالة الاستراتيجيات والإشارات."],["إدارة المخاطر","مراقبة ضوابط المخاطر وحالة إيقاف التنفيذ."],["التداول الورقي","اختبار التشغيل دون تعريض أموال حقيقية للخطر."]] : [["Strategies","Monitor strategy and signal status."],["Risk management","Monitor risk limits and execution-stop status."],["Paper trading","Test safely without putting real funds at risk."]]).map(([title,description])=><article className="hunter-feature" key={title}><h2>{title}</h2><p>{description}</p></article>)}
    </section>
    <footer className="hunter-landing-footer">{ar ? "تنبيه: التداول ينطوي على مخاطر مالية. بعض وظائف المنصة تجريبية." : "Warning: Trading involves financial risk. Some platform functions are experimental."}</footer>
  </main>;
}

export function PublicRegistration() {
  const { lang, choose } = usePublicLocale();
  const ar = lang === "ar";
  return <main className="hunter-public hunter-auth-page" dir={ar ? "rtl" : "ltr"}><div className="hunter-auth-wrap">
    <div className="hunter-public-auth-tools"><a href="/">{ar ? "← العودة للرئيسية" : "← Back to home"}</a><LocaleSelector lang={lang} choose={choose}/></div>
    <section className="hunter-auth-card">
      <header className="hunter-brand-row"><div className="hunter-brand"><span className="hunter-shield" aria-hidden="true">◆</span><div><strong>HUNTER KSA1</strong><small>{ar ? "منصة التداول الآلي" : "Automated trading platform"}</small></div></div></header>
      <h1>{ar ? "إنشاء الحساب" : "Create an account"}</h1><p className="hunter-auth-description">{ar ? "الانضمام إلى منصة Hunter KSA1" : "Join Hunter KSA1"}</p>
      <div className="hunter-auth-inner hunter-info">
        <h2>{ar ? "إنشاء حساب جديد" : "Create a new account"}</h2>
        <p>{ar ? "أنشئ حسابًا باستخدام البريد وكلمة المرور لدى مزود الهوية الآمن، ثم تحقق من بريدك الإلكتروني." : "Create an account with your email and password at our secure identity provider, then verify your email address."}</p>
        <p>{ar ? "يحصل الحساب الجديد على صلاحية مستخدم عادي فقط؛ ولا يمنح صلاحيات مدير أو يفعّل التداول الحقيقي." : "New accounts receive standard user access only. Registration does not grant administrator privileges or enable live trading."}</p>
        <a className="hunter-primary-link" href={`/api/v1/auth/start?register=true&lang=${lang}`}>{ar ? "إنشاء الحساب والتحقق من البريد ←" : "Create account and verify email →"}</a>
        <p>{ar ? "بعد تأكيد البريد يمكنك تسجيل الدخول بصورة آمنة." : "After confirming your email, sign in securely."}</p>
        <a href={`/api/v1/auth/start?lang=${lang}`}>{ar ? "الانتقال إلى تسجيل الدخول" : "Go to sign in"}</a>
      </div>
    </section>
  </div></main>;
}

export function PublicLoginRedirect() {
  const { lang, ready } = usePublicLocale();
  useEffect(() => { if (ready) window.location.replace(`/api/v1/auth/start?lang=${lang}`); }, [lang, ready]);
  return <main className="hunter-public hunter-auth-page" dir={lang === "ar" ? "rtl" : "ltr"}>
    <div className="hunter-auth-wrap"><section className="hunter-auth-card">
      <h1>{lang === "ar" ? "الانتقال إلى تسجيل الدخول الآمن" : "Continue to secure sign in"}</h1>
      <a className="hunter-primary-link" href={`/api/v1/auth/start?lang=${lang}`}>{lang === "ar" ? "متابعة" : "Continue"}</a>
    </section></div>
  </main>;
}
