"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useAuth } from "./AuthProvider";
import { useI18n } from "../ndsp/i18n";

export const workspaceSymbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "LINKUSDT", "XRPUSDT", "DOGEUSDT", "BNBUSDT"] as const;
export const workspaceIntervals = ["5m", "15m", "1h", "4h", "1d"] as const;
export type WorkspaceSettings = {
  mode: "INVESTMENT" | "SPECULATIVE";
  symbol: typeof workspaceSymbols[number];
  interval: typeof workspaceIntervals[number];
  execution_method: "MANUAL" | "AUTOMATIC";
  leverage: number;
  margin_mode: "ISOLATED" | "CROSS";
};
export type Workspace = WorkspaceSettings & {
  persisted: boolean;
  execution_authorized: false;
  ndsp_contract_bound: false;
};
const endpoint = "/api/v1/trading/profile/workspace";
const initial: WorkspaceSettings = {
  mode: "SPECULATIVE", symbol: "BTCUSDT", interval: "5m",
  execution_method: "MANUAL", leverage: 1, margin_mode: "ISOLATED",
};
function valid(input: unknown): input is Workspace {
  if (!input || typeof input !== "object") return false;
  const p = input as Partial<Workspace>;
  return workspaceSymbols.includes(p.symbol as Workspace["symbol"]) &&
    workspaceIntervals.includes(p.interval as Workspace["interval"]) &&
    (p.mode === "INVESTMENT" || p.mode === "SPECULATIVE") &&
    (p.execution_method === "MANUAL" || p.execution_method === "AUTOMATIC") &&
    (p.margin_mode === "ISOLATED" || p.margin_mode === "CROSS") &&
    Number.isInteger(p.leverage) && p.leverage! >= 1 && p.leverage! <= 125 &&
    typeof p.persisted === "boolean" && p.execution_authorized === false && p.ndsp_contract_bound === false;
}
type ContextValue = {
  workspace: Workspace | null; busy: boolean; message: string;
  apply: (settings: WorkspaceSettings) => Promise<void>;
};
const Context = createContext<ContextValue | null>(null);
export function useTradingWorkspace() {
  const value = useContext(Context);
  if (!value) throw new Error("WORKSPACE_PROVIDER_MISSING");
  return value;
}

export function TradingWorkspaceProvider({ children }: { children: ReactNode }) {
  const { state, identity, getCsrfToken } = useAuth();
  const { lang } = useI18n();
  const ar = lang === "ar";
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [workspaceOwner, setWorkspaceOwner] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const loading = useRef(false);
  useEffect(() => {
    const current = ++generation.current;
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    loading.current = false;
    setWorkspace(null);
    setBusy(false);
    setMessage("");
    if (state !== "authenticated" || !identity) return () => abort.abort();
    const deadline = setTimeout(() => abort.abort(), 10_000);
    void (async () => {
      try {
        const response = await fetch(endpoint, { credentials: "same-origin", cache: "no-store", signal: abort.signal });
        const data: unknown = await response.json();
        if (!response.ok || !valid(data)) throw new Error("WORKSPACE_UNAVAILABLE");
        if (generation.current === current && !abort.signal.aborted) { setWorkspace(data); setWorkspaceOwner(identity.user_id); }
      } catch {
        if (generation.current === current) setMessage(ar ? "تعذر تحميل إعدادات الخادم؛ أعد تحميل الصفحة." : "Cannot load server settings; reload the page.");
      } finally { clearTimeout(deadline); }
    })();
    return () => { abort.abort(); clearTimeout(deadline); };
  }, [state, identity?.user_id, ar]);

  const apply = useCallback(async (settings: WorkspaceSettings) => {
    const csrf = getCsrfToken();
    if (loading.current || state !== "authenticated" || !csrf || !workspace ||
        workspaceOwner !== identity?.user_id) return;
    loading.current = true;
    setBusy(true);
    setMessage("");
    const current = generation.current;
    const abort = new AbortController();
    controller.current = abort;
    const deadline = setTimeout(() => abort.abort(), 10_000);
    try {
      const response = await fetch(endpoint, {
        method: "PUT", credentials: "same-origin", cache: "no-store", signal: abort.signal,
        headers: { "Content-Type": "application/json", "X-NEX-CSRF": csrf },
        body: JSON.stringify(settings),
      });
      const data: unknown = await response.json();
      if (!response.ok || !valid(data) || !data.persisted ||
          Object.entries(settings).some(([key, value]) => data[key as keyof Workspace] !== value)) {
        throw new Error("WORKSPACE_SAVE_UNCONFIRMED");
      }
      if (generation.current !== current || abort.signal.aborted) return;
      setWorkspace(data);
      window.dispatchEvent(new Event("hunter-workspace-applied"));
      setMessage(ar ? "تم الحفظ والتأكيد من الخادم. شغّل المراقبة والفحص بالإعداد الجديد عند الحاجة." : "Server settings confirmed. Start monitoring or scanning with the new selection when needed.");
    } catch {
      if (generation.current === current) {
        // A timed-out PUT may have committed; invalidate the old state so no
        // consumer continues to label outputs with an unconfirmed selection.
        setWorkspace(null);
        setMessage(ar ? "لم يصل تأكيد الحفظ. أعد تحميل الصفحة للتحقق من إعدادات الخادم." : "Save not confirmed. Reload to verify server settings.");
      }
    } finally {
      clearTimeout(deadline);
      if (generation.current === current) { loading.current = false; setBusy(false); }
    }
  }, [state, identity?.user_id, workspace, workspaceOwner, getCsrfToken, ar]);

  const visibleWorkspace = state === "authenticated" && workspaceOwner === identity?.user_id ? workspace : null;
  return <Context.Provider value={{ workspace: visibleWorkspace, busy, message, apply }}>{children}</Context.Provider>;
}

