import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "BRAIN Control Center",
  description: "FALK · BRAIN · Multi-Agent Control Deck",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="de" className="dark">
      <body className="min-h-screen bg-brain-bg text-slate-50">
        {children}
      </body>
    </html>
  )
}
