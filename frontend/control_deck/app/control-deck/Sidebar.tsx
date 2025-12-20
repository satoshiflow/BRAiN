"use client";

import Link from "next/link";
import { useModuleRegistry } from "./ModuleRegistryProvider";

// Static Phase 4 Module Links
const PHASE_4_MODULES = [
  {
    name: "Phase 4: Advanced Features",
    label: "PHASE 4 MODULES",
    routes: [
      { path: "/maintenance", label: "Predictive Maintenance" },
      { path: "/navigation", label: "Advanced Navigation" },
      { path: "/collaboration", label: "Multi-Robot Collaboration" },
      { path: "/learning", label: "Learning from Demonstration" },
    ],
  },
];

export function Sidebar() {
  const { modules, loading } = useModuleRegistry();

  if (loading) return <div className="p-4 text-sm">Lade Module…</div>;

  return (
    <nav className="p-4 text-sm">
      {/* Dynamic Modules from Backend */}
      {modules.map((m) => (
        <div key={m.name} className="mb-4">
          <div className="text-xs font-semibold text-neutral-500 mb-2">
            {m.label}
          </div>
          {m.routes?.map((r) => (
            <Link
              key={r.path}
              href={r.path}
              className="block py-1 text-neutral-200 hover:text-white"
            >
              {r.label}
            </Link>
          ))}
        </div>
      ))}

      {/* Static Phase 4 Modules */}
      {PHASE_4_MODULES.map((m) => (
        <div key={m.name} className="mb-4">
          <div className="text-xs font-semibold text-emerald-500 mb-2">
            {m.label}
          </div>
          {m.routes.map((r) => (
            <Link
              key={r.path}
              href={r.path}
              className="block py-1 text-neutral-200 hover:text-white"
            >
              {r.label}
            </Link>
          ))}
        </div>
      ))}
    </nav>
  );
}