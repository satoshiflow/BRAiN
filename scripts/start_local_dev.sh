#!/usr/bin/env bash
# BRAiN Local Development Stack Starter
# Follows Runtime Deployment Contract (docs/specs/runtime_deployment_contract.md)

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "🧠 BRAiN Local Development Stack"
echo "=================================="
echo ""

# Check Docker availability
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker not found. Please install Docker Desktop."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Error: Docker daemon not running. Please start Docker Desktop."
    exit 1
fi

echo "✅ Docker available"
echo ""

COMPOSE_CMD=""
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

# Start infrastructure services
echo "🚀 Starting infrastructure services (postgres, redis, qdrant)..."
$COMPOSE_CMD -f docker-compose.dev.yml up -d postgres redis qdrant

# Wait for services to be healthy
echo "⏳ Waiting for services to become healthy..."
max_wait=60
elapsed=0

while [ $elapsed -lt $max_wait ]; do
    postgres_status=$(docker inspect --format='{{.State.Health.Status}}' brain-dev-postgres 2>/dev/null || echo "none")
    redis_status=$(docker inspect --format='{{.State.Health.Status}}' brain-dev-redis 2>/dev/null || echo "none")
    
    if [ "$postgres_status" = "healthy" ] && [ "$redis_status" = "healthy" ]; then
        echo "✅ All services healthy"
        break
    fi
    
    echo "   Waiting... (postgres: $postgres_status, redis: $redis_status)"
    sleep 2
    elapsed=$((elapsed + 2))
done

if [ $elapsed -ge $max_wait ]; then
    echo "⚠️  Warning: Services did not become healthy within ${max_wait}s"
    echo "   Check status: $COMPOSE_CMD -f docker-compose.dev.yml ps"
fi

echo ""
echo "📦 Infrastructure Services Running:"
echo "   - PostgreSQL: localhost:${POSTGRES_PORT_HOST:-5432}"
echo "   - Redis: localhost:${REDIS_PORT_HOST:-6379}"
echo "   - Qdrant: localhost:${QDRANT_HTTP_PORT_HOST:-6334}"
echo ""
echo "🎯 Next Steps:"
echo ""
echo "   Terminal 1 - Start Backend:"
echo "   $ cd backend"
echo "   $ uvicorn main:app --reload --host 127.0.0.1 --port 8000"
echo ""
echo "   Terminal 2 - Start AXE UI:"
echo "   $ cd frontend/axe_ui"
echo "   $ npm run dev"
echo ""
echo "   URLs:"
echo "   - Backend API: http://127.0.0.1:8000"
echo "   - Backend Docs: http://127.0.0.1:8000/docs"
echo "   - AXE UI: http://127.0.0.1:3002"
echo ""
echo "   To stop services:"
echo "   $ $COMPOSE_CMD -f docker-compose.dev.yml down"
echo ""
echo "✅ Infrastructure ready for local development"
