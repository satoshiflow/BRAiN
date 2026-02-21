import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@ui-core/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        // Default = secondary
        default: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        // Primary = Gold accent
        primary: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        // Destructive
        destructive: "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        // Status variants
        success: "border-transparent bg-success/20 text-success hover:bg-success/30",
        warning: "border-transparent bg-warning/20 text-warning hover:bg-warning/30",
        danger: "border-transparent bg-danger/20 text-danger hover:bg-danger/30",
        info: "border-transparent bg-info/20 text-info hover:bg-info/30",
        // Outline
        outline: "text-foreground",
        // Muted
        muted: "border-transparent bg-muted text-muted-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };