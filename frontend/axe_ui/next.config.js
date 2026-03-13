/** @type {import('next').NextConfig} */

// Build-time validation: prevent localhost in production builds
if (process.env.NODE_ENV === 'production') {
  const apiBase = process.env.NEXT_PUBLIC_BRAIN_API_BASE;
  
  if (apiBase && (apiBase.includes('localhost') || apiBase.includes('127.0.0.1'))) {
    throw new Error(
      `❌ Production build error: NEXT_PUBLIC_BRAIN_API_BASE cannot point to localhost.\n` +
      `   Current value: ${apiBase}\n` +
      `   Set it to your production API URL (e.g., https://api.brain.falklabs.de)`
    );
  }
  
  console.log('✅ Build validation passed: NEXT_PUBLIC_BRAIN_API_BASE is production-safe');
}

const nextConfig = {
  output: 'standalone',
  distDir:
    process.env.NEXT_DIST_DIR ||
    (process.env.NODE_ENV === 'development' ? '.next-dev' : '.next'),
  images: {
    unoptimized: true,
  },
}

module.exports = nextConfig
