#!/bin/bash
################################################################################
# check-ports.sh - Verify BRAiN dev ports are available
#
# Checks required dev ports (backend + 3 frontends) and shows owning PIDs.
# Exits non-zero if any required port is already in use (unless --allow-in-use).
#
# Usage:
#   ./scripts/check-ports.sh              # Check all required ports
#   ./scripts/check-ports.sh --allow-in-use  # Only report, don't fail
#   ./scripts/check-ports.sh --ports 8001,3456,3002  # Custom ports
#
################################################################################

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default BRAiN dev ports
PORTS_BACKEND=8001
PORTS_FRONTEND_CONTROLDECK=3456
PORTS_FRONTEND_AXE=3002
PORTS_FRONTEND_LEGACY=3001

# Flags
ALLOW_IN_USE=false
VERBOSE=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# PARSING
# ============================================================================

while [[ $# -gt 0 ]]; do
    case "$1" in
        --allow-in-use)
            ALLOW_IN_USE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --ports)
            IFS=',' read -ra CUSTOM_PORTS <<< "$2"
            PORTS_BACKEND="${CUSTOM_PORTS[0]:-$PORTS_BACKEND}"
            PORTS_FRONTEND_CONTROLDECK="${CUSTOM_PORTS[1]:-$PORTS_FRONTEND_CONTROLDECK}"
            PORTS_FRONTEND_AXE="${CUSTOM_PORTS[2]:-$PORTS_FRONTEND_AXE}"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ============================================================================
# FUNCTIONS
# ============================================================================

check_port() {
    local port=$1
    local service=$2
    
    # Try to find PID using lsof
    local pid=""
    if command -v lsof &> /dev/null; then
        pid=$(lsof -t -i ":$port" 2>/dev/null || echo "")
    elif command -v netstat &> /dev/null; then
        # Fallback to netstat
        pid=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $NF}' | cut -d'/' -f1 || echo "")
    fi
    
    if [ -n "$pid" ] && [ "$pid" != "-" ]; then
        local cmd=""
        if [ -r "/proc/$pid/cmdline" ]; then
            cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline" | cut -d' ' -f1)
        fi
        
        echo -e "${RED}✗${NC} Port $port (${service}): IN USE"
        echo "  PID $pid: $cmd"
        return 1
    else
        echo -e "${GREEN}✓${NC} Port $port (${service}): Available"
        return 0
    fi
}

# ============================================================================
# MAIN
# ============================================================================

echo "🔍 Checking BRAiN dev ports..."
echo ""

failed=0

check_port $PORTS_BACKEND "Backend" || ((failed++))
check_port $PORTS_FRONTEND_CONTROLDECK "ControlDeck-v2" || ((failed++))
check_port $PORTS_FRONTEND_AXE "AXE_UI" || ((failed++))
# Legacy frontend is optional
if [ "$VERBOSE" = true ]; then
    check_port $PORTS_FRONTEND_LEGACY "Control Deck (legacy)" || true
fi

echo ""
if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✅ All required ports are available${NC}"
    exit 0
else
    echo -e "${RED}❌ $failed port(s) already in use${NC}"
    if [ "$ALLOW_IN_USE" = true ]; then
        echo "⚠️  Continuing anyway (--allow-in-use)"
        exit 0
    else
        echo "💡 Tip: Use --allow-in-use to override, or kill with: lsof -t -i :PORT | xargs kill -9"
        exit 1
    fi
fi
