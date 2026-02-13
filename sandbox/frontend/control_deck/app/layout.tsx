"use client";

import type { Metadata } from "next"
import "./globals.css"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useState } from "react"

// Cannot use metadata in client component, so we'll set it via head tags if needed

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
        refetchOnWindowFocus: false,
      },
    },
  }))

  return (
    <html lang="de" className="h-full">
      <head>
        <title>BRAiN ControlDeck</title>
        <meta name="description" content="BRAiN Core v2.0" />
      </head>
      <body className="h-full bg-slate-950 text-slate-50">
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </body>
    </html>
  )
}
