#!/bin/bash
# Security Features Test Script
# Tests: Security Headers, Rate Limiting, Password Environment Variables

echo "=========================================="
echo "🔒 BRAiN Security Features Test"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Security Headers
echo "📋 Test 1: Security Headers (OWASP)"
echo "------------------------------------------"
HEADERS=$(curl -sI http://localhost:8000/api/health)

check_header() {
    local header=$1
    local name=$2
    if echo "$HEADERS" | grep -qi "^$header:"; then
        echo -e "${GREEN}✅${NC} $name: $(echo "$HEADERS" | grep -i "^$header:" | cut -d' ' -f2-)"
    else
        echo -e "${RED}❌${NC} $name: Missing"
    fi
}

check_header "X-Content-Type-Options" "X-Content-Type-Options"
check_header "X-Frame-Options" "X-Frame-Options"
check_header "X-XSS-Protection" "X-XSS-Protection"
check_header "Referrer-Policy" "Referrer-Policy"
check_header "Permissions-Policy" "Permissions-Policy"

# Check HSTS (only in production)
ENV=$(grep "^ENVIRONMENT=" /srv/dev/.env 2>/dev/null | cut -d'=' -f2)
if [ "$ENV" = "production" ]; then
    check_header "Strict-Transport-Security" "HSTS (Production)"
else
    echo -e "${YELLOW}⚠️${NC}  HSTS: Skipped (only enabled in production)"
fi

echo ""

# Test 2: Rate Limiting
echo "📊 Test 2: Rate Limiting (Login endpoint)"
echo "------------------------------------------"
echo "Testing 6 rapid login attempts (limit: 5/minute)..."

SUCCESS=0
RATE_LIMITED=0

for i in {1..6}; do
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/auth/login \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=test&password=wrong" 2>&1)

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "429" ]; then
        RATE_LIMITED=1
        echo -e "  Attempt $i: ${GREEN}✅ RATE LIMITED (HTTP 429)${NC}"
        break
    elif [ "$HTTP_CODE" = "401" ]; then
        SUCCESS=$((SUCCESS + 1))
        echo -e "  Attempt $i: ${YELLOW}⚠️  Allowed (HTTP 401 - Invalid credentials)${NC}"
    else
        echo -e "  Attempt $i: HTTP $HTTP_CODE"
    fi

    sleep 0.1  # Small delay between requests
done

if [ $RATE_LIMITED -eq 1 ]; then
    echo -e "${GREEN}✅ Rate Limiting WORKS${NC} - Blocked after $SUCCESS attempts"
else
    echo -e "${RED}❌ Rate Limiting FAILED${NC} - All 6 attempts went through"
fi

echo ""

# Test 3: Environment Variable Passwords
echo "🔑 Test 3: Password Environment Variables"
echo "------------------------------------------"

check_env_var() {
    local var=$1
    if grep -q "^${var}=" /srv/dev/.env 2>/dev/null; then
        local value=$(grep "^${var}=" /srv/dev/.env | cut -d'=' -f2)
        if [ "$value" = "password" ]; then
            echo -e "${RED}❌${NC} $var: ${RED}INSECURE (using default 'password')${NC}"
        elif [ -n "$value" ]; then
            echo -e "${GREEN}✅${NC} $var: Set (secure)"
        else
            echo -e "${YELLOW}⚠️${NC}  $var: Empty"
        fi
    else
        echo -e "${YELLOW}⚠️${NC}  $var: Not set (using default 'password')"
    fi
}

check_env_var "BRAIN_ADMIN_PASSWORD"
check_env_var "BRAIN_OPERATOR_PASSWORD"
check_env_var "BRAIN_VIEWER_PASSWORD"

echo ""

# Test 4: CORS Configuration
echo "🌐 Test 4: CORS Configuration"
echo "------------------------------------------"
echo "Checking CORS origins in .env..."

if grep -q "^CORS_ORIGINS=" /srv/dev/.env 2>/dev/null; then
    CORS=$(grep "^CORS_ORIGINS=" /srv/dev/.env | cut -d'=' -f2-)

    if echo "$CORS" | grep -q '"*"'; then
        echo -e "${RED}❌ CORS Wildcard FOUND${NC} - Security risk!"
    else
        echo -e "${GREEN}✅ CORS Wildcard REMOVED${NC}"

        # Check if Traefik IP is included
        if echo "$CORS" | grep -q "10.0.39.7:8000"; then
            echo -e "${GREEN}✅ Traefik Internal IP INCLUDED${NC} (10.0.39.7:8000)"
        else
            echo -e "${YELLOW}⚠️  Traefik Internal IP MISSING${NC} (health checks may fail)"
        fi
    fi

    # Show CORS origins
    echo ""
    echo "Current CORS origins:"
    echo "$CORS" | tr ',' '\n' | sed 's/\[//g; s/\]//g; s/"//g' | sed 's/^/  - /'
else
    echo -e "${YELLOW}⚠️${NC}  CORS_ORIGINS not found in .env"
fi

echo ""

# Summary
echo "=========================================="
echo "📊 Test Summary"
echo "=========================================="

TOTAL=10  # Approximate count
PASSED=0

# Count passed tests (simplified)
echo "$HEADERS" | grep -qi "X-Content-Type-Options" && PASSED=$((PASSED + 1))
echo "$HEADERS" | grep -qi "X-Frame-Options" && PASSED=$((PASSED + 1))
echo "$HEADERS" | grep -qi "X-XSS-Protection" && PASSED=$((PASSED + 1))
echo "$HEADERS" | grep -qi "Referrer-Policy" && PASSED=$((PASSED + 1))
echo "$HEADERS" | grep -qi "Permissions-Policy" && PASSED=$((PASSED + 1))

[ $RATE_LIMITED -eq 1 ] && PASSED=$((PASSED + 1))

grep -q "^BRAIN_ADMIN_PASSWORD=" /srv/dev/.env 2>/dev/null && \
    [ "$(grep "^BRAIN_ADMIN_PASSWORD=" /srv/dev/.env | cut -d'=' -f2)" != "password" ] && \
    PASSED=$((PASSED + 1))

grep -q "^CORS_ORIGINS=" /srv/dev/.env 2>/dev/null && \
    ! echo "$(grep "^CORS_ORIGINS=" /srv/dev/.env)" | grep -q '"*"' && \
    PASSED=$((PASSED + 1))

echo "Total Tests: $TOTAL"
echo "Passed: $PASSED"
echo "Failed: $((TOTAL - PASSED))"
echo ""

if [ $PASSED -ge 8 ]; then
    echo -e "${GREEN}✅ Security features are working well!${NC}"
else
    echo -e "${YELLOW}⚠️  Some security features need attention${NC}"
fi

echo ""
