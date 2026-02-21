import * as React from "react";
import { cn } from "@ui-core/utils";
import { Badge } from "./badge";

interface ConsoleEvent {
  id: string;
  timestamp: string;
  message: string;
  severity: "info" | "warning" | "error" | "success" | "critical";
  source?: string;
  details?: Record<string, unknown>;
}

interface ConsoleFeedProps extends React.HTMLAttributes<HTMLDivElement> {
  events: ConsoleEvent[];
  maxLines?: number;
  autoScroll?: boolean;
  showTimestamp?: boolean;
  showSeverity?: boolean;
  filter?: "all" | "info" | "warning" | "error" | "success" | "critical";
  className?: string;
  emptyMessage?: string;
}

const severityColors = {
  info: "text-info",
  warning: "text-warning",
  error: "text-danger",
  critical: "text-danger font-bold",
  success: "text-success",
};

const severityPrefixes = {
  info: "[INFO]",
  warning: "[WARN]",
  error: "[ERROR]",
  critical: "[CRIT]",
  success: "[OK]",
};

const severityBadges = {
  info: "info" as const,
  warning: "warning" as const,
  error: "danger" as const,
  critical: "danger" as const,
  success: "success" as const,
};

function ConsoleFeed({
  events,
  maxLines = 100,
  autoScroll = true,
  showTimestamp = true,
  showSeverity = true,
  filter = "all",
  className,
  emptyMessage = "No events to display",
  ...props
}: ConsoleFeedProps) {
  const scrollRef = React.useRef<HTMLDivElement>(null);
  
  const filteredEvents = React.useMemo(() => {
    let filtered = filter === "all" 
      ? events 
      : events.filter((e) => e.severity === filter);
    
    // Limit to maxLines (keep newest)
    if (filtered.length > maxLines) {
      filtered = filtered.slice(-maxLines);
    }
    
    return filtered;
  }, [events, filter, maxLines]);

  // Auto-scroll to bottom
  React.useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [filteredEvents, autoScroll]);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("de-DE", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  };

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-[#0B1220] font-mono text-sm overflow-hidden",
        className
      )}
      {...props}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-card">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Console</span>
          {filter !== "all" && (
            <Badge variant={severityBadges[filter]} className="text-xs">
              {filter.toUpperCase()}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span>{filteredEvents.length} lines</span>
          {autoScroll && (
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-success animate-pulse" />
              LIVE
            </span>
          )}
        </div>
      </div>

      {/* Console Output */}
      <div
        ref={scrollRef}
        className="p-4 overflow-auto max-h-[400px] space-y-1 scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent"
      >
        {filteredEvents.length === 0 ? (
          <div className="text-muted-foreground text-center py-8">
            {emptyMessage}
          </div>
        ) : (
          filteredEvents.map((event, index) => (
            <div
              key={event.id || index}
              className="flex items-start gap-2 hover:bg-white/5 px-1 -mx-1 rounded"
            >
              {/* Timestamp */}
              {showTimestamp && (
                <span className="text-muted-foreground shrink-0 w-20">
                  {formatTimestamp(event.timestamp)}
                </span>
              )}
              
              {/* Severity */}
              {showSeverity && (
                <span className={cn("shrink-0 w-14", severityColors[event.severity])}>
                  {severityPrefixes[event.severity]}
                </span>
              )}
              
              {/* Source */}
              {event.source && (
                <span className="text-muted-foreground shrink-0 w-24 truncate">
                  [{event.source}]
                </span>
              )}
              
              {/* Message */}
              <span className={cn("break-all", severityColors[event.severity])}>
                {event.message}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export { ConsoleFeed };
export type { ConsoleEvent };