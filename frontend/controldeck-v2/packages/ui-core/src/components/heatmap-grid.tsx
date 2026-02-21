import * as React from "react";
import { cn } from "@ui-core/utils";
import { Badge } from "./badge";

interface HeatmapCell {
  id: string;
  label: string;
  status: "healthy" | "warning" | "critical" | "offline" | "idle";
  value?: number;
  sublabel?: string;
  onClick?: () => void;
}

interface HeatmapGridProps extends React.HTMLAttributes<HTMLDivElement> {
  cells: HeatmapCell[];
  columns?: 2 | 3 | 4 | 5 | 6 | 8;
  gap?: "sm" | "md" | "lg";
  showLabels?: boolean;
  showValues?: boolean;
  className?: string;
}

const statusConfig = {
  healthy: {
    bg: "bg-success/20",
    border: "border-success/30",
    text: "text-success",
    glow: "hover:shadow-[0_0_12px_rgba(16,185,129,0.3)]",
  },
  warning: {
    bg: "bg-warning/20",
    border: "border-warning/30",
    text: "text-warning",
    glow: "hover:shadow-[0_0_12px_rgba(245,158,11,0.3)]",
  },
  critical: {
    bg: "bg-danger/20",
    border: "border-danger/30",
    text: "text-danger",
    glow: "hover:shadow-[0_0_12px_rgba(239,68,68,0.3)]",
  },
  offline: {
    bg: "bg-muted/30",
    border: "border-muted",
    text: "text-muted-foreground",
    glow: "",
  },
  idle: {
    bg: "bg-info/20",
    border: "border-info/30",
    text: "text-info",
    glow: "hover:shadow-[0_0_12px_rgba(59,130,246,0.3)]",
  },
};

const statusBadges = {
  healthy: "success" as const,
  warning: "warning" as const,
  critical: "danger" as const,
  offline: "muted" as const,
  idle: "info" as const,
};

function HeatmapGrid({
  cells,
  columns = 4,
  gap = "md",
  showLabels = true,
  showValues = false,
  className,
  ...props
}: HeatmapGridProps) {
  const gapClasses = {
    sm: "gap-2",
    md: "gap-3",
    lg: "gap-4",
  };

  const colClasses = {
    2: "grid-cols-2",
    3: "grid-cols-3",
    4: "grid-cols-2 md:grid-cols-4",
    5: "grid-cols-2 md:grid-cols-5",
    6: "grid-cols-2 md:grid-cols-3 lg:grid-cols-6",
    8: "grid-cols-2 md:grid-cols-4 lg:grid-cols-8",
  };

  return (
    <div
      className={cn(
        "grid",
        colClasses[columns],
        gapClasses[gap],
        className
      )}
      {...props}
    >
      {cells.map((cell) => {
        const config = statusConfig[cell.status];
        
        return (
          <button
            key={cell.id}
            onClick={cell.onClick}
            className={cn(
              "relative p-4 rounded-lg border transition-all duration-200",
              "hover:scale-[1.02] active:scale-[0.98]",
              config.bg,
              config.border,
              config.glow,
              cell.onClick && "cursor-pointer",
              !cell.onClick && "cursor-default"
            )}
          >
            {/* Status Indicator */}
            <div
              className={cn(
                "absolute top-2 right-2 h-2 w-2 rounded-full",
                config.text.replace("text-", "bg-")
              )}
            />
            
            {/* Content */}
            <div className="text-left">
              {showLabels && (
                <p className={cn("font-medium text-sm", config.text)}>
                  {cell.label}
                </p>
              )}
              
              {cell.sublabel && (
                <p className="text-xs text-muted-foreground mt-1">
                  {cell.sublabel}
                </p>
              )}
              
              {showValues && cell.value !== undefined && (
                <p className={cn("text-lg font-bold mt-2", config.text)}>
                  {cell.value}%
                </p>
              )}
              
              <Badge
                variant={statusBadges[cell.status]}
                className="mt-2 text-xs"
              >
                {cell.status}
              </Badge>
            </div>
          </button>
        );
      })}
      
      {cells.length === 0 && (
        <div className="col-span-full text-center py-8 text-muted-foreground">
          No data to display
        </div>
      )}
    </div>
  );
}

// Summary stats for the heatmap
interface HeatmapStatsProps {
  cells: HeatmapCell[];
  className?: string;
}

function HeatmapStats({ cells, className }: HeatmapStatsProps) {
  const stats = React.useMemo(() => {
    const total = cells.length;
    const healthy = cells.filter((c) => c.status === "healthy").length;
    const warning = cells.filter((c) => c.status === "warning").length;
    const critical = cells.filter((c) => c.status === "critical").length;
    const offline = cells.filter((c) => c.status === "offline").length;
    
    return { total, healthy, warning, critical, offline };
  }, [cells]);

  return (
    <div className={cn("flex flex-wrap gap-4", className)}>
      <div className="flex items-center gap-2">
        <div className="h-3 w-3 rounded-full bg-success" />
        <span className="text-sm text-muted-foreground">
          Healthy: {stats.healthy}/{stats.total}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <div className="h-3 w-3 rounded-full bg-warning" />
        <span className="text-sm text-muted-foreground">
          Warning: {stats.warning}/{stats.total}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <div className="h-3 w-3 rounded-full bg-danger" />
        <span className="text-sm text-muted-foreground">
          Critical: {stats.critical}/{stats.total}
        </span>
      </div>
      {stats.offline > 0 && (
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-muted" />
          <span className="text-sm text-muted-foreground">
            Offline: {stats.offline}/{stats.total}
          </span>
        </div>
      )}
    </div>
  );
}

export { HeatmapGrid, HeatmapStats };
export type { HeatmapCell };