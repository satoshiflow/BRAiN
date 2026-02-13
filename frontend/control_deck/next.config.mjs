/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  env: {
    AUTH_SECRET: process.env.AUTH_SECRET,
  },
};

export default nextConfig;
