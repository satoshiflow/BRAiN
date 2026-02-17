#!/bin/bash
#
# BRAiN Server Status Check
# Purpose: Analyze current server state before making changes
# Usage: bash check-server-status.sh
#

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}BRAiN Server Status Check${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

#
# 1. USER ANALYSIS
#
echo -e "${GREEN}[1] USER ANALYSIS${NC}"
echo ""

echo "Current user:"
whoami
echo ""

echo "Available users with home directories:"
ls -la /home/ 2>/dev/null || echo "No /home directory"
echo ""

echo "User 'claude' exists?"
if id "claude" &>/dev/null; then
    echo -e "${GREEN}✅ Yes${NC}"
    echo "  Home: $(eval echo ~claude)"
    echo "  Shell: $(getent passwd claude | cut -d: -f7)"
    echo "  Groups: $(groups claude)"
else
    echo -e "${RED}❌ No${NC}"
fi
echo ""

echo "User 'root' info:"
echo "  Home: $HOME"
echo "  Current dir: $(pwd)"
echo ""

#
# 2. SSH KEY ANALYSIS
#
echo -e "${GREEN}[2] SSH KEY ANALYSIS${NC}"
echo ""

echo "Root SSH keys:"
if [ -d "/root/.ssh" ]; then
    ls -la /root/.ssh/
    echo ""
    if [ -f "/root/.ssh/id_rsa.pub" ] || [ -f "/root/.ssh/id_ed25519.pub" ]; then
        echo "Public keys found:"
        cat /root/.ssh/id_*.pub 2>/dev/null || echo "None"
    fi
else
    echo -e "${YELLOW}⚠️  No /root/.ssh directory${NC}"
fi
echo ""

echo "Claude SSH keys:"
if [ -d "/home/claude/.ssh" ]; then
    ls -la /home/claude/.ssh/
    echo ""
    if [ -f "/home/claude/.ssh/id_rsa.pub" ] || [ -f "/home/claude/.ssh/id_ed25519.pub" ]; then
        echo "Public keys found:"
        cat /home/claude/.ssh/id_*.pub 2>/dev/null || echo "None"
    fi
else
    echo -e "${YELLOW}⚠️  No /home/claude/.ssh directory${NC}"
fi
echo ""

echo "Testing GitHub SSH access (as root):"
ssh -T git@github.com 2>&1 | head -5
echo ""

echo "Testing GitHub SSH access (as claude):"
if id "claude" &>/dev/null; then
    su - claude -c "ssh -T git@github.com 2>&1 | head -5"
else
    echo "User claude doesn't exist"
fi
echo ""

#
# 3. DIRECTORY STRUCTURE
#
echo -e "${GREEN}[3] DIRECTORY STRUCTURE${NC}"
echo ""

echo "/root/BRAiN/:"
if [ -d "/root/BRAiN" ]; then
    echo -e "${GREEN}✅ Exists${NC}"
    echo "  Size: $(du -sh /root/BRAiN 2>/dev/null | cut -f1)"
    echo "  Files: $(find /root/BRAiN -maxdepth 1 -type f 2>/dev/null | wc -l)"
    echo "  Dirs: $(find /root/BRAiN -maxdepth 1 -type d 2>/dev/null | wc -l)"
    if [ -d "/root/BRAiN/.git" ]; then
        echo -e "  ${GREEN}Git repo: Yes${NC}"
        cd /root/BRAiN && git remote -v 2>/dev/null
        cd - > /dev/null
    else
        echo "  Git repo: No"
    fi
else
    echo -e "${YELLOW}⚠️  Does not exist${NC}"
fi
echo ""

echo "/srv/dev/:"
if [ -d "/srv/dev" ]; then
    echo -e "${GREEN}✅ Exists${NC}"
    echo "  Size: $(du -sh /srv/dev 2>/dev/null | cut -f1)"
    echo "  Owner: $(stat -c '%U:%G' /srv/dev)"
    if [ -d "/srv/dev/.git" ]; then
        echo -e "  ${GREEN}Git repo: Yes${NC}"
        cd /srv/dev && git remote -v 2>/dev/null && git branch 2>/dev/null
        cd - > /dev/null
    else
        echo "  Git repo: No"
    fi
    echo "  docker-compose.yml: $([ -f /srv/dev/docker-compose.yml ] && echo "✅ Yes" || echo "❌ No")"
    echo "  .env.dev: $([ -f /srv/dev/.env.dev ] && echo "✅ Yes" || echo "❌ No")"
else
    echo -e "${RED}❌ Does not exist${NC}"
fi
echo ""

echo "/srv/main/:"
if [ -d "/srv/main" ]; then
    echo -e "${GREEN}✅ Exists${NC}"
    echo "  Empty: $([ -z "$(ls -A /srv/main 2>/dev/null)" ] && echo "Yes" || echo "No")"
else
    echo -e "${YELLOW}⚠️  Does not exist${NC}"
fi
echo ""

echo "/srv/stage/:"
if [ -d "/srv/stage" ]; then
    echo -e "${GREEN}✅ Exists${NC}"
    echo "  Empty: $([ -z "$(ls -A /srv/stage 2>/dev/null)" ] && echo "Yes" || echo "No")"
else
    echo -e "${YELLOW}⚠️  Does not exist${NC}"
fi
echo ""

echo "/srv/prod/:"
if [ -d "/srv/prod" ]; then
    echo -e "${GREEN}✅ Exists${NC}"
    echo "  Empty: $([ -z "$(ls -A /srv/prod 2>/dev/null)" ] && echo "Yes" || echo "No")"
else
    echo -e "${YELLOW}⚠️  Does not exist${NC}"
fi
echo ""

#
# 4. DOCKER STATUS
#
echo -e "${GREEN}[4] DOCKER STATUS${NC}"
echo ""

echo "Docker installed:"
if command -v docker &>/dev/null; then
    echo -e "${GREEN}✅ Yes${NC}"
    docker --version
else
    echo -e "${RED}❌ No${NC}"
fi
echo ""

echo "Running containers:"
if command -v docker &>/dev/null; then
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -20
else
    echo "Docker not available"
fi
echo ""

echo "Docker compose files in /srv/dev/:"
if [ -d "/srv/dev" ]; then
    ls -l /srv/dev/docker-compose*.yml 2>/dev/null || echo "None found"
fi
echo ""

#
# 5. CLEANUP TARGETS
#
echo -e "${GREEN}[5] CLEANUP TARGETS${NC}"
echo ""

echo "/opt/brain-v2/:"
if [ -d "/opt/brain-v2" ]; then
    echo -e "${YELLOW}⚠️  Still exists${NC}"
    echo "  Size: $(du -sh /opt/brain-v2 2>/dev/null | cut -f1)"
else
    echo -e "${GREEN}✅ Already removed${NC}"
fi
echo ""

echo "/opt/containerd/:"
if [ -d "/opt/containerd" ]; then
    echo -e "${YELLOW}⚠️  Exists${NC}"
    echo "  Size: $(du -sh /opt/containerd 2>/dev/null | cut -f1)"
    echo "  Contents:"
    ls -la /opt/containerd/ 2>/dev/null
else
    echo -e "${GREEN}✅ Already removed${NC}"
fi
echo ""

echo "/opt/openwebui/:"
if [ -d "/opt/openwebui" ]; then
    echo -e "${GREEN}✅ Exists${NC}"
    echo "  Files:"
    ls -la /opt/openwebui/ 2>/dev/null
    echo "  .env exists: $([ -f /opt/openwebui/.env ] && echo "✅ Yes" || echo "❌ No")"
    echo "  docker-compose.yml exists: $([ -f /opt/openwebui/docker-compose.yml ] && echo "✅ Yes" || echo "❌ No")"
else
    echo -e "${RED}❌ Does not exist${NC}"
fi
echo ""

#
# 6. BACKUPS
#
echo -e "${GREEN}[6] BACKUPS${NC}"
echo ""

echo "/root/backups/:"
if [ -d "/root/backups" ]; then
    echo -e "${GREEN}✅ Exists${NC}"
    echo "  Total size: $(du -sh /root/backups 2>/dev/null | cut -f1)"
    echo "  Backup files:"
    ls -lh /root/backups/*.tar.gz 2>/dev/null | tail -10 || echo "  No .tar.gz files"
else
    echo -e "${YELLOW}⚠️  Does not exist${NC}"
fi
echo ""

#
# 7. DISK SPACE
#
echo -e "${GREEN}[7] DISK SPACE${NC}"
echo ""
df -h / /srv /root 2>/dev/null
echo ""

#
# SUMMARY
#
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}SUMMARY & RECOMMENDATIONS${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

WARNINGS=0
ERRORS=0

# Check critical items
if ! id "claude" &>/dev/null; then
    echo -e "${RED}⚠️  WARNING: User 'claude' does not exist${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

if [ ! -d "/srv/dev" ]; then
    echo -e "${RED}❌ ERROR: /srv/dev does not exist${NC}"
    ERRORS=$((ERRORS + 1))
fi

if ! docker ps &>/dev/null; then
    echo -e "${YELLOW}⚠️  WARNING: Cannot check Docker status${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

if [ "$WARNINGS" -eq 0 ] && [ "$ERRORS" -eq 0 ]; then
    echo -e "${GREEN}✅ All critical checks passed${NC}"
    echo ""
    echo "Safe to proceed with:"
    echo "  1. Setting up /root/BRAiN as development workspace"
    echo "  2. Cleanup of /opt/containerd"
    echo "  3. Backup of /opt/openwebui files"
else
    echo -e "${RED}Found $ERRORS errors and $WARNINGS warnings${NC}"
    echo ""
    echo "Please review the output above before proceeding."
fi

echo ""
echo -e "${BLUE}================================================${NC}"
echo "Report generated: $(date)"
echo -e "${BLUE}================================================${NC}"
