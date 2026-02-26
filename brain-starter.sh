#!/bin/bash
################################################################################
# brain-starter.sh - DEPRECATED - Use scripts/dev-up.sh instead
#
# This script is kept for backwards compatibility but is no longer maintained.
# All functionality has been moved to scripts/dev-up.sh which provides:
#  - Safe PID tracking
#  - Proper port checking
#  - Clean shutdown with scripts/dev-down.sh
#
# This wrapper delegates to the new scripts and shows a deprecation warning.
#
# USAGE (deprecated):
#   ./brain-starter.sh
#
# NEW USAGE:
#   ./scripts/dev-up.sh --all      # Start all services
#   ./scripts/dev-down.sh          # Stop all services
#   ./scripts/dev-status.sh        # Show running services
#
################################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# DEPRECATION WARNING
# ============================================================================

echo ""
echo "${RED}⚠️  DEPRECATION WARNING${NC}"
echo "${RED}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "  ${YELLOW}brain-starter.sh is DEPRECATED${NC}"
echo ""
echo "  This script is no longer maintained and can leave orphaned"
echo "  processes if run under systemd or another supervisor."
echo ""
echo "  ${BLUE}Please use the new safe dev scripts instead:${NC}"
echo ""
echo "    ./scripts/dev-up.sh --all      # Start all services"
echo "    ./scripts/dev-down.sh          # Stop all services"
echo "    ./scripts/dev-status.sh        # Show running services"
echo ""
echo "  The new scripts provide:"
echo "    ✓ Safe PID tracking"
echo "    ✓ Port availability checks"
echo "    ✓ Clean shutdown"
echo "    ✓ Better logging"
echo ""
echo "${RED}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# ============================================================================
# SAFETY CHECKS
# ============================================================================

# Fail if in CI environment
if [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ]; then
    echo "${RED}❌ ERROR: brain-starter.sh cannot be used in CI${NC}"
    echo "Use scripts/dev-up.sh instead"
    exit 1
fi

# Fail if BRAIN_ENV=production
if [ "${BRAIN_ENV:-}" = "production" ]; then
    echo "${RED}❌ ERROR: brain-starter.sh cannot be used in production${NC}"
    exit 1
fi

# ============================================================================
# DELEGATE TO NEW SCRIPT
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/scripts/dev-up.sh" --all
