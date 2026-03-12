import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { Navigation } from "@/components/Navigation";
import { PwaInit } from "@/components/PwaInit";
import { AuthProvider } from "@/components/auth/AuthProvider";

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
      <body className="h-full overflow-hidden text-slate-50">
        <AuthProvider>
          <PwaInit />
          <div className="axe-grid-overlay relative flex h-full">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_10%,rgba(20,196,216,0.10),transparent_35%),radial-gradient(circle_at_82%_84%,rgba(225,122,58,0.15),transparent_30%)]" />

            <Navigation />

            <main className="relative flex-1 overflow-auto pt-16 lg:pt-0">
              <div className="p-4 sm:p-6 lg:p-8">
                {children}
              </div>
            </main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
