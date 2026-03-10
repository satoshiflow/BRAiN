#!/bin/bash
################################################################################
# dev-up.sh - Safe BRAiN dev startup with PID tracking
#
# Starts backend + 3 frontends with proper PID tracking and logging.
# Tracks PIDs in .brain/dev-pids/ and logs in .brain/dev-logs/
#
# Usage:
#   ./scripts/dev-up.sh --all              # Start all services
#   ./scripts/dev-up.sh --only backend     # Start only backend
#   ./scripts/dev-up.sh --foreground       # Run in foreground (no nohup)
#
# Cleanup:
#   ./scripts/dev-down.sh
#
################################################################################

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_ROOT="$(dirname "$SCRIPT_DIR")"

# Directories
DEV_PID_DIR="$BRAIN_ROOT/.brain/dev-pids"
DEV_LOG_DIR="$BRAIN_ROOT/.brain/dev-logs"
WORK_DIR="$BRAIN_ROOT"

# Ports
PORT_BACKEND=8001
PORT_CONTROLDECK=3456
PORT_AXE_UI=3002

# Services to start (can be filtered by --only)
START_BACKEND=true
START_CONTROLDECK=true
START_AXE_UI=true
RUN_FOREGROUND=false

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
        --all)
            START_BACKEND=true
            START_CONTROLDECK=true
            START_AXE_UI=true
            shift
            ;;
        --only)
            START_BACKEND=false
            START_CONTROLDECK=false
            START_AXE_UI=false
            case "$2" in
                backend) START_BACKEND=true ;;
                controldeck|frontend1) START_CONTROLDECK=true ;;
                axe_ui|frontend2) START_AXE_UI=true ;;
                *) echo "Unknown service: $2"; exit 1 ;;
            esac
            shift 2
            ;;
        --foreground)
            RUN_FOREGROUND=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ============================================================================
# SETUP
# ============================================================================

# Create directories
mkdir -p "$DEV_PID_DIR" "$DEV_LOG_DIR"

# Log function
log_info() {
    local msg="$1"
    echo -e "${BLUE}ℹ${NC} $msg"
}

log_success() {
    local msg="$1"
    echo -e "${GREEN}✓${NC} $msg"
}

log_error() {
    local msg="$1"
    echo -e "${RED}✗${NC} $msg"
}

# Port check
log_info "Checking required ports..."
if ! "$SCRIPT_DIR/check-ports.sh" --ports "$PORT_BACKEND,$PORT_CONTROLDECK,$PORT_AXE_UI"; then
    log_error "Port check failed. Cannot start services."
    exit 1
fi
echo ""

# ============================================================================
# START SERVICES
# ============================================================================

start_service() {
    local name=$1
    local port=$2
    local cmd=$3
    local cwd=$4
    local pidfile="$DEV_PID_DIR/$name.pid"
    local logfile="$DEV_LOG_DIR/$name.log"
    
    log_info "Starting $name (port $port)..."
    
    cd "$cwd"
    
    if [ "$RUN_FOREGROUND" = true ]; then
        # Run in foreground (useful for debugging)
        log_info "Running in foreground: $cmd"
        eval "$cmd"
        echo $! > "$pidfile"
    else
        # Run in background with nohup
        nohup bash -c "$cmd" > "$logfile" 2>&1 &
        local pid=$!
        echo $pid > "$pidfile"
        
        # Give it a moment to start, then verify it's running
        sleep 1
        if ! kill -0 $pid 2>/dev/null; then
            log_error "Failed to start $name (PID $pid died immediately)"
            echo "Last 10 lines of log:"
            tail -10 "$logfile"
            exit 1
        fi
    fi
    
    log_success "$name running (PID: $(cat $pidfile))"
    log_info "  Logs: $logfile"
}

# Backend
if [ "$START_BACKEND" = true ]; then
    start_service "backend" "$PORT_BACKEND" \
        "uvicorn main:app --host 127.0.0.1 --port $PORT_BACKEND" \
        "$BRAIN_ROOT/backend"
    echo ""
fi

# ControlDeck
if [ "$START_CONTROLDECK" = true ]; then
    start_service "controldeck-v2" "$PORT_CONTROLDECK" \
        "PORT=$PORT_CONTROLDECK npm run dev" \
        "$BRAIN_ROOT/frontend/controldeck-v2"
    echo ""
fi

# AXE_UI
if [ "$START_AXE_UI" = true ]; then
    start_service "axe_ui" "$PORT_AXE_UI" \
        "PORT=$PORT_AXE_UI npm run dev" \
        "$BRAIN_ROOT/frontend/axe_ui"
    echo ""
fi

# ============================================================================
# SUMMARY
# ============================================================================

echo "${GREEN}=================================${NC}"
echo "${GREEN}✅ BRAiN Services Started${NC}"
echo "${GREEN}=================================${NC}"
echo ""
echo "🔗 URLs:"
if [ "$START_BACKEND" = true ]; then
    echo "   Backend API:  http://127.0.0.1:$PORT_BACKEND/api/health"
fi
if [ "$START_CONTROLDECK" = true ]; then
    echo "   ControlDeck:  http://localhost:$PORT_CONTROLDECK"
fi
if [ "$START_AXE_UI" = true ]; then
    echo "   AXE_UI:       http://localhost:$PORT_AXE_UI"
fi
echo ""

echo "📊 Logs:"
if [ -d "$DEV_LOG_DIR" ]; then
    for logfile in "$DEV_LOG_DIR"/*.log; do
        if [ -f "$logfile" ]; then
            echo "   $(basename "$logfile"): tail -f $logfile"
        fi
    done
fi
echo ""

echo "🛑 To stop all services:"
echo "   ./scripts/dev-down.sh"
echo ""

echo "📁 PID files: $DEV_PID_DIR"
echo "📁 Log files: $DEV_LOG_DIR"
