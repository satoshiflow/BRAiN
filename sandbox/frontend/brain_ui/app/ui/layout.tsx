import type { ReactNode } from "react";

export const metadata = {
  title: "BRAiN UI · Onboarding",
  description: "Choose how you want to meet BRAiN – circle or avatar."
};

export default function UiLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#050509] text-gray-100 flex flex-col overflow-hidden">
      <div className="pointer-events-none fixed inset-0 opacity-40">
        <div className="absolute -top-40 -left-40 h-80 w-80 rounded-full bg-purple-500/30 blur-3xl" />
        <div className="absolute -bottom-40 -right-40 h-80 w-80 rounded-full bg-cyan-500/30 blur-3xl" />
      </div>

      <header className="relative z-10 border-b border-white/5 px-4 md:px-8 py-4 flex items-center justify-between backdrop-blur-sm bg-black/30">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-2xl bg-gradient-to-br from-indigo-500 via-sky-500 to-emerald-400 shadow-lg shadow-sky-500/40" />
          <div className="flex flex-col leading-tight">
            <span className="text-[10px] font-medium tracking-[0.3em] uppercase text-white/60">
              BRAiN UI
            </span>
            <span className="text-xs text-white/40">
              Immersive Conversational Interface
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 text-[11px] text-white/45">
          <span className="hidden md:inline">Mode Setup</span>
          <span className="inline-flex items-center gap-1 rounded-full border border-white/10 px-2 py-1 bg-white/5 backdrop-blur">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Online</span>
          </span>
        </div>
      </header>

      <main className="relative z-10 flex-1 flex items-center justify-center px-4 md:px-8 py-8">
        <div className="w-full max-w-5xl mx-auto">{children}</div>
      </main>
    </div>
  );
}
