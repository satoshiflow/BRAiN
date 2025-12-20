import "./globals.css";

export const metadata = {
  title: "BRAiN × RYR — Robot as a Service",
  description: "Autonomous labor as a service for SMEs. Powered by BRAiN.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body>{children}</body>
    </html>
  );
}
