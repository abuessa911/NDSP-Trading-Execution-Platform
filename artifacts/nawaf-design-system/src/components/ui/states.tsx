import { AlertTriangle, Inbox, RotateCw } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./button";

// Source: Loading, EmptyState, ErrorState in ndsp-console/src/ndsp/ui.tsx.
// Adaptation: i18n singleton removed; labels are caller-owned props whose defaults are the source English strings.
// The inline skeleton heights/opacity ramp is preserved through the row index (first row taller).
export function Loading({ rows = 4, label = "Loading" }: { rows?: number; label?: string }) {
  return (
    <div className="nawaf-skeleton-stack" role="status" aria-label={label}>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="nawaf-skeleton" style={{ height: i === 0 ? "4.625rem" : "2.75rem", opacity: 1 - i * 0.12 }} />
      ))}
    </div>
  );
}

export function EmptyState({ title, text, icon }: { title: string; text: string; icon?: ReactNode }) {
  return (
    <div className="nawaf-empty-state">
      {icon ?? <Inbox className="size-ds-empty-icon" aria-hidden />}
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}

export function ErrorState({
  onRetry,
  title = "Request failed",
  text = "The demo adapter could not return data. Nothing was substituted.",
  retryLabel = "Retry",
}: { onRetry: () => void; title?: string; text?: string; retryLabel?: string }) {
  return (
    <div className="nawaf-error-state" role="alert">
      <AlertTriangle className="size-ds-error-icon" aria-hidden />
      <div><strong>{title}</strong><p>{text}</p></div>
      <Button variant="outline" size="sm" onClick={onRetry}><RotateCw aria-hidden />{retryLabel}</Button>
    </div>
  );
}
