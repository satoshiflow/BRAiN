type ChartAreaInteractiveProps = {
  title?: string
  description?: string
}

export function ChartAreaInteractive({
  title = "Activity overview",
  description = "Quick overview of recent system activity.",
}: ChartAreaInteractiveProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="mb-2 flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-slate-100">{title}</div>
          <div className="text-xs text-slate-400">{description}</div>
        </div>
        <span className="rounded-full bg-slate-800 px-2 py-1 text-xs text-slate-300">
          Demo
        </span>
      </div>
      <div className="mt-3 h-40 rounded-md border border-dashed border-slate-800 bg-slate-950/60 text-xs text-slate-500">
        <div className="flex h-full items-center justify-center">
          Chart placeholder – später echte Telemetrie
        </div>
      </div>
    </div>
  )
}