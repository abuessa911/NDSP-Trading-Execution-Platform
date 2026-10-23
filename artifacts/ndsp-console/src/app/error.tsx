"use client";

import { useI18n } from "../ndsp/i18n";

/** Recovery from a rendering or chunk-loading failure, NOT an M1 approval gate. */
export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const { t } = useI18n();
  return (
    <section className="panel" role="alert">
      <h1>{t("Page display failed")}</h1>
      <p className="muted">{t("This is a page-rendering problem, not an M1 approval decision. No operation was confirmed.")}</p>
      <div className="demo-actions">
        <button type="button" className="button" onClick={() => reset()}>{t("Try again")}</button>
        <button type="button" className="button" onClick={() => window.location.reload()}>{t("Reload page")}</button>
      </div>
    </section>
  );
}
