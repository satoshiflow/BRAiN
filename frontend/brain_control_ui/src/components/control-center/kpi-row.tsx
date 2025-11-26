type KpiProps = {
  label: string
  value: string
  hint?: string
}

function KpiCard({ label, value, hint }: KpiProps) {
  return (
    <div className="flex-1 rounded-2xl bg-brain-panel/80 border border-white/5 px-5 py-4 shadow-sm">
      <div className="text-[0.65rem] uppercase tracking-[0.2em] text-slate-400">
        {label}
      </div>
      <div className="mt-1 text-3xl font-semibold text-slate-50">
        {value}
      </div>
      {hint && (
        <div className="mt-1 text-xs text-slate-400">
          {hint}
        </div>
      )}
    </div>
  )
}

export function KpiRow() {
  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between gap-4">
        <div>
          <h1 className="text-3xl font-light tracking-wide">
            BRAIN Control Center
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Zentrales Frontend für Cluster, Missionen, Agenten, Health &amp; Settings.
          </p>
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-4">
        <KpiCard
          label="Systemstatus"
          value="Online"
          hint="Cluster synchron · 0 kritische Incidents"
        />
        <KpiCard
          label="Aktive Missionen"
          value="12"
          hint="3 in Warteschlange · 4 heute abgeschlossen"
        />
        <KpiCard
          label="Aktive Agenten"
          value="27"
          hint="2 im Self-Repair · 1 pausiert"
        />
        <KpiCard
          label="System Health"
          value="98%"
          hint="Letzter Check vor 36 Sekunden"
        />
      </div>
    </section>
  )
}
