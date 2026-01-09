#!/bin/bash
# Phase 1: Mage.ai Setup Script
# Executes: PostgreSQL pgvector + Ollama model pull + Mage.ai deployment

set -e  # Exit on error

echo "============================================"
echo "Phase 1: Mage.ai Setup"
echo "============================================"
echo ""

# Check if running on server
if [ ! -f "/root/.ssh/ssh_key_github" ]; then
    echo "⚠️  WARNING: Not running on brain.falklabs.de server"
    echo "This script should be executed on the deployment server."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Backup current state
echo "📦 Step 1: Creating backup..."
docker-compose ps > docker-compose-backup-$(date +%Y%m%d_%H%M%S).txt
echo "✅ Backup created"
echo ""

# Step 2: Stop existing services (if any)
echo "🛑 Step 2: Stopping existing containers..."
docker-compose down
echo "✅ Containers stopped"
echo ""

# Step 3: Pull new images
echo "🐳 Step 3: Pulling Docker images..."
docker pull pgvector/pgvector:pg16
docker pull mageai/mageai:latest
docker pull ollama/ollama:latest
echo "✅ Images pulled"
echo ""

# Step 4: Start services with pgvector
echo "🚀 Step 4: Starting services with pgvector + Mage.ai..."
docker-compose -f docker-compose.yml -f docker-compose.mage.yml up -d
echo "✅ Services started"
echo ""

# Step 5: Wait for PostgreSQL to be ready
echo "⏳ Step 5: Waiting for PostgreSQL to initialize..."
sleep 10

# Check PostgreSQL logs for pgvector
echo "📋 Checking pgvector installation..."
docker logs brain-postgres 2>&1 | grep -i "pgvector" || echo "⚠️  No pgvector logs yet (may take a moment)"
echo ""

# Step 6: Pull Ollama models
echo "🤖 Step 6: Pulling Ollama models..."
echo "This may take 5-10 minutes depending on connection speed..."

# Pull llama3.2 (if not already present)
docker exec brain-ollama ollama pull llama3.2:latest

# Pull nomic-embed-text for embeddings
docker exec brain-ollama ollama pull nomic-embed-text

echo "✅ Ollama models pulled"
echo ""

# Step 7: Wait for Mage.ai to start
echo "⏳ Step 7: Waiting for Mage.ai to start (60 seconds)..."
sleep 60
echo "✅ Mage.ai should be ready"
echo ""

# Step 8: Display service status
echo "============================================"
echo "📊 Service Status"
echo "============================================"
docker-compose -f docker-compose.yml -f docker-compose.mage.yml ps
echo ""

# Step 9: Display access information
echo "============================================"
echo "🎯 Access Information"
echo "============================================"
echo "Mage.ai (internal only):"
echo "  URL: http://localhost:6789"
echo "  From server: curl http://localhost:6789/api/status"
echo ""
echo "PostgreSQL (internal only):"
echo "  Host: postgres"
echo "  Port: 5432"
echo "  Database: brain"
echo "  User: brain"
echo "  pgvector: ✅ ENABLED"
echo ""
echo "Ollama (internal only):"
echo "  URL: http://ollama:11434"
echo "  Models: llama3.2:latest, nomic-embed-text"
echo ""

echo "============================================"
echo "✅ Phase 1 Setup Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Run verification: bash verify-phase1.sh"
echo "2. Check logs: docker-compose logs -f mage"
echo "3. Access Mage.ai: ssh -L 6789:localhost:6789 brain"
echo ""
