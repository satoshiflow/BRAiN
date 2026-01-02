#!/bin/bash
# BRAiN Deployment Script
# Deploys specific branch to specific environment
# Usage: ./deploy.sh <environment> [branch]
#   environment: dev | stage | prod
#   branch: optional, defaults based on environment

set -e

# Configuration
ENVIRONMENTS=("dev" "stage" "prod")
DEFAULT_BRANCHES=(
    ["dev"]="dev"
    ["stage"]="stage"
    ["prod"]="main"
)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
ENV=$1
BRANCH=$2

# Validate environment
if [[ ! " ${ENVIRONMENTS[@]} " =~ " ${ENV} " ]]; then
    echo -e "${RED}Error: Invalid environment '$ENV'${NC}"
    echo "Usage: $0 <environment> [branch]"
    echo "  environment: dev | stage | prod"
    echo "  branch: git branch to deploy (default: dev→dev, stage→stage, prod→main)"
    exit 1
fi

# Set default branch if not provided
if [ -z "$BRANCH" ]; then
    case $ENV in
        dev) BRANCH="dev" ;;
        stage) BRANCH="stage" ;;
        prod) BRANCH="main" ;;
    esac
fi

# Configuration based on environment
DEPLOY_PATH="/srv/$ENV"
REPO_URL="git@github.com:satoshiflow/BRAiN.git"
COMPOSE_FILE="docker-compose.yml"
COMPOSE_ENV_FILE="docker-compose.$ENV.yml"

echo "========================================"
echo -e "${BLUE}BRAiN Deployment${NC}"
echo "========================================"
echo "Environment: $ENV"
echo "Branch: $BRANCH"
echo "Deploy path: $DEPLOY_PATH"
echo ""

# Confirm production deployment
if [ "$ENV" == "prod" ]; then
    echo -e "${YELLOW}⚠️  PRODUCTION DEPLOYMENT${NC}"
    echo "This will deploy to PRODUCTION environment!"
    read -p "Are you sure? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Deployment cancelled."
        exit 0
    fi
    echo ""
fi

echo -e "${YELLOW}[1/8] Preparing deployment directory...${NC}"

# Create deployment directory if it doesn't exist
if [ ! -d "$DEPLOY_PATH" ]; then
    sudo mkdir -p "$DEPLOY_PATH"
    sudo chown $USER:$USER "$DEPLOY_PATH"
    echo "✓ Created $DEPLOY_PATH"
else
    echo "✓ $DEPLOY_PATH exists"
fi

cd "$DEPLOY_PATH"

echo ""
echo -e "${YELLOW}[2/8] Cloning/updating repository...${NC}"

# Clone or pull repository
if [ ! -d ".git" ]; then
    echo "Cloning repository..."
    git clone -b "$BRANCH" "$REPO_URL" .
    echo "✓ Repository cloned"
else
    echo "Updating repository..."
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
    echo "✓ Repository updated"
fi

CURRENT_COMMIT=$(git rev-parse --short HEAD)
COMMIT_MSG=$(git log -1 --format='%s')
echo "✓ At commit: $CURRENT_COMMIT - $COMMIT_MSG"

echo ""
echo -e "${YELLOW}[3/8] Setting up environment files...${NC}"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ Created .env from .env.example"
        echo -e "${RED}⚠️  IMPORTANT: Edit .env and configure your environment!${NC}"
    else
        echo -e "${RED}⚠️  .env.example not found - create .env manually!${NC}"
    fi
else
    echo "✓ .env exists"
fi

# Copy environment-specific overrides
if [ -f ".env.$ENV" ]; then
    echo "✓ Using .env.$ENV overrides"
fi

echo ""
echo -e "${YELLOW}[4/8] Checking environment configuration...${NC}"

# Check critical environment variables
REQUIRED_VARS=(
    "DATABASE_URL"
    "REDIS_URL"
    "POSTGRES_PASSWORD"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^$var=" .env 2>/dev/null; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}⚠️  Missing environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Edit .env and configure these variables before continuing."
    read -p "Continue anyway? (yes/no): " CONTINUE
    if [ "$CONTINUE" != "yes" ]; then
        exit 1
    fi
fi

echo ""
echo -e "${YELLOW}[5/8] Building Docker images...${NC}"

# Determine compose files to use
COMPOSE_CMD="docker-compose -f $COMPOSE_FILE"
if [ -f "$COMPOSE_ENV_FILE" ]; then
    COMPOSE_CMD="$COMPOSE_CMD -f $COMPOSE_ENV_FILE"
    echo "✓ Using $COMPOSE_ENV_FILE overrides"
fi

# Build images
$COMPOSE_CMD build --no-cache
echo "✓ Images built"

echo ""
echo -e "${YELLOW}[6/8] Running database migrations...${NC}"

# Check if alembic exists
if [ -d "backend/alembic" ]; then
    # Run migrations in backend container
    $COMPOSE_CMD run --rm backend alembic upgrade head || {
        echo -e "${YELLOW}⚠️  Migration failed or no migrations to run${NC}"
    }
    echo "✓ Migrations checked"
else
    echo "⚠️  No alembic directory found - skipping migrations"
fi

echo ""
echo -e "${YELLOW}[7/8] Starting services...${NC}"

# Stop existing containers
$COMPOSE_CMD down

# Start services
$COMPOSE_CMD up -d

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 10

# Check service health
echo "Checking service health..."
$COMPOSE_CMD ps

echo ""
echo -e "${YELLOW}[8/8] Post-deployment verification...${NC}"

# Check if backend is responding
BACKEND_PORT=$(grep -E "API_PORT|8000" .env | cut -d'=' -f2 | tr -d ' ' || echo "8000")
BACKEND_URL="http://localhost:$BACKEND_PORT"

echo "Testing backend at $BACKEND_URL/api/health..."
if curl -s -f "$BACKEND_URL/api/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Backend health check failed - check logs${NC}"
fi

# Check if frontend is responding (if exists)
FRONTEND_PORT=$(grep -E "NEXT.*PORT|3000" .env | cut -d'=' -f2 | tr -d ' ' || echo "3000")
FRONTEND_URL="http://localhost:$FRONTEND_PORT"

if $COMPOSE_CMD ps | grep -q control_deck; then
    echo "Testing frontend at $FRONTEND_URL..."
    if curl -s -f "$FRONTEND_URL" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend is healthy${NC}"
    else
        echo -e "${YELLOW}⚠️  Frontend health check failed - check logs${NC}"
    fi
fi

echo ""
echo "========================================"
echo -e "${GREEN}Deployment Complete!${NC}"
echo "========================================"
echo ""
echo "Environment: $ENV"
echo "Branch: $BRANCH ($CURRENT_COMMIT)"
echo "Path: $DEPLOY_PATH"
echo ""
echo "Services:"
if [ "$ENV" == "dev" ]; then
    echo "  Backend: http://localhost:8001"
    echo "  Frontend: http://localhost:3001"
    echo "  Domain: https://dev.brain.falklabs.de"
elif [ "$ENV" == "stage" ]; then
    echo "  Backend: http://localhost:8002"
    echo "  Frontend: http://localhost:3003"
    echo "  Domain: https://stage.brain.falklabs.de"
elif [ "$ENV" == "prod" ]; then
    echo "  Backend: http://localhost:8000"
    echo "  Frontend: http://localhost:3000"
    echo "  Domain: https://brain.falklabs.de"
fi
echo ""
echo "View logs:"
echo "  cd $DEPLOY_PATH"
echo "  $COMPOSE_CMD logs -f"
echo ""
echo "Restart services:"
echo "  $COMPOSE_CMD restart"
echo ""
