#!/bin/bash
set -e  # Exit on error

#############################################
# BRAiN V2 Deployment Script
# Replaces /opt/brain/ with V2 installation
#############################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root or sudo
if [ "$EUID" -eq 0 ]; then
    log_warning "Running as root. This is okay, but not required."
fi

log_info "======================================"
log_info "BRAiN V2 Deployment Starting"
log_info "======================================"

#############################################
# Step 1: Stop old /opt/brain/ installation
#############################################
log_info "Step 1/7: Stopping old /opt/brain/ installation..."

# Check for existing Ollama volume before stopping
log_info "Checking for existing Ollama data..."
OLD_OLLAMA_VOLUME=$(docker volume ls --format "{{.Name}}" | grep -E "brain.*ollama|ollama" | head -1)
if [ -n "$OLD_OLLAMA_VOLUME" ]; then
    log_success "Found existing Ollama volume: $OLD_OLLAMA_VOLUME"
    REUSE_OLLAMA=true
else
    log_info "No existing Ollama volume found - will download models fresh"
    REUSE_OLLAMA=false
fi

if [ -d "/opt/brain" ]; then
    cd /opt/brain
    if [ -f "docker-compose.yml" ]; then
        log_info "Stopping old containers (keeping volumes)..."
        docker compose down || docker-compose down || true
        log_success "Old containers stopped"
    else
        log_warning "No docker-compose.yml found in /opt/brain/"
    fi
else
    log_warning "/opt/brain/ directory not found - skipping"
fi

#############################################
# Step 2: Update V2 Repository
#############################################
log_info "Step 2/7: Updating V2 repository..."

V2_DIR="/root/BRAiN"
if [ ! -d "$V2_DIR" ]; then
    log_error "V2 repository not found at $V2_DIR"
    log_info "Trying alternative location: /home/user/BRAiN"
    V2_DIR="/home/user/BRAiN"
    if [ ! -d "$V2_DIR" ]; then
        log_error "V2 repository not found in either location"
        exit 1
    fi
fi

cd "$V2_DIR"
log_info "Fetching latest changes from Git..."
git fetch origin
git checkout claude/migrate-v2-launch-01UQ1FuiVg8Rv6UQwwDar1g5
git pull origin claude/migrate-v2-launch-01UQ1FuiVg8Rv6UQwwDar1g5
log_success "Repository updated"

#############################################
# Step 3: Create .env.dev file
#############################################
log_info "Step 3/7: Creating .env.dev configuration..."

# Generate secure passwords
POSTGRES_PASSWORD=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 64)

cat > "$V2_DIR/.env.dev" <<EOF
# 🧠 BRAIN v2.0 - Development Environment Configuration
# Auto-generated: $(date +%Y-%m-%d)
#############################################
# B R A I N   –   GLOBAL CONFIG
#############################################

APP_ENV=development
APP_NAME=BRAIN-v2-Dev
APP_VERSION=0.3.0
ENVIRONMENT=dev

# Options: development | staging | production
BRAiN_MODE=development

#############################################
# BACKEND / API
#############################################

# FastAPI host/port (Docker uses 0.0.0.0)
API_HOST=0.0.0.0
API_PORT=8000

# Enable/Disable Mission Worker loop
ENABLE_MISSION_WORKER=true

# Worker interval (seconds)
MISSION_WORKER_POLL_INTERVAL=2.0


#############################################
# POSTGRESQL
#############################################

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=brain_v2_dev
POSTGRES_USER=brain
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# SQLAlchemy Database URL (async)
DATABASE_URL=postgresql+asyncpg://brain:$POSTGRES_PASSWORD@postgres:5432/brain_v2_dev


#############################################
# REDIS
#############################################

REDIS_URL=redis://redis:6379/0


#############################################
# QDRANT VECTOR DB
#############################################

QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_API_KEY=
QDRANT_USE_HTTPS=false


#############################################
# LLM CLIENT (Ollama)
#############################################

# Ollama inside Docker network
LLM_PROVIDER=ollama
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=phi3

# Maximum tokens, temperature etc.
LLM_MAX_TOKENS=1024
LLM_TEMPERATURE=0.5


#############################################
# FRONTEND – Control Deck & AXE UI
#############################################

NEXT_PUBLIC_API_BASE=http://backend:8000


#############################################
# SUPERVISOR / HEALTH / AGENTS
#############################################

SUPERVISOR_ENABLE=true
AGENT_HEARTBEAT_INTERVAL=10
AGENT_TIMEOUT_SECONDS=60


#############################################
# DOCKER INTERNAL NETWORKING
#############################################

DOCKER_BRIDGE_NETWORK=brain_net


#############################################
# LOGGING
#############################################

LOG_LEVEL=DEBUG
LOG_FORMAT=json
LOG_FILE=logs/brain.log
LOG_FILE_MAX_BYTES=10485760
LOG_FILE_BACKUP_COUNT=5
LOG_ENABLE_CONSOLE=true

#############################################
# SECURITY
#############################################
JWT_SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=300
PASSWORD_SALT_ROUNDS=12

#############################################
# CORS (Frontend-Zugriff erlauben)
#############################################
CORS_ORIGINS=["http://localhost:8000","http://localhost:8001","http://localhost:3001","http://localhost:3002","http://localhost:8080","https://brain.falklabs.de","https://dev.brain.falklabs.de"]

