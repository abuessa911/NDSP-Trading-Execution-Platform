// Source: Ring and Meter in ndsp-console/src/ndsp/ui.tsx. Sizing/colors come from token CSS (component-theme.css).
export function Ring({ pct, label, size, tone }: { pct: number; label: string; size?: number; tone?: "warn" | "bad" }) {
  const r = 42, c = 2 * Math.PI * r;
  const t = tone ?? (pct >= 85 ? "bad" : pct >= 60 ? "warn" : "ok");
  return (
    <figure className={`nawaf-ring nawaf-ring-${t}`} style={{ width: size }}>
      <svg viewBox="0 0 100 100" style={{ width: size ?? "var(--ds-sizing-ring-size)", height: size ?? "var(--ds-sizing-ring-size)" }} role="img" aria-label={`${label} ${pct}%`}>
        <circle cx="50" cy="50" r={r} className="track" />
        <circle cx="50" cy="50" r={r} className="arc" strokeDasharray={`${(pct / 100) * c} ${c}`} transform="rotate(-90 50 50)" />
        <text x="50" y="55" textAnchor="middle">{pct}%</text>
      </svg>
      <figcaption>{label}</figcaption>
    </figure>
  );
}

export function Meter({ pct, label }: { pct: number; label: string }) {
  const value = Math.max(0, Math.min(100, pct));
  return (
    <div className="nawaf-meter" role="meter" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <span style={{ transform: `scaleX(${value / 100})` }} />
    </div>
  );
}
