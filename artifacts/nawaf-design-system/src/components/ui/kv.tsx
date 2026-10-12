import type { ReactNode } from "react";

// Source: KV in ndsp-console/src/ndsp/ui.tsx. Values render isolated by the caller (wrap signed numbers in dir="ltr").
export function KV({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <dl className="nawaf-kv-list">
      {rows.map(([k, v]) => (
        <div className="nawaf-kv-row" key={k}><dt>{k}</dt><dd>{v}</dd></div>
      ))}
    </dl>
  );
}
