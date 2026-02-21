import * as React from "react";
import { cn } from "@ui-core/utils";
import { Card, CardContent, CardHeader, CardTitle } from "./card";
import { Badge } from "./badge";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

interface KpiCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  value: string | number;
  delta?: {
    value: number;
    label?: string;
  };
  status?: "positive" | "negative" | "neutral" | "warning" | "danger";
  icon?: React.ReactNode;
  loading?: boolean;
  'data-testid'?: string;
}

function KpiCard({
  title,
  value,
  delta,
  status = "neutral",
  icon,
  loading = false,
  className,
  ...props
}: KpiCardProps) {
  const getDeltaIcon = () => {
    if (!delta) return null;
    if (delta.value > 0) return <ArrowUpRight className="h-4 w-4" />;
    if (delta.value < 0) return <ArrowDownRight className="h-4 w-4" />;
    return <Minus className="h-4 w-4" />;
  };

  const getDeltaColor = () => {
    if (status !== "neutral") {
      return status === "positive" || status === "warning"
        ? "text-success"
        : status === "negative" || status === "danger"
        ? "text-danger"
        : "text-muted-foreground";
    }
    if (!delta) return "text-muted-foreground";
    if (delta.value > 0) return "text-success";
    if (delta.value < 0) return "text-danger";
    return "text-muted-foreground";
  };

  if (loading) {
    return (
      <Card className={cn("animate-pulse", className)} {...props}>
        <CardHeader className="pb-2">
          <div className="h-4 w-24 bg-muted rounded" />
        </CardHeader>
        <CardContent>
          <div className="h-8 w-16 bg-muted rounded mb-2" />
          <div className="h-3 w-20 bg-muted rounded" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid={`kpi-card-${title.toLowerCase().replace(/\s+/g, '-')}`} className={cn("", className)} {...props}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        {icon && <div className="text-muted-foreground">{icon}</div>}
      </CardHeader>
      <CardContent>
        <div data-testid="kpi-value" className="text-2xl font-bold">{value}</div>
        {delta && (
          <div data-testid="kpi-delta" className={cn("flex items-center gap-1 text-xs mt-1", getDeltaColor())}>
            {getDeltaIcon()}
            <span>{Math.abs(delta.value)}%</span>
            {delta.label && (
              <span className="text-muted-foreground ml-1">{delta.label}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export { KpiCard };