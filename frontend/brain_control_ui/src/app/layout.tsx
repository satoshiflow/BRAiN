// frontend/brain_control_ui/src/app/layout.tsx
import type { Metadata } from "next";
import "./globals.css";
import { ReactNode } from "react";
import { ReactQueryProvider } from "@/components/providers/react-query-provider";
// ggf. Font-Imports etc. bleiben wie sie sind

export const metadata: Metadata = {
  title: "BRAIN Control Center",
  description: "Admin & Monitoring UI for BRAiN",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ReactQueryProvider>{children}</ReactQueryProvider>
      </body>
    </html>
  );
}
