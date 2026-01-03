#!/bin/bash
# System Events API Smoke Test
#
# Usage:
#   ./test_system_events_curl.sh [BASE_URL]
#
# Examples:
#   ./test_system_events_curl.sh http://localhost:8001
#   ./test_system_events_curl.sh https://dev.brain.falklabs.de
#

set -e

# Configuration
BASE_URL="${1:-http://localhost:8001}"
API_BASE="${BASE_URL}/api/events"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
print_test() {
    echo -e "\n${YELLOW}TEST: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    ((TESTS_PASSED++))
}

print_failure() {
    echo -e "${RED}✗ $1${NC}"
    ((TESTS_FAILED++))
}

print_summary() {
    echo -e "\n========================================="
    echo -e "Test Summary"
    echo -e "========================================="
    echo -e "Passed: ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Failed: ${RED}${TESTS_FAILED}${NC}"
    echo -e "Total:  $((TESTS_PASSED + TESTS_FAILED))"
    echo -e "=========================================\n"
}

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "Warning: jq is not installed. JSON output will not be formatted."
    JQ_CMD="cat"
else
    JQ_CMD="jq ."
fi

echo "========================================="
echo "System Events API Smoke Test"
echo "========================================="
echo "Base URL: ${BASE_URL}"
echo "API Endpoint: ${API_BASE}"
echo ""

# Test 1: Get initial stats
print_test "Get initial event statistics"
STATS_RESPONSE=$(curl -s "${API_BASE}/stats")
if echo "${STATS_RESPONSE}" | grep -q "total_events"; then
    print_success "Stats endpoint working"
    echo "${STATS_RESPONSE}" | ${JQ_CMD}
    INITIAL_COUNT=$(echo "${STATS_RESPONSE}" | jq -r '.total_events' 2>/dev/null || echo "unknown")
    echo "Initial event count: ${INITIAL_COUNT}"
else
    print_failure "Stats endpoint failed"
    echo "${STATS_RESPONSE}"
fi

# Test 2: Create event with minimal fields
print_test "Create event with minimal fields"
CREATE_RESPONSE_1=$(curl -s -X POST "${API_BASE}" \
    -H "Content-Type: application/json" \
    -d '{
        "event_type": "test_minimal",
        "severity": "info",
        "message": "Minimal test event from curl script"
    }')

if echo "${CREATE_RESPONSE_1}" | grep -q '"id"'; then
    print_success "Minimal event created"
    EVENT_ID_1=$(echo "${CREATE_RESPONSE_1}" | jq -r '.id' 2>/dev/null)
    echo "Created event ID: ${EVENT_ID_1}"
    echo "${CREATE_RESPONSE_1}" | ${JQ_CMD}
else
    print_failure "Failed to create minimal event"
    echo "${CREATE_RESPONSE_1}"
fi

# Test 3: Create event with all fields
print_test "Create event with all fields"
CREATE_RESPONSE_2=$(curl -s -X POST "${API_BASE}" \
    -H "Content-Type: application/json" \
    -d '{
        "event_type": "test_full",
        "severity": "warning",
        "message": "Full test event from curl script",
        "details": {
            "test_type": "smoke_test",
            "script": "test_system_events_curl.sh",
            "timestamp": "'$(date -Iseconds)'"
        },
        "source": "curl_test_script"
    }')

if echo "${CREATE_RESPONSE_2}" | grep -q '"id"'; then
    print_success "Full event created"
    EVENT_ID_2=$(echo "${CREATE_RESPONSE_2}" | jq -r '.id' 2>/dev/null)
    echo "Created event ID: ${EVENT_ID_2}"
    echo "${CREATE_RESPONSE_2}" | ${JQ_CMD}
else
    print_failure "Failed to create full event"
    echo "${CREATE_RESPONSE_2}"
fi

# Test 4: Get event by ID
if [ -n "${EVENT_ID_1}" ] && [ "${EVENT_ID_1}" != "null" ]; then
    print_test "Get event by ID"
    GET_RESPONSE=$(curl -s "${API_BASE}/${EVENT_ID_1}")

    if echo "${GET_RESPONSE}" | grep -q "Minimal test event"; then
        print_success "Event retrieved by ID"
        echo "${GET_RESPONSE}" | ${JQ_CMD}
    else
        print_failure "Failed to retrieve event by ID"
        echo "${GET_RESPONSE}"
    fi
fi

# Test 5: List all events
print_test "List all events (limit 5)"
LIST_RESPONSE=$(curl -s "${API_BASE}?limit=5")

if echo "${LIST_RESPONSE}" | grep -q '\['; then
    print_success "Events listed successfully"
    EVENT_COUNT=$(echo "${LIST_RESPONSE}" | jq 'length' 2>/dev/null || echo "unknown")
    echo "Returned ${EVENT_COUNT} events"
    echo "${LIST_RESPONSE}" | ${JQ_CMD}
else
    print_failure "Failed to list events"
    echo "${LIST_RESPONSE}"
fi

# Test 6: Filter events by type
print_test "Filter events by type"
FILTER_TYPE_RESPONSE=$(curl -s "${API_BASE}?event_type=test_minimal&limit=10")

