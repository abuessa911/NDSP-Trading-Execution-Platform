"use client";

import { useEffect, useState } from "react";
import { useAuth } from "../components/AuthProvider";
import { useI18n } from "./i18n";

type DecisionStyle = "INVESTMENT" | "SPECULATIVE";
type Profile = {
  mode: DecisionStyle;
  persisted: boolean;
  execution_authorized: false;
  ndsp_contract_bound: false;
};
const endpoint = "/api/v1/trading/profile";

function validProfile(input: unknown): input is Profile {
  if (!input || typeof input !== "object") return false;
  const p = input as Partial<Profile>;
  return (p.mode === "INVESTMENT" || p.mode === "SPECULATIVE") &&
    typeof p.persisted === "boolean" &&
    p.execution_authorized === false && p.ndsp_contract_bound === false;
}

export default function DecisionStyleSelector() {
  const { state, identity, getCsrfToken } = useAuth();
  const { t } = useI18n();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setProfile(null);
    if (state !== "authenticated" || !identity) {
      setMessage("Sign in to select a decision style.");
      return () => controller.abort();
    }
    setMessage("Loading server decision style…");
    void (async () => {
      try {
        const response = await fetch(endpoint, {
          credentials: "same-origin", cache: "no-store", signal: controller.signal,
        });
        if (!response.ok) throw new Error("SERVER_UNAVAILABLE");
        const data: unknown = await response.json();
        if (!validProfile(data)) throw new Error("INVALID_PROFILE");
        if (!controller.signal.aborted) {
          setProfile(data);
          setMessage(data.persisted
            ? "Decision style retrieved from Hunter backend."
            : "Default style shown. Choose a style to save it in Hunter backend.");
        }
      } catch {
        if (!controller.signal.aborted) setMessage("Server decision style unavailable. No change applied.");
      }
    })();
    return () => controller.abort();
  }, [state, identity?.user_id]);

  async function select(mode: DecisionStyle) {
    if (busy || state !== "authenticated" || !identity) return;
    const csrf = getCsrfToken();
    if (!csrf) {
      setMessage("Server session required; refresh your session.");
      return;
    }
    setBusy(true);
    setMessage("Saving decision style to Hunter backend…");
    try {
      const response = await fetch(endpoint, {
        method: "PUT", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json", "X-NEX-CSRF": csrf },
        body: JSON.stringify({ mode }),
      });
      if (!response.ok) throw new Error("SERVER_REJECTED");
      const data: unknown = await response.json();
      if (!validProfile(data) || data.mode !== mode || !data.persisted) throw new Error("INVALID_ACK");
      setProfile(data);
      setMessage("Saved by Hunter backend; this does not activate trading or connect NDSP.");
    } catch {
      setMessage("Saving failed. No decision style change was confirmed by the server.");
    } finally {
      setBusy(false);
    }
  }

  return <section className="panel" aria-label={t("Decision style")}>
    <h2>{t("Decision style")}</h2>
    <p className="muted">{t("Investment and speculation are strategy profiles, separate from manual and automatic execution.")}</p>
    <div className="seg full" role="group" aria-label={t("Decision style")}>
      {(["INVESTMENT", "SPECULATIVE"] as const).map(mode =>
        <button type="button" key={mode}
          aria-pressed={profile?.mode === mode}
          className={profile?.mode === mode ? "on" : ""}
          disabled={busy || state !== "authenticated" || !identity}
          onClick={() => void select(mode)}>{t(mode === "INVESTMENT" ? "Investment" : "Speculation")}</button>)}
    </div>
    <p role="status" className="muted">{t(message)}</p>
    <p className="notice">{t("The selection is saved in the bot backend only. No NDSP contract connection, automatic strategy activation, or order execution is authorized.")}</p>
  </section>;
}
