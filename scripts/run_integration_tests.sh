#!/bin/bash
#
# Run Integration Tests for Constitutional Agents
#
# This script runs all integration and E2E tests with coverage reporting.
#
# Usage:
#   ./scripts/run_integration_tests.sh [options]
#
# Options:
#   --with-llm      Run tests with real LLM (requires Ollama)
#   --coverage      Generate coverage report
#   --verbose       Verbose output
#   --quick         Run only fast tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

# Parse arguments
WITH_LLM=false
WITH_COVERAGE=false
VERBOSE=false
QUICK=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --with-llm)
            WITH_LLM=true
            shift
            ;;
        --coverage)
            WITH_COVERAGE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --quick)
            QUICK=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "============================================================"
echo -e "${BLUE}BRAiN Constitutional Agents - Integration Tests${NC}"
echo "============================================================"
echo ""

cd "$BACKEND_DIR"

# Check pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}Installing pytest...${NC}"
    pip install pytest pytest-asyncio pytest-cov
fi

# Build pytest command
PYTEST_CMD="pytest tests/integration/"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v -s"
else
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$WITH_COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=backend.brain.agents --cov=backend.app.api.routes.agent_ops --cov=backend.app.modules.policy --cov-report=html --cov-report=term"
fi

if [ "$QUICK" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -k 'not performance'"
fi

# Set environment variables
if [ "$WITH_LLM" = true ]; then
    echo -e "${YELLOW}Running tests with REAL LLM${NC}"
    echo "⚠ Requires Ollama running at http://localhost:11434"
    echo ""
    export REAL_LLM=true
else
    echo -e "${YELLOW}Running tests with MOCKED LLM${NC}"
    echo ""
fi

# Run tests
echo -e "${BLUE}Running integration tests...${NC}"
echo ""
echo "Command: $PYTEST_CMD"
echo ""

$PYTEST_CMD

# Summary
echo ""
echo "============================================================"
echo -e "${GREEN}Integration Tests Completed${NC}"
echo "============================================================"
echo ""

if [ "$WITH_COVERAGE" = true ]; then
    echo "Coverage report generated:"
    echo "  HTML: file://$(pwd)/htmlcov/index.html"
    echo "  Terminal: See output above"
    echo ""
fi

# Check if tests passed
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
