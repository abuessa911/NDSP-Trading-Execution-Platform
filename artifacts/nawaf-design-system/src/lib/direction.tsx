import type { ReactNode } from "react";
import { DirectionProvider as RadixDirectionProvider } from "@radix-ui/react-direction";

/** Propagates reading direction to Radix keyboard navigation and portals. Wrap the app root (also set `dir` on <html>). */
export function DirectionProvider({ dir, children }: { dir: "ltr" | "rtl"; children: ReactNode }) {
  return <RadixDirectionProvider dir={dir}>{children}</RadixDirectionProvider>;
}