#############################################
# OTHER SETTINGS
#############################################
MAX_CONCURRENT_MISSIONS=5
MAX_MISSION_RETRIES=3
DEFAULT_TIMEZONE=UTC
ENABLE_API_CACHING=false
API_CACHE_TTL=300
ENABLE_RATE_LIMITING=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_TIME_WINDOW=60

#############################################
# EMAIL / SMTP SETTINGS (Optional)
#############################################
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password
SMTP_USE_TLS=true

#####################################################################################
# NOTE: Secure passwords generated automatically. Keep this file secure!
#####################################################################################
EOF

log_success ".env.dev created with secure passwords"

#############################################
# Step 4: Pull Docker images
#############################################
log_info "Step 4/7: Pulling Docker images..."

cd "$V2_DIR"
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml pull

log_success "Docker images pulled"

#############################################
# Step 5: Start V2 services
#############################################
log_info "Step 5/7: Starting V2 services..."

cd "$V2_DIR"
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

log_success "V2 services started"

#############################################
# Step 6: Migrate Ollama data (if exists)
#############################################
log_info "Step 6/7: Checking Ollama data migration..."

if [ "$REUSE_OLLAMA" = true ] && [ -n "$OLD_OLLAMA_VOLUME" ]; then
    log_info "Migrating existing Ollama models from $OLD_OLLAMA_VOLUME..."

    # Copy models from old volume to new volume
    docker run --rm \
        -v "$OLD_OLLAMA_VOLUME:/source:ro" \
        -v "brain_ollama_data_dev:/dest" \
        alpine sh -c "cp -r /source/* /dest/ 2>/dev/null || true"

    log_success "Ollama models migrated - no need to re-download!"
    log_info "Restarting Ollama to load models..."
    docker restart brain-ollama-dev
    sleep 5
else
    log_info "No existing Ollama data to migrate"
    log_warning "You will need to download Ollama models manually:"
    log_warning "  docker exec brain-ollama-dev ollama pull phi3"
    log_warning "  docker exec brain-ollama-dev ollama pull llama3.2"
fi

#############################################
# Step 7: Health checks
#############################################
log_info "Step 7/7: Running health checks..."

# Wait for services to be ready
log_info "Waiting 30 seconds for services to initialize..."
sleep 30

# Check backend
log_info "Checking backend health..."
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
    log_success "✓ Backend is healthy (http://localhost:8001)"
else
    log_warning "✗ Backend health check failed"
fi

# Check frontend control deck
log_info "Checking Control Deck..."
if curl -f http://localhost:3001 > /dev/null 2>&1; then
    log_success "✓ Control Deck is running (http://localhost:3001)"
else
    log_warning "✗ Control Deck not accessible"
fi

# Check AXE UI
log_info "Checking AXE UI..."
if curl -f http://localhost:3002 > /dev/null 2>&1; then
    log_success "✓ AXE UI is running (http://localhost:3002)"
else
    log_warning "✗ AXE UI not accessible"
fi

# Check OpenWebUI
log_info "Checking OpenWebUI..."
if curl -f http://localhost:8080 > /dev/null 2>&1; then
    log_success "✓ OpenWebUI is running (http://localhost:8080)"
else
    log_warning "✗ OpenWebUI not accessible (may still be starting)"
fi

# Check Ollama
log_info "Checking Ollama..."
if curl -f http://localhost:11434/api/tags > /dev/null 2>&1; then
    log_success "✓ Ollama is running (http://localhost:11434)"
else
    log_warning "✗ Ollama not accessible"
fi

# Check Qdrant
log_info "Checking Qdrant..."
if curl -f http://localhost:6334 > /dev/null 2>&1; then
    log_success "✓ Qdrant is running (http://localhost:6334)"
else
    log_warning "✗ Qdrant not accessible"
fi

# Check Postgres
log_info "Checking PostgreSQL..."
if docker exec brain-postgres-dev pg_isready -U brain > /dev/null 2>&1; then
    log_success "✓ PostgreSQL is healthy"
else
    log_warning "✗ PostgreSQL health check failed"
fi

# Check Redis
log_info "Checking Redis..."
if docker exec brain-redis-dev redis-cli ping > /dev/null 2>&1; then
    log_success "✓ Redis is healthy"
else
    log_warning "✗ Redis health check failed"
fi

#############################################
# Summary
#############################################
echo ""
log_info "======================================"
log_success "BRAiN V2 Deployment Complete!"
log_info "======================================"
echo ""
log_info "Services running:"
log_info "  • Backend API:    http://localhost:8001"
log_info "  • Control Deck:   http://localhost:3001"
log_info "  • AXE UI:         http://localhost:3002"
log_info "  • OpenWebUI:      http://localhost:8080"
log_info "  • Ollama:         http://localhost:11434"
log_info "  • Qdrant:         http://localhost:6334"
log_info "  • PostgreSQL:     localhost:5433"
log_info "  • Redis:          localhost:6380"
echo ""
log_info "View logs with:"
log_info "  cd $V2_DIR"
log_info "  ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f"
echo ""
if [ "$REUSE_OLLAMA" != true ]; then
    log_info "To download Ollama models:"
    log_info "  docker exec brain-ollama-dev ollama pull phi3"
    log_info "  docker exec brain-ollama-dev ollama pull llama3.2"
    echo ""
else
    log_success "Ollama models were migrated from old installation! ✓"
    log_info "Check available models:"
    log_info "  docker exec brain-ollama-dev ollama list"
    echo ""
fi
log_success "Deployment completed successfully! 🎉"
