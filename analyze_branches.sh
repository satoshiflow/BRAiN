#!/bin/bash

# BRAiN Branch Analysis Script
# Purpose: Analyze branch status without deleting anything
# Date: 2026-01-02

set -e

echo "========================================"
echo "BRAiN Branch Analysis"
echo "========================================"
echo ""

# Ensure we're up to date
git fetch origin --prune

# Get base branch (v2)
BASE_BRANCH="v2"

echo "Base branch: $BASE_BRANCH"
echo "Latest commit: $(git log -1 --format='%h - %s' origin/$BASE_BRANCH)"
echo ""

# Analyze claude branches
echo "Analyzing Claude branches..."
echo ""

MERGED_COUNT=0
UNMERGED_COUNT=0
TOTAL_COUNT=0

# Header
printf "%-60s | %-10s | %-20s\n" "Branch" "Status" "Last Update"
printf "%.80s\n" "--------------------------------------------------------------------------------"

for branch in $(git branch -r | grep "origin/claude" | sed 's/origin\///' | tr -d ' '); do
    ((TOTAL_COUNT++))

    # Check if merged
    if git branch -r --merged origin/$BASE_BRANCH | grep -q "origin/$branch"; then
        STATUS="✅ MERGED"
        ((MERGED_COUNT++))
    else
        STATUS="⚠️  UNMERGED"
        ((UNMERGED_COUNT++))
    fi

    # Get last commit date
    LAST_UPDATE=$(git log -1 --format='%ar' origin/$branch 2>/dev/null || echo "unknown")

    printf "%-60s | %-10s | %-20s\n" "$branch" "$STATUS" "$LAST_UPDATE"
done

echo ""
echo "========================================"
echo "Summary"
echo "========================================"
echo "Total branches:    $TOTAL_COUNT"
echo "✅ Merged:         $MERGED_COUNT (safe to delete)"
echo "⚠️  Unmerged:       $UNMERGED_COUNT (needs review)"
echo ""

if [ $UNMERGED_COUNT -gt 0 ]; then
    echo "⚠️  WARNING: $UNMERGED_COUNT branches have unmerged commits!"
    echo "Review these branches before cleanup:"
    echo ""

    for branch in $(git branch -r | grep "origin/claude" | sed 's/origin\///' | tr -d ' '); do
        if ! git branch -r --merged origin/$BASE_BRANCH | grep -q "origin/$branch"; then
            echo "  - $branch"
            echo "    Commits not in $BASE_BRANCH:"
            git log origin/$BASE_BRANCH...origin/$branch --oneline | head -5
            echo ""
        fi
    done
fi

echo ""
echo "Next steps:"
echo "1. Review unmerged branches (if any)"
echo "2. Run ./cleanup_merged_branches.sh to delete merged branches"
echo "3. Manually merge or archive important unmerged branches"
