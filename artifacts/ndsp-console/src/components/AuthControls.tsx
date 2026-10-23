"use client";

import Link from "./DocumentLink";
import { useAuth } from "./AuthProvider";
import { useI18n } from "../ndsp/i18n";

/** Ordinary user account UI; server session is the only authentication authority. */
export default function AuthControls() {
  const { state, identity, busy, message, act, revalidate } = useAuth();
  const { t } = useI18n();
  if (state === "loading") {
    return <section className="panel" aria-label={t("Account status")}>
      <p role="status" className="muted">{t("Checking authentication configuration…")}</p>
      <a className="button hunter-auth-nohydrate" href="/api/v1/auth/start">{t("Sign in")}</a>
    </section>;
  }
  if (state === "authenticated" && identity) {
    return <section className="panel" aria-label={t("Account status")}>
      <div className="row"><div><h2>{t("Account connected")}</h2><p className="muted">{t("Signed in as")} <bdi dir="ltr">{identity.email}</bdi></p></div>
        <div className="row"><Link className="button" href="/dashboard/">{t("Dashboard")}</Link>
          <button type="button" className="button" disabled={busy} onClick={() => void act("logout")}>{t("Sign out")}</button></div>
      </div>
    </section>;
  }
  return <section className="panel" aria-label={t("Account status")}>
    <div className="row"><div><h2>{t("Sign in to your account")}</h2>
      <p role="status" className="muted">{state === "anonymous" ? t("Your email verification does not automatically sign you in. Please sign in to continue.") : t(message)}</p></div>
      <div className="row">
        {state === "anonymous" && <a className="button" href="/api/v1/auth/start">{t("Sign in")}</a>}
        <button type="button" className="button" disabled={busy} onClick={() => void revalidate()}>{t("Check session")}</button>
      </div>
    </div>
    <p className="muted">{t("Accounts require verified email.")}</p>
  </section>;
}
