"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

const navItems = [
  { href: "/agents", label: "AGENTS" },
  { href: "/system", label: "SYSTEM" },
  { href: "/dna", label: "DNA" },
  { href: "/soul", label: "SOUL" },
  { href: "/economy", label: "ECONOMY" },
]

export function Header() {
  const pathname = usePathname()

  return (
    <header className="flex items-center justify-between gap-6">
      <div className="flex items-center gap-8">
        <div className="text-2xl font-light tracking-[0.25em] uppercase">
          FALK
        </div>
        <nav className="hidden md:flex items-center gap-6 text-xs tracking-[0.25em] text-slate-400 uppercase">
          {navItems.map((item) => {
            const active = pathname?.startsWith(item.href)
            return (
              <Link key={item.href} href={item.href} className="relative">
                <span
                  className={
                    active
                      ? "text-brain-goldStrong"
                      : "hover:text-slate-200 transition-colors"
                  }
                >
                  {item.label}
                </span>
              </Link>
            )
          })}
        </nav>
      </div>

      <div className="flex items-center gap-4">
        <span className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-wide text-slate-400">
          Env: <span className="text-brain-goldStrong">LOCAL DEV</span>
        </span>
        <button className="h-9 w-9 rounded-full bg-gradient-to-br from-brain-goldStrong/80 to-brain-gold/40 flex items-center justify-center text-xs font-semibold">
          OF
        </button>
      </div>
    </header>
  )
}