export function TradingWorkspaceBar() {
  const { state } = useAuth();
  const { lang } = useI18n();
  const ar = lang === "ar";
  const { workspace, busy, message, apply } = useTradingWorkspace();
  const [draft, setDraft] = useState<WorkspaceSettings>(initial);
  useEffect(() => { if (workspace) setDraft(workspace); }, [workspace]);
  if (state !== "authenticated") return null;
  const update = <K extends keyof WorkspaceSettings>(key: K, value: WorkspaceSettings[K]) =>
    setDraft(previous => ({ ...previous, [key]: value }));
  return <section className="panel" aria-label={ar ? "إعدادات البوت الموحدة" : "Shared bot settings"}>
    <h2>{ar ? "إعدادات البوت الموحدة" : "Shared bot settings"}</h2>
    <form onSubmit={event => { event.preventDefault(); void apply({
      mode: draft.mode, symbol: draft.symbol, interval: draft.interval,
      execution_method: draft.execution_method, leverage: draft.leverage, margin_mode: draft.margin_mode,
    }); }}>
      <fieldset disabled={!workspace || busy} style={{ border: 0, padding: 0, margin: 0 }}>
        <div className="row" style={{ gap: 12, flexWrap: "wrap", alignItems: "end" }}>
          <label className="field">{ar ? "الأصل" : "Asset"}<select aria-label={ar ? "الأصل" : "Asset"} value={draft.symbol} onChange={event => update("symbol", event.target.value as Workspace["symbol"])}>{workspaceSymbols.map(symbol => <option key={symbol}>{symbol}</option>)}</select></label>
          <label className="field">{ar ? "الإطار الزمني" : "Timeframe"}<select aria-label={ar ? "الإطار الزمني" : "Timeframe"} value={draft.interval} onChange={event => update("interval", event.target.value as Workspace["interval"])}>{workspaceIntervals.map(interval => <option key={interval}>{interval}</option>)}</select></label>
          <label className="field">{ar ? "نمط التداول" : "Decision style"}<select aria-label={ar ? "نمط التداول" : "Decision style"} value={draft.mode} onChange={event => update("mode", event.target.value as Workspace["mode"])}><option value="SPECULATIVE">{ar ? "مضاربي" : "Speculation"}</option><option value="INVESTMENT">{ar ? "استثماري" : "Investment"}</option></select></label>
          <label className="field">{ar ? "طريقة التنفيذ" : "Execution method"}<select aria-label={ar ? "طريقة التنفيذ" : "Execution method"} value={draft.execution_method} onChange={event => update("execution_method", event.target.value as Workspace["execution_method"])}><option value="MANUAL">{ar ? "يدوي" : "Manual"}</option><option value="AUTOMATIC">{ar ? "آلي" : "Automatic"}</option></select></label>
          <label className="field">{ar ? "الرافعة المطلوبة" : "Requested leverage"}<input aria-label={ar ? "الرافعة المطلوبة" : "Requested leverage"} type="number" min={1} max={125} step={1} required value={draft.leverage} onChange={event => update("leverage", event.target.valueAsNumber)} /></label>
          <label className="field">{ar ? "الهامش" : "Margin"}<select aria-label={ar ? "الهامش" : "Margin"} value={draft.margin_mode} onChange={event => update("margin_mode", event.target.value as Workspace["margin_mode"])}><option value="ISOLATED">{ar ? "معزول" : "Isolated"}</option><option value="CROSS">{ar ? "متقاطع" : "Cross"}</option></select></label>
          <button type="submit" className="button">{busy ? (ar ? "جار التأكيد..." : "Confirming…") : (ar ? "تأكيد / تطبيق" : "Confirm / Apply")}</button>
        </div>
      </fieldset>
    </form>
    <p className="muted">{workspace ? `${workspace.symbol} · ${workspace.interval} · ${workspace.leverage}x` : (ar ? "إعدادات الخادم غير متاحة." : "Server settings unavailable.")}</p>
    <p className="muted">{ar ? "تطبيق الإعدادات يوقف المراقبة والفحص السابقين لمنع خلط المخرجات. اختيار آلي أو الرافعة يحفظ تفضيلًا فقط؛ تنفيذ الأوامر وحدود البورصة غير مفعّلين." : "Applying settings stops previous monitoring/scans to prevent mixed outputs. Automatic mode and leverage are saved preferences; order execution and exchange limits are not enabled."}</p>
    <p role="status" aria-live="polite">{message || (workspace?.persisted ? (ar ? "الإعدادات مؤكدة ومحفوظة على الخادم." : "Settings confirmed and saved on the server.") : (ar ? "قيم افتراضية؛ اضغط تأكيد لحفظ اختياراتك." : "Defaults shown; confirm to save your choices."))}</p>
  </section>;
}
