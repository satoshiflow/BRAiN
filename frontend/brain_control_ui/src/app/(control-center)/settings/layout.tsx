"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

type Props = {
  children: React.ReactNode;
};

type SettingsNavItem = {
  label: string;
  href: string;
  description?: string;
};

const NAV_ITEMS: SettingsNavItem[] = [
  { label: "Overview", href: "/settings" },
  { label: "LLM", href: "/settings/llm" },
  { label: "Agents", href: "/settings/agents" },
  // Später: System, Security, Integrations usw.
];

export default function SettingsLayout({ children }: Props) {
  const pathname = usePathname();

  return (
    <div className="px-4 py-6 md:px-6 lg:px-8 space-y-6">
      {/* Header */}
      <header className="flex items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-sm text-muted-foreground">
            Zentrale Konfiguration von BRAiN (LLM, Agents, System).
          </p>
        </div>
      </header>

      {/* Sub-Navigation */}
      <nav className="flex flex-wrap gap-2 border-b border-border/60 pb-2 text-sm">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "px-3 py-1.5 rounded-full border transition-colors",
                active
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-transparent hover:border-border hover:bg-muted/60 text-muted-foreground",
              ].join(" ")}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Page Content */}
      <div>{children}</div>
    </div>
  );
}
