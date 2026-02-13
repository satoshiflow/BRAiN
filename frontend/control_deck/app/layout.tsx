"use client";

import "./globals.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Layout } from "@/components/layout";
import { Inter } from "next/font/google";
import { AuthProvider } from "./providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <html lang="de" className={`${inter.variable} dark`}>
      <head>
        <title>BRAiN Control Deck</title>
        <meta name="description" content="BRAiN Core v2.0 - Control Center" />
      </head>
      <body className={`${inter.className} h-full bg-background text-foreground`}>
        <AuthProvider>
          <QueryClientProvider client={queryClient}>
            <Layout>{children}</Layout>
          </QueryClientProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
