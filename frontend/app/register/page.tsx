"use client";

import { useState } from "react";
import { HunterNav, t, useLang } from "../components/HunterShell";

export default function RegisterPage() {
  const { lang, setLang, dir } = useLang();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [message, setMessage] = useState("");

  async function register() {
    setMessage("");

    if (!email || !password) {
      setMessage(t(lang, "أدخل البريد وكلمة المرور.", "Enter email and password."));
      return;
    }

    if (password.length < 8) {
      setMessage(t(lang, "كلمة المرور يجب أن تكون 8 أحرف على الأقل.", "Password must be at least 8 characters."));
      return;
    }

    try {
      const res = await fetch("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          password,
          invite_code: inviteCode || null
        })
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(data?.detail || JSON.stringify(data) || "Register failed");
      }

      setMessage(t(lang, "تم التسجيل بنجاح. يمكنك الآن تسجيل الدخول.", "Registered successfully. You can now login."));
    } catch (e: any) {
      setMessage(t(lang, "فشل التسجيل: ", "Registration failed: ") + e.message);
    }
  }

  async function loginAfterRegister() {
    setMessage("");

    try {
      const form = new URLSearchParams();
      form.set("username", email);
      form.set("password", password);

      const res = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: form.toString()
      });

      const data = await res.json();

      if (!res.ok) throw new Error(data?.detail || "Login failed");

      localStorage.setItem("token", data.access_token);
      window.location.href = "/account";
    } catch (e: any) {
      setMessage(t(lang, "فشل تسجيل الدخول بعد التسجيل: ", "Login after register failed: ") + e.message);
    }
  }

  return (
    <main className="container hunter-page" dir={dir}>
      <HunterNav lang={lang} setLang={setLang} />

      <section className="hunter-hero register">
        <div>
          <p className="eyebrow">NDSP Access</p>
          <h1>{t(lang, "إنشاء حساب", "Create Account")}</h1>
          <p>{t(lang, "أنشئ حسابًا للدخول إلى لوحة تداول NDSP.", "Create an account to access NDSP Trading Dashboard.")}</p>
        </div>
        <div className="hunter-watermark">hunter_ksa1</div>
      </section>

      {message && <div className="hunter-alert">{message}</div>}

      <div className="hunter-grid two">
        <div className="hunter-card">
          <h2>{t(lang, "بيانات التسجيل", "Registration Details")}</h2>

          <label>{t(lang, "البريد الإلكتروني", "Email")}</label>
          <input className="input" value={email} onChange={e => setEmail(e.target.value)} placeholder="name@example.com" />

          <label>{t(lang, "كلمة المرور", "Password")}</label>
          <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} />

          <label>{t(lang, "كود الدعوة إن وجد", "Invite Code if available")}</label>
          <input className="input" value={inviteCode} onChange={e => setInviteCode(e.target.value)} />

          <button className="btn btn-primary" onClick={register}>
            {t(lang, "إنشاء الحساب", "Create Account")}
          </button>

          <button className="btn btn-secondary" onClick={loginAfterRegister}>
            {t(lang, "تسجيل الدخول بعد التسجيل", "Login After Register")}
          </button>
        </div>

        <div className="hunter-card">
          <h2>{t(lang, "تنبيهات الأمان", "Security Notes")}</h2>
          <ul className="hunter-list">
            <li>{t(lang, "لا تستخدم كلمة مرور ضعيفة.", "Do not use a weak password.")}</li>
            <li>{t(lang, "لا تشارك API Secret مع أي شخص.", "Never share your API Secret.")}</li>
            <li>{t(lang, "لا تفعّل صلاحية Withdraw في Binance.", "Never enable Withdraw permission in Binance.")}</li>
            <li>{t(lang, "في وضع live قد يتم تنفيذ صفقات حقيقية.", "In live mode, real trades may execute.")}</li>
            <li>{t(lang, "ابدأ دائمًا باختبارات NO_TRADE.", "Always start with NO_TRADE tests.")}</li>
          </ul>

          <a className="btn btn-danger" href="/">
            {t(lang, "العودة لتسجيل الدخول", "Back to Login")}
          </a>
        </div>
      </div>
    </main>
  );
}
