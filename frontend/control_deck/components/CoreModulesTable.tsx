export type CoreModule = {
  name: string
  version: string
  router_prefix: string
  status: string
  security?: {
    required_roles?: string[]
  }
  governance?: {
    level?: number
  }
  ui?: {
    group?: string
    icon?: string
  }
  path?: string
}

type CoreModulesTableProps = {
  modules: CoreModule[]
}

export function CoreModulesTable({ modules }: CoreModulesTableProps) {
  if (!modules.length) {
    return (
      <div className="px-4 pb-6 pt-2 lg:px-6">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-400">
          Keine Module gefunden. Prüfe manifest.json Dateien unter
          <span className="font-mono text-slate-300">
            {" "}
            backend/app/modules/*/manifest.json
          </span>
          .
        </div>
      </div>
    )
  }

  const sorted = [...modules].sort((a, b) => {
    const ga = a.ui?.group ?? "Core"
    const gb = b.ui?.group ?? "Core"
    if (ga === gb) return a.name.localeCompare(b.name)
    return ga.localeCompare(gb)
  })

  return (
    <div className="px-4 pb-6 pt-2 lg:px-6">
      <div className="mb-2 flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-slate-100">
            Core Modules
          </div>
          <div className="text-xs text-slate-400">
            Live aus <span className="font-mono">/api/core/modules</span>.
          </div>
        </div>
      </div>
      <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/80">
        <div className="max-h-80 overflow-auto">
          <table className="min-w-full text-left text-xs">
            <thead className="sticky top-0 bg-slate-900">
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="px-3 py-2 font-medium">Name</th>
                <th className="px-3 py-2 font-medium">Group</th>
                <th className="px-3 py-2 font-medium">Version</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Router</th>
                <th className="px-3 py-2 font-medium">Gov</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((m) => (
                <tr
                  key={m.name}
                  className="border-b border-slate-900/60 text-slate-200 hover:bg-slate-900/80"
                >
                  <td className="px-3 py-2">
                    <div className="flex flex-col">
                      <span className="font-medium text-slate-50">
                        {m.name}
                      </span>
                      {m.ui?.icon && (
                        <span className="text-[10px] text-slate-500">
                          icon: {m.ui.icon}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-slate-300">
                    {m.ui?.group ?? "Core"}
                  </td>
                  <td className="px-3 py-2 font-mono text-slate-300">
                    {m.version}
                  </td>
                  <td className="px-3 py-2">
                    <StatusBadge status={m.status} />
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px] text-slate-300">
                    {m.router_prefix}
                  </td>
                  <td className="px-3 py-2 text-slate-300">
                    <span className="rounded-full bg-slate-800 px-2 py-1 text-[10px]">
                      L{m.governance?.level ?? 0}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase()
  let className = "bg-slate-800 text-slate-100"

  if (normalized === "stable") {
    className = "bg-emerald-900/60 text-emerald-300"
  } else if (normalized === "experimental") {
    className = "bg-sky-900/60 text-sky-300"
  } else if (normalized === "deprecated") {
    className = "bg-amber-900/60 text-amber-300"
  }

  return (
    <span
      className={`rounded-full px-2 py-1 text-[10px] uppercase tracking-wide ${className}`}
    >
      {status}
    </span>
  )
}