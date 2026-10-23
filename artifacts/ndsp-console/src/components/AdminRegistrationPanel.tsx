"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  getBrowserAdminRegistrations, createBrowserAdminRegistration,
  type RegistrationInvitation,
} from "@workspace/api-client-react";
import { useAuth, browserRequest } from "./AuthProvider";
import { useI18n } from "../ndsp/i18n";

type ErrorInfo = { status?: number; data?: { reason_code?: string } };
const safeCode = (value: unknown): string | null =>
  typeof value === "string" && /^[A-Z0-9_]{1,60}$/.test(value) ? value : null;

export default function AdminRegistrationPanel() {
  const { state, administratorMfaVerified, identity, getCsrfToken, revalidate } = useAuth();
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [rows, setRows] = useState<RegistrationInvitation[]>([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const authorized = state === "authenticated" && administratorMfaVerified &&
    (identity?.role === "ADMIN" || identity?.role === "SUPER_ADMIN");

  const refresh = useCallback(async () => {
    if (!authorized) return;
    setLoading(true);
    try {
      const response = await getBrowserAdminRegistrations(browserRequest);
      setRows(response.invitations);
      setError(null);
    } catch (cause) {
      const issue = cause as ErrorInfo;
      setError(safeCode(issue.data?.reason_code) ?? "REGISTRATIONS_UNAVAILABLE");
      if (issue.status === 401 || issue.status === 403) void revalidate();
    } finally {
      setLoading(false);
    }
  }, [authorized, revalidate]);

  useEffect(() => {
    if (!authorized) { setRows([]); setResult(null); return; }
    void refresh();
  }, [authorized, refresh]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!authorized || busy) return;
    const csrf = getCsrfToken();
    if (!csrf) { setError("SESSION_CSRF_NOT_AVAILABLE"); return; }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const created = await createBrowserAdminRegistration(email.trim().toLowerCase(), csrf, browserRequest);
      if (created.status !== "PENDING" || created.role !== "USER") {
        throw new Error("INVALID_REGISTRATION_RESULT");
      }
      setEmail("");
      setResult("Registration request saved as pending. No email has been sent.");
      await refresh();
    } catch (cause) {
      const issue = cause as ErrorInfo;
      setError(safeCode(issue.data?.reason_code) ?? "REGISTRATION_NOT_SAVED");
      if (issue.status === 401 || issue.status === 403) void revalidate();
    } finally {
      setBusy(false);
    }
  }

  if (!authorized) return null;
  return <section className="panel admin-directory" aria-label={t("Protected account registration")}>
    <div className="row admin-panel-heading">
      <div>
        <p className="eyebrow">{t("MFA REQUIRED · SERVER CONTROLLED")}</p>
        <h2>{t("Protected account registration")}</h2>
        <p className="muted">{t("Invite only verified identity-provider accounts. New accounts always receive USER access. Passwords are never collected here.")}</p>
      </div>
    </div>
    <form onSubmit={e => void submit(e)}>
      <label className="field">
        <span>{t("New user's email")}</span>
        <input type="email" autoComplete="off" inputMode="email" dir="ltr" required
          maxLength={254} value={email} onChange={e => setEmail(e.target.value)}
          placeholder="user@example.com" disabled={busy || loading} />
      </label>
      <p className="muted">{t("The identity provider must verify this address before the pending account activates. No invitation email is sent automatically.")}</p>
      <button className="button" type="submit" disabled={!email.trim() || busy || loading}>
        {busy ? t("Saving registration…") : t("Create pending registration")}
      </button>
    </form>
    {error && <p role="alert" className="admin-error">{t("Registration unavailable")}: {error}</p>}
    {result && <p role="status">{t(result)}</p>}
    <div className="row">
      <h3>{t("Registration requests")}</h3>
      <button className="button" type="button" disabled={busy || loading} onClick={() => void refresh()}>
        {t("Refresh requests")}
      </button>
    </div>
    {loading ? <p role="status">{t("Loading registrations…")}</p> : rows.length ? (
      <div className="admin-audit-table-wrap"><table className="admin-audit-table">
        <thead><tr><th>{t("Email")}</th><th>{t("Role")}</th><th>{t("Status")}</th><th>{t("Expires")}</th></tr></thead>
        <tbody>{rows.map(row => <tr key={row.id}>
          <td dir="ltr">{row.email}</td><td>{row.role}</td><td>{t(row.status)}</td>
          <td>{new Date(row.expires_at).toLocaleDateString()}</td>
        </tr>)}</tbody>
      </table></div>
    ) : <p className="muted">{t("No registration requests available.")}</p>}
  </section>;
}
