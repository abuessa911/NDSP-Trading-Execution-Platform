import type { Metadata } from "next";
import { BOT_NAME } from "../lib/bot-profile";
import { AuthProvider } from "../components/AuthProvider";
import PublicShellGate from "../components/PublicShellGate";
import { I18nProvider } from "../ndsp/i18n";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: `${BOT_NAME} · M1 Console`, template: `%s · ${BOT_NAME} M1` },
  description: `Independent ${BOT_NAME} M1 identity, tenant, service-health and safety console. M1 remains NOT ACCEPTED; trading is unavailable.`,
  referrer: "no-referrer",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body><I18nProvider><AuthProvider><PublicShellGate>{children}</PublicShellGate></AuthProvider></I18nProvider><script defer src="/hunter-legacy-controls.js" /></body></html>;
}