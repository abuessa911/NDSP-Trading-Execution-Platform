import * as React from "react"
import { AlertTriangle, CircleCheck, CircleX } from "lucide-react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "../../lib/utils"

const badgeVariants = cva(
  // @replit
  // Whitespace-nowrap: Badges should never wrap.
  "whitespace-nowrap inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2" +
  " hover-elevate ",
  {
    variants: {
      variant: {
        default:
          // @replit shadow-xs instead of shadow, no hover because we use hover-elevate
          "border-transparent bg-primary text-primary-foreground shadow-xs",
        secondary:
          // @replit no hover because we use hover-elevate
          "border-transparent bg-secondary text-secondary-foreground",
        destructive:
          // @replit shadow-xs instead of shadow, no hover because we use hover-elevate
          "border-transparent bg-destructive text-destructive-foreground shadow-xs",
          // @replit shadow-xs" - use badge outline variable
        outline: "text-foreground border [border-color:var(--badge-outline)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

// Source: Chip in ndsp-console/src/ndsp/ui.tsx. Adaptation: classes are token-driven (component-theme.css).
export type ChipTone = "ok" | "warn" | "bad" | "info" | "mute"

function Chip({ tone, children }: { tone: ChipTone; children: React.ReactNode }) {
  const Icon = tone === "ok" ? CircleCheck : tone === "bad" ? CircleX : tone === "warn" ? AlertTriangle : null
  return (
    <span className={`nawaf-chip nawaf-chip-${tone}`}>
      {Icon && <Icon aria-hidden />}
      {children}
    </span>
  )
}

export { Badge, badgeVariants, Chip }
