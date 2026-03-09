import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { Navigation } from "@/components/Navigation";
import { PwaInit } from "@/components/PwaInit";

export const metadata: Metadata = {
  title: "BRAiN AXE UI",
  description: "Auxiliary Execution Engine Dashboard",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "AXE UI",
  },
  icons: {
    icon: [
      { url: "/icons/axe-192.png", type: "image/png", sizes: "192x192" },
      { url: "/icons/axe-512.png", type: "image/png", sizes: "512x512" },
      { url: "/icons/axe-192.svg", type: "image/svg+xml", sizes: "192x192" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#020617",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full bg-slate-950 text-slate-50 overflow-hidden">
        <PwaInit />
        <div className="flex h-full">
          <Navigation />

          {/* Main Content - Responsive padding */}
          <main className="flex-1 overflow-auto pt-16 lg:pt-0">
            <div className="p-4 sm:p-6 lg:p-8">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
