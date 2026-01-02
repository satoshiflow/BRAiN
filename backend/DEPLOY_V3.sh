#!/bin/bash
# Deploy BRAiN Minimal Backend v3 with Events CRUD System

set -e

echo "🚀 Deploying BRAiN Minimal Backend v3 (Phase 2)..."

# Navigate to backend directory
cd /srv/dev/backend

# Stop old container
echo "🛑 Stopping old backend..."
docker stop dev_backend_minimal 2>/dev/null || true
docker rm dev_backend_minimal 2>/dev/null || true

# Build new image
echo "🔨 Building new image (v3)..."
docker build -f Dockerfile.minimal.v3 -t dev_backend_minimal:v3 .

# Run database migrations BEFORE starting the container
echo "📊 Running database migrations..."
docker run --rm \
  --network dev_brain_internal \
  -e DATABASE_URL="postgresql://brain:brain@dev-postgres:5432/brain_dev" \
  dev_backend_minimal:v3 \
  alembic upgrade head

echo "✅ Migrations complete!"

# Run new container
echo "🚀 Starting new backend (v3)..."
docker run -d \
  --name dev_backend_minimal \
  --network dev_brain_internal \
  -p 8001:8000 \
  -e DATABASE_URL="postgresql://brain:brain@dev-postgres:5432/brain_dev" \
  -e REDIS_URL="redis://dev-redis:6379/0" \
  dev_backend_minimal:v3

# Wait for startup
echo "⏳ Waiting for backend to start..."
sleep 5

# Check status
echo "📊 Container status:"
docker ps | grep dev_backend_minimal

# Check logs
echo ""
echo "📋 Startup logs:"
docker logs dev_backend_minimal | tail -20

# Test endpoints
echo ""
echo "🧪 Testing endpoints..."

echo "1. Basic health check:"
curl -s http://localhost:8001/api/health | jq .

echo ""
echo "2. Database health check:"
curl -s http://localhost:8001/api/db/health | jq .

echo ""
echo "3. Events stats (should be empty initially):"
curl -s http://localhost:8001/api/events/stats | jq .

echo ""
echo "4. Create test event:"
curl -s -X POST http://localhost:8001/api/events \
  -H "Content-Type: application/json" \
  -d '{"event_type":"deployment","severity":"info","message":"Phase 2 deployed successfully!","details":{"version":"v3"},"source":"deploy_script"}' | jq .

echo ""
echo "5. List all events:"
curl -s http://localhost:8001/api/events | jq .

echo ""
echo "6. Events stats (should have 1 event now):"
curl -s http://localhost:8001/api/events/stats | jq .

echo ""
echo "✅ Phase 2 Deployment complete!"
echo ""
echo "Available endpoints:"
echo "  - http://localhost:8001/api/health"
echo "  - http://localhost:8001/api/db/health"
echo "  - http://localhost:8001/api/events"
echo "  - http://localhost:8001/api/events/stats"
echo ""
echo "  - https://dev.brain.falklabs.de/api/health"
echo "  - https://dev.brain.falklabs.de/api/db/health"
echo "  - https://dev.brain.falklabs.de/api/events"
echo "  - https://dev.brain.falklabs.de/api/events/stats"
echo ""
echo "📚 API Documentation: https://dev.brain.falklabs.de/docs"
