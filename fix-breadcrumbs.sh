#!/bin/bash
# Fix BreadcrumbItem className errors directly on server

echo "=== Fixing BreadcrumbItem TypeScript Errors ==="

cd /opt/brain

# Remove the conflicting file
rm -f sync-server.sh

# Stash any local changes
git stash

# Pull the fixes
git pull origin claude/migrate-v2-launch-01UQ1FuiVg8Rv6UQwwDar1g5

echo ""
echo "✓ Fixes applied successfully"
echo ""
echo "Verify the changes:"
grep -A 8 "BreadcrumbList>" frontend/control_deck/app/settings/page.tsx | head -15

echo ""
echo "Now rebuild: docker compose build --no-cache control_deck axe_ui"
