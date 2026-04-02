/** @type {import('next').NextConfig} */

if (process.env.NODE_ENV === "production" && process.env.NEXT_PUBLIC_APP_ENV !== "local") {
  const apiBase = process.env.NEXT_PUBLIC_BRAIN_API_BASE;

  if (apiBase && (apiBase.includes("localhost") || apiBase.includes("127.0.0.1"))) {
    throw new Error(
      `Production build error: NEXT_PUBLIC_BRAIN_API_BASE cannot point to localhost. Current value: ${apiBase}`
    );
  }
}

const nextConfig = {
  reactStrictMode: true,
  transpilePackages: [],
  output: "standalone",
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  async rewrites() {
    const apiBase = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://127.0.0.1:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
