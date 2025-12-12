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
import { fetchJson } from "@/lib/api"

type SupervisorStatus = {
  status: string
  timestamp: string
  total_missions: number
  running_missions: number
  pending_missions: number
  completed_missions: number
  failed_missions: number
  cancelled_missions: number
  agents: {
    id: string
    name: string
    role?: string | null
    state: string
    last_heartbeat?: string | null
    missions_running: number
  }[]
}

async function getData() {
  const supervisor = await fetchJson<SupervisorStatus>("/api/supervisor/status")
  return { supervisor }
}

export default async function SupervisorPage() {
  const { supervisor } = await getData()

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
                  <BreadcrumbItem>
                    <BreadcrumbLink href="/">ControlDeck</BreadcrumbLink>
                  </BreadcrumbItem>
                  <BreadcrumbSeparator />
                </div>
                <BreadcrumbItem>
                  <BreadcrumbPage>Supervisor</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </div>
        </header>

        <div className="flex flex-1 flex-col gap-4 p-4 pt-3">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
                Supervisor Status
              </div>
              <div className="flex items-center justify-between">
                <div className="text-lg font-semibold text-slate-50">
                  {supervisor.status}
                </div>
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
              </div>
              <div className="mt-2 text-xs text-slate-400">
                Updated at{" "}
                <span className="font-mono">
                  {new Date(supervisor.timestamp).toLocaleString("de-DE")}
                </span>
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
                Missions Overview
              </div>
              <div className="text-lg font-semibold text-slate-50">
                {supervisor.total_missions} Missions
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-400">
                <StatLine label="Running" value={supervisor.running_missions} />
                <StatLine label="Pending" value={supervisor.pending_missions} />
                <StatLine
                  label="Completed"
                  value={supervisor.completed_missions}
                />
                <StatLine label="Failed" value={supervisor.failed_missions} />
                <StatLine
                  label="Cancelled"
                  value={supervisor.cancelled_missions}
                />
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
                Agents
              </div>
              <div className="text-lg font-semibold text-slate-50">
                {supervisor.agents.length} Agents
              </div>
              <div className="mt-2 text-xs text-slate-400">
                Agent-Daten folgen, sobald das Immune-System angebunden ist.
              </div>
            </div>
          </div>

          <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-100">
                Supervisor Details
              </h2>
            </div>
            <pre className="max-h-96 overflow-auto rounded-md bg-slate-950/80 p-3 text-xs text-slate-200">
              {JSON.stringify(supervisor, null, 2)}
            </pre>
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