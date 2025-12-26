import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/app-sidebar"
import { Separator } from "@/components/ui/separator"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { NewThreatForm } from "@/components/NewThreatForm"
import { ThreatTable, Threat } from "@/components/ThreatTable"
import { fetchJson } from "@/lib/api"

export const dynamic = "force-dynamic"

type ThreatListResponse = {
  threats: Threat[]
}

type ThreatStatsResponse = {
  stats: {
    total: number
    by_severity: Record<string, number>
    by_status: Record<string, number>
    last_updated: number
  }
}

async function getData() {
  const [threats, stats] = await Promise.all([
    fetchJson<ThreatListResponse>("/api/threats"),
    fetchJson<ThreatStatsResponse>("/api/threats/stats/overview"),
  ])
  return { threats, stats }
}

export default async function ImmunePage() {
  const { threats, stats } = await getData()
  const s = stats.stats

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-16 shrink-0 items-center gap-2 border-b border-slate-800 bg-slate-950/80 px-4">
          <div className="flex items-center gap-2">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 h-5" />
            <Breadcrumb>
              <BreadcrumbList>
                <div className="hidden md:block">
                  <BreadcrumbItem>
                    <BreadcrumbLink href="/">BRAiN</BreadcrumbLink>
                  </BreadcrumbItem>
                  <BreadcrumbSeparator />
                </div>
                <BreadcrumbItem>
                  <BreadcrumbPage>Immune</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </div>
        </header>

        <div className="flex flex-1 flex-col gap-4 p-4 pt-3">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
                Threats total
              </div>
              <div className="text-lg font-semibold text-slate-50">
                {s.total}
              </div>
              <div className="mt-2 text-xs text-slate-400">
                Letztes Update{" "}
                <span className="font-mono">
                  {new Date(s.last_updated * 1000).toLocaleString("de-DE")}
                </span>
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
                By severity
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-400">
                <StatLine label="LOW" value={s.by_severity.LOW ?? 0} />
                <StatLine label="MEDIUM" value={s.by_severity.MEDIUM ?? 0} />
                <StatLine label="HIGH" value={s.by_severity.HIGH ?? 0} />
                <StatLine label="CRITICAL" value={s.by_severity.CRITICAL ?? 0} />
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
                By status
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-400">
                <StatLine label="OPEN" value={s.by_status.OPEN ?? 0} />
                <StatLine
                  label="INVESTIGATING"
                  value={s.by_status.INVESTIGATING ?? 0}
                />
                <StatLine
                  label="MITIGATED"
                  value={s.by_status.MITIGATED ?? 0}
                />
                <StatLine label="IGNORED" value={s.by_status.IGNORED ?? 0} />
                <StatLine
                  label="ESCALATED"
                  value={s.by_status.ESCALATED ?? 0}
                />
              </div>
            </div>
          </div>

          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-100">
                Threat Memory
              </h2>
            </div>
            <NewThreatForm />
            <ThreatTable threats={threats.threats} />
          </section>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}

function StatLine({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-300">{label}</span>
      <span className="font-mono text-slate-100">{value}</span>
    </div>
  )
}