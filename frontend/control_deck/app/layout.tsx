import "./globals.css";
import { Layout } from "@/components/layout";
import { Inter } from "next/font/google";
import { Providers } from "./providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

// Force dynamic rendering - disable static generation to prevent useContext errors
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export const metadata = {
  title: "BRAiN Control Deck",
  description: "BRAiN Core v2.0 - Control Center",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="de" className={`${inter.variable} dark`}>
      <body className={`${inter.className} h-full bg-background text-foreground`}>
        <Providers>
          <Layout>{children}</Layout>
        </Providers>
      </body>
    </html>
  );
}
