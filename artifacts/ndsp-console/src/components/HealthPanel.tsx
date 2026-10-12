"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getLiveness, getReadiness, type ReadyResponse } from "@workspace/api-client-react";
import { browserRequest } from "./AuthProvider";

function isReadiness(value: unknown): value is ReadyResponse {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  return typeof candidate.status === "string"
    && (candidate.reason_code === null || typeof candidate.reason_code === "string")
    && !!candidate.components && typeof candidate.components === "object"
    && !Array.isArray(candidate.components)
    && Object.values(candidate.components).every(v => typeof v === "string");
}

export default function HealthPanel() {
  const [live, setLive] = useState<string | null>(null);
  const [ready, setReady] = useState<ReadyResponse | null>(null);
  const [busy, setBusy] = useState(true);
  const [checked, setChecked] = useState<Date | null>(null);
  const alive = useRef(true);
  const pending = useRef(false);

  const load = useCallback(async () => {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    const results = await Promise.allSettled([getLiveness(browserRequest), getReadiness(browserRequest)]);
    if (alive.current) {
      setLive(results[0].status === "fulfilled" ? results[0].value.status : null);
      const readiness = results[1];
      if (readiness.status === "fulfilled") setReady(readiness.value);
      else {
        // 503 is a real readiness result, not an empty success or fake green.
        const error = readiness.reason as { status?: number; data?: unknown };
        setReady(error?.status === 503 && isReadiness(error.data) ? error.data : null);
      }
      setChecked(new Date());
      setBusy(false);
    }
    pending.current = false;
  }, []);

  useEffect(() => {
    alive.current = true;
    void load();
    const timer = setInterval(() => void load(), 30_000);
    return () => { alive.current = false; clearInterval(timer); };
  }, [load]);

  return (
    <section className="panel">
      <div className="row"><h2>Control API health</h2><button className="button" disabled={busy} onClick={() => void load()}>Refresh health</button></div>
      <p className="muted" role="status">{busy ? "Checking live API…" : checked ? `Checked ${checked.toLocaleTimeString()}; refreshes every 30 seconds.` : "Not checked."}</p>
      <dl className="kv-list">
        <div className="kv-row"><dt>Liveness</dt><dd>{live ?? (busy ? "Checking" : "Unavailable")}</dd></div>
        <div className="kv-row"><dt>Readiness</dt><dd>{ready?.status ?? (busy ? "Checking" : "Unavailable")}</dd></div>
        {ready && Object.entries(ready.components).map(([name, status]) => <div className="kv-row" key={name}><dt>{name}</dt><dd>{status}</dd></div>)}
      </dl>
      {ready?.reason_code && <p className="notice mono">{ready.reason_code}</p>}
      <p className="muted">Public, user-safe health only. Liveness does not prove readiness or M1 acceptance. No exchange, NDSP or worker health is inferred.</p>
    </section>
  );
}