#!/bin/bash
# Start full BRAiN stack: Backend + AXE UI + ControlDeck + OpenWebUI
# Usage: ./start-stack.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  BRAiN Full Stack Starter"
echo "=========================================="
echo ""

# Check if required services are running
check_service() {
    local name=$1
    local check_fn=$2
    echo -n "Checking $name... "
    if eval "$check_fn" >/dev/null 2>&1; then
        echo "✓ running"
        return 0
    else
        echo "✗ not running"
        return 1
    fi
}

# Function to check if port is in use
check_port() {
    local port=$1
    lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1
}

# Function to check if docker container is running
check_docker() {
    docker ps --format '{{.Names}}' | grep -q "^$1$"
}

echo "Step 1: Checking infrastructure services..."

# Check Docker services
check_docker "brain-dev-redis" || echo "  ⚠️ Redis not running (start with: docker compose up -d redis)"
check_docker "brain-dev-postgres" || echo "  ⚠️ Postgres not running (start with: docker compose up -d postgres)"
check_docker "brain-dev-qdrant" || echo "  ⚠️ Qdrant not running (start with: docker compose up -d qdrant)"

# Check OpenWebUI
if check_docker "openwebui"; then
    echo "  ✓ OpenWebUI running on http://localhost:3000"
else
    echo "  ⚠️ OpenWebUI not running (start with: docker start openwebui)"
fi

echo ""
echo "Step 2: Starting Backend..."

# Kill existing processes on ports
for port in 8000 3001 3002; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "  Stopping existing process on port $port..."
        lsof -Pi :$port -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
    fi
done
sleep 2

# Start backend with clean environment
(
    cd "$SCRIPT_DIR/backend"
    
    # Load env but unset problematic vars
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | grep -v '^$' | xargs)
    fi
    unset OPENAI_BASE_URL
    
    export REDIS_URL="${REDIS_URL:-redis://localhost:6380/0}"
    export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://brain:brain_dev_pass@localhost:5433/brain_dev}"
    export BRAIN_RUNTIME_MODE="${BRAIN_RUNTIME_MODE:-local}"
    export AXE_FUSION_ALLOW_LOCAL_REQUESTS="true"
    export AXE_FUSION_ALLOW_LOCAL_FALLBACK="true"
    export LOCAL_LLM_MODE="${LOCAL_LLM_MODE:-openai}"
    
    echo "  Backend starting on http://localhost:8000"
    echo "  LLM Provider: $LOCAL_LLM_MODE"
    exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
) > /tmp/brain-backend.log 2>&1 &

BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# Wait for backend to be ready
echo "  Waiting for backend..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health >/dev/null 2>&1; then
        echo "  ✓ Backend ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "  ✗ Backend failed to start"
        tail -20 /tmp/brain-backend.log
        exit 1
    fi
    sleep 1
done

echo ""
echo "Step 3: Starting Frontends..."

# Start AXE UI (port 3002)
(
    cd "$SCRIPT_DIR/frontend/axe_ui"
    export PORT=3002
    export NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8000
    echo "  AXE UI starting on http://localhost:3002"
    exec npm run dev
) > /tmp/axe_ui.log 2>&1 &
AXE_UI_PID=$!
echo "  AXE UI PID: $AXE_UI_PID"

# Start ControlDeck (port 3001)
(
    cd "$SCRIPT_DIR/frontend/control_deck"
    export PORT=3001
    export NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8000
    echo "  ControlDeck starting on http://localhost:3001"
    exec npm run dev
) > /tmp/control_deck.log 2>&1 &
CONTROL_DECK_PID=$!
echo "  ControlDeck PID: $CONTROL_DECK_PID"

# Wait for frontends
echo ""
echo "Waiting for frontends..."
sleep 10

# Check if frontends are running
if curl -s http://localhost:3002/api/health >/dev/null 2>&1 || curl -s http://localhost:3002 >/dev/null 2>&1; then
    echo "  ✓ AXE UI ready at http://localhost:3002"
else
    echo "  ⚠️ AXE UI may need more time to start"
fi

if curl -s http://localhost:3001/api/health >/dev/null 2>&1 || curl -s http://localhost:3001 >/dev/null 2>&1; then
    echo "  ✓ ControlDeck ready at http://localhost:3001"
else
    echo "  ⚠️ ControlDeck may need more time to start"
fi

echo ""
echo "=========================================="
echo "  BRAiN Stack Started"
echo "=========================================="
echo ""
echo "Services:"
echo "  - Backend API:    http://localhost:8000"
echo "  - Health Check:   http://localhost:8000/api/health"
echo "  - AXE UI:         http://localhost:3002"
echo "  - ControlDeck:    http://localhost:3001"
echo "  - OpenWebUI:      http://localhost:3000"
echo ""
echo "Logs:"
echo "  - Backend:  tail -f /tmp/brain-backend.log"
echo "  - AXE UI:   tail -f /tmp/axe_ui.log"
echo "  - ControlDeck: tail -f /tmp/control_deck.log"
echo ""
echo "To stop: pkill -f 'uvicorn main:app' && pkill -f 'npm run dev'"
echo ""

# Keep script running
wait