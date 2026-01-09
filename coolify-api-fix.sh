#!/bin/bash
# Coolify API Fix Script - Backend Domain Korrektur
# Nutzt Coolify API um fehlerhafte Domains zu fixen

set -e

COOLIFY_TOKEN="${COOLIFY_TOKEN:-ipA2f1MKBVlMQy997BRNj1xvYXw5f4qBMzx1qme2i7lCt5axHrrp1PHlmFzOEaV2}"
COOLIFY_URL="https://coolify.falklabs.de/api/v1"

echo "🔧 COOLIFY API FIX - Backend Domain Korrektur"
echo "=============================================="
echo ""

# 1. Liste alle Applications
echo "📋 1. Hole Liste aller Applications..."
APPS=$(curl -s -H "Authorization: Bearer $COOLIFY_TOKEN" "$COOLIFY_URL/applications")

# Finde BRAIN Backend
echo "🔍 2. Suche nach BRAIN Backend Application..."
BACKEND_UUID=$(echo "$APPS" | jq -r '.data[] | select(.name | test("backend|brain.*backend"; "i")) | .uuid' | head -1)

if [ -z "$BACKEND_UUID" ]; then
    echo "❌ Backend Application nicht gefunden!"
    echo "📊 Verfügbare Applications:"
    echo "$APPS" | jq -r '.data[] | "\(.name) (\(.uuid))"'
    exit 1
fi

echo "✅ Backend gefunden: $BACKEND_UUID"
echo ""

# 3. Hole aktuelle Backend Config
echo "📖 3. Hole aktuelle Backend Configuration..."
BACKEND_CONFIG=$(curl -s -H "Authorization: Bearer $COOLIFY_TOKEN" "$COOLIFY_URL/applications/$BACKEND_UUID")
echo "$BACKEND_CONFIG" | jq '.'
echo ""

# 4. Zeige aktuelle Domains
echo "🌐 4. Aktuelle Domains:"
CURRENT_DOMAINS=$(echo "$BACKEND_CONFIG" | jq -r '.data.fqdn')
echo "   $CURRENT_DOMAINS"
echo ""

# 5. Korrigiere Domains
echo "🔧 5. Korrigiere Backend Domains..."
NEW_DOMAINS="dev.brain.falklabs.de"

UPDATE_PAYLOAD=$(cat <<EOF
{
  "fqdn": "$NEW_DOMAINS"
}
EOF
)

echo "   Payload:"
echo "$UPDATE_PAYLOAD" | jq '.'
echo ""

RESPONSE=$(curl -s -X PATCH \
  -H "Authorization: Bearer $COOLIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$UPDATE_PAYLOAD" \
  "$COOLIFY_URL/applications/$BACKEND_UUID")

echo "✅ Response:"
echo "$RESPONSE" | jq '.'
echo ""

# 6. Redeploy Backend
echo "🔄 6. Redeploy Backend mit korrigierten Domains..."
REDEPLOY_RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer $COOLIFY_TOKEN" \
  "$COOLIFY_URL/applications/$BACKEND_UUID/restart")

echo "✅ Redeploy Response:"
echo "$REDEPLOY_RESPONSE" | jq '.'
echo ""

echo "=============================================="
echo "✅ FIX ABGESCHLOSSEN"
echo "=============================================="
echo ""
echo "⏳ Warte 30 Sekunden auf Redeploy..."
sleep 30

echo "🧪 7. Teste Backend Health..."
curl -I https://dev.brain.falklabs.de/api/health

echo ""
echo "📊 8. Check Traefik Logs (sollten keine Errors mehr zeigen)..."
docker logs $(docker ps | grep traefik | awk '{print $1}') 2>&1 | tail -10

echo ""
echo "✅ FERTIG!"
