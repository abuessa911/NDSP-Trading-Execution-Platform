import type { AnchorHTMLAttributes } from "react";

/**
 * This console is a static export behind an authenticated API gateway.
 * Navigate to the exported HTML document; client-router RSC requests have a
 * separate session gate and can redirect or stall an otherwise valid link.
 * Browser cookies still reach the authenticated APIs on the destination page.
 */
export default function DocumentLink({ href, ...props }: AnchorHTMLAttributes<HTMLAnchorElement>) {
  const basePath = process.env.NEXT_PUBLIC_BOT_BASE_PATH ?? "";
  const target = href?.startsWith("/") && !href.startsWith("//") ? basePath + href : href;
  return <a {...props} href={target} />;
}
