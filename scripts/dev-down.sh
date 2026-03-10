#!/bin/bash
################################################################################
# dev-down.sh - Safe BRAiN dev shutdown
#
# Stops all services started by dev-up.sh.
# Sends TERM, waits, then KILL if needed.
# Cleans up PID files.
#
# Usage:
#   ./scripts/dev-down.sh        # Stop all services
#   ./scripts/dev-down.sh --kill # Force kill immediately
#   ./scripts/dev-down.sh --verbose  # Show all actions
#
################################################################################

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_ROOT="$(dirname "$SCRIPT_DIR")"

DEV_PID_DIR="$BRAIN_ROOT/.brain/dev-pids"

# Options
FORCE_KILL=false
VERBOSE=false
TERM_TIMEOUT=5  # seconds to wait for TERM before KILL

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# PARSE ARGUMENTS
# ============================================================================

while [[ $# -gt 0 ]]; do
    case "$1" in
        --kill)
            FORCE_KILL=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
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

log_info() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}ℹ${NC} $1"
    fi
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Stop a service gracefully
stop_service() {
    local name=$1
    local pidfile="$DEV_PID_DIR/$name.pid"
    
    if [ ! -f "$pidfile" ]; then
        log_info "No PID file for $name (not running?)"
        return 0
    fi
    
    local pid=$(cat "$pidfile")
    
    # Check if process exists
    if ! kill -0 "$pid" 2>/dev/null; then
        log_info "Process $name (PID $pid) not running, removing stale PID file"
        rm -f "$pidfile"
        return 0
    fi
    
    log_info "Stopping $name (PID $pid)..."
    
    if [ "$FORCE_KILL" = true ]; then
        log_info "  Sending KILL (force mode)"
        kill -9 "$pid" 2>/dev/null || true
    else
        log_info "  Sending TERM signal"
        kill -TERM "$pid" 2>/dev/null || true
        
        # Wait for process to die
        local waited=0
        while kill -0 "$pid" 2>/dev/null && [ $waited -lt $TERM_TIMEOUT ]; do
            sleep 0.5
            ((waited += 1))
        done
        
        # If still alive, use KILL
        if kill -0 "$pid" 2>/dev/null; then
            log_info "  Process didn't die after ${TERM_TIMEOUT}s, sending KILL"
            kill -9 "$pid" 2>/dev/null || true
            sleep 1
        fi
    fi
    
    # Verify it's dead
    if kill -0 "$pid" 2>/dev/null; then
        log_error "Failed to kill $name (PID $pid) - may be zombie"
        return 1
    fi
    
    log_success "$name stopped (PID $pid)"
    rm -f "$pidfile"
    return 0
}

# ============================================================================
# MAIN
# ============================================================================

if [ ! -d "$DEV_PID_DIR" ]; then
    log_info "No dev services running (PID dir doesn't exist)"
    exit 0
fi

echo "🛑 Stopping BRAiN services..."
echo ""

# Get all PID files
pidfiles=($(ls "$DEV_PID_DIR"/*.pid 2>/dev/null || echo ""))

if [ ${#pidfiles[@]} -eq 0 ]; then
    log_info "No running services found"
    exit 0
fi

# Stop each service
failures=0
for pidfile in "${pidfiles[@]}"; do
    service_name=$(basename "$pidfile" .pid)
    stop_service "$service_name" || ((failures++))
done

echo ""

# Verify ports are released
log_info "Verifying ports are released..."
if "$SCRIPT_DIR/check-ports.sh" --allow-in-use > /dev/null 2>&1; then
    log_success "All ports are now available"
else
    log_error "Some ports may still be in use - check with: lsof -i -P"
fi

echo ""
if [ $failures -eq 0 ]; then
    log_success "All services stopped successfully"
    exit 0
else
    log_error "$failures service(s) failed to stop"
    exit 1
fi
