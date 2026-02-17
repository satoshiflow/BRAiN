#!/bin/bash
# BRAIN Backend Debug & Fix Script
# Ausführen auf brain.falklabs.de als root oder claude user

set -e

echo "🔍 BRAIN BACKEND DEBUG REPORT"
echo "=============================="
echo "Timestamp: $(date)"
echo "User: $(whoami)"
echo ""

# 1. CONTAINER STATUS
echo "📦 1. BACKEND CONTAINER STATUS"
echo "--------------------------------"
docker ps -a | grep backend
echo ""

# 2. BACKEND LOGS
echo "📋 2. BACKEND LOGS (Last 50 lines)"
echo "--------------------------------"
docker logs mw0ck04s8go048c0g4so48cc-backend 2>&1 | tail -50
echo ""

# 3. INTERNAL HEALTH CHECK
echo "🏥 3. BACKEND INTERNAL HEALTH CHECK"
echo "--------------------------------"
docker exec mw0ck04s8go048c0g4so48cc-backend curl -sI http://localhost:8000/api/health 2>&1 || echo "❌ Container exec failed or app not responding"
echo ""

# 4. DOCKER LABELS (Traefik Config)
echo "🏷️  4. BACKEND TRAEFIK LABELS"
echo "--------------------------------"
docker inspect mw0ck04s8go048c0g4so48cc-backend | jq '.[0].Config.Labels' 2>/dev/null || docker inspect mw0ck04s8go048c0g4so48cc-backend | grep -A 30 "Labels"
echo ""

# 5. NETWORK INSPECTION
echo "🌐 5. BACKEND NETWORK CONFIG"
echo "--------------------------------"
docker inspect mw0ck04s8go048c0g4so48cc-backend | jq '.[0].NetworkSettings.Networks' 2>/dev/null || docker inspect mw0ck04s8go048c0g4so48cc-backend | grep -A 20 "Networks"
echo ""

# 6. TRAEFIK CONTAINER STATUS
echo "🚦 6. TRAEFIK CONTAINER STATUS"
echo "--------------------------------"
docker ps | grep traefik || echo "❌ Traefik container not found"
echo ""

# 7. RECENT TRAEFIK LOGS
echo "📊 7. TRAEFIK LOGS (Last 20 lines)"
echo "--------------------------------"
docker logs $(docker ps | grep traefik | awk '{print $1}') 2>&1 | tail -20 || echo "❌ Cannot read Traefik logs"
echo ""

# 8. BACKEND ENVIRONMENT VARIABLES (masked)
echo "⚙️  8. BACKEND ENVIRONMENT (sensitive masked)"
echo "--------------------------------"
docker inspect mw0ck04s8go048c0g4so48cc-backend | jq '.[0].Config.Env' 2>/dev/null | grep -v -i "password\|secret\|token\|key" || echo "Cannot read env vars"
echo ""

# 9. CONTAINER RESTART COUNT
echo "🔄 9. BACKEND RESTART COUNT"
echo "--------------------------------"
docker inspect mw0ck04s8go048c0g4so48cc-backend | jq '.[0].RestartCount' 2>/dev/null || echo "Cannot read restart count"
echo ""

# 10. QUICK FIX CHECK
echo "🔧 10. QUICK FIX AVAILABILITY"
echo "--------------------------------"
echo "Checking if we can directly modify Docker labels..."

# Check if Coolify is managing this container
if docker inspect mw0ck04s8go048c0g4so48cc-backend | grep -q "coolify"; then
    echo "✅ Container is Coolify-managed"
    echo "⚠️  Direct label modification will be overwritten by Coolify"
    echo "💡 Solution: Must fix via Coolify API or docker-compose.yml + redeploy"
else
    echo "❌ Container not Coolify-managed (unexpected)"
fi

echo ""
echo "=============================="
echo "✅ DEBUG REPORT COMPLETE"
echo "=============================="
echo ""
echo "📤 NEXT STEPS:"
echo "1. Copy this ENTIRE output"
echo "2. Paste it to Claude Code"
echo "3. Claude will analyze and provide fix"
