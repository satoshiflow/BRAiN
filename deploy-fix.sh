#!/bin/bash
# ==============================================================================
# BRAiN Backend Import Fix - Automated Deployment Script
# ==============================================================================
# Branch: claude/check-project-status-y4koZ
# Commit: 96cb90b
# Date: 2026-01-11
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BRANCH="claude/check-project-status-y4koZ"
COMPOSE_FILE="docker-compose.yml"
ENV_TYPE="${1:-dev}"  # dev, stage, or prod (default: dev)

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ==============================================================================
# Step 1: Pre-Deployment Checks
# ==============================================================================

log_info "Starting BRAiN Backend Import Fix Deployment..."
log_info "Environment: $ENV_TYPE"
echo ""

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    log_error "docker-compose.yml not found. Are you in the BRAiN directory?"
    exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    log_error "Docker Compose is not installed or not in PATH"
    exit 1
fi

log_success "Pre-deployment checks passed"
echo ""

# ==============================================================================
# Step 2: Git Operations
# ==============================================================================

log_info "Current branch: $(git branch --show-current)"
log_info "Pulling changes from branch: $BRANCH"

# Stash any local changes
if ! git diff-index --quiet HEAD --; then
    log_warning "Local changes detected, stashing..."
    git stash save "Auto-stash before deployment $(date +%Y%m%d_%H%M%S)"
fi

# Pull changes
if git pull origin "$BRANCH"; then
    log_success "Git pull successful"
else
    log_error "Git pull failed"
    exit 1
fi

echo ""

# ==============================================================================
# Step 3: Build Backend Container
# ==============================================================================

log_info "Building backend container..."

# Determine compose files based on environment
case $ENV_TYPE in
    dev)
        COMPOSE_CMD="docker compose -f docker-compose.yml -f docker-compose.dev.yml"
        ;;
    stage)
        COMPOSE_CMD="docker compose -f docker-compose.yml -f docker-compose.stage.yml"
        ;;
    prod)
        COMPOSE_CMD="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
        ;;
    *)
        COMPOSE_CMD="docker compose"
        ;;
esac

log_info "Using compose command: $COMPOSE_CMD"

# Build with no cache to ensure fresh build
if $COMPOSE_CMD build backend --no-cache; then
    log_success "Backend build successful"
else
    log_error "Backend build failed"
    exit 1
fi

echo ""

# ==============================================================================
# Step 4: Restart Backend Service
# ==============================================================================

log_info "Restarting backend service..."

# Stop backend
$COMPOSE_CMD stop backend
log_success "Backend stopped"

# Remove old container
$COMPOSE_CMD rm -f backend
log_success "Old container removed"

# Start backend
$COMPOSE_CMD up -d backend
log_success "Backend started"

echo ""

# ==============================================================================
# Step 5: Wait for Startup
# ==============================================================================

log_info "Waiting for backend startup (15 seconds)..."
sleep 15

echo ""

# ==============================================================================
# Step 6: Health Checks
# ==============================================================================

log_info "Running health checks..."

# Check if container is running
if ! docker ps | grep -q "brain.*backend"; then
    log_error "Backend container is not running!"
    log_info "Showing recent logs:"
    $COMPOSE_CMD logs backend --tail=50
    exit 1
fi

log_success "Backend container is running"

# Check health endpoint
HEALTH_URL="http://localhost:8000/api/health"
log_info "Checking health endpoint: $HEALTH_URL"

if curl -f -s "$HEALTH_URL" > /dev/null; then
    log_success "Health endpoint is responding"
    curl -s "$HEALTH_URL" | jq . 2>/dev/null || curl -s "$HEALTH_URL"
else
    log_error "Health endpoint is not responding"
    log_info "Showing backend logs:"
    $COMPOSE_CMD logs backend --tail=50
    exit 1
fi

echo ""

# ==============================================================================
# Step 7: Verify Fixes
# ==============================================================================

log_info "Verifying fixes..."

# Check for import errors
log_info "Checking for import errors..."
if $COMPOSE_CMD logs backend 2>&1 | grep -iq "ModuleNotFoundError\|No module named 'backend\.brain'"; then
    log_error "Import errors still present in logs!"
    $COMPOSE_CMD logs backend 2>&1 | grep -i "ModuleNotFoundError\|ImportError"
    exit 1
else
    log_success "No import errors found"
fi

# Check for bcrypt warnings
log_info "Checking for bcrypt warnings..."
if $COMPOSE_CMD logs backend 2>&1 | grep -iq "error reading bcrypt version\|__about__"; then
    log_warning "bcrypt warnings still present (non-critical)"
else
    log_success "No bcrypt warnings found"
fi

# Check if EventStream started
log_info "Checking EventStream startup..."
if $COMPOSE_CMD logs backend 2>&1 | grep -q "Event Stream started"; then
    log_success "EventStream started successfully"
else
    log_warning "EventStream status unclear"
fi

# Check if all systems operational
log_info "Checking system status..."
if $COMPOSE_CMD logs backend 2>&1 | grep -q "All systems operational"; then
    log_success "All systems operational"
else
    log_warning "System status message not found"
fi

echo ""

# ==============================================================================
# Step 8: Test Critical Endpoints
# ==============================================================================

log_info "Testing critical endpoints..."

# Test agents endpoint
if curl -f -s "http://localhost:8000/api/agents/info" > /dev/null; then
    log_success "Agents endpoint: OK"
else
    log_warning "Agents endpoint: Failed"
fi

# Test missions endpoint
if curl -f -s "http://localhost:8000/api/missions/info" > /dev/null; then
    log_success "Missions endpoint: OK"
else
    log_warning "Missions endpoint: Failed"
fi

# Test NeuroRail endpoint
if curl -f -s "http://localhost:8000/api/neurorail/v1/identity/health" > /dev/null 2>&1; then
    log_success "NeuroRail endpoint: OK"
else
    log_warning "NeuroRail endpoint: Failed (may not be enabled)"
fi

# Test Governor endpoint
if curl -f -s "http://localhost:8000/api/governor/v1/stats" > /dev/null 2>&1; then
    log_success "Governor endpoint: OK"
else
    log_warning "Governor endpoint: Failed (may not be enabled)"
fi

echo ""

# ==============================================================================
# Step 9: Summary
# ==============================================================================

log_success "================================"
log_success "  DEPLOYMENT COMPLETED"
log_success "================================"
echo ""
log_info "Backend is running and responding to requests"
log_info "Branch: $BRANCH"
log_info "Environment: $ENV_TYPE"
echo ""
log_info "Next steps:"
echo "  1. Check logs: $COMPOSE_CMD logs -f backend"
echo "  2. Test frontend: curl http://localhost:3000"
echo "  3. Monitor: $COMPOSE_CMD ps"
echo ""
log_info "Deployment logs saved to: deployment-$(date +%Y%m%d_%H%M%S).log"

# Save deployment info
cat > "deployment-$(date +%Y%m%d_%H%M%S).log" <<EOF
BRAiN Backend Import Fix Deployment
=====================================
Date: $(date)
Branch: $BRANCH
Commit: $(git rev-parse HEAD)
Environment: $ENV_TYPE
User: $(whoami)
Host: $(hostname)

Container Status:
$($COMPOSE_CMD ps backend)

Health Check:
$(curl -s http://localhost:8000/api/health | jq . 2>/dev/null || echo "Health check failed")

Recent Logs:
$($COMPOSE_CMD logs backend --tail=20)
EOF

log_success "All done! 🎉"
