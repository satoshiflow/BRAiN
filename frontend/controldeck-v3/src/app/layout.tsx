import type { Metadata } from "next";
import Script from "next/script";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "ControlDeck v3 - BRAiN OS Governance",
  description: "Central governance console for BRAiN Operating System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans antialiased">
        <Script id="controldeck-theme-init" strategy="beforeInteractive">
          {`(() => {
            try {
              const savedTheme = localStorage.getItem('controldeck-theme') || 'system';
              const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
              const useDark = savedTheme === 'dark' || (savedTheme === 'system' && prefersDark);
              document.documentElement.classList.toggle('dark', useDark);
            } catch (_) {}
          })();`}
        </Script>
        {children}
      </body>
    </html>
  );
}
