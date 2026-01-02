#!/bin/bash

# BRAiN Repository Cleanup Script
# Purpose: Delete all merged Claude branches that are already in v2
# Date: 2026-01-02

set -e

echo "========================================"
echo "BRAiN Branch Cleanup Script"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Ensure we're on v2 and up to date
echo -e "${YELLOW}[1/5] Ensuring v2 is up to date...${NC}"
git checkout v2
git pull origin v2

# Get all claude branches
echo -e "${YELLOW}[2/5] Fetching all branches...${NC}"
git fetch origin --prune

# Find all merged claude branches
echo -e "${YELLOW}[3/5] Identifying merged branches...${NC}"
MERGED_BRANCHES=$(git branch -r --merged v2 | grep "origin/claude" | sed 's/origin\///' | tr -d ' ')

if [ -z "$MERGED_BRANCHES" ]; then
    echo -e "${GREEN}✅ No merged branches to clean up!${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}Found $(echo "$MERGED_BRANCHES" | wc -l) merged branches:${NC}"
echo "$MERGED_BRANCHES"
echo ""

# Count branches
BRANCH_COUNT=$(echo "$MERGED_BRANCHES" | wc -l)

# Ask for confirmation
echo -e "${YELLOW}⚠️  This will delete $BRANCH_COUNT remote branches!${NC}"
echo ""
read -p "Do you want to proceed? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${RED}Aborted by user.${NC}"
    exit 1
fi

# Delete branches
echo -e "${YELLOW}[4/5] Deleting merged branches...${NC}"
DELETED=0
FAILED=0

while IFS= read -r branch; do
    branch=$(echo "$branch" | xargs)
    if [ -n "$branch" ]; then
        echo "Deleting: $branch"
        if git push origin --delete "$branch" 2>/dev/null; then
            echo -e "${GREEN}  ✅ Deleted${NC}"
            ((DELETED++))
        else
            echo -e "${RED}  ❌ Failed (might not exist or no permission)${NC}"
            ((FAILED++))
        fi
    fi
done <<< "$MERGED_BRANCHES"

echo ""
echo -e "${YELLOW}[5/5] Cleanup Summary${NC}"
echo "========================================"
echo -e "${GREEN}Deleted: $DELETED branches${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED branches${NC}"
fi
echo ""

# Cleanup local references
echo -e "${YELLOW}Cleaning up local references...${NC}"
git fetch origin --prune
git remote prune origin

echo ""
echo -e "${GREEN}✅ Cleanup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Check GitHub PRs and close merged ones"
echo "2. Verify v2 branch is healthy"
echo "3. Consider merging v2 → main if ready for production"
