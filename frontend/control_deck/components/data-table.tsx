type Row = {
  id: number
  header: string
  type: string
  status: string
  target: string
  limit: string
  reviewer: string
}

type DataTableProps = {
  data: Row[]
}

export function DataTable({ data }: DataTableProps) {
  return (
    <div className="px-4 pb-6 pt-2 lg:px-6">
      <div className="mb-2 flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-slate-100">
            Proposal sections
          </div>
          <div className="text-xs text-slate-400">
            Demo-Tabelle aus data.json – später BRAiN-spezifische Tabellen.
          </div>
        </div>
      </div>
      <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/80">
        <div className="max-h-80 overflow-auto">
          <table className="min-w-full text-left text-xs">
            <thead className="sticky top-0 bg-slate-900">
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="px-3 py-2 font-medium">Header</th>
                <th className="px-3 py-2 font-medium">Type</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Target</th>
                <th className="px-3 py-2 font-medium">Limit</th>
                <th className="px-3 py-2 font-medium">Reviewer</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr
                  key={row.id}
                  className="border-b border-slate-900/60 text-slate-200 hover:bg-slate-900/80"
                >
                  <td className="px-3 py-2">{row.header}</td>
                  <td className="px-3 py-2 text-slate-400">{row.type}</td>
                  <td className="px-3 py-2">
                    <span className="rounded-full bg-slate-800 px-2 py-1 text-[10px] uppercase tracking-wide text-slate-200">
                      {row.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-slate-300">
                    {row.target}
                  </td>
                  <td className="px-3 py-2 font-mono text-slate-300">
                    {row.limit}
                  </td>
                  <td className="px-3 py-2 text-slate-300">{row.reviewer}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}