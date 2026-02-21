import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@ui-core/utils";

const statusPillVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium",
  {
    variants: {
      status: {
        live: "bg-success/20 text-success",
        degraded: "bg-warning/20 text-warning",
        down: "bg-danger/20 text-danger",
        safe: "bg-info/20 text-info",
        idle: "bg-muted text-muted-foreground",
      },
    },
    defaultVariants: {
      status: "idle",
    },
  }
);

export interface StatusPillProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof statusPillVariants> {
  pulse?: boolean;
}

function StatusPill({ className, status, pulse = false, children, ...props }: StatusPillProps) {
  return (
    <div className={cn(statusPillVariants({ status }), className)} {...props}>
      {pulse && (
        <span className="relative flex h-2 w-2">
          <span className={cn(
            "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
            status === "live" && "bg-success",
            status === "degraded" && "bg-warning",
            status === "down" && "bg-danger",
            status === "safe" && "bg-info",
            status === "idle" && "bg-muted-foreground",
          )} />
          <span className={cn(
            "relative inline-flex rounded-full h-2 w-2",
            status === "live" && "bg-success",
            status === "degraded" && "bg-warning",
            status === "down" && "bg-danger",
            status === "safe" && "bg-info",
            status === "idle" && "bg-muted-foreground",
          )} />
        </span>
      )}
      {!pulse && (
        <span className={cn(
          "h-2 w-2 rounded-full",
          status === "live" && "bg-success",
          status === "degraded" && "bg-warning",
          status === "down" && "bg-danger",
          status === "safe" && "bg-info",
          status === "idle" && "bg-muted-foreground",
        )} />
      )}
      {children}
    </div>
  );
}

export { StatusPill, statusPillVariants };