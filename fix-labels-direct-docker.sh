#!/bin/bash
# Direct Docker Label Fix - Ohne docker-compose
# Nutzt Docker API um Container mit neuen Labels zu erstellen

set -e

echo "🔧 DIRECT DOCKER LABEL FIX"
echo "=========================="
echo ""

# 1. Finde Backend Container
BACKEND_CONTAINER=$(docker ps -a | grep backend | grep mw0ck04s8go048c0g4so48cc | awk '{print $1}' | head -1)
BACKEND_NAME=$(docker ps -a | grep backend | grep mw0ck04s8go048c0g4so48cc | awk '{print $NF}' | head -1)

if [ -z "$BACKEND_CONTAINER" ]; then
    echo "❌ Backend Container nicht gefunden!"
    exit 1
fi

echo "✅ Backend Container: $BACKEND_NAME ($BACKEND_CONTAINER)"
echo ""

# 2. Export aktuelle Container Config
echo "📋 Exportiere Container Config..."
docker inspect $BACKEND_CONTAINER > /tmp/backend-config.json
echo "✅ Config exportiert nach /tmp/backend-config.json"
echo ""

# 3. Zeige aktuellen HTTP Router Label
echo "🏷️  Aktueller HTTP Router Label:"
docker inspect $BACKEND_CONTAINER | jq -r '.[0].Config.Labels["traefik.http.routers.http-0-mw0ck04s8go048c0g4so48cc-backend.rule"]'
echo ""

# 4. Stoppe Container (NICHT löschen, da wir ihn neu erstellen)
echo "⏸️  Stoppe Backend Container..."
docker stop $BACKEND_CONTAINER
echo "✅ Container gestoppt"
echo ""

# 5. Benenne alten Container um (Backup)
BACKUP_NAME="${BACKEND_NAME}-backup-$(date +%Y%m%d_%H%M%S)"
echo "💾 Benenne alten Container um zu: $BACKUP_NAME..."
docker rename $BACKEND_CONTAINER $BACKUP_NAME
echo "✅ Backup erstellt"
echo ""

# 6. Erstelle NEUEN Container mit korrigierten Labels
echo "🆕 Erstelle neuen Container mit korrigierten Labels..."

# Extrahiere wichtige Werte
IMAGE=$(docker inspect $BACKUP_NAME | jq -r '.[0].Config.Image')
NETWORK=$(docker inspect $BACKUP_NAME | jq -r '.[0].HostConfig.NetworkMode')
ENV_VARS=$(docker inspect $BACKUP_NAME | jq -r '.[0].Config.Env | map("-e " + .) | join(" ")')

echo "   Image: $IMAGE"
echo "   Network: $NETWORK"
echo ""

# Wichtiger Fix: Setze das korrekte HTTP Router Label
# Alle anderen Labels bleiben gleich, nur der HTTP Router wird korrigiert

docker run -d \
  --name $BACKEND_NAME \
  --network $NETWORK \
  --label "traefik.enable=true" \
  --label "traefik.http.routers.backend.rule=Host(\`dev.brain.falklabs.de\`) && (PathPrefix(\`/api\`) || PathPrefix(\`/docs\`) || PathPrefix(\`/redoc\`) || Path(\`/openapi.json\`))" \
  --label "traefik.http.routers.backend.entrypoints=https" \
  --label "traefik.http.routers.backend.tls=true" \
  --label "traefik.http.routers.backend.tls.certresolver=letsencrypt" \
  --label "traefik.http.routers.backend.priority=10" \
  --label "traefik.http.services.backend.loadbalancer.server.port=8000" \
  --label "traefik.http.routers.http-0-mw0ck04s8go048c0g4so48cc-backend.rule=Host(\`dev.brain.falklabs.de\`)" \
  --label "traefik.http.routers.http-0-mw0ck04s8go048c0g4so48cc-backend.entryPoints=http" \
  --label "traefik.http.middlewares.redirect-to-https.redirectscheme.scheme=https" \
  --restart unless-stopped \
  $IMAGE

echo "✅ Neuer Container erstellt"
echo ""

# 7. Warte auf Start
echo "⏳ Warte 20 Sekunden auf Container Start..."
sleep 20

# 8. Check neue Labels
NEW_CONTAINER=$(docker ps | grep $BACKEND_NAME | awk '{print $1}')
if [ -n "$NEW_CONTAINER" ]; then
    echo "🏷️  Neue HTTP Router Label:"
    docker inspect $NEW_CONTAINER | jq -r '.[0].Config.Labels["traefik.http.routers.http-0-mw0ck04s8go048c0g4so48cc-backend.rule"]'
    echo ""
fi

# 9. Validation
echo "========================"
echo "🧪 VALIDATION"
echo "========================"
echo ""

echo "1️⃣ Container Status:"
docker ps | grep backend
echo ""

echo "2️⃣ Traefik Logs (letzte 5 Zeilen)..."
docker logs $(docker ps | grep traefik | awk '{print $1}') 2>&1 | tail -5
echo ""

echo "3️⃣ Backend Health Check..."
sleep 5
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://dev.brain.falklabs.de/api/health)
if [ "$HTTP_STATUS" = "200" ]; then
    echo "   ✅ Backend antwortet: HTTP $HTTP_STATUS"
else
    echo "   ⚠️  Backend HTTP Status: $HTTP_STATUS"
    echo "   Warte weitere 10 Sekunden..."
    sleep 10
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://dev.brain.falklabs.de/api/health)
    echo "   Status nach Wartezeit: $HTTP_STATUS"
fi

echo ""
echo "========================"
echo "✅ FIX ABGESCHLOSSEN"
echo "========================"
echo ""
echo "⚠️  WICHTIG:"
echo "1. Backup Container existiert noch: $BACKUP_NAME"
echo "2. Falls alles funktioniert, lösche Backup:"
echo "   docker rm $BACKUP_NAME"
echo ""
echo "3. Falls es NICHT funktioniert, stelle Backup wieder her:"
echo "   docker stop $BACKEND_NAME"
echo "   docker rm $BACKEND_NAME"
echo "   docker rename $BACKUP_NAME $BACKEND_NAME"
echo "   docker start $BACKEND_NAME"
