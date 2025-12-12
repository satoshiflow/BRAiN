"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"

const tabs = [
  { href: "/", label: "Overview" },
  { href: "/control", label: "Control Deck" },
  { href: "/missions", label: "Mission Deck" },
  { href: "/agents", label: "Agenten Deck" },
  { href: "/health", label: "Health Deck" },
  { href: "/settings", label: "Settings" },
]

export function DeckTabs() {
  const pathname = usePathname()

  return (
    <div className="inline-flex rounded-full bg-brain-panelSoft/70 border border-white/5 p-1 text-xs">
      {tabs.map((tab) => {
        const active =
          pathname === tab.href || (tab.href === "/" && pathname === "/")
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              "px-4 py-2 rounded-full transition-all",
              active
                ? "bg-brain-gold/10 text-brain-goldStrong shadow-brain-glow"
                : "text-slate-400 hover:text-slate-100"
            )}
          >
            {tab.label}
          </Link>
        )
      })}
    </div>
  )
}