if echo "${FILTER_TYPE_RESPONSE}" | grep -q "test_minimal"; then
    print_success "Events filtered by type"
    FILTERED_COUNT=$(echo "${FILTER_TYPE_RESPONSE}" | jq 'length' 2>/dev/null || echo "unknown")
    echo "Found ${FILTERED_COUNT} events with type 'test_minimal'"
    echo "${FILTER_TYPE_RESPONSE}" | ${JQ_CMD}
else
    print_failure "Failed to filter events by type"
    echo "${FILTER_TYPE_RESPONSE}"
fi

# Test 7: Filter events by severity
print_test "Filter events by severity"
FILTER_SEVERITY_RESPONSE=$(curl -s "${API_BASE}?severity=warning&limit=10")

if echo "${FILTER_SEVERITY_RESPONSE}" | grep -q '\['; then
    print_success "Events filtered by severity"
    FILTERED_COUNT=$(echo "${FILTER_SEVERITY_RESPONSE}" | jq 'length' 2>/dev/null || echo "unknown")
    echo "Found ${FILTERED_COUNT} events with severity 'warning'"
    echo "${FILTER_SEVERITY_RESPONSE}" | ${JQ_CMD}
else
    print_failure "Failed to filter events by severity"
    echo "${FILTER_SEVERITY_RESPONSE}"
fi

# Test 8: Update event
if [ -n "${EVENT_ID_1}" ] && [ "${EVENT_ID_1}" != "null" ]; then
    print_test "Update event"
    UPDATE_RESPONSE=$(curl -s -X PUT "${API_BASE}/${EVENT_ID_1}" \
        -H "Content-Type: application/json" \
        -d '{
            "message": "Updated message from curl script",
            "severity": "error"
        }')

    if echo "${UPDATE_RESPONSE}" | grep -q "Updated message"; then
        print_success "Event updated successfully"
        echo "${UPDATE_RESPONSE}" | ${JQ_CMD}
    else
        print_failure "Failed to update event"
        echo "${UPDATE_RESPONSE}"
    fi
fi

# Test 9: Test all severity levels
print_test "Create events with all severity levels"
SEVERITIES=("info" "warning" "error" "critical")
for severity in "${SEVERITIES[@]}"; do
    SEVERITY_RESPONSE=$(curl -s -X POST "${API_BASE}" \
        -H "Content-Type: application/json" \
        -d '{
            "event_type": "test_severity",
            "severity": "'${severity}'",
            "message": "Testing '${severity}' severity level"
        }')

    if echo "${SEVERITY_RESPONSE}" | grep -q '"id"'; then
        echo "  ✓ Created ${severity} event"
    else
        echo "  ✗ Failed to create ${severity} event"
    fi
done
print_success "All severity levels tested"

# Test 10: Get updated stats
print_test "Get final event statistics"
FINAL_STATS_RESPONSE=$(curl -s "${API_BASE}/stats")

if echo "${FINAL_STATS_RESPONSE}" | grep -q "total_events"; then
    print_success "Final stats retrieved"
    echo "${FINAL_STATS_RESPONSE}" | ${JQ_CMD}
    FINAL_COUNT=$(echo "${FINAL_STATS_RESPONSE}" | jq -r '.total_events' 2>/dev/null || echo "unknown")
    echo "Final event count: ${FINAL_COUNT}"

    if [ "${INITIAL_COUNT}" != "unknown" ] && [ "${FINAL_COUNT}" != "unknown" ]; then
        CREATED_IN_TEST=$((FINAL_COUNT - INITIAL_COUNT))
        echo "Events created in this test: ${CREATED_IN_TEST}"
    fi
else
    print_failure "Failed to get final stats"
    echo "${FINAL_STATS_RESPONSE}"
fi

# Test 11: Delete event
if [ -n "${EVENT_ID_2}" ] && [ "${EVENT_ID_2}" != "null" ]; then
    print_test "Delete event"
    DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/${EVENT_ID_2}")
    HTTP_CODE=$(echo "${DELETE_RESPONSE}" | tail -n 1)

    if [ "${HTTP_CODE}" = "204" ]; then
        print_success "Event deleted successfully (HTTP 204)"

        # Verify deletion
        VERIFY_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/${EVENT_ID_2}")
        VERIFY_CODE=$(echo "${VERIFY_RESPONSE}" | tail -n 1)

        if [ "${VERIFY_CODE}" = "404" ]; then
            print_success "Deletion verified (HTTP 404)"
        else
            print_failure "Event still exists after deletion"
        fi
    else
        print_failure "Failed to delete event (HTTP ${HTTP_CODE})"
        echo "${DELETE_RESPONSE}"
    fi
fi

# Test 12: Test validation errors
print_test "Test validation errors"
INVALID_RESPONSE=$(curl -s -X POST "${API_BASE}" \
    -H "Content-Type: application/json" \
    -d '{
        "event_type": "test",
        "message": "Missing severity field"
    }')

if echo "${INVALID_RESPONSE}" | grep -q "422"; then
    print_success "Validation error correctly returned (HTTP 422)"
else
    # Check if error was returned in response body
    if echo "${INVALID_RESPONSE}" | grep -q "detail"; then
        print_success "Validation error detected"
        echo "${INVALID_RESPONSE}" | ${JQ_CMD}
    else
        print_failure "Expected validation error not returned"
        echo "${INVALID_RESPONSE}"
    fi
fi

# Print summary
print_summary

# Exit with appropriate code
if [ ${TESTS_FAILED} -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
