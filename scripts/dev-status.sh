#!/bin/bash
################################################################################
# dev-status.sh - Show status of BRAiN dev services
#
# Displays running services, PIDs, ports, and log locations.
#
# Usage:
#   ./scripts/dev-status.sh         # Show all services
#   ./scripts/dev-status.sh --logs  # Show last 10 lines of each log
#
################################################################################

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_ROOT="$(dirname "$SCRIPT_DIR")"

DEV_PID_DIR="$BRAIN_ROOT/.brain/dev-pids"
DEV_LOG_DIR="$BRAIN_ROOT/.brain/dev-logs"

# Options
SHOW_LOGS=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============================================================================
# PARSE ARGUMENTS
# ============================================================================

while [[ $# -gt 0 ]]; do
    case "$1" in
        --logs)
            SHOW_LOGS=true
            shift
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

check_process() {
    local pid=$1
    if kill -0 "$pid" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

get_process_cmd() {
    local pid=$1
    if [ -r "/proc/$pid/cmdline" ]; then
        tr '\0' ' ' < "/proc/$pid/cmdline" | cut -d' ' -f1-2
    else
        echo "???"
    fi
}

# ============================================================================
# MAIN
# ============================================================================

echo "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo "${CYAN}║          BRAiN Development Services Status                ║${NC}"
echo "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ ! -d "$DEV_PID_DIR" ] || [ -z "$(ls $DEV_PID_DIR/*.pid 2>/dev/null || echo '')" ]; then
    echo "${YELLOW}⚠️  No services running${NC}"
    echo ""
    echo "Start services with:"
    echo "  ./scripts/dev-up.sh --all"
    exit 0
fi

# Collect status
declare -A services
declare -A pids
declare -A ports
declare -A commands

# Read PID files
for pidfile in "$DEV_PID_DIR"/*.pid; do
    if [ -f "$pidfile" ]; then
        name=$(basename "$pidfile" .pid)
        pid=$(cat "$pidfile")
        pids[$name]=$pid
        
        if check_process "$pid"; then
            services[$name]="${GREEN}RUNNING${NC}"
        else
            services[$name]="${RED}DEAD${NC}"
        fi
        
        cmd=$(get_process_cmd "$pid" 2>/dev/null || echo "???")
        commands[$name]="$cmd"
    fi
done

# Detect ports
for name in "${!pids[@]}"; do
    pid=${pids[$name]}
    if [ -r "/proc/$pid/net/tcp" ]; then
        # Parse /proc/net/tcp to find listening port
        port=$(awk -v p="$pid" '$NF==p {
            split($2, a, ":");
            printf "%d\n", strtonum("0x" a[2])
        }' /proc/net/tcp 2>/dev/null | head -1)
        [ -n "$port" ] && ports[$name]=$port || ports[$name]="???"
    else
        ports[$name]="???"
    fi
done

# Print table
printf "${CYAN}%-20s %-12s %-8s %-40s${NC}\n" "Service" "Status" "Port" "Command"
printf "${CYAN}%-20s %-12s %-8s %-40s${NC}\n" "---" "---" "---" "---"

for name in "${!services[@]}"; do
    status=${services[$name]}
    pid=${pids[$name]}
    port=${ports[$name]:-"???"}
    cmd=${commands[$name]}
    
    printf "%-20s %b %-8s %s\n" "$name" "$status" "$port" "$cmd"
done

echo ""

# Log locations
echo "${CYAN}📁 PID files:${NC}"
echo "   $DEV_PID_DIR"
echo ""
echo "${CYAN}📁 Log files:${NC}"
echo "   $DEV_LOG_DIR"
echo ""

# Tail logs if requested
if [ "$SHOW_LOGS" = true ]; then
    echo "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo "${CYAN}Recent logs (last 10 lines):${NC}"
    echo "${CYAN}════════════════════════════════════════════════════════════${NC}"
    for logfile in "$DEV_LOG_DIR"/*.log; do
        if [ -f "$logfile" ]; then
            echo ""
            echo "${BLUE}📄 $(basename "$logfile"):${NC}"
            tail -10 "$logfile" | sed 's/^/  /'
        fi
    done
fi

echo ""
