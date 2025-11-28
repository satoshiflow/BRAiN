"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const nav = [
  { href: "/", label: "Overview" },
  { href: "/settings/llm", label: "LLM Config" },
  { href: "/settings/agents", label: "Agents" },
  { href: "/missions", label: "Missions" },
  { href: "/supervisor", label: "Supervisor" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:flex w-64 border-r border-border bg-secondary/40 backdrop-blur-xl">
      <nav className="flex flex-col gap-2 p-6">
        {nav.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`px-4 py-2 rounded-xl text-sm transition-colors ${
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-secondary/70"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
