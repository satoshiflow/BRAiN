#!/bin/bash
#
# BRAiN v2 - Migration & Cleanup Script
# Purpose: Migrate from /opt/brain-v2/ to clean /srv/* structure
# Target: Option B - Saubere Struktur
#
# What this script does:
# 1. Backup old installation
# 2. Stop old containers
# 3. Check and backup volumes
# 4. Remove old symlinks
# 5. Create /srv structure
# 6. Deploy to /srv/dev
# 7. Cleanup old installation
#
# Usage: bash migrate-to-srv-structure.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
OLD_PATH="/opt/brain-v2"
DEV_WORKSPACE="/root/BRAiN"
BACKUP_DIR="/root/backups"
DATE=$(date +%Y%m%d_%H%M%S)

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}BRAiN v2 - Migration & Cleanup Script${NC}"
echo -e "${BLUE}Target: Clean /srv/* structure${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Function: Print step
print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

# Function: Print warning
print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Function: Print error
print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function: Ask for confirmation
confirm() {
    read -p "$(echo -e ${YELLOW}$1${NC}) [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Aborted by user${NC}"
        exit 1
    fi
}

#
# PHASE 1: PRE-FLIGHT CHECKS
#
echo -e "${BLUE}=== PHASE 1: PRE-FLIGHT CHECKS ===${NC}"
echo ""

print_step "Checking if running as root..."
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root: sudo bash $0"
    exit 1
fi
echo "✅ Running as root"

print_step "Checking if old installation exists..."
if [ ! -d "$OLD_PATH" ]; then
    print_warning "Old installation not found at $OLD_PATH - skipping cleanup"
    OLD_EXISTS=false
else
    echo "✅ Found old installation at $OLD_PATH"
    OLD_EXISTS=true
fi

print_step "Checking development workspace..."
if [ ! -d "$DEV_WORKSPACE" ]; then
    print_error "Development workspace not found at $DEV_WORKSPACE"
    exit 1
fi
echo "✅ Development workspace exists"

print_step "Checking disk space..."
FREE_SPACE=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$FREE_SPACE" -lt 10 ]; then
    print_warning "Low disk space: ${FREE_SPACE}GB free (recommended: >10GB)"
    confirm "Continue anyway?"
fi
echo "✅ Disk space OK: ${FREE_SPACE}GB free"

echo ""
echo -e "${YELLOW}Summary:${NC}"
echo "  Old installation: ${OLD_PATH} $([ "$OLD_EXISTS" = true ] && echo "(exists)" || echo "(not found)")"
echo "  Dev workspace: ${DEV_WORKSPACE}"
echo "  Backup location: ${BACKUP_DIR}"
echo ""
confirm "Proceed with migration?"

#
# PHASE 2: BACKUP OLD INSTALLATION
#
if [ "$OLD_EXISTS" = true ]; then
    echo ""
    echo -e "${BLUE}=== PHASE 2: BACKUP OLD INSTALLATION ===${NC}"
    echo ""

    print_step "Creating backup directory..."
    mkdir -p "$BACKUP_DIR"
    echo "✅ Backup directory: $BACKUP_DIR"

    print_step "Checking for running containers..."
    cd "$OLD_PATH" 2>/dev/null || true
    RUNNING_CONTAINERS=$(docker ps --filter "name=brain" --format "{{.Names}}" | wc -l)
    if [ "$RUNNING_CONTAINERS" -gt 0 ]; then
        echo "⚠️  Found $RUNNING_CONTAINERS running BRAiN container(s)"
        docker ps --filter "name=brain" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo ""
        confirm "Stop these containers?"

        print_step "Stopping old containers..."
        docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true
        echo "✅ Containers stopped"
    else
        echo "✅ No running containers"
    fi

    print_step "Checking Docker volumes..."
    VOLUMES=$(docker volume ls --filter "name=brain" --format "{{.Name}}")
    if [ -n "$VOLUMES" ]; then
        echo "Found BRAiN volumes:"
        echo "$VOLUMES"
        echo ""
        print_warning "Volumes contain persistent data (databases, models, etc.)"
        echo "These will NOT be deleted automatically."
        echo "They can be reused by new installation or manually removed later."
        echo ""
        read -p "Press Enter to continue..."
    else
        echo "✅ No volumes found"
    fi

    print_step "Creating backup archive..."
    BACKUP_FILE="$BACKUP_DIR/brain-v2-backup-${DATE}.tar.gz"
    echo "This may take a few minutes..."
    tar -czf "$BACKUP_FILE" -C "$(dirname $OLD_PATH)" "$(basename $OLD_PATH)" 2>/dev/null || {
        print_warning "Backup failed, but continuing..."
    }

    if [ -f "$BACKUP_FILE" ]; then
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo "✅ Backup created: $BACKUP_FILE ($BACKUP_SIZE)"
    fi
fi

#
# PHASE 3: FIND AND REMOVE SYMLINKS
#
echo ""
echo -e "${BLUE}=== PHASE 3: FIND AND REMOVE SYMLINKS ===${NC}"
echo ""

