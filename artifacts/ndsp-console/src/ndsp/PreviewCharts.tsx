"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useId } from "react";
import { useI18n } from "./i18n";

export default function PreviewChart({ values, label, unit = "USD" }: { values: number[]; label: string; unit?: string }) {
  const { t } = useI18n();
  const id = useId().replaceAll(":", "");
  const data = values.map((value, index) => ({ sample: index + 1, value }));
  return <figure className="chart-layout" data-testid="preview-chart">
    <figcaption>{t(label)} <span className="mono">{t("DEMO")} · {unit} · {t("synthetic sample sequence")}</span></figcaption>
    <div dir="ltr" style={{ width: "100%", height: 240 }} role="img" aria-label={`${t(label)}, ${values.length} ${t("synthetic samples")} · ${unit}`}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 15, right: 10, left: 0, bottom: 0 }}>
          <defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--accent)" stopOpacity={0.25} /><stop offset="100%" stopColor="var(--accent)" stopOpacity={0} /></linearGradient></defs>
          <CartesianGrid stroke="var(--line)" vertical={false} />
          <XAxis dataKey="sample" tick={{ fill: "var(--muted)", fontSize: 10 }} minTickGap={30} />
          <YAxis domain={["auto", "auto"]} width={68} tick={{ fill: "var(--muted)", fontSize: 10 }} tickFormatter={value => Number(value).toLocaleString("en-US", { maximumFractionDigits: 0 })} />
          <Tooltip contentStyle={{ background: "var(--panel)", borderColor: "var(--line)", color: "var(--text)" }} labelFormatter={value => `${t("DEMO")} · ${t("Sample")} ${value}`} formatter={value => [Number(value).toLocaleString("en-US", { maximumFractionDigits: 2 }), unit]} />
          <Area dataKey="value" type="linear" stroke="var(--accent)" fill={`url(#${id})`} strokeWidth={2} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
    <details><summary>{t("View synthetic sample values")}</summary><p className="mono" dir="ltr">{values.map(v => v.toFixed(2)).join(" · ")}</p></details>
  </figure>;
}
