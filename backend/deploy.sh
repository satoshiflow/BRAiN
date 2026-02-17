#!/bin/bash
# ============================================================================
# BRAiN Backend Deployment Script
# ============================================================================
# Purpose: One-command deployment with all fixes applied
# Branch: fix/python-path-and-deps-h1NXi
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}🧠 BRAiN Backend Deployment${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: docker-compose.yml not found${NC}"
    echo -e "${RED}   Please run this script from /srv/dev${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Deployment Steps:${NC}"
echo -e "  1. Stop existing containers"
echo -e "  2. Clean up old images"
echo -e "  3. Build backend with fixes"
echo -e "  4. Start services"
echo -e "  5. Verify health"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Step 1: Stop containers
echo -e "\n${BLUE}Step 1/5: Stopping containers...${NC}"
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
echo -e "${GREEN}✅ Containers stopped${NC}"

# Step 2: Clean up
echo -e "\n${BLUE}Step 2/5: Cleaning up...${NC}"
docker system prune -f > /dev/null 2>&1 || true
echo -e "${GREEN}✅ Cleanup complete${NC}"

# Step 3: Build backend
echo -e "\n${BLUE}Step 3/5: Building backend (this may take 2-3 minutes)...${NC}"
docker compose -f docker-compose.yml -f docker-compose.dev.yml build backend --no-cache

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backend build successful${NC}"
else
    echo -e "${RED}❌ Backend build failed${NC}"
    echo -e "${RED}   Check logs above for errors${NC}"
    exit 1
fi

# Step 4: Start services
echo -e "\n${BLUE}Step 4/5: Starting services...${NC}"
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres redis backend

echo -e "${YELLOW}⏳ Waiting for services to start (10 seconds)...${NC}"
sleep 10

# Step 5: Verify health
echo -e "\n${BLUE}Step 5/5: Verifying deployment...${NC}"

# Check container status
BACKEND_STATUS=$(docker compose ps backend --format json 2>/dev/null | grep -o '"State":"running"' || echo "")
if [ -n "$BACKEND_STATUS" ]; then
    echo -e "${GREEN}✅ Backend container running${NC}"
else
    echo -e "${RED}❌ Backend container not running${NC}"
    echo -e "${YELLOW}Showing logs:${NC}"
    docker compose logs backend --tail 50
    exit 1
fi

# Check health endpoint
echo -e "\n${YELLOW}Testing API health...${NC}"
sleep 2  # Give it a moment

HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8001/api/health 2>/dev/null || echo "000")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ API health check successful${NC}"

    # Check for UTF-8 charset
    CHARSET=$(curl -s -I http://localhost:8001/api/health 2>/dev/null | grep -i "content-type" | grep -o "charset=utf-8" || echo "")
    if [ -n "$CHARSET" ]; then
        echo -e "${GREEN}✅ UTF-8 charset detected${NC}"
    else
        echo -e "${YELLOW}⚠️  UTF-8 charset not detected (may not be critical)${NC}"
    fi
else
    echo -e "${RED}❌ API health check failed (HTTP $HTTP_CODE)${NC}"
    echo -e "${YELLOW}Showing logs:${NC}"
    docker compose logs backend --tail 30
    exit 1
fi

# Summary
echo -e "\n${BLUE}============================================${NC}"
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "${GREEN}✅ Services Running:${NC}"
echo -e "   • Backend:  http://localhost:8001"
echo -e "   • Postgres: localhost:5432"
echo -e "   • Redis:    localhost:6379"
echo ""
echo -e "${GREEN}🔗 External Access:${NC}"
echo -e "   • HTTPS: https://dev.brain.falklabs.de"
echo ""
echo -e "${BLUE}📊 Useful Commands:${NC}"
echo -e "   • View logs:    ${YELLOW}docker compose logs -f backend${NC}"
echo -e "   • Container status: ${YELLOW}docker compose ps${NC}"
echo -e "   • Stop all:     ${YELLOW}docker compose down${NC}"
echo ""
echo -e "${BLUE}🔍 Quick Tests:${NC}"
echo -e "   • Health check: ${YELLOW}curl http://localhost:8001/api/health${NC}"
echo -e "   • UTF-8 check:  ${YELLOW}curl -I http://localhost:8001/api/health | grep charset${NC}"
echo ""

# Offer to show logs
echo -e "${BLUE}============================================${NC}"
read -p "Show live logs? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Showing live logs (Ctrl+C to exit)...${NC}"
    docker compose logs -f backend
fi
