"use client";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import ConsoleShell from "./ConsoleShell";
export default function PublicShellGate({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isPublic = ["/", "/login", "/registration", "/admin-login"].includes(pathname.replace(/\/$/, "") || "/");
  return isPublic ? <>{children}</> : <ConsoleShell>{children}</ConsoleShell>;
}
