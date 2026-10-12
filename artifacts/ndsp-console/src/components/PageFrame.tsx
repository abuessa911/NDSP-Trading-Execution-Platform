"use client";
import type { ReactNode } from "react";
import { useI18n } from "../ndsp/i18n";

export default function PageFrame({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  const { t } = useI18n();
  return <div className="page-frame">
    <header className="page-heading surface-header page-heading--editorial"><p className="eyebrow">{t("NAWAF CONTROL PLANE")}</p><h1>{t(title)}</h1><p className="muted">{t(description)}</p></header>
    <div className="page-content page-content--workspace">{children}</div>
  </div>;
}
