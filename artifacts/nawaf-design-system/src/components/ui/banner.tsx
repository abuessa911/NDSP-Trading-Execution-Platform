import type { ReactNode } from "react";

// Source: DemoBanner in ndsp-console/src/ndsp/ui.tsx and the `.notice` class in globals.css.
// Adaptation: DemoBanner's i18n tags become the caller-owned `tags` prop; text is `what`.
export function DemoBanner({ what, tags = ["DEMO DATA", "NOT CONNECTED", "READ-ONLY UI PREVIEW"] }: { what?: string; tags?: string[] }) {
  return (
    <div className="nawaf-demo-banner" role="note" data-testid="demo-banner">
      {tags.map((tag) => <span key={tag} className="nawaf-demo-tag">{tag}</span>)}
      <span className="nawaf-demo-text">{what ?? "Illustrative records from a local frontend dataset. Nothing here is live, persisted or sent to an exchange."}</span>
    </div>
  );
}

export function Notice({ children }: { children: ReactNode }) {
  return <div className="nawaf-notice" role="note">{children}</div>;
}
