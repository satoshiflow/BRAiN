import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "BRAiN ControlDeck",
  description: "BRAiN Core v1.0",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="de" className="h-full">
      <body className="h-full bg-slate-950 text-slate-50">
        {children}
      </body>
    </html>
  )
}
