#!/bin/bash
# Deploy Minimal Backend v2 with Database Support

set -e

echo "🚀 Deploying BRAiN Minimal Backend v2..."

# Navigate to backend directory
cd /srv/dev/backend

# Stop old container
echo "🛑 Stopping old backend..."
docker stop dev_backend_minimal 2>/dev/null || true
docker rm dev_backend_minimal 2>/dev/null || true

# Build new image
echo "🔨 Building new image..."
docker build -f Dockerfile.minimal.v2 -t dev_backend_minimal:v2 .

# Run new container
echo "🚀 Starting new backend..."
docker run -d \
  --name dev_backend_minimal \
  --network dev_brain_internal \
  -p 8001:8000 \
  -e DATABASE_URL="postgresql://brain:brain@dev-postgres:5432/brain_dev" \
  -e REDIS_URL="redis://dev-redis:6379/0" \
  dev_backend_minimal:v2

# Wait for startup
echo "⏳ Waiting for backend to start..."
sleep 3

# Check status
echo "📊 Container status:"
docker ps | grep dev_backend_minimal

# Check logs
echo ""
echo "📋 Startup logs:"
docker logs dev_backend_minimal

# Test endpoints
echo ""
echo "🧪 Testing endpoints..."
echo "1. Basic health check:"
curl -s http://localhost:8001/api/health | jq .

echo ""
echo "2. Database health check:"
curl -s http://localhost:8001/api/db/health | jq .

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Available endpoints:"
echo "  - http://localhost:8001/api/health"
echo "  - http://localhost:8001/api/db/health"
echo "  - https://dev.brain.falklabs.de/api/health"
echo "  - https://dev.brain.falklabs.de/api/db/health"
