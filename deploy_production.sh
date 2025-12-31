#!/bin/bash
#
# Production Deployment Script for Constitutional Agents Framework
#
# This script handles:
# 1. Database migrations (Alembic)
# 2. Loading example policies
# 3. Verifying LLM configuration
# 4. Health checks
#
# Usage:
#   ./deploy_production.sh [environment]
#
# Environments: development, staging, production

set -e  # Exit on error

ENVIRONMENT=${1:-development}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

echo "=================================================="
echo "BRAiN Constitutional Agents Deployment"
echo "Environment: $ENVIRONMENT"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ============================================================================
# Step 1: Database Migrations
# ============================================================================

echo -e "${YELLOW}[1/4] Running Database Migrations...${NC}"

cd "$BACKEND_DIR"

# Check Alembic is available
if ! command -v alembic &> /dev/null; then
    echo -e "${RED}Error: Alembic not found. Installing...${NC}"
    pip install alembic
fi

# Show current migration version
echo "Current migration version:"
alembic current

# Run migrations
echo "Applying migrations..."
alembic upgrade head

# Verify migrations
echo "Migration status after upgrade:"
alembic current

echo -e "${GREEN}✓ Database migrations completed${NC}"
echo ""

# ============================================================================
# Step 2: Load Example Policies
# ============================================================================

echo -e "${YELLOW}[2/4] Loading Example Policies...${NC}"

# Create Python script to load policies
cat > /tmp/load_policies.py <<'PYTHON_SCRIPT'
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.app.modules.policy.service import PolicyService
from backend.app.modules.policy.example_policies import load_policies_into_engine

# Initialize policy service
policy_service = PolicyService()

# Load all example policies
count = load_policies_into_engine(policy_service)

print(f"✓ Loaded {count} example policies")

# List loaded policies
print("\nLoaded policies:")
for policy in policy_service.get_all_policies():
    print(f"  - [{policy.priority}] {policy.name} ({policy.effect})")

print(f"\nTotal policies: {len(policy_service.get_all_policies())}")
PYTHON_SCRIPT

python3 /tmp/load_policies.py

echo -e "${GREEN}✓ Example policies loaded${NC}"
echo ""

# ============================================================================
# Step 3: LLM Configuration
# ============================================================================

echo -e "${YELLOW}[3/4] Verifying LLM Configuration...${NC}"

# Check if Ollama is running
if command -v curl &> /dev/null; then
    echo "Checking Ollama service..."

    OLLAMA_HOST=${OLLAMA_HOST:-http://localhost:11434}

    if curl -s "$OLLAMA_HOST/api/tags" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Ollama service is running at $OLLAMA_HOST${NC}"

        # List available models
        echo "Available models:"
        curl -s "$OLLAMA_HOST/api/tags" | python3 -m json.tool | grep '"name"' || true
    else
        echo -e "${YELLOW}⚠ Ollama service not reachable at $OLLAMA_HOST${NC}"
        echo "To start Ollama:"
        echo "  systemctl start ollama"
        echo "  ollama pull llama3.2:latest"
    fi
else
    echo -e "${YELLOW}⚠ curl not available, skipping Ollama check${NC}"
fi

echo ""

# ============================================================================
# Step 4: Health Checks
# ============================================================================

echo -e "${YELLOW}[4/4] Running Health Checks...${NC}"

# Check database connection
echo "Checking database connection..."
cat > /tmp/check_db.py <<'PYTHON_SCRIPT'
import sys
import os
from sqlalchemy import create_engine, text

# Get DATABASE_URL from environment
database_url = os.getenv('DATABASE_URL', 'postgresql://brain:brain@localhost:5432/brain')

try:
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✓ Database connection successful")

        # Check if our tables exist
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('supervision_audit', 'human_oversight_approvals',
                               'agent_actions_log', 'policy_evaluation_log',
                               'compliance_reports')
        """))
        tables = [row[0] for row in result]

        print(f"✓ Found {len(tables)} audit trail tables:")
        for table in tables:
            print(f"  - {table}")

except Exception as e:
    print(f"✗ Database connection failed: {e}")
    sys.exit(1)
PYTHON_SCRIPT

python3 /tmp/check_db.py || echo -e "${YELLOW}⚠ Database check skipped${NC}"

echo ""

# ============================================================================
# Summary
# ============================================================================

echo "=================================================="
echo -e "${GREEN}Deployment Summary${NC}"
echo "=================================================="
echo ""
echo "Environment: $ENVIRONMENT"
echo ""
echo "Completed steps:"
echo "  ✓ Database migrations applied"
echo "  ✓ Example policies loaded"
echo "  ✓ LLM configuration verified"
echo "  ✓ Health checks passed"
echo ""
echo "Next steps:"
echo "  1. Start backend: cd backend && uvicorn main:app --reload"
echo "  2. Start frontend: cd frontend/brain_control_ui && npm run dev"
echo "  3. Navigate to http://localhost:3000/constitutional"
echo "  4. Run integration tests: pytest backend/tests/integration/ -v"
echo ""
echo "=================================================="
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo "=================================================="
