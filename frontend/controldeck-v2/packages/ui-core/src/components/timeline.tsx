import * as React from "react";
import { cn } from "@ui-core/utils";
import { Badge } from "./badge";

interface TimelineEvent {
  id: string;
  timestamp: string;
  title: string;
  description?: string;
  severity: "info" | "warning" | "error" | "success" | "critical";
  icon?: React.ReactNode;
}

interface TimelineProps extends React.HTMLAttributes<HTMLDivElement> {
  events: TimelineEvent[];
  groupBy?: "hour" | "day" | "none";
  className?: string;
}

const severityColors = {
  info: "bg-info",
  warning: "bg-warning",
  error: "bg-danger",
  critical: "bg-danger",
  success: "bg-success",
};

const severityBadges = {
  info: "info" as const,
  warning: "warning" as const,
  error: "danger" as const,
  critical: "danger" as const,
  success: "success" as const,
};

function Timeline({ events, groupBy = "none", className, ...props }: TimelineProps) {
  const groupedEvents = React.useMemo(() => {
    if (groupBy === "none") return { "": events };
    
    const groups: Record<string, TimelineEvent[]> = {};
    
    events.forEach((event) => {
      const date = new Date(event.timestamp);
      let key: string;
      
      if (groupBy === "day") {
        key = date.toLocaleDateString("de-DE", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
        });
      } else {
        key = date.toLocaleDateString("de-DE", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          hour: "2-digit",
        }) + ":00";
      }
      
      if (!groups[key]) groups[key] = [];
      groups[key].push(event);
    });
    
    return groups;
  }, [events, groupBy]);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("de-DE", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className={cn("space-y-6", className)} {...props}>
      {Object.entries(groupedEvents).map(([groupKey, groupEvents]) => (
        <div key={groupKey}>
          {groupBy !== "none" && groupKey && (
            <div className="sticky top-0 z-10 mb-4">
              <Badge variant="secondary" className="text-xs">
                {groupKey}
              </Badge>
            </div>
          )}
          
          <div className="relative">
            {/* Timeline Line */}
            <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />
            
            {/* Events */}
            <div className="space-y-4">
              {groupEvents.map((event, index) => (
                <div key={event.id} className="relative flex gap-4">
                  {/* Dot */}
                  <div className="relative z-10 flex-shrink-0">
                    <div
                      className={cn(
                        "h-8 w-8 rounded-full flex items-center justify-center",
                        severityColors[event.severity],
                        event.severity === "critical" && "animate-pulse"
                      )}
                    >
                      {event.icon ? (
                        <span className="text-white text-xs">{event.icon}</span>
                      ) : (
                        <div className="h-2 w-2 rounded-full bg-white" />
                      )}
                    </div>
                  </div>
                  
                  {/* Content */}
                  <div className="flex-1 pb-4">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-muted-foreground font-mono">
                        {formatTime(event.timestamp)}
                      </span>
                      <Badge variant={severityBadges[event.severity]} className="text-xs">
                        {event.severity}
                      </Badge>
                    </div>
                    <h4 className="font-medium mt-1">{event.title}</h4>
                    {event.description && (
                      <p className="text-sm text-muted-foreground mt-1">
                        {event.description}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
      
      {events.length === 0 && (
        <div className="text-center py-8 text-muted-foreground">
          No events to display
        </div>
      )}
    </div>
  );
}

export { Timeline };
export type { TimelineEvent };