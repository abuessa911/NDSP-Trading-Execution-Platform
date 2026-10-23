"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import {
  getAuthConfiguration, getBrowserSession, getMe, login, logout, refreshBrowserSession,
  type MeResponse, type SessionResult,
} from "@workspace/api-client-react";

export const browserRequest = { credentials: "same-origin" as const, cache: "no-store" as const };
type AuthState = "loading" | "authenticated" | "anonymous" | "unconfigured" | "unavailable";
type AuthContextValue = {
  state: AuthState;
  identity: MeResponse | null;
  administratorMfaVerified: boolean;
  busy: boolean;
  message: string;
  act: (action: "login" | "mfa_login" | "logout" | "refresh") => Promise<void>;
  revalidate: () => Promise<void>;
  getCsrfToken: () => string | null;
};
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>("loading");
  const [identity, setIdentity] = useState<MeResponse | null>(null);
  const [administratorMfaVerified, setAdministratorMfaVerified] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Checking authentication configuration…");
  // Session/CSRF data live only in memory, never props sent by a server or storage.
  const session = useRef<SessionResult | null>(null);
  const epoch = useRef(0);
  const inFlight = useRef(false);
  const actionInFlight = useRef(false);
  const mounted = useRef(true);
  const channel = useRef<BroadcastChannel | null>(null);

  const clear = useCallback(() => {
    epoch.current++;
    session.current = null;
    setIdentity(null);
    setAdministratorMfaVerified(false);
  }, []);

  const revalidate = useCallback(async () => {
    if (inFlight.current || actionInFlight.current) return;
    inFlight.current = true;
    const currentEpoch = epoch.current;
    const valid = () => mounted.current && currentEpoch === epoch.current;
    try {
      const config = await getAuthConfiguration(browserRequest);
      if (!valid()) return;
      if (!config.browser_login_enabled) {
        clear();
        setState("unconfigured");
        setMessage("Browser login is not configured in this environment.");
        return;
      }
      try {
        let current: SessionResult;
        try {
          current = await getBrowserSession(browserRequest);
        } catch (error) {
          // An access JWT can expire before the sealed browser session. Only
          // on a real HTTP 401 and with an existing in-memory CSRF proof do we
          // ask the server to rotate it; revoked or expired MFA still fails closed.
          const status = error && typeof error === "object" && "status" in error ? error.status : null;
          const csrf = session.current?.csrf_token;
          if (status !== 401 || !csrf || !valid()) throw error;
          await refreshBrowserSession({ ...browserRequest, headers: { "X-NEX-CSRF": csrf } });
          current = await getBrowserSession(browserRequest);
        }
        const me = await getMe(browserRequest);
        if (!valid()) return;
        if (!current.authenticated || current.user_id !== me.user_id || current.tenant_id !== me.tenant_id || current.role !== me.role) {
          throw new Error("Identity mismatch");
        }
        session.current = current;
        setIdentity(me);
        setAdministratorMfaVerified(current.administrator_mfa_verified === true);
        setState("authenticated");
        setMessage(current.administrator_mfa_verified
          ? "Authenticated administrator session; password + TOTP verified server-side."
          : "Authenticated application session.");
      } catch (error) {
        if (!valid()) return;
        // Only an explicit 401 proves the browser session is absent or invalid.
        // Network, gateway and provider failures must not appear as a logout.
        const status = error && typeof error === "object" && "status" in error ? error.status : null;
        clear();
        if (status === 401) {
          setState("anonymous");
          setMessage("Sign in with the configured identity provider. No protected access is granted.");
        } else {
          setState("unavailable");
          setMessage("Authentication service is unavailable. No access was granted.");
        }
      }
    } catch {
      if (!valid()) return;
      clear();
      setState("unavailable");
      setMessage("Authentication service is unavailable. No access was granted.");
    } finally {
      inFlight.current = false;
    }
  }, [clear]);

  useEffect(() => {
    mounted.current = true;
    void revalidate().then(() => {
      const url = new URL(window.location.href);
      const code = url.searchParams.get("auth_error");
      if (code && /^[A-Z0-9_]{1,60}$/.test(code)) {
        setMessage(`Sign-in rejected: ${code}`);
        url.searchParams.delete("auth_error");
        window.history.replaceState(null, "", url.pathname + url.search + url.hash);
      }
    });
    const timer = window.setInterval(() => void revalidate(), 30_000);
    const focus = () => {
      if (document.visibilityState === "visible") void revalidate();
    };
    window.addEventListener("focus", focus);
    document.addEventListener("visibilitychange", focus);
    // Send only a logout signal, no identity, tokens or session identifiers.
    if ("BroadcastChannel" in window) {
      channel.current = new BroadcastChannel("nex-session-status");
      channel.current.onmessage = (event) => {
        if (event.data === "logout") {
          clear();
          setState("anonymous");
          setMessage("Application session terminated in another tab.");
        }
      };
    }
    return () => {
      mounted.current = false;
      epoch.current++;
      inFlight.current = false;
      clearInterval(timer);
      window.removeEventListener("focus", focus);
      document.removeEventListener("visibilitychange", focus);
      channel.current?.close();
      channel.current = null;
    };
  }, [clear, revalidate]);

  async function act(action: "login" | "mfa_login" | "logout" | "refresh") {
    if (actionInFlight.current) return;
    actionInFlight.current = true;
    setBusy(true);
    // Invalidate earlier identity requests so they cannot restore state after logout.
    epoch.current++;
    try {
      if (action === "login" || action === "mfa_login") {
        const result = await login({ admin_mfa: action === "mfa_login" }, browserRequest);
        window.location.assign(result.authorization_url);
      } else {
        const csrf = session.current?.csrf_token;
        if (!csrf) throw new Error("No active session");
        const options = { ...browserRequest, headers: { "X-NEX-CSRF": csrf } };
        if (action === "logout") {
          setMessage("Terminating application session…");
          const result = await logout(options);
          // Do not advertise sign-out until the server acknowledges revocation.
          clear();
          setState("anonymous");
          channel.current?.postMessage("logout");
          setMessage("Application session terminated.");
          if (result.logout_url) window.location.assign(result.logout_url);
        } else {
          clear();
          const refreshEpoch = epoch.current;
          setState("loading");
          await refreshBrowserSession(options);
          const current = await getBrowserSession(browserRequest);
          const me = await getMe(browserRequest);
          if (!current.authenticated || current.user_id !== me.user_id || current.tenant_id !== me.tenant_id || current.role !== me.role) {
            throw new Error("Identity mismatch");
          }
          if (mounted.current && epoch.current === refreshEpoch) {
            session.current = current;
            setIdentity(me);
            setAdministratorMfaVerified(current.administrator_mfa_verified === true);
            setState("authenticated");
            setMessage("Session refreshed.");
          }
        }
      }
    } catch (error) {
      clear();
      setState(action === "logout" ? "unavailable" : "anonymous");
      const code = error instanceof Error
        ? error.message.replace(/[^A-Za-z0-9_ -]/g, "").slice(0, 100)
        : "UNKNOWN_ERROR";
      setMessage(action === "logout"
        ? "Sign-out could not be confirmed."
        : `Authentication failed: ${code}`);
    } finally {
      actionInFlight.current = false;
      setBusy(false);
    }
  }

  const getCsrfToken = () => session.current?.csrf_token ?? null;
  return <AuthContext.Provider value={{ state, identity, administratorMfaVerified, busy, message, act, revalidate, getCsrfToken }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider is required");
  return value;
}