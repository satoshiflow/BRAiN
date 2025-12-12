"use client";

import Sidebar from "./sidebar";
import Topbar from "./topbar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen w-full">
      <Sidebar />

      <main className="flex flex-1 flex-col bg-background text-foreground">
        <Topbar />
        <div className="brain-shell">
          {children}
        </div>
      </main>
    </div>
  );
}
