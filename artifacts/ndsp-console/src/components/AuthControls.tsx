"use client";

import { useAuth } from "./AuthProvider";

export default function AuthControls() {
  const { state, identity, busy, message, act, revalidate } = useAuth();
  return (
    <section aria-label="M1 authentication" className="panel">
      <div className="row">
        <div>
          <h2>M1 authentication</h2>
          <p role="status" className="muted">{message}</p>
          {identity && <p className="muted">Role: {identity.role}</p>}
        </div>
        <div className="row">
          {state === "authenticated" ? <>
            <button className="button" disabled={busy} onClick={() => void act("refresh")}>Refresh session</button>
            <button className="button" disabled={busy} onClick={() => void act("logout")}>Sign out</button>
          </> : <>
            <button className="button" disabled={!["anonymous", "blocked"].includes(state) || busy} onClick={() => void act("login")}>Sign in</button>
            <button className="button" disabled={!["anonymous", "blocked"].includes(state) || busy} onClick={() => void act("mfa_login")}>Administrator MFA sign in</button>
            <button className="button" disabled={state === "loading" || busy} onClick={() => void revalidate()}>Check session</button>
          </>}
        </div>
      </div>
      <p className="muted">Administrator access requires fresh, server-verified password + TOTP MFA.</p>
    </section>
  );
}