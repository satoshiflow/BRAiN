#!/bin/bash
# BRAiN Branch Strategy Setup
# Run this with GitHub Admin rights

set -e

echo "========================================"
echo "BRAiN Branch Strategy Setup"
echo "========================================"
echo ""

# Configuration
GITHUB_REPO="satoshiflow/BRAiN"
BASE_BRANCH="v2"

echo "This script will create the following branch strategy:"
echo "  - main   (Production) from $BASE_BRANCH"
echo "  - dev    (Development) from $BASE_BRANCH"
echo "  - stage  (Testing) from $BASE_BRANCH"
echo ""

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) not found!"
    echo ""
    echo "Install with:"
    echo "  Ubuntu/Debian: sudo apt install gh"
    echo "  macOS: brew install gh"
    echo "  Or: https://cli.github.com/"
    echo ""
    echo "After install: gh auth login"
    exit 1
fi

# Check authentication
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub!"
    echo "Run: gh auth login"
    exit 1
fi

echo "✓ GitHub CLI ready"
echo ""

# Ensure we're on v2
git checkout $BASE_BRANCH
git pull origin $BASE_BRANCH

CURRENT_COMMIT=$(git rev-parse HEAD)
echo "Base commit: $CURRENT_COMMIT ($(git log -1 --format='%s' | head -c 50)...)"
echo ""

# Function to create or update branch
create_branch() {
    local branch=$1
    local description=$2

    echo "Creating $branch branch ($description)..."

    # Create local branch
    git branch -D $branch 2>/dev/null || true
    git checkout -b $branch $BASE_BRANCH

    # Push to GitHub (force to ensure it's at correct commit)
    if git push -u origin $branch --force; then
        echo "✓ $branch created successfully"
    else
        echo "⚠️  Failed to push $branch (may require admin rights)"
    fi

    echo ""
}

# Create branches
create_branch "main" "Production - Stable releases only"
create_branch "dev" "Development - Active development"
create_branch "stage" "Testing - Pre-production testing"

# Return to dev (primary development branch)
git checkout dev

echo "========================================"
echo "Branch Strategy Summary"
echo "========================================"
git branch -a | grep -E "  (main|dev|stage|$BASE_BRANCH)$" || true

echo ""
echo "Next steps:"
echo "1. Configure branch protection rules (see BRANCH_PROTECTION.md)"
echo "2. Update GitHub Actions workflows"
echo "3. Set default branch to 'dev' on GitHub"
echo ""
echo "✓ Done!"