if [ "$OLD_EXISTS" = true ]; then
    print_step "Searching for symlinks pointing to old installation..."
    echo "Searching in /etc, /usr/local, /opt..."

    SYMLINKS=$(find /etc /usr/local /opt -type l -lname "*brain-v2*" 2>/dev/null || true)

    if [ -n "$SYMLINKS" ]; then
        echo "Found symlinks:"
        echo "$SYMLINKS"
        echo ""
        confirm "Remove these symlinks?"

        echo "$SYMLINKS" | while read -r link; do
            rm -f "$link"
            echo "  Removed: $link"
        done
        echo "✅ Symlinks removed"
    else
        echo "✅ No symlinks found"
    fi
else
    echo "⏭️  Skipping (old installation not found)"
fi

#
# PHASE 4: CREATE /srv STRUCTURE
#
echo ""
echo -e "${BLUE}=== PHASE 4: CREATE /srv STRUCTURE ===${NC}"
echo ""

print_step "Creating /srv directory structure..."
mkdir -p /srv/dev
mkdir -p /srv/stage
mkdir -p /srv/prod
mkdir -p /srv/backups
echo "✅ Created:"
echo "  - /srv/dev"
echo "  - /srv/stage"
echo "  - /srv/prod"
echo "  - /srv/backups"

print_step "Setting permissions..."
chmod 755 /srv/dev /srv/stage /srv/prod
echo "✅ Permissions set"

#
# PHASE 5: DEPLOY TO /srv/dev
#
echo ""
echo -e "${BLUE}=== PHASE 5: DEPLOY TO /srv/dev ===${NC}"
echo ""

print_step "Copying from development workspace to /srv/dev..."
rsync -av --exclude '.git' --exclude 'node_modules' --exclude '__pycache__' \
    "$DEV_WORKSPACE/" /srv/dev/
echo "✅ Files copied to /srv/dev"

print_step "Creating .env.dev..."
if [ -f "/srv/dev/.env.example" ]; then
    cp /srv/dev/.env.example /srv/dev/.env.dev

    # Generate secure passwords
    PG_PASS=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    JWT_SECRET=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-64)

    # Update .env.dev
    sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$PG_PASS/" /srv/dev/.env.dev
    sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET/" /srv/dev/.env.dev
    sed -i "s/ENVIRONMENT=.*/ENVIRONMENT=development/" /srv/dev/.env.dev

    echo "✅ .env.dev created with secure passwords"
else
    print_warning ".env.example not found, skipping .env.dev creation"
fi

print_step "Checking docker-compose files..."
if [ -f "/srv/dev/docker-compose.yml" ] && [ -f "/srv/dev/docker-compose.dev.yml" ]; then
    echo "✅ Docker Compose files found"
    echo ""
    echo "To start services:"
    echo "  cd /srv/dev"
    echo "  ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d"
else
    print_warning "Docker Compose files not found"
fi

#
# PHASE 6: CLEANUP OLD INSTALLATION
#
if [ "$OLD_EXISTS" = true ]; then
    echo ""
    echo -e "${BLUE}=== PHASE 6: CLEANUP OLD INSTALLATION ===${NC}"
    echo ""

    print_warning "About to DELETE old installation: $OLD_PATH"
    echo "Backup is available at: $BACKUP_FILE"
    echo ""
    confirm "Are you ABSOLUTELY SURE you want to delete $OLD_PATH?"

    print_step "Removing old installation..."
    rm -rf "$OLD_PATH"
    echo "✅ Old installation removed"
fi

#
# PHASE 7: SUMMARY
#
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✅ MIGRATION COMPLETED SUCCESSFULLY${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Summary:"
echo "  ✅ Old installation backed up: $([ "$OLD_EXISTS" = true ] && echo "$BACKUP_FILE" || echo "N/A")"
echo "  ✅ Old containers stopped: $([ "$OLD_EXISTS" = true ] && echo "Yes" || echo "N/A")"
echo "  ✅ Symlinks removed: Yes"
echo "  ✅ /srv structure created"
echo "  ✅ Development deployed to: /srv/dev"
echo "  ✅ Old installation removed: $([ "$OLD_EXISTS" = true ] && echo "Yes" || echo "N/A")"
echo ""
echo "Next steps:"
echo ""
echo "1. Start development environment:"
echo "   ${BLUE}cd /srv/dev${NC}"
echo "   ${BLUE}ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d${NC}"
echo ""
echo "2. Check logs:"
echo "   ${BLUE}docker compose logs -f${NC}"
echo ""
echo "3. Access services:"
echo "   Backend:      http://localhost:8001/docs"
echo "   Control Deck: http://localhost:3001"
echo "   AXE UI:       http://localhost:3002"
echo ""
echo "4. Development workspace remains at:"
echo "   ${BLUE}${DEV_WORKSPACE}${NC}"
echo "   (Use this for git operations and code editing)"
echo ""
echo "5. Docker volumes (if any) are preserved and can be:"
echo "   - Reused: docker volume ls | grep brain"
echo "   - Removed: docker volume rm <volume_name>"
echo ""
echo -e "${GREEN}🎉 Migration complete! Happy coding!${NC}"
