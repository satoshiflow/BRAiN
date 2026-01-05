#!/bin/bash
#
# BRAiN Development Workspace Setup
# Purpose: Setup /root/BRAiN/ as development workspace + cleanup
# Usage: bash setup-brain-workspace.sh
#

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}BRAiN Development Workspace Setup${NC}"
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
# PRE-FLIGHT CHECKS
#
echo -e "${BLUE}=== PRE-FLIGHT CHECKS ===${NC}"
echo ""

print_step "Checking if running as root..."
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root: sudo bash $0"
    exit 1
fi
echo "✅ Running as root"

print_step "Checking disk space..."
FREE_SPACE=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$FREE_SPACE" -lt 5 ]; then
    print_warning "Low disk space: ${FREE_SPACE}GB free (recommended: >5GB)"
    confirm "Continue anyway?"
fi
echo "✅ Disk space OK: ${FREE_SPACE}GB free"

print_step "Checking if /srv/dev/ is running..."
if ! docker ps | grep -q "dev-backend"; then
    print_warning "/srv/dev/ containers not running"
    confirm "Continue anyway?"
else
    echo "✅ /srv/dev/ containers running"
fi

echo ""
echo -e "${YELLOW}This script will:${NC}"
echo "  1. Clone BRAiN repo to /root/BRAiN/ via HTTPS (Branch: v2)"
echo "  2. Create /root/backups/ directory"
echo "  3. Backup /opt/openwebui/ files to /root/backups/openwebui/"
echo "  4. Delete /opt/containerd/ (2 empty directories)"
echo ""
confirm "Proceed?"

#
# PHASE 1: SETUP /root/BRAiN/ WORKSPACE
#
echo ""
echo -e "${BLUE}=== PHASE 1: SETUP /root/BRAiN/ ===${NC}"
echo ""

if [ -d "/root/BRAiN" ]; then
    print_warning "/root/BRAiN/ already exists"
    ls -la /root/BRAiN/
    echo ""
    confirm "Delete and re-clone?"
    rm -rf /root/BRAiN
    echo "✅ Old /root/BRAiN/ deleted"
fi

print_step "Cloning BRAiN repository (Branch: v2) via HTTPS..."
cd /root
git clone -b v2 https://github.com/satoshiflow/BRAiN.git BRAiN

if [ $? -eq 0 ]; then
    echo "✅ Repository cloned successfully"
    cd /root/BRAiN
    echo ""
    echo "Repository info:"
    git remote -v
    git branch
    echo ""
    echo "Files: $(find . -type f | wc -l)"
    echo "Size: $(du -sh . | cut -f1)"
else
    print_error "Git clone failed"
    exit 1
fi

#
# PHASE 2: CREATE BACKUPS DIRECTORY
#
echo ""
echo -e "${BLUE}=== PHASE 2: CREATE BACKUPS DIRECTORY ===${NC}"
echo ""

print_step "Creating /root/backups/ directory..."
mkdir -p /root/backups
mkdir -p /root/backups/openwebui
echo "✅ Backups directory created"

#
# PHASE 3: BACKUP OPENWEBUI FILES
#
echo ""
echo -e "${BLUE}=== PHASE 3: BACKUP OPENWEBUI FILES ===${NC}"
echo ""

if [ -d "/opt/openwebui" ]; then
    print_step "Backing up /opt/openwebui/ files..."

    if [ -f "/opt/openwebui/.env" ]; then
        cp /opt/openwebui/.env /root/backups/openwebui/
        echo "✅ Copied .env"
    else
        print_warning ".env not found"
    fi

    if [ -f "/opt/openwebui/docker-compose.yml" ]; then
        cp /opt/openwebui/docker-compose.yml /root/backups/openwebui/
        echo "✅ Copied docker-compose.yml"
    else
        print_warning "docker-compose.yml not found"
    fi

    echo ""
    echo "Backup location:"
    ls -lh /root/backups/openwebui/
else
    print_warning "/opt/openwebui/ not found - skipping backup"
fi

#
# PHASE 4: CLEANUP /opt/containerd/
#
echo ""
echo -e "${BLUE}=== PHASE 4: CLEANUP /opt/containerd/ ===${NC}"
echo ""

