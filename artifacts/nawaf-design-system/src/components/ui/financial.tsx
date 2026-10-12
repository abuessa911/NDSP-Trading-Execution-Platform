import { ArrowDown, ArrowUp } from "lucide-react";

// Source: ndsp-console/src/ndsp/ui.tsx. Pure presentation only.
export const money = (n: number, dp = 2) => `${n < 0 ? "-" : ""}$${Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: dp, maximumFractionDigits: dp })}`;
export const signed = (n: number, dp = 2) => `${n > 0 ? "+" : n < 0 ? "-" : ""}${Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: dp, maximumFractionDigits: dp })}`;
export const num = (n: number) => n.toLocaleString("en-US", { maximumFractionDigits: 4 });

export function Kpi({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "gain" | "loss" | "warn" }) {
  return <div className={`nawaf-kpi ${tone ?? ""}`}><span className="nawaf-kpi-label">{label}</span><span className="nawaf-kpi-value" dir="ltr">{value}</span>{sub && <span className="nawaf-kpi-sub">{sub}</span>}</div>;
}

export function Pnl({ v, money: m = true }: { v: number; money?: boolean }) {
  return <span dir="ltr" className={`nawaf-pnl ${v > 0 ? "gain" : v < 0 ? "loss" : ""}`}>{v > 0 ? <ArrowUp aria-hidden /> : v < 0 ? <ArrowDown aria-hidden /> : null}{m ? `${v < 0 ? "-" : "+"}${money(Math.abs(v))}` : `${signed(v)}%`}</span>;
}
