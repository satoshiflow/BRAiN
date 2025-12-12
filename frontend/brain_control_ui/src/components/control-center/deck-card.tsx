import Link from "next/link"
import type { ReactNode } from "react"

type DeckCardProps = {
  title: string
  subtitle: string
  kpiLabel: string
  kpiValue: string
  meta?: string
  href: string
  accent?: "gold" | "blue" | "green" | "red" | "purple"
  children?: ReactNode
}

const accentMap: Record<string, string> = {
  gold: "from-brain-gold/40 to-transparent",
  blue: "from-brain-blue/40 to-transparent",
  green: "from-brain-green/40 to-transparent",
  red: "from-brain-red/50 to-transparent",
  purple: "from-brain-purple/45 to-transparent",
}

export function DeckCard({
  title,
  subtitle,
  kpiLabel,
  kpiValue,
  meta,
  href,
  accent = "gold",
  children,
}: DeckCardProps) {
  return (
    <Link
      href={href}
      className="group relative rounded-2xl border border-white/5 bg-brain-panel/80 hover:border-brain-gold/40 transition-all shadow-sm hover:shadow-brain-glow overflow-hidden"
    >
      <div
        className={`pointer-events-none absolute inset-0 opacity-0 group-hover:opacity-100 bg-gradient-to-br ${accentMap[accent]} transition-opacity`}
      />
      <div className="relative px-5 py-4 space-y-3">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="text-[0.6rem] uppercase tracking-[0.25em] text-slate-400">
              {subtitle}
            </div>
            <div className="mt-1 text-lg font-semibold">{title}</div>
          </div>
          <div className="text-right">
            <div className="text-[0.6rem] uppercase tracking-[0.2em] text-slate-500">
              {kpiLabel}
            </div>
            <div className="text-2xl font-semibold">{kpiValue}</div>
          </div>
        </div>

        {meta && (
          <div className="text-xs text-slate-400">{meta}</div>
        )}

        {children}

        <div className="pt-1 text-xs text-brain-goldStrong flex items-center gap-1">
          <span>Öffnen</span>
          <span aria-hidden>→</span>
        </div>
      </div>
    </Link>
  )
}
