#!/usr/bin/env bash
# BRAiN Local Stack E2E Smoke Test
# Validates that Backend + Frontend are running and can communicate

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:3002}"
TIMEOUT=10

echo "🧪 BRAiN E2E Smoke Test"
echo "======================="
echo "Backend:  $BACKEND_URL"
echo "Frontend: $FRONTEND_URL"
echo ""

if [[ -x "$ROOT/scripts/wait_for_backend_ready.sh" ]]; then
  "$ROOT/scripts/wait_for_backend_ready.sh"
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILED=0

# Helper: check URL with timeout
check_url() {
    local url=$1
    local name=$2
    local expected_status=${3:-200}
    
    echo -n "  Checking $name... "
    
    if command -v curl &> /dev/null; then
        response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$url" 2>/dev/null || echo "000")
        
        if [ "$response" = "$expected_status" ]; then
            echo -e "${GREEN}✓${NC} ($response)"
            return 0
        else
            echo -e "${RED}✗${NC} (got $response, expected $expected_status)"
            return 1
        fi
    else
        echo -e "${YELLOW}⊘${NC} (curl not available)"
        return 2
    fi
}

# Helper: check JSON response contains key
check_json_key() {
    local url=$1
    local name=$2
    local key=$3
    
    echo -n "  Checking $name... "
    
    if command -v curl &> /dev/null && command -v jq &> /dev/null; then
        response=$(curl -s --max-time $TIMEOUT "$url" 2>/dev/null || echo "{}")
        
        if echo "$response" | jq -e ".$key" > /dev/null 2>&1; then
            value=$(echo "$response" | jq -r ".$key")
            echo -e "${GREEN}✓${NC} ($key=$value)"
            return 0
        else
            echo -e "${RED}✗${NC} (key '$key' not found in response)"
            echo "  Response: $response"
            return 1
        fi
    else
        echo -e "${YELLOW}⊘${NC} (jq not available, skipping)"
        return 2
    fi
}

# Test 1: Backend Health
echo "1️⃣  Backend Health Endpoint"
if ! check_url "$BACKEND_URL/api/health" "Backend /api/health"; then
    FAILED=$((FAILED + 1))
fi

if ! check_json_key "$BACKEND_URL/api/health" "Backend health status" "status"; then
    FAILED=$((FAILED + 1))
fi

echo ""

# Test 2: Backend API Docs
echo "2️⃣  Backend API Documentation"
if ! check_url "$BACKEND_URL/docs" "Backend /docs" "200"; then
    FAILED=$((FAILED + 1))
fi

echo ""

# Test 3: Frontend Reachable
echo "3️⃣  Frontend Reachability"
if ! check_url "$FRONTEND_URL" "Frontend root"; then
    FAILED=$((FAILED + 1))
fi

# Check if we can reach a specific frontend route
if ! check_url "$FRONTEND_URL/chat" "Frontend /chat"; then
    FAILED=$((FAILED + 1))
fi

echo ""

# Test 4: CORS Preflight (Backend accepts Frontend origin)
echo "4️⃣  CORS Configuration"
echo -n "  Checking CORS headers... "

if command -v curl &> /dev/null; then
    cors_response=$(curl -s -o /dev/null -w "%{http_code}" \
        -X OPTIONS \
        -H "Origin: $FRONTEND_URL" \
        -H "Access-Control-Request-Method: GET" \
        --max-time $TIMEOUT \
        "$BACKEND_URL/api/health" 2>/dev/null || echo "000")
    
    # OPTIONS should return 200 or 204
    if [ "$cors_response" = "200" ] || [ "$cors_response" = "204" ]; then
        echo -e "${GREEN}✓${NC} (CORS preflight passed)"
    else
        echo -e "${YELLOW}⚠${NC}  (got $cors_response, may indicate CORS issue)"
        # Not failing the gate, just warning
    fi
else
    echo -e "${YELLOW}⊘${NC} (curl not available)"
fi

echo ""

# Test 5: WebSocket Path (best-effort probe only)
echo "5️⃣  WebSocket Endpoint"
echo -n "  Checking WebSocket path... "

# Plain HTTP probing of WebSocket routes is unreliable across frameworks and
# can legitimately return 404 even when the WS route is healthy.
ws_test_url="${BACKEND_URL}/api/axe/ws/test-session"
ws_response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$ws_test_url" 2>/dev/null || echo "000")

if [ "$ws_response" = "426" ] || [ "$ws_response" = "400" ]; then
    echo -e "${GREEN}✓${NC} (WebSocket endpoint exists)"
elif [ "$ws_response" = "404" ]; then
    echo -e "${YELLOW}⚠${NC}  (HTTP probe returned 404; route may still require a real WS handshake)"
else
    echo -e "${YELLOW}⚠${NC}  (got $ws_response, unexpected but may be ok)"
fi

echo ""

# Summary
echo "======================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ PASSED${NC}: All smoke tests successful"
    echo ""
    echo "Local stack is ready for development."
    exit 0
else
    echo -e "${RED}❌ FAILED${NC}: $FAILED test(s) failed"
    echo ""
    echo "Check that both backend and frontend are running:"
    echo "  Backend:  cd backend && uvicorn main:app --reload --host 127.0.0.1 --port 8000"
    echo "  Frontend: cd frontend/axe_ui && npm run dev"
    exit 1
fi
