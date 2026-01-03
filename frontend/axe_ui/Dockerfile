FROM node:22-alpine AS builder

WORKDIR /app

# Build-time arguments for Next.js
ARG NEXT_PUBLIC_BRAIN_API_BASE=http://backend:8000
ENV NEXT_PUBLIC_BRAIN_API_BASE=$NEXT_PUBLIC_BRAIN_API_BASE

COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

COPY . .
RUN npm run build

# Ensure public directory exists
RUN mkdir -p public

FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000

CMD ["npm", "start"]
