"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "./AuthProvider";
import { useI18n } from "../ndsp/i18n";
import { useTradingWorkspace } from "./TradingWorkspace";

type Candidate = {
  symbol: string;
  decision: "LONG_RESEARCH" | "SHORT_RESEARCH" | "CONFLICT";
  evidence: string[];
  intervals: string[];
};
type Projection = {
  stage: "M3_RESEARCH_DECISION_GATE";
  execution_allowed: false;
  mainnet_orders_enabled: false;
  ndsp_execution_verified: false;
  risk: {
    state: string;
    daily_loss_pct: string | null;
    new_entries_blocked: boolean;
    opening_equity: string | null;
    current_equity: string | null;
  };
  active_scanners: number;
  stalled_scanners: number;
  candidates: Candidate[];
  blockers: string[];
};

export default function HunterExecutionReviewPanel() {
  const { lang } = useI18n();
  const ar = lang === "ar";
  const { state, identity } = useAuth();
  const { workspace, busy: workspaceBusy } = useTradingWorkspace();
  const generation = useRef(0);
  const [data, setData] = useState<Projection | null>(null);
  const [error, setError] = useState("");
  const refresh = useCallback(async () => {
    const current = ++generation.current;
    if (state !== "authenticated" || !workspace || workspaceBusy) { setData(null); return; }
    try {
      const r = await fetch("/api/v1/trading/execution/review", {
        credentials: "same-origin", cache: "no-store",
      });
      if (!r.ok) throw Error(`HTTP_${r.status}`);
      const value = await r.json() as Projection;
      if (value.stage !== "M3_RESEARCH_DECISION_GATE"
          || value.execution_allowed !== false
          || value.mainnet_orders_enabled !== false
          || value.ndsp_execution_verified !== false
          || !Array.isArray(value.blockers)
          || !Array.isArray(value.candidates) || !value.risk
          || typeof value.risk.new_entries_blocked !== "boolean")
        throw Error("INVALID_EXECUTION_REVIEW");
      if (current !== generation.current) return;
      setData(value);
      setError("");
    } catch (e) {
      if (current !== generation.current) return;
      setData(null);
      setError(e instanceof Error ? e.message : "REVIEW_UNAVAILABLE");
    }
  }, [state, identity?.user_id, workspace, workspaceBusy]);
  useEffect(() => {
    setData(null);
    void refresh();
    if (state !== "authenticated") return;
    const timer = setInterval(() => { void refresh(); }, 30_000);
    return () => { generation.current++; clearInterval(timer); };
  }, [refresh, state]);
  return (
    <section className="panel" aria-label="Server verified strategy risk review">
      <h2>{ar ? "بوابة قرار الاستراتيجيات والمخاطر" : "Strategy & risk decision gate"}</h2>
      <p className="notice">
        {ar
          ? "تحليل حقيقي لإشارات الاستراتيجيات الأربع وحالة Equity وحد الخسارة المحفوظ. هذه توصيات بحثية فقط: فتح الصفقات الحقيقية وتسويتها غير متصلين بعد."
          : "Server-side review of four live research scanners and user-selected equity risk. Advisory only: real orders and reconciliation remain disconnected."}
      </p>
      <p><strong>{ar ? "تنفيذ الصفقات" : "Order execution"}:</strong> {ar ? "معطّل" : "Disabled"} · <strong>{ar ? "ربط NDSP" : "NDSP"}:</strong> {ar ? "غير موثق" : "Unverified"}</p>
      <p><strong>{ar ? "الاستراتيجيات العاملة" : "Active scanners"}:</strong> {data?.active_scanners ?? "—"}
        {" · "}<strong>{ar ? "المتوقفة بسبب تعذر الفحص" : "Stalled"}:</strong> {data?.stalled_scanners ?? "—"}</p>
      <p><strong>{ar ? "حد الخسارة الذي حدده المستخدم" : "User-selected loss limit"}:</strong>{" "}
        <bdi dir="ltr">{data?.risk.daily_loss_pct != null ? `${data.risk.daily_loss_pct}%` : "—"}</bdi>
        {" · "}<strong>{ar ? "حالة المخاطر" : "Risk"}:</strong> {data?.risk.state ?? "—"}</p>
      {data && data.candidates.length > 0 && (
        <div>
          <h3>{ar ? "المرشحات الموثقة للفحص فقط" : "Research candidates only"}</h3>
          <ul>{data.candidates.map(row =>
            <li key={row.symbol}>
              <bdi dir="ltr">{row.symbol}</bdi>: {row.decision} · {row.evidence.join(", ")} · {row.intervals.join(", ")}
            </li>)}</ul>
        </div>
      )}
      {data && <p className="muted">{ar ? "موانع التنفيذ" : "Execution blockers"}: {data.blockers.join(" · ")}</p>}
      {error && <p role="alert" className="notice">{ar ? "تعذر التحقق من بوابة القرار" : "Decision review unavailable"}: {error}</p>}
      <button type="button" className="button" disabled={state !== "authenticated" || !workspace || workspaceBusy}
        onClick={() => { void refresh(); }}>
        {ar ? "تحديث القرار" : "Refresh review"}
      </button>
    </section>
  );
}
