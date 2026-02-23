# Stage 1: Install dependencies with caching (cache-bust: 2026-02-23-1249-v3)
FROM node:22-alpine AS deps

WORKDIR /app

# Copy dependency files
COPY package.json package-lock.json* ./

# Install dependencies with BuildKit cache mount
RUN --mount=type=cache,target=/root/.npm \
    npm install --legacy-peer-deps --no-audit --loglevel=error

# Stage 2: Build application
FROM node:22-alpine AS builder

WORKDIR /app

# Build-time arguments for Next.js
ARG NEXT_PUBLIC_BRAIN_API_BASE=https://api.brain.falklabs.de
ENV NEXT_PUBLIC_BRAIN_API_BASE=$NEXT_PUBLIC_BRAIN_API_BASE

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY . .

# Remove test files to avoid TypeScript errors
RUN find . -path ./node_modules -prune -o \( -name "*.test.tsx" -o -name "*.test.ts" \) -print | xargs rm -f && rm -f src/test/setup.ts

# Build Next.js application
RUN npm run build

# Ensure public directory exists
RUN mkdir -p public

# Stage 3: Production runtime with standalone output
FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Install SQLite dependencies for better-sqlite3
RUN apk add --no-cache libc6-compat

# Create data directory for SQLite (persisted via volume)
RUN mkdir -p /app/data && chmod 777 /app/data

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs && \
    chown -R nextjs:nodejs /app/data

# Copy standalone output (much smaller than full node_modules)
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
ENV AUTH_DATA_DIR=/app/data

CMD ["node", "server.js"]
