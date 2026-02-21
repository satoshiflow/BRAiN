#!/bin/bash
# Better Auth Service Deployment via Coolify API

export COOLIFY_TOKEN="PjRwoJmo0G5p444YtShps370lnxT291mCbbzylmP73e5dcb3"
export COOLIFY_API_URL="http://46.224.37.114:8000/api/v1"

PROJECT_UUID="aossgwggsggsg0w8ccws8c0o"
SERVER_UUID="eko8c8ow4w84gocsc84gw0cg"

# Generate secret
BETTER_AUTH_SECRET=$(openssl rand -base64 32)

echo "Creating Better Auth Service in Coolify..."

# Create Application
curl -X POST "${COOLIFY_API_URL}/applications" \
  -H "Authorization: Bearer ${COOLIFY_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_uuid\": \"${PROJECT_UUID}\",
    \"server_uuid\": \"${SERVER_UUID}\",
    \"environment_name\": \"production\",
    \"git_repository\": \"local\",
    \"git_branch\": \"main\",
    \"build_pack\": \"dockercompose\",
    \"name\": \"better-auth-node\",
    \"description\": \"Better Auth Node.js Service\",
    \"fqdn\": \"https://auth.falklabs.de\",
    \"ports_exposes\": \"3000\",
    \"instant_deploy\": false
  }" 2>/dev/null | jq -r '.data.uuid // .message'

echo ""
echo "Deployment preparation complete."
echo ""
echo "Next steps:"
echo "1. Go to Coolify UI: http://46.224.37.114:8000"
echo "2. Select Project: BRAiN"
echo "3. Find Service: better-auth-node"
echo "4. Configure Environment Variables:"
echo "   DATABASE_URL=postgresql://user:password@postgres-qcks8kwws80cw0s4sscw00wg:5432/better_auth"
echo "   BETTER_AUTH_SECRET=${BETTER_AUTH_SECRET}"
echo "   BETTER_AUTH_URL=https://auth.falklabs.de"
echo "   TRUSTED_ORIGINS=https://control.brain.falklabs.de,https://axe.brain.falklabs.de,https://api.brain.falklabs.de"
echo "   PORT=3000"
echo "   NODE_ENV=production"
echo "5. Upload Docker Compose from: /home/oli/projects/BRAiN/BRAiN/better-auth-node/docker-compose.yml"
echo "6. Deploy"
