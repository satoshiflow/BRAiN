"use client";

import type { ReactNode } from "react";
import "./globals.css";
import { Navigation } from "@/components/Navigation";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <head>
        <title>BRAiN AXE UI</title>
        <meta name="description" content="Auxiliary Execution Engine Dashboard" />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
      </head>
      <body className="h-full bg-slate-950 text-slate-50 overflow-hidden">
        <div className="flex h-full">
          <Navigation />

          {/* Main Content - Responsive padding */}
          <main className="flex-1 overflow-auto">
            <div className="p-4 sm:p-6 lg:p-8">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
