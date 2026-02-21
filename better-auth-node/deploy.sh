#!/bin/bash
# Deploy Better Auth Service to Coolify

export COOLIFY_TOKEN="PjRwoJmo0G5p444YtShps370lnxT291mCbbzylmP73e5dcb3"
export COOLIFY_API_URL="http://46.224.37.114:8000/api/v1"

PROJECT_UUID="aossgwggsggsg0w8ccws8c0o"  # BRAiN Project
SERVICE_NAME="better-auth-node"
DOMAIN="auth.falklabs.de"
PORT="3000"

echo "=== Better Auth Node.js Deployment ==="
echo "Project: BRAiN ($PROJECT_UUID)"
echo "Service: $SERVICE_NAME"
echo "Domain: $DOMAIN"
echo ""

# Generate secret
BETTER_AUTH_SECRET=$(openssl rand -base64 32)
echo "Generated BETTER_AUTH_SECRET: ${BETTER_AUTH_SECRET:0:20}..."

# PostgreSQL from Identity Service
DATABASE_URL="postgresql://user:password@postgres-qcks8kwws80cw0s4sscw00wg:5432/better_auth"
TRUSTED_ORIGINS="https://control.brain.falklabs.de,https://axe.brain.falklabs.de,https://api.brain.falklabs.de"

echo ""
echo "=== Docker Compose Content ==="
cat /home/oli/projects/BRAiN/BRAiN/better-auth-node/docker-compose.yml
echo ""
echo "=== End of Docker Compose ==="
echo ""
echo "To deploy manually:"
echo "1. Go to Coolify UI: http://46.224.37.114:8000"
echo "2. Select Project: BRAiN"
echo "3. Click: + Add Service"
echo "4. Select: Docker Compose"
echo "5. Name: better-auth-node"
echo "6. Docker Compose: Paste content from above"
echo "7. Domain: auth.falklabs.de"
echo "8. Port: 3000"
echo ""
echo "Environment Variables:"
echo "  DATABASE_URL=$DATABASE_URL"
echo "  BETTER_AUTH_SECRET=$BETTER_AUTH_SECRET"
echo "  BETTER_AUTH_URL=https://auth.falklabs.de"
echo "  TRUSTED_ORIGINS=$TRUSTED_ORIGINS"
echo "  PORT=3000"
echo "  NODE_ENV=production"
