import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BRAiN ControlDeck v2",
  description: "Enterprise Futuristic Control System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de" className="dark">
      <body className="min-h-screen bg-background font-sans antialiased">
        {children}
      </body>
    </html>
  );
}