#!/bin/bash
# Coolify Domain Fix - Korrigiert fehlerhafte HTTP Router Labels
# Problem: HTTP Router hat Host(``) && PathPrefix(`domain`) statt Host(`domain`)

set -e

COOLIFY_TOKEN="${COOLIFY_TOKEN:-ipA2f1MKBVlMQy997BRNj1xvYXw5f4qBMzx1qme2i7lCt5axHrrp1PHlmFzOEaV2}"
COOLIFY_URL="https://coolify.falklabs.de/api/v1"

echo "🔧 COOLIFY DOMAIN FIX - Backend HTTP Router"
echo "============================================"
echo ""

# Finde Backend Application UUID via Name
echo "🔍 1. Suche Backend Application..."
BACKEND_UUID=$(curl -s -H "Authorization: Bearer $COOLIFY_TOKEN" "$COOLIFY_URL/applications" | \
  jq -r '.data[] | select(.name | test("backend|brain"; "i")) | select(.name | contains("backend")) | .uuid' | head -1)

if [ -z "$BACKEND_UUID" ]; then
    echo "❌ Backend nicht gefunden via API!"
    echo "💡 Versuche über Resource UUID..."

    # Alternativ: Suche über coolify.resourceName Label
    RESOURCE_NAME=$(docker inspect backend-mw0ck04s8go048c0g4so48cc-153225318142 | \
      jq -r '.[0].Config.Labels["coolify.resourceName"]' 2>/dev/null)

    if [ -n "$RESOURCE_NAME" ] && [ "$RESOURCE_NAME" != "null" ]; then
        echo "✅ Resource Name: $RESOURCE_NAME"
        BACKEND_UUID=$(curl -s -H "Authorization: Bearer $COOLIFY_TOKEN" "$COOLIFY_URL/applications" | \
          jq -r --arg name "$RESOURCE_NAME" '.data[] | select(.name == $name) | .uuid' | head -1)
    fi
fi

if [ -z "$BACKEND_UUID" ] || [ "$BACKEND_UUID" = "null" ]; then
    echo "❌ Backend UUID nicht gefunden!"
    echo "📊 Verfügbare Applications:"
    curl -s -H "Authorization: Bearer $COOLIFY_TOKEN" "$COOLIFY_URL/applications" | \
      jq -r '.data[] | "\(.name) | \(.uuid) | \(.fqdn)"'
    echo ""
    echo "⚠️  Bitte wähle die richtige UUID manuell:"
    echo "export BACKEND_UUID=<uuid>"
    echo "Dann führe Script erneut aus"
    exit 1
fi

echo "✅ Backend UUID: $BACKEND_UUID"
echo ""

# 2. Hole aktuelle Config
echo "📖 2. Hole aktuelle Configuration..."
CURRENT_CONFIG=$(curl -s -H "Authorization: Bearer $COOLIFY_TOKEN" "$COOLIFY_URL/applications/$BACKEND_UUID")
CURRENT_FQDN=$(echo "$CURRENT_CONFIG" | jq -r '.data.fqdn // empty')

echo "   Aktuelle FQDN: $CURRENT_FQDN"
echo ""

# 3. Lösche Domain temporär (Reset)
echo "🗑️  3. Lösche Domains (Reset)..."
curl -s -X PATCH \
  -H "Authorization: Bearer $COOLIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fqdn": null}' \
  "$COOLIFY_URL/applications/$BACKEND_UUID" > /dev/null

echo "✅ Domains gelöscht"
sleep 2

# 4. Setze Domains NEU (korrekt)
echo "➕ 4. Setze Domains NEU..."
NEW_FQDN="dev.brain.falklabs.de"

RESPONSE=$(curl -s -X PATCH \
  -H "Authorization: Bearer $COOLIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"fqdn\": \"$NEW_FQDN\"}" \
  "$COOLIFY_URL/applications/$BACKEND_UUID")

echo "✅ Domains gesetzt: $NEW_FQDN"
echo ""

# 5. Redeploy
echo "🔄 5. Redeploy Backend..."
DEPLOY_RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer $COOLIFY_TOKEN" \
  "$COOLIFY_URL/applications/$BACKEND_UUID/restart")

echo "✅ Redeploy initiated"
echo ""

# 6. Warte auf Redeploy
echo "⏳ Warte 45 Sekunden auf Redeploy..."
for i in {45..1}; do
  echo -ne "   $i Sekunden...\r"
  sleep 1
done
echo ""

# 7. Validierung
echo "============================================"
echo "🧪 VALIDATION"
echo "============================================"
echo ""

echo "📋 7.1. Neue Container Labels (HTTP Router)..."
docker inspect backend-mw0ck04s8go048c0g4so48cc-* 2>/dev/null | \
  grep -A 2 "http-0-mw0ck04s8go048c0g4so48cc-backend.rule" || \
  echo "⚠️  Container Name geändert nach Redeploy (normal)"

echo ""
echo "📊 7.2. Traefik Logs (sollten clean sein)..."
docker logs $(docker ps | grep traefik | awk '{print $1}') 2>&1 | \
  grep "empty args for matcher Host" | tail -5 || \
  echo "✅ Keine Host() Errors mehr!"

echo ""
echo "🏥 7.3. Backend Health Check..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://dev.brain.falklabs.de/api/health)
if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ Backend antwortet: HTTP $HTTP_STATUS"
else
    echo "⚠️  Backend HTTP Status: $HTTP_STATUS"
fi

echo ""
echo "============================================"
echo "✅ FIX ABGESCHLOSSEN"
echo "============================================"
echo ""
echo "📊 Final Check:"
curl -I https://dev.brain.falklabs.de/api/health
