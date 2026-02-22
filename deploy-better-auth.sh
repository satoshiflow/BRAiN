#!/bin/bash
# Deploy Better Auth to Coolify via API

set -e

export COOLIFY_TOKEN="PjRwoJmo0G5p444YtShps370lnxT291mCbbzylmP73e5dcb3"
export COOLIFY_API_URL="http://46.224.37.114:8000/api/v1"

PROJECT_UUID="aossgwggsggsg0w8ccws8c0o"
SERVER_UUID="eko8c8ow4w84gocsc84gw0cg"

# Generate secret
BETTER_AUTH_SECRET=$(openssl rand -base64 32)

echo "🚀 Deploying Better Auth Service..."
echo ""

# Step 1: Create Application
echo "Step 1: Creating application..."
APP_RESPONSE=$(curl -s -X POST "${COOLIFY_API_URL}/applications" \
  -H "Authorization: Bearer ${COOLIFY_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_uuid\": \"${PROJECT_UUID}\",
    \"server_uuid\": \"${SERVER_UUID}\",
    \"environment_name\": \"production\",
    \"git_repository\": \"https://github.com/satoshiflow/BRAiN\",
    \"git_branch\": \"better-auth-controldeck-v2\",
    \"build_pack\": \"dockercompose\",
    \"name\": \"better-auth-node\",
    \"description\": \"Better Auth Node.js Service\",
    \"fqdn\": \"https://auth.falklabs.de\",
    \"ports_exposes\": \"3030\",
    \"instant_deploy\": false,
    \"base_directory\": \"better-auth-node\"
  }" 2>/dev/null)

echo "Response: $APP_RESPONSE"
echo ""

APP_UUID=$(echo $APP_RESPONSE | jq -r '.data.uuid // empty')

if [ -z "$APP_UUID" ]; then
  echo "❌ Failed to create application"
  echo "Response: $APP_RESPONSE"
  exit 1
fi

echo "✅ Application created with UUID: $APP_UUID"
echo ""

# Step 2: Update Environment Variables
echo "Step 2: Setting environment variables..."
curl -s -X PATCH "${COOLIFY_API_URL}/applications/${APP_UUID}" \
  -H "Authorization: Bearer ${COOLIFY_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"environment_variables\": {
      \"DATABASE_URL\": \"postgresql://user:password@postgres-qcks8kwws80cw0s4sscw00wg:5432/better_auth\",
      \"BETTER_AUTH_SECRET\": \"${BETTER_AUTH_SECRET}\",
      \"BETTER_AUTH_URL\": \"https://auth.falklabs.de\",
      \"TRUSTED_ORIGINS\": \"https://control.brain.falklabs.de,https://axe.brain.falklabs.de,https://api.brain.falklabs.de\",
      \"PORT\": \"3000\",
      \"NODE_ENV\": \"production\"
    }
  }" 2>/dev/null | jq -r '.message // "OK"'

echo "✅ Environment variables set"
echo ""

# Step 3: Deploy
echo "Step 3: Deploying..."
curl -s -X POST "${COOLIFY_API_URL}/applications/${APP_UUID}/deploy" \
  -H "Authorization: Bearer ${COOLIFY_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{}' 2>/dev/null | jq -r '.message // "Deployment started"'

echo ""
echo "✅ Better Auth deployment initiated!"
echo ""
echo "Check status at: http://46.224.37.114:8000/project/${PROJECT_UUID}"
echo ""
echo "Environment Variables set:"
echo "  DATABASE_URL: postgresql://user:password@postgres-qcks8kwws80cw0s4sscw00wg:5432/better_auth"
echo "  BETTER_AUTH_SECRET: ${BETTER_AUTH_SECRET:0:20}..."
echo "  BETTER_AUTH_URL: https://auth.falklabs.de"
echo "  TRUSTED_ORIGINS: https://control.brain.falklabs.de,https://axe.brain.falklabs.de,https://api.brain.falklabs.de"
echo "  PORT: 3000"
echo "  NODE_ENV: production"
