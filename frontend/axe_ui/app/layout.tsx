import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "BRAiN AXE UI",
  description: "Interactive Agent Experience UI",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-black text-slate-50">
        <main className="mx-auto flex min-h-screen max-w-4xl flex-col px-4 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
