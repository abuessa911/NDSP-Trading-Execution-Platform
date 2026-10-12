import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { userPages } from "../../lib/console-pages";
import PageFrame from "../../components/PageFrame";
import PreviewWorkspace from "../../ndsp/PreviewWorkspace";
import { SecurityView } from "../../ndsp/OperationsPreview";
import HealthPanel from "../../components/HealthPanel";
import IdentityPanel from "../../components/IdentityPanel";
import SettingsPanel from "../../components/SettingsPanel";
import AdminBlocked from "../../components/AdminBlocked";

export const dynamicParams = false;
export function generateStaticParams() {
  return userPages.filter(p => p.slug !== "command-center").map(p => ({ section: p.slug }));
}
type Props = { params: Promise<{ section: string }> };
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { section } = await params;
  const page = userPages.find(p => p.slug === section);
  return { title: page?.title ?? "Not found", description: page?.description };
}

export default async function UserPage({ params }: Props) {
  const { section } = await params;
  const page = userPages.find(p => p.slug === section);
  if (!page || section === "command-center") notFound();
  let content;
  if (section === "health") content = <><HealthPanel /><PreviewWorkspace section="future-health" /></>;
  else if (section === "settings") content = <><SettingsPanel /><PreviewWorkspace section="bot-settings" /></>;
  else if (section === "security") content = <SecurityView />;
  else if (section === "subscription") content = <IdentityPanel entitlementsOnly />;
  else if (section === "audit") content = <AdminBlocked />;
  else content = <PreviewWorkspace key={section} section={section} />;
  return <PageFrame title={page.title} description={page.description}>{content}</PageFrame>;
}