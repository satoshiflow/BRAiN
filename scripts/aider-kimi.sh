#!/usr/bin/env bash
#
# Aider + Moonshot Kimi Launcher
# Loads .env files and configures Aider to use Kimi API via OpenAI-compatible endpoint
#

set -euo pipefail

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Find project root (where this script's parent dir is)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${GREEN}🚀 Aider + Moonshot Kimi Launcher${NC}"
echo "Project root: $PROJECT_ROOT"
echo ""

# Load .env files (root and backend)
ENV_FILES=("$PROJECT_ROOT/.env" "$PROJECT_ROOT/backend/.env")

for env_file in "${ENV_FILES[@]}"; do
    if [ -f "$env_file" ]; then
        echo -e "${GREEN}✓${NC} Loading: $env_file"
        # Export all variables from .env (ignoring comments and empty lines)
        set -a
        source "$env_file" 2>/dev/null || true
        set +a
    else
        echo -e "${YELLOW}⚠${NC}  Not found: $env_file (skipping)"
    fi
done

echo ""

# Check for Moonshot API key
if [ -z "${MOONSHOT_API_KEY:-}" ]; then
    echo -e "${RED}❌ ERROR: MOONSHOT_API_KEY not found in .env files${NC}"
    echo ""
    echo "Please add your Moonshot API key to one of:"
    echo "  - $PROJECT_ROOT/.env"
    echo "  - $PROJECT_ROOT/backend/.env"
    echo ""
    echo "Example:"
    echo "  MOONSHOT_API_KEY=sk-xxxxxxxxxxxxx"
    echo ""
    exit 1
fi

# Configure OpenAI-compatible environment for Moonshot
export OPENAI_API_KEY="$MOONSHOT_API_KEY"
export OPENAI_API_BASE="https://api.moonshot.ai/v1"
export OPENAI_BASE_URL="https://api.moonshot.ai/v1"

# Default model (can be overridden by passing argument like openai/model-name)
# Only treat first arg as model if it starts with a provider prefix
# Note: Moonshot API models are named moonshot-v1-* not kimi-*
MODEL="openai/moonshot-v1-8k"
if [ $# -gt 0 ] && [[ "$1" =~ ^[a-z]+/ ]] && [[ "$1" != /* ]]; then
    MODEL="$1"
    shift
fi

echo -e "${GREEN}✓${NC} MOONSHOT_API_KEY loaded (${#MOONSHOT_API_KEY} chars)"
echo -e "${GREEN}✓${NC} OPENAI_API_BASE=$OPENAI_API_BASE"
echo -e "${GREEN}✓${NC} Model: $MODEL"
echo ""

# Check if aider is installed
if ! command -v aider &> /dev/null; then
    echo -e "${RED}❌ ERROR: aider not found in PATH${NC}"
    echo ""
    echo "Install with:"
    echo "  pip install aider-chat"
    echo "  # or"
    echo "  pipx install aider-chat"
    echo ""
    exit 1
fi

echo -e "${GREEN}Starting aider...${NC}"
echo "─────────────────────────────────────────────────────────────"
echo ""

# Run aider with the configured model
# Pass through any additional arguments ($@)
cd "$PROJECT_ROOT"
exec aider --model "$MODEL" "$@"
