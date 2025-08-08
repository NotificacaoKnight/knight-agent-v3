import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "../../lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
        success:
          "border-transparent bg-green-500 text-white hover:bg-green-600",
        "ranking-gold":
          "border border-yellow-600/40 bg-gradient-to-r from-yellow-400 to-yellow-600 text-yellow-900 font-bold shadow-md bg-clip-padding",
        "ranking-silver": 
          "border border-gray-500/40 bg-gradient-to-r from-gray-300 to-gray-500 text-gray-800 font-bold shadow-md bg-clip-padding",
        "ranking-bronze":
          "border border-orange-600/40 bg-gradient-to-r from-orange-400 to-orange-600 text-orange-900 font-bold shadow-md bg-clip-padding",
        "ranking-top":
          "border border-blue-600/40 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-semibold shadow-sm bg-clip-padding",
        "ranking-regular":
          "border border-secondary bg-secondary text-secondary-foreground bg-clip-padding",
        "ranking-none":
          "border border-border bg-muted text-muted-foreground bg-clip-padding",
        "status-pending":
          "border border-gray-400 bg-gradient-to-r from-gray-400/30 via-gray-400/20 to-gray-400/10 text-foreground font-medium shadow-sm bg-clip-padding",
        "status-processing":
          "border border-blue-500 bg-gradient-to-r from-blue-500/30 via-blue-500/20 to-blue-500/10 text-foreground font-medium shadow-sm bg-clip-padding",
        "status-processed":
          "border border-green-500 bg-gradient-to-r from-green-500/30 via-green-500/20 to-green-500/10 text-foreground font-medium shadow-sm bg-clip-padding",
        "status-error":
          "border border-red-500 bg-gradient-to-r from-red-500/30 via-red-500/20 to-red-500/10 text-foreground font-medium shadow-sm bg-clip-padding",
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

export { Badge, badgeVariants }