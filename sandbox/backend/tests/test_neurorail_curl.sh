#!/bin/bash
# NeuroRail E2E Test Script (curl-based)
# Quick smoke test for NeuroRail API integration

set -e  # Exit on error

BASE_URL="${BASE_URL:-http://localhost:8000}"
BOLD="\033[1m"
GREEN="\033[0;32m"
RED="\033[0;31m"
RESET="\033[0m"

echo "========================================="
echo "NeuroRail E2E Test (curl)"
echo "========================================="
echo "Base URL: $BASE_URL"
echo ""

# Helper function to test endpoint
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"

    echo -n "Testing: $name ... "

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓ OK${RESET} (HTTP $http_code)"
        return 0
    else
        echo -e "${RED}✗ FAILED${RESET} (HTTP $http_code)"
        echo "Response: $body"
        return 1
    fi
}

# Test 1: Health Check
echo "--- Test 1: Health Check ---"
test_endpoint "Global health" "GET" "/api/health" ""
echo ""

# Test 2: Route Discovery
echo "--- Test 2: Route Discovery ---"
echo -n "Checking NeuroRail routes ... "
routes=$(curl -s "$BASE_URL/debug/routes" | grep -o "neurorail" | wc -l)
if [ "$routes" -gt 0 ]; then
    echo -e "${GREEN}✓ Found $routes NeuroRail routes${RESET}"
else
    echo -e "${RED}✗ No NeuroRail routes found${RESET}"
    exit 1
fi
echo ""

# Test 3: Create Mission Identity
echo "--- Test 3: Create Mission Identity ---"
mission_response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{"tags": {"test": "curl"}}' \
    "$BASE_URL/api/neurorail/v1/identity/mission")

mission_id=$(echo "$mission_response" | grep -o '"mission_id":"[^"]*' | cut -d'"' -f4)

if [ -n "$mission_id" ]; then
    echo -e "${GREEN}✓ Mission created: $mission_id${RESET}"
else
    echo -e "${RED}✗ Failed to create mission${RESET}"
    echo "Response: $mission_response"
    exit 1
fi
echo ""

# Test 4: Create Plan Identity
echo "--- Test 4: Create Plan Identity ---"
plan_response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "{\"mission_id\": \"$mission_id\", \"plan_type\": \"sequential\"}" \
    "$BASE_URL/api/neurorail/v1/identity/plan")

plan_id=$(echo "$plan_response" | grep -o '"plan_id":"[^"]*' | cut -d'"' -f4)

if [ -n "$plan_id" ]; then
    echo -e "${GREEN}✓ Plan created: $plan_id${RESET}"
else
    echo -e "${RED}✗ Failed to create plan${RESET}"
    exit 1
fi
echo ""

# Test 5: Create Job Identity
echo "--- Test 5: Create Job Identity ---"
job_response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "{\"plan_id\": \"$plan_id\", \"job_type\": \"llm_call\"}" \
    "$BASE_URL/api/neurorail/v1/identity/job")

job_id=$(echo "$job_response" | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)

if [ -n "$job_id" ]; then
    echo -e "${GREEN}✓ Job created: $job_id${RESET}"
else
    echo -e "${RED}✗ Failed to create job${RESET}"
    exit 1
fi
echo ""

# Test 6: Create Attempt Identity
echo "--- Test 6: Create Attempt Identity ---"
attempt_response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "{\"job_id\": \"$job_id\", \"attempt_number\": 1}" \
    "$BASE_URL/api/neurorail/v1/identity/attempt")

attempt_id=$(echo "$attempt_response" | grep -o '"attempt_id":"[^"]*' | cut -d'"' -f4)

if [ -n "$attempt_id" ]; then
    echo -e "${GREEN}✓ Attempt created: $attempt_id${RESET}"
else
    echo -e "${RED}✗ Failed to create attempt${RESET}"
    exit 1
fi
echo ""

# Test 7: Retrieve Trace Chain
echo "--- Test 7: Retrieve Trace Chain ---"
test_endpoint "Trace chain" "GET" "/api/neurorail/v1/identity/trace/attempt/$attempt_id" ""
echo ""

# Test 8: State Transitions
echo "--- Test 8: State Transitions ---"
test_endpoint "Transition to RUNNING" "POST" "/api/neurorail/v1/lifecycle/transition/attempt" \
    "{\"entity_id\": \"$attempt_id\", \"transition\": \"start\", \"metadata\": {}}"

test_endpoint "Transition to SUCCEEDED" "POST" "/api/neurorail/v1/lifecycle/transition/attempt" \
    "{\"entity_id\": \"$attempt_id\", \"transition\": \"complete\", \"metadata\": {\"duration_ms\": 100}}"
echo ""

# Test 9: Audit Logging
echo "--- Test 9: Audit Logging ---"
test_endpoint "Log audit event" "POST" "/api/neurorail/v1/audit/log" \
    "{\"mission_id\": \"$mission_id\", \"attempt_id\": \"$attempt_id\", \"event_type\": \"test\", \"event_category\": \"execution\", \"severity\": \"info\", \"message\": \"Test event\"}"

test_endpoint "Query audit events" "GET" "/api/neurorail/v1/audit/events?mission_id=$mission_id&limit=10" ""
echo ""

# Test 10: Governor Mode Decision
echo "--- Test 10: Governor Mode Decision ---"
test_endpoint "LLM call (should be RAIL)" "POST" "/api/governor/v1/decide" \
    "{\"job_type\": \"llm_call\", \"context\": {}, \"shadow_evaluate\": false}"

test_endpoint "Low-risk operation (should be DIRECT)" "POST" "/api/governor/v1/decide" \
    "{\"job_type\": \"read_config\", \"context\": {}, \"shadow_evaluate\": false}"
echo ""

# Test 11: Telemetry Snapshot
echo "--- Test 11: Telemetry Snapshot ---"
test_endpoint "Telemetry snapshot" "GET" "/api/neurorail/v1/telemetry/snapshot" ""
echo ""

# Summary
echo "========================================="
echo -e "${GREEN}${BOLD}✅ All tests passed!${RESET}"
echo "========================================="
echo ""
echo "Trace Chain Created:"
echo "  Mission:  $mission_id"
echo "  Plan:     $plan_id"
echo "  Job:      $job_id"
echo "  Attempt:  $attempt_id"
echo ""
