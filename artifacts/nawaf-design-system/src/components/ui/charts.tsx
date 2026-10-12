import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useId } from "react";
import { signed } from "./financial";

// Source: default export of ndsp-console/src/ndsp/PreviewCharts.tsx (Recharts AreaChart) plus LineChart and Bars from ndsp/ui.tsx.
// Adaptations: CSS variable colors resolve through the token channels (hsl(var(--primary)) etc.); chart copy is caller-owned with
// the source English as defaults; a real <table> of values replaces the paragraph fallback; animation stays disabled (isActive false).
const stroke = "hsl(var(--primary))";
const muted = "hsl(var(--muted-foreground))";

// Recharts needs numeric props: resolve a generated rem token to px at render (geometry constants and viewBox math are exempt).
function px(name: string): number {
  if (typeof document === "undefined") return 0;
  const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const root = Number.parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
  return raw.endsWith("rem") ? Number.parseFloat(raw) * root : Number.parseFloat(raw) || 0;
}

export default function PreviewChart({ values, label, unit = "USD", caption, sampleLabel = (v: number | string) => `Demo sample ${v}`, detailsLabel = "View synthetic sample values", sampleHeader = "Sample", ariaLabel }: {
  values: number[]; label: string; unit?: string; caption?: string; sampleLabel?: (v: number | string) => string; detailsLabel?: string; sampleHeader?: string;
  /** Accessible name of the chart image. Default is English; callers supply localized copy. */
  ariaLabel?: string;
}) {
  const id = useId().replaceAll(":", "");
  const data = values.map((value, index) => ({ sample: index + 1, value }));
  return (
    <figure className="nawaf-chart-layout" data-testid="preview-chart">
      <figcaption>{label} <span className="nawaf-mono">{caption ?? `DEMO · ${unit} · synthetic sample sequence`}</span></figcaption>
      <div dir="ltr" style={{ width: "100%", height: "var(--ds-sizing-chart-height)" }} role="img" aria-label={ariaLabel ?? `${label}, ${values.length} synthetic samples in ${unit}`}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: px("--ds-sizing-chart-margin-top"), right: px("--ds-sizing-chart-margin-end"), left: 0, bottom: 0 }} accessibilityLayer>
            <defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={stroke} stopOpacity={0.25} /><stop offset="100%" stopColor={stroke} stopOpacity={0} /></linearGradient></defs>
            <CartesianGrid stroke="hsl(var(--border))" vertical={false} />
            <XAxis dataKey="sample" tick={{ fill: muted, fontSize: px("--ds-sizing-chart-tick") }} minTickGap={30} />
            <YAxis domain={["auto", "auto"]} width={px("--ds-sizing-chart-axis-width")} tick={{ fill: muted, fontSize: px("--ds-sizing-chart-tick") }} tickFormatter={(value) => Number(value).toLocaleString("en-US", { maximumFractionDigits: 0 })} />
            <Tooltip contentStyle={{ background: "hsl(var(--popover))", borderColor: "hsl(var(--border))", color: "hsl(var(--popover-foreground))" }} itemStyle={{ color: "hsl(var(--popover-foreground))" }} labelStyle={{ color: "hsl(var(--popover-foreground))" }} labelFormatter={(value) => sampleLabel(value as number | string)} formatter={(value) => [Number(value).toLocaleString("en-US", { maximumFractionDigits: 2 }), unit]} />
            <Area dataKey="value" type="linear" stroke={stroke} fill={`url(#${id})`} strokeWidth={2} isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <details><summary>{detailsLabel}</summary>
        <table className="nawaf-chart-table"><thead><tr><th scope="col">{sampleHeader}</th><th scope="col">{unit}</th></tr></thead>
          <tbody>{values.map((v, i) => <tr key={i}><td dir="ltr">{i + 1}</td><td dir="ltr">{v.toFixed(2)}</td></tr>)}</tbody></table>
      </details>
    </figure>
  );
}
export { PreviewChart };

export function LineChart({ data, height, label, area = true, insufficientText }: { data: number[]; height?: number; label: string; area?: boolean; insufficientText?: string }) {
  if (data.length < 2) return <p className="nawaf-mono">{insufficientText ?? `Insufficient sample data for ${label}.`}</p>;
  const min = Math.min(...data), max = Math.max(...data), span = max - min || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * 100},${100 - ((v - min) / span) * 90 - 5}`);
  const up = data[data.length - 1] >= data[0];
  return (
    <svg className={`nawaf-line-chart ${up ? "up" : "down"}`} viewBox="0 0 100 100" preserveAspectRatio="none" style={{ direction: "ltr", height: height ?? "var(--ds-sizing-line-chart-height)" }} role="img" aria-label={label}>
      {[25, 50, 75].map((y) => <line key={y} x1="0" x2="100" y1={y} y2={y} className="grid" vectorEffect="non-scaling-stroke" />)}
      {area && <polygon points={`0,100 ${pts.join(" ")} 100,100`} className="fill" />}
      <polyline points={pts.join(" ")} className="stroke" fill="none" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export function Bars({ data, label }: { data: number[]; label: string }) {
  const max = Math.max(1, ...data.map(Math.abs));
  return (
    <div dir="ltr" className="nawaf-bars" role="img" aria-label={label}>
      {data.map((v, i) => <span key={i} className={v >= 0 ? "pos" : "neg"} style={{ height: `${Math.max(6, (Math.abs(v) / max) * 100)}%` }} title={signed(v)} />)}
    </div>
  );
}
