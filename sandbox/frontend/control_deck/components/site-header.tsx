import Link from "next/link"

export function SiteHeader() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-800 bg-slate-950/80 px-4 backdrop-blur md:px-6">
      <div className="flex flex-col">
        <span className="text-sm font-semibold text-slate-100">
          BRAiN ControlDeck
        </span>
        <span className="text-xs text-slate-400">Core v1.0 • Local</span>
      </div>
      <div className="flex items-center gap-2 text-xs">
        <span className="rounded-full bg-emerald-500/10 px-2 py-1 text-emerald-400">
          API healthy
        </span>
        <Link
          href="/settings"
          className="rounded-md border border-slate-700 px-2 py-1 text-slate-300 hover:border-emerald-500 hover:text-emerald-300"
        >
          Settings
        </Link>
      </div>
    </header>
  )
}
