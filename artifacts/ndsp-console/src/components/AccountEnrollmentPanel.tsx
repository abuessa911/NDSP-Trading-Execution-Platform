"use client";

import Link from "./DocumentLink";
import { useI18n } from "../ndsp/i18n";
import { useAuth } from "./AuthProvider";
import AuthControls from "./AuthControls";

/**
 * Server-controlled account onboarding status.
 * This view intentionally cannot create or elevate accounts: the M1 API
 * requires verified identity and never creates privileged sessions locally.
 */
export default function AccountEnrollmentPanel({ registration = false }: { registration?: boolean }) {
  const { t, lang } = useI18n();
  const { state, identity, administratorMfaVerified } = useAuth();
  const signedIn = state === "authenticated" && identity !== null;
  const administrator = signedIn && administratorMfaVerified &&
    (identity.role === "ADMIN" || identity.role === "SUPER_ADMIN");
  const localized = (ar: string, en: string) => lang === "ar" ? ar : en;
  return (
    <section className="panel" aria-label={t(registration ? "Account Registration" : "Account Access")}>
      <div className="row">
        <div>
          <p className="eyebrow">{t("Server-governed identity")}</p>
          <h2>{t(registration ? "Account Registration" : "Account Access")}</h2>
          <p className="muted">{t("Public self-registration is available with verified email. New accounts receive USER access only.")}</p>
        </div>
        <span className="tag">{t(signedIn ? "Authenticated" : "Not signed in")}</span>
      </div>
      <p role="status">
        {t(signedIn
          ? "Your authenticated session is active. The server determines your role and tenant."
          : state === "unavailable" || state === "unconfigured"
            ? "Authentication is temporarily unavailable. Please retry when the provider is ready."
            : "Use the sign-in buttons below to access your account, or create a new verified-email account.")}
      </p>
      {signedIn && (
        <div className="admin-audit-summary">
          <div><span>{t("Email")}</span><strong dir="ltr">{identity.email}</strong></div>
          {administrator && <div><span>{t("Administrator MFA")}</span><strong>{t("Verified by the server")}</strong></div>}
        </div>
      )}
      {registration && (
        <div className="notice" role="note">
          <strong>{t("Verified self-registration")}</strong>
          <p>{t("Create a personal account through /registration/. Email verification is mandatory and new accounts have no administrator or trading execution permissions.")}</p>
        </div>
      )}
      <AuthControls />
      <div className="demo-actions" aria-label={localized("روابط الحساب", "Account links")}>
        {signedIn ? <>
          <Link className="button" href="/dashboard/">{localized("لوحة التحكم", "Dashboard")}</Link>
          <Link className="button" href="/settings/">{t("Account settings")}</Link>
          {administrator && <Link className="button" href="/admin/users-tenants/">{t("Administrator user directory")}</Link>}
        </> : <>
          <Link className="button" href="/registration/">{localized("إنشاء حساب جديد بدون دعوة", "Create an account without an invitation")}</Link>
          <Link className="button" href="/login/">{localized("صفحة تسجيل الدخول", "Sign-in page")}</Link>
        </>}
      </div>
      <p className="muted">{t("No user is created, role changed, or trading enabled from this page.")}</p>
    </section>
  );
}
