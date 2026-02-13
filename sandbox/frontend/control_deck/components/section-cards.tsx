type MissionStats = {
  total: number
  by_status: Record<string, number>
  last_updated: number
}

type SupervisorStatus = {
  status: string
  timestamp: string
  total_missions: number
  running_missions: number
  pending_missions: number
  completed_missions: number
  failed_missions: number
  cancelled_missions: number
}

type SectionCardsProps = {
  coreStatus: string
  missionStats: MissionStats
  supervisor: SupervisorStatus
}

export function SectionCards({
  coreStatus,
  missionStats,
  supervisor,
}: SectionCardsProps) {
  const ok = coreStatus === "ok"
  const total = missionStats.total ?? 0
  const running = missionStats.by_status?.RUNNING ?? 0
  const pending = missionStats.by_status?.PENDING ?? 0
  const completed = missionStats.by_status?.COMPLETED ?? 0

  return (
    <div className="grid gap-4 px-4 md:grid-cols-3 lg:px-6">
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
          Core API
        </div>
        <div className="flex items-center justify-between">
          <div className="text-lg font-semibold text-slate-50">
            {ok ? "Online" : "Degraded"}
          </div>
          <span
            className={`h-2 w-2 rounded-full ${
              ok ? "bg-emerald-400" : "bg-rose-400"
            }`}
          />
        </div>
        <div className="mt-1 text-xs text-slate-500">
          Status: <span className="font-mono">{coreStatus}</span>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
          Missions
        </div>
        <div className="text-lg font-semibold text-slate-50">
          {total} Missions
        </div>
        <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-400">
          <div>
            <div className="text-slate-300">Running</div>
            <div className="font-mono text-emerald-400">{running}</div>
          </div>
          <div>
            <div className="text-slate-300">Pending</div>
            <div className="font-mono text-amber-300">{pending}</div>
          </div>
          <div>
            <div className="text-slate-300">Done</div>
            <div className="font-mono text-sky-300">{completed}</div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
          Supervisor
        </div>
        <div className="flex items-center justify-between">
          <div className="text-lg font-semibold text-slate-50">
            {supervisor.status}
          </div>
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
        </div>
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-400">
          <div>
            <div className="text-slate-300">Running</div>
            <div className="font-mono text-emerald-400">
              {supervisor.running_missions}
            </div>
          </div>
          <div>
            <div className="text-slate-300">Failed</div>
            <div className="font-mono text-rose-400">
              {supervisor.failed_missions}
            </div>
          </div>
          <div>
            <div className="text-slate-300">Completed</div>
            <div className="font-mono text-sky-300">
              {supervisor.completed_missions}
            </div>
          </div>
          <div>
            <div className="text-slate-300">Cancelled</div>
            <div className="font-mono text-slate-300">
              {supervisor.cancelled_missions}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}