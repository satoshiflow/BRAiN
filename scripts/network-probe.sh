#!/bin/bash
################################################################################
# BRAiN Network Probe Script
#
# Tests network connectivity from inside BRAiN containers to verify
# sovereign mode enforcement. Should FAIL when sovereign mode is active.
#
# Exit Codes:
#   0 = Isolated (no internet access) ← Expected in sovereign mode
#   1 = Has internet access          ← BAD in sovereign mode
#   2 = Error during probe
#
# Usage:
#   # From host
#   docker exec brain-backend bash /app/scripts/network-probe.sh
#
#   # From inside container
#   bash /app/scripts/network-probe.sh
#
# Version: 1.0.0
# Date: 2025-12-24
################################################################################

set -u

# Test targets (public internet)
TARGETS=(
    "1.1.1.1:80"         # Cloudflare
    "8.8.8.8:80"         # Google DNS
    "www.google.com:443" # Google HTTPS
)

# Timeout for each probe (seconds)
TIMEOUT=5

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ============================================================================
# PROBES
# ============================================================================

probe_http() {
    local target="$1"
    local url="http://${target}"

    if command -v curl &> /dev/null; then
        curl -s -I --connect-timeout "$TIMEOUT" "$url" &> /dev/null
        return $?
    elif command -v wget &> /dev/null; then
        wget -q --timeout="$TIMEOUT" --spider "$url" &> /dev/null
        return $?
    else
        return 2  # No HTTP client available
    fi
}

probe_tcp() {
    local host="${1%%:*}"
    local port="${1##*:}"

    if command -v nc &> /dev/null; then
        nc -z -w "$TIMEOUT" "$host" "$port" &> /dev/null
        return $?
    elif command -v telnet &> /dev/null; then
        timeout "$TIMEOUT" telnet "$host" "$port" &> /dev/null
        return $?
    else
        return 2  # No TCP client available
    fi
}

probe_ping() {
    local host="${1%%:*}"

    if command -v ping &> /dev/null; then
        ping -c 1 -W "$TIMEOUT" "$host" &> /dev/null
        return $?
    else
        return 2  # Ping not available
    fi
}

# ============================================================================
# MAIN PROBE LOGIC
# ============================================================================

main() {
    local success_count=0
    local fail_count=0
    local error_count=0

    echo "🔍 BRAiN Network Probe"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    for target in "${TARGETS[@]}"; do
        echo -n "Testing $target ... "

        # Try HTTP first
        if probe_http "$target"; then
            echo -e "${RED}✗ CONNECTED${NC} (HTTP)"
            ((success_count++))
            continue
        fi

        # Try TCP
        if probe_tcp "$target"; then
            echo -e "${RED}✗ CONNECTED${NC} (TCP)"
            ((success_count++))
            continue
        fi

        # Try ping
        if probe_ping "$target"; then
            echo -e "${RED}✗ CONNECTED${NC} (ICMP)"
            ((success_count++))
            continue
        fi

        # All probes failed - target unreachable
        echo -e "${GREEN}✓ BLOCKED${NC}"
        ((fail_count++))
    done

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Summary
    local total=${#TARGETS[@]}
    echo "Results: $success_count reachable, $fail_count blocked (of $total tested)"

    # Verdict
    if [[ $success_count -eq 0 ]]; then
        echo -e "${GREEN}✓ ISOLATED${NC} - No internet access detected"
        echo ""
        echo "Sovereign mode enforcement: VERIFIED"
        exit 0  # Isolated = success

    elif [[ $fail_count -eq 0 ]]; then
        echo -e "${RED}✗ CONNECTED${NC} - Full internet access detected"
        echo ""
        echo "Sovereign mode enforcement: FAILED"
        exit 1  # Connected = failure in sovereign mode

    else
        echo -e "${YELLOW}⚠ PARTIAL${NC} - Some internet access detected"
        echo ""
        echo "Sovereign mode enforcement: DEGRADED"
        exit 1  # Partial = failure
    fi
}

# Run main
main
