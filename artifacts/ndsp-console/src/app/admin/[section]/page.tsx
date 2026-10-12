import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { adminPages } from "../../../lib/console-pages";
import AdminBlocked from "../../../components/AdminBlocked";
import AdminAuditPanel from "../../../components/AdminAuditPanel";
import AdminHealthPanel from "../../../components/AdminHealthPanel";
import PageFrame from "../../../components/PageFrame";

export const dynamicParams = false;
export function generateStaticParams() { return adminPages.map(page => ({ section: page.slug })); }
type Props = { params: Promise<{ section: string }> };
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { section } = await params;
  const page = adminPages.find(p => p.slug === section);
  return { title: page ? `${page.title} — M1 Admin` : "Not found", description: page?.description };
}
export default async function AdminPage({ params }: Props) {
  const { section } = await params;
  const page = adminPages.find(p => p.slug === section);
  if (!page) notFound();
  let content;
  if (section === "operations-center") content = <AdminHealthPanel />;
  else if (section === "audit") content = <AdminAuditPanel />;
  else content = <AdminBlocked />;
  return <PageFrame title={page.title} description={page.description}>{content}</PageFrame>;
}