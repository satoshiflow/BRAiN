import * as React from "react"

type SeparatorProps = {
  orientation?: "horizontal" | "vertical"
  className?: string
}

export function Separator({
  orientation = "horizontal",
  className,
}: SeparatorProps) {
  const base =
    orientation === "vertical"
      ? "h-full w-px"
      : "h-px w-full"

  return (
    <div
      className={`${base} bg-slate-800 ${className ?? ""}`}
      data-orientation={orientation}
    />
  )
}