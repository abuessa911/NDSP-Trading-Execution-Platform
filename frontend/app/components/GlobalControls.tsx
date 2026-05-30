"use client";

import { usePathname } from "next/navigation";

export default function GlobalControls() {
  const pathname = usePathname();
  const isHome = pathname === "/";

  if (isHome) return null;

  return (
    <div className="global-controls-fixed" data-no-translate>
      <a className="home-pill-fixed" href="/">
        <span>⌂</span>
        <b>الرئيسية</b>
      </a>
    </div>
  );
}
