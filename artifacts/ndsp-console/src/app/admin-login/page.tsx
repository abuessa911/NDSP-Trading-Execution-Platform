import type { Metadata } from "next";
import Link from "next/link";
export const metadata: Metadata = { title: "بوابة المدير | Hunter KSA1", robots: { index: false, follow: false } };
export default function AdminLogin() {
  return <main className="hunter-public hunter-auth-page" dir="rtl"><div className="hunter-auth-wrap">
    <Link href="/" className="hunter-return">← العودة للرئيسية</Link>
    <section className="hunter-auth-card">
      <h1>بوابة إدارة HUNTER KSA1</h1>
      <p>دخول المدير فقط. يتطلب كلمة المرور والتحقق الثنائي TOTP وحسابًا مخوّلًا بدور إداري. يفرض الخادم الصلاحيات على كل طلب محمي.</p>
      <div className="hunter-auth-inner"><a className="hunter-primary-link" href="/api/v1/auth/start?admin_mfa=true">الدخول الآمن للمدير ←</a></div>
    </section></div></main>;
}
