# Stage 1: Install dependencies with caching
FROM node:22-alpine AS deps

WORKDIR /app

# CRITICAL: Set NODE_ENV=development to install devDependencies
# (autoprefixer, tailwindcss, typescript, etc. are required for build)
ENV NODE_ENV=development

# Install build dependencies
RUN apk add --no-cache libc6-compat

# Copy dependency files
COPY package.json package-lock.json* ./

# Install dependencies with BuildKit cache mount
RUN --mount=type=cache,target=/root/.npm \
    npm ci --legacy-peer-deps --prefer-offline --no-audit --loglevel=error

# Stage 2: Build application
FROM node:22-alpine AS builder

WORKDIR /app

# Install build dependencies for native modules
RUN apk add --no-cache libc6-compat

# Build-time arguments for Next.js
ARG NEXT_PUBLIC_BRAIN_API_BASE=http://backend:8000
ARG AUTH_SECRET
ENV NEXT_PUBLIC_BRAIN_API_BASE=$NEXT_PUBLIC_BRAIN_API_BASE
ENV AUTH_SECRET=$AUTH_SECRET

# Disable telemetry and enable CI mode
ENV NEXT_TELEMETRY_DISABLED=1
ENV CI=true
# CRITICAL: Force NODE_ENV=development during build to ensure devDependencies are available
ENV NODE_ENV=development

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY . .

# Build Next.js application with debug output
# Logs werden in /tmp/build-logs gespeichert
RUN mkdir -p /tmp/build-logs && \
    (npm run build 2>&1 || echo "BUILD_FAILED=true" > /tmp/build-logs/status.log) | tee /tmp/build-logs/build.log && \
    if [ -f /tmp/build-logs/status.log ]; then \
        echo "=== BUILD FAILED - LAST 100 LINES ===" && \
        tail -100 /tmp/build-logs/build.log && \
        exit 1; \
    fi

# Ensure public directory exists
RUN mkdir -p public

# Stage 3: Production runtime with standalone output
FROM node:22-alpine AS runner

WORKDIR /app

# Runtime environment variables
ARG AUTH_SECRET
ARG NEXT_PUBLIC_BRAIN_API_BASE
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV AUTH_SECRET=$AUTH_SECRET
ENV NEXT_PUBLIC_BRAIN_API_BASE=$NEXT_PUBLIC_BRAIN_API_BASE

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy standalone output (much smaller than full node_modules)
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

# Copy build logs for debugging (optional)
COPY --from=builder /tmp/build-logs /app/build-logs || true

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
