"use client";

import Link from "next/link";
import { useModuleRegistry } from "./ModuleRegistryProvider";

export function Sidebar() {
  const { modules, loading } = useModuleRegistry();

  if (loading) return <div className="p-4 text-sm">Lade Module…</div>;

  return (
    <nav className="p-4 text-sm">
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
    </nav>
  );
}