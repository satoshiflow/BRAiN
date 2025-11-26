import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "BRAiN UI",
  description: "Immersive conversational interface for BRAiN"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-brain-bg text-gray-100 antialiased">
        {children}
      </body>
    </html>
  );
}
