#!/bin/bash
# Direct Backend Fix - Ohne Coolify API
# Stoppt Container, entfernt ihn, und startet neu mit korrigierten Labels

set -e

echo "🔧 DIRECT BACKEND FIX"
echo "===================="
echo ""

# 1. Finde aktuellen Backend Container
echo "🔍 1. Finde Backend Container..."
BACKEND_CONTAINER=$(docker ps -a | grep backend | grep mw0ck04s8go048c0g4so48cc | awk '{print $1}')

if [ -z "$BACKEND_CONTAINER" ]; then
    echo "❌ Backend Container nicht gefunden!"
    exit 1
fi

BACKEND_NAME=$(docker ps -a | grep backend | grep mw0ck04s8go048c0g4so48cc | awk '{print $NF}')
echo "✅ Backend Container: $BACKEND_NAME ($BACKEND_CONTAINER)"
echo ""

# 2. Finde Coolify Project Directory
echo "📁 2. Finde Coolify Project Directory..."
PROJECT_DIR=$(docker inspect $BACKEND_CONTAINER | jq -r '.[0].Config.Labels["com.docker.compose.project.working_dir"]')

if [ -z "$PROJECT_DIR" ] || [ "$PROJECT_DIR" = "null" ]; then
    echo "❌ Project Directory nicht gefunden!"
    exit 1
fi

echo "✅ Project Directory: $PROJECT_DIR"
echo ""

# 3. Backup docker-compose.yml
echo "💾 3. Backup docker-compose.yml..."
if [ -f "$PROJECT_DIR/docker-compose.yml" ]; then
    cp "$PROJECT_DIR/docker-compose.yml" "$PROJECT_DIR/docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ Backup erstellt"
else
    echo "⚠️  docker-compose.yml nicht gefunden in $PROJECT_DIR"
    echo "📋 Verzeichnis-Inhalt:"
    ls -la "$PROJECT_DIR/" | head -20
fi
echo ""

# 4. Fix: HTTP Router Label entfernen
echo "🔧 4. Entferne fehlerhaften HTTP Router..."

# Option A: Via Coolify Redeploy mit docker-compose restart
echo "   Wechsle zu Project Directory..."
cd "$PROJECT_DIR"

echo "   Stoppe Backend Container..."
docker-compose stop backend

echo "   Entferne Backend Container..."
docker-compose rm -f backend

echo "   Starte Backend neu (mit bestehender Config)..."
docker-compose up -d backend

echo "✅ Backend neu gestartet"
echo ""

# 5. Warte auf Container Start
echo "⏳ 5. Warte 20 Sekunden auf Container Start..."
sleep 20

# 6. Finde neuen Container
NEW_BACKEND=$(docker ps | grep backend | grep mw0ck04s8go048c0g4so48cc | awk '{print $1}')
if [ -z "$NEW_BACKEND" ]; then
    echo "⚠️  Backend Container nicht gefunden (noch am starten?)"
    NEW_BACKEND=$(docker ps -a | grep backend | grep mw0ck04s8go048c0g4so48cc | awk '{print $1}')
fi

echo "🆔 Neuer Backend Container: $NEW_BACKEND"
echo ""

# 7. Check neue Labels
echo "🏷️  7. Prüfe neue HTTP Router Labels..."
docker inspect $NEW_BACKEND | grep -A 2 "http-0.*backend.rule" || echo "HTTP Router Label nicht gefunden (evtl. entfernt?)"
echo ""

# 8. Validation
echo "============================================"
echo "🧪 VALIDATION"
echo "============================================"
echo ""

echo "📊 8.1. Traefik Logs (letzte 10 Zeilen)..."
docker logs $(docker ps | grep traefik | awk '{print $1}') 2>&1 | tail -10
echo ""

echo "🏥 8.2. Backend Health Check (intern via docker network)..."
sleep 5
docker exec $NEW_BACKEND wget -O- -q http://localhost:8000/api/health 2>/dev/null || \
  docker exec $NEW_BACKEND python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/health').read().decode())" 2>/dev/null || \
  echo "⚠️  Kann Health Check nicht ausführen (curl/wget nicht verfügbar)"
echo ""

echo "🌐 8.3. External Health Check..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://dev.brain.falklabs.de/api/health)
echo "   Backend HTTP Status: $HTTP_STATUS"

if [ "$HTTP_STATUS" = "200" ]; then
    echo "   ✅ Backend antwortet korrekt!"
else
    echo "   ⚠️  Backend antwortet nicht mit 200"
fi
echo ""

echo "============================================"
echo "✅ FIX ABGESCHLOSSEN"
echo "============================================"
echo ""
echo "📋 Nächste Schritte:"
echo "1. Prüfe Traefik Logs auf Errors: docker logs coolify-proxy 2>&1 | tail -20"
echo "2. Teste Backend: curl -I https://dev.brain.falklabs.de/api/health"
echo "3. Wenn immer noch Fehler: Zeige mir docker inspect output vom neuen Container"
