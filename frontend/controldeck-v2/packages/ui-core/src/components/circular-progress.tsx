import * as React from "react";
import { cn } from "@ui-core/utils";

interface CircularProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number;
  size?: "sm" | "md" | "lg" | "xl";
  color?: "primary" | "success" | "warning" | "danger" | "info";
  label?: string;
  sublabel?: string;
  showValue?: boolean;
  thickness?: number;
  animated?: boolean;
}

const sizeConfig = {
  sm: { width: 64, stroke: 6, font: "text-sm" },
  md: { width: 96, stroke: 8, font: "text-base" },
  lg: { width: 128, stroke: 10, font: "text-lg" },
  xl: { width: 160, stroke: 12, font: "text-xl" },
};

const colorConfig = {
  primary: "stroke-primary",
  success: "stroke-success",
  warning: "stroke-warning",
  danger: "stroke-danger",
  info: "stroke-info",
};

function CircularProgress({
  value,
  size = "md",
  color = "primary",
  label,
  sublabel,
  showValue = true,
  thickness,
  animated = true,
  className,
  ...props
}: CircularProgressProps) {
  const config = sizeConfig[size];
  const strokeWidth = thickness ?? config.stroke;
  const radius = (config.width - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(Math.max(value, 0), 100);
  const offset = circumference - (progress / 100) * circumference;
  
  const isComplete = progress >= 100;

  return (
    <div
      className={cn("flex flex-col items-center gap-2", className)}
      {...props}
    >
      <div className="relative" style={{ width: config.width, height: config.width }}>
        {/* Background Circle */}
        <svg
          className="transform -rotate-90"
          width={config.width}
          height={config.width}
        >
          <circle
            cx={config.width / 2}
            cy={config.width / 2}
            r={radius}
            fill="none"
            className="stroke-muted/20"
            strokeWidth={strokeWidth}
          />
          
          {/* Progress Circle */}
          <circle
            cx={config.width / 2}
            cy={config.width / 2}
            r={radius}
            fill="none"
            className={cn(
              colorConfig[color],
              "transition-all duration-500 ease-out",
              animated && "transition-all duration-700 ease-out",
              isComplete && color === "success" && "drop-shadow-[0_0_8px_rgba(16,185,129,0.5)]"
            )}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{
              filter: isComplete ? `drop-shadow(0 0 6px currentColor)` : undefined,
            }}
          />
        </svg>
        
        {/* Center Content */}
        {showValue && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={cn("font-semibold", config.font)}>
              {Math.round(progress)}%
            </span>
          </div>
        )}
        
        {/* Complete Indicator */}
        {isComplete && (
          <div className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-success flex items-center justify-center">
            <svg className="h-3 w-3 text-success-foreground" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          </div>
        )}
      </div>
      
      {/* Labels */}
      {(label || sublabel) && (
        <div className="text-center">
          {label && (
            <p className="text-sm font-medium">{label}</p>
          )}
          {sublabel && (
            <p className="text-xs text-muted-foreground">{sublabel}</p>
          )}
        </div>
      )}
    </div>
  );
}

export { CircularProgress };