"use client";

import type { ReactNode } from "react";
import "./globals.css";
import { Navigation } from "@/components/Navigation";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <title>BRAiN AXE UI</title>
        <meta name="description" content="Auxiliary Execution Engine Dashboard" />
      </head>
      <body className="min-h-screen bg-slate-950 text-slate-50">
        <div className="flex min-h-screen">
          <Navigation />
          <main className="flex-1 overflow-auto">
            <div className="p-8">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
