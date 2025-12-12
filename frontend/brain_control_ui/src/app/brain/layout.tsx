import Link from "next/link";

export default function BrainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-emerald-500/90" />
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300/80">
                BRAiN
              </p>
              <p className="text-sm font-medium text-slate-100">
                Control Center
              </p>
            </div>
          </div>
          <nav className="flex gap-4 text-xs font-medium text-slate-300">
            <Link
              href="/brain"
              className="rounded-md px-3 py-1 hover:bg-slate-800 hover:text-slate-50"
            >
              Overview
            </Link>
            <Link
              href="/brain/debug"
              className="rounded-md px-3 py-1 hover:bg-slate-800 hover:text-slate-50"
            >
              Debug
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
    </div>
  );
}