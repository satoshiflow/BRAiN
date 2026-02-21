import * as React from "react";
import { cn } from "@ui-core/utils";
import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";

interface ChartDataPoint {
  timestamp: string;
  value: number;
  label?: string;
}

interface LineChartProps extends React.HTMLAttributes<HTMLDivElement> {
  data: ChartDataPoint[];
  title?: string;
  color?: string;
  showArea?: boolean;
  showGrid?: boolean;
  showDots?: boolean;
  height?: number;
  yAxisLabel?: string;
  xAxisLabel?: string;
  formatXAxis?: (value: string) => string;
  formatYAxis?: (value: number) => string;
  formatTooltip?: (value: number, timestamp: string) => string;
  className?: string;
}

const defaultColors = {
  primary: "#3B82F6",   // info
  success: "#10B981",
  warning: "#F59E0B",
  danger: "#EF4444",
};

function LineChart({
  data,
  title,
  color = "primary",
  showArea = true,
  showGrid = true,
  showDots = false,
  height = 200,
  yAxisLabel,
  xAxisLabel,
  formatXAxis,
  formatYAxis,
  formatTooltip,
  className,
  ...props
}: LineChartProps) {
  const chartColor = defaultColors[color as keyof typeof defaultColors] || color;
  
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("de-DE", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const CustomTooltip = ({ active, payload, label }: {
    active?: boolean;
    payload?: Array<{ value: number }>;
    label?: string;
  }) => {
    if (active && payload && payload.length) {
      const value = payload[0].value;
      const displayValue = formatTooltip 
        ? formatTooltip(value, label || '')
        : `${value}`;
      
      return (
        <div className="bg-card border border-border rounded-lg p-2 shadow-lg">
          <p className="text-xs text-muted-foreground">
            {label ? formatTime(label) : ''}
          </p>
          <p className="text-sm font-semibold" style={{ color: chartColor }}>
            {displayValue}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card p-4",
        className
      )}
      {...props}
    >
      {title && (
        <h3 className="text-sm font-medium mb-4">{title}</h3>
      )}
      
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#334155"
              opacity={0.3}
            />
          )}
          
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatXAxis || formatTime}
            stroke="#6B7280"
            fontSize={10}
            tickLine={false}
            axisLine={false}
            minTickGap={30}
          />
          
          <YAxis
            tickFormatter={formatYAxis || ((v) => `${v}`)}
            stroke="#6B7280"
            fontSize={10}
            tickLine={false}
            axisLine={false}
            width={40}
          />
          
          <Tooltip content={<CustomTooltip />} />
          
          {showArea && (
            <Area
              type="monotone"
              dataKey="value"
              stroke={chartColor}
              strokeWidth={2}
              fill={chartColor}
              fillOpacity={0.1}
              dot={showDots}
              activeDot={{ r: 4, fill: chartColor }}
              animationDuration={500}
            />
          )}
          
          <Line
            type="monotone"
            dataKey="value"
            stroke={chartColor}
            strokeWidth={2}
            dot={showDots ? { r: 3, fill: chartColor } : false}
            activeDot={{ r: 5, fill: chartColor }}
            animationDuration={500}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// Simple sparkline variant
interface SparklineProps extends React.HTMLAttributes<HTMLDivElement> {
  data: number[];
  color?: "primary" | "success" | "warning" | "danger";
  height?: number;
  className?: string;
}

function Sparkline({
  data,
  color = "primary",
  height = 40,
  className,
  ...props
}: SparklineProps) {
  const chartColor = defaultColors[color];
  
  const chartData = data.map((value, index) => ({
    index,
    value,
  }));

  return (
    <div className={cn("inline-block", className)} {...props}>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={chartData}>
          <Area
            type="monotone"
            dataKey="value"
            stroke={chartColor}
            strokeWidth={2}
            fill={chartColor}
            fillOpacity={0.1}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export { LineChart, Sparkline };
export type { ChartDataPoint };