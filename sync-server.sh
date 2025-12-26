#!/bin/bash
#
# sync-server.sh - Sync local changes with remote repository
#

set -e

echo "=== Syncing with Remote Repository ==="

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "Error: Not a git repository"
    exit 1
fi

# Show current status
echo "Current branch:"
git branch --show-current

echo -e "\nCurrent status:"
git status --short

# Stash any local changes
if ! git diff-index --quiet HEAD --; then
    echo -e "\n=== Stashing local changes ==="
    git stash push -m "Auto-stash before sync $(date +%Y%m%d-%H%M%S)"
    echo "✓ Local changes stashed"
fi

# Configure pull strategy to rebase
echo -e "\n=== Pulling latest changes ==="
git config pull.rebase false
git pull origin v2

echo -e "\n=== Sync Complete ==="
echo "Repository is now up to date with remote v2 branch"

# Show final status
git log --oneline -5
