/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    typedRoutes: true,
  },
  output: 'standalone',
  distDir: '.next',
  images: {
    unoptimized: true,
  },
}

module.exports = nextConfig