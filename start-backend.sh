#!/bin/bash
# Start BRAiN Backend with correct environment configuration
# This script properly handles environment variables for local development

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment from .env (excluding comments and empty lines)
if [ -f "backend/.env" ]; then
    set -a
    source <(grep -v '^#' backend/.env | grep -v '^$' | sed 's/^/export /')
    set +a
fi

# Ensure BRAIN_RUNTIME_MODE is set (critical for local dev)
export BRAIN_RUNTIME_MODE="${BRAIN_RUNTIME_MODE:-local}"

# Ensure LOCAL_LLM_MODE is set to openai for cloud LLM
export LOCAL_LLM_MODE="${LOCAL_LLM_MODE:-openai}"

# Override settings that might cause issues
export BRAIN_STARTUP_PROFILE="${BRAIN_STARTUP_PROFILE:-minimal}"
export BRAIN_EVENTSTREAM_MODE="${BRAIN_EVENTSTREAM_MODE:-degraded}"

# Ensure OpenAI vars are correct
export OPENAI_BASE_URL="https://api.openai.com/v1"

echo "Starting BRAiN Backend..."
echo "  - Runtime Mode: $BRAIN_RUNTIME_MODE"
echo "  - LLM Provider: $LOCAL_LLM_MODE"
echo "  - OpenAI Model: ${OPENAI_MODEL:-gpt-4o-mini}"
echo "  - Redis: $REDIS_URL"
echo "  - Database: $DATABASE_URL"
echo "  - Startup Profile: $BRAIN_STARTUP_PROFILE"
echo "  - EventStream Mode: $BRAIN_EVENTSTREAM_MODE"

# Kill existing process on port 8000 if any
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Stopping existing process on port 8000..."
    lsof -Pi :8000 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
    sleep 2
fi

cd backend
exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000