if [ -d "/opt/containerd" ]; then
    print_step "Checking /opt/containerd/ contents..."
    echo "Contents:"
    ls -la /opt/containerd/
    echo ""

    # Check if directories are empty
    BIN_EMPTY=$([ -z "$(ls -A /opt/containerd/bin 2>/dev/null)" ] && echo "yes" || echo "no")
    LIB_EMPTY=$([ -z "$(ls -A /opt/containerd/lib 2>/dev/null)" ] && echo "yes" || echo "no")

    echo "  /opt/containerd/bin empty: $BIN_EMPTY"
    echo "  /opt/containerd/lib empty: $LIB_EMPTY"
    echo ""

    if [ "$BIN_EMPTY" = "yes" ] && [ "$LIB_EMPTY" = "yes" ]; then
        confirm "Delete /opt/containerd/ (both directories are empty)?"

        print_step "Deleting /opt/containerd/..."
        rm -rf /opt/containerd/
        echo "✅ /opt/containerd/ deleted"
    else
        print_warning "Directories not empty - skipping deletion"
        echo "Please check manually"
    fi
else
    echo "✅ /opt/containerd/ already removed"
fi

#
# PHASE 5: VERIFICATION
#
echo ""
echo -e "${BLUE}=== PHASE 5: VERIFICATION ===${NC}"
echo ""

print_step "Verifying setup..."

# Check /root/BRAiN/
if [ -d "/root/BRAiN/.git" ]; then
    echo "✅ /root/BRAiN/ is a git repository"
else
    echo "❌ /root/BRAiN/ is NOT a git repository"
fi

# Check backups
if [ -d "/root/backups/openwebui" ]; then
    BACKUP_FILES=$(ls -1 /root/backups/openwebui/ | wc -l)
    echo "✅ Backups created: $BACKUP_FILES files"
else
    echo "❌ Backup directory missing"
fi

# Check cleanup
if [ ! -d "/opt/containerd" ]; then
    echo "✅ /opt/containerd/ removed"
else
    echo "⚠️  /opt/containerd/ still exists"
fi

# Check /srv/dev/ still running
if docker ps | grep -q "dev-backend"; then
    echo "✅ /srv/dev/ containers still running"
else
    echo "⚠️  /srv/dev/ containers not running"
fi

#
# SUMMARY
#
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✅ SETUP COMPLETED SUCCESSFULLY${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Summary:"
echo "  ✅ /root/BRAiN/ created (Branch: v2)"
echo "  ✅ /root/backups/ created"
echo "  ✅ OpenWebUI files backed up"
echo "  ✅ /opt/containerd/ cleaned up"
echo ""
echo "Directory structure:"
echo "  ${BLUE}/root/BRAiN/${NC}          → Development workspace (git operations, code editing)"
echo "  ${BLUE}/srv/dev/${NC}             → Running deployment (Docker containers)"
echo "  ${BLUE}/srv/main/${NC}            → Future main branch"
echo "  ${BLUE}/srv/stage/${NC}           → Staging environment"
echo "  ${BLUE}/srv/prod/${NC}            → Production environment"
echo "  ${BLUE}/root/backups/${NC}        → Backup files"
echo ""
echo "Next steps:"
echo ""
echo "1. Development workflow:"
echo "   ${BLUE}cd /root/BRAiN${NC}"
echo "   ${BLUE}git checkout -b feature/my-feature${NC}"
echo "   ${BLUE}# Edit code...${NC}"
echo "   ${BLUE}git commit -m \"feat: My feature\"${NC}"
echo "   ${BLUE}git push origin feature/my-feature${NC}"
echo ""
echo "2. Check services:"
echo "   Backend:      http://$(hostname -f):8001/docs"
echo "   Control Deck: http://$(hostname -f):3001"
echo "   AXE UI:       http://$(hostname -f):3002"
echo "   OpenWebUI:    http://$(hostname -f):8080"
echo ""
echo "3. Backups available at:"
echo "   ${BLUE}/root/backups/openwebui/${NC}"
echo ""
echo -e "${GREEN}🎉 Ready for development!${NC}"
