"use client";
import { LockKeyhole } from "lucide-react";
import Link from "next/link";
import { useI18n } from "../ndsp/i18n";

export default function DeferredPanel({ title, description, milestone }: { title: string; description: string; milestone: string }) {
  const { t } = useI18n();
  return <section className="panel deferred-panel deferred-panel--boundary" aria-label={`${t(title)} ${t("unavailable")}`}>
    <div className="deferred-icon"><LockKeyhole size={24} aria-hidden /></div>
    <span className="tag">{t("DEFERRED")} · {milestone}</span>
    <h2>{t(title)} {t("is unavailable in M1")}</h2>
    <p>{t(description)}</p>
    <p className="muted">{t("This capability is not implemented. Its route is part of the Master Spec V1 navigation inventory, not evidence of functioning trading, integration or execution services.")}</p>
    <p className="notice">{t("No live data, no credentials accepted, no trading controls enabled. Any preview shown elsewhere is labelled DEMO DATA. M1 remains NOT ACCEPTED.")}</p>
    <Link href="/" className="button">{t("Return to Command Center")}</Link>
  </section>;
}
