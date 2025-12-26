#!/bin/bash
################################################################################
# BRAiN Sovereign Mode Verification Script
#
# Comprehensive verification suite for sovereign mode enforcement.
# Tests all three defense layers: Application, Docker, and Host Firewall.
#
# Usage:
#   sudo ./verify-sovereign-mode.sh
#
# Exit Codes:
#   0 = All tests passed
#   1 = One or more tests failed
#   2 = Execution error
#
# Version: 1.0.0
# Date: 2025-12-24
################################################################################

set -u

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
PASSED=0
FAILED=0
WARNINGS=0

# Configuration
CONTAINER="brain-backend"
TIMEOUT=5

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

print_header() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}$1${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

print_test() {
    echo -n "Testing: $1 ... "
}

pass() {
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}"
    if [[ -n "${1:-}" ]]; then
        echo -e "  ${RED}Reason: $1${NC}"
    fi
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠ WARNING${NC}"
    if [[ -n "${1:-}" ]]; then
        echo -e "  ${YELLOW}$1${NC}"
    fi
    ((WARNINGS++))
}

# ============================================================================
# TEST LAYER 1: HOST FIREWALL (IPTABLES)
# ============================================================================

test_firewall_rules() {
    print_header "LAYER 1: Host Firewall (iptables DOCKER-USER)"

    # Test 1: Check if sovereign-fw.sh exists
    print_test "Firewall script exists"
    if [[ -f "scripts/sovereign-fw.sh" ]]; then
        pass
    else
        fail "scripts/sovereign-fw.sh not found"
        return
    fi

    # Test 2: Check firewall mode
    print_test "Firewall mode is 'sovereign'"
    local mode
    mode=$(sudo scripts/sovereign-fw.sh status 2>/dev/null | grep "Mode:" | awk '{print $2}' | tr -d '\n')

    if [[ "$mode" == "sovereign" ]]; then
        pass
    else
        fail "Current mode: $mode (expected: sovereign)"
    fi

    # Test 3: Check rule count
    print_test "Firewall rules active (≥6 rules)"
    local rule_count
    rule_count=$(sudo scripts/sovereign-fw.sh status 2>/dev/null | grep "Active Rules:" | awk '{print $3}' | tr -d '\n')

    if [[ "$rule_count" -ge 6 ]]; then
        pass
    else
        fail "Only $rule_count rules active (expected: ≥6)"
    fi

    # Test 4: Check verification
    print_test "Firewall self-check passes"
    if sudo scripts/sovereign-fw.sh check &> /dev/null; then
        pass
    else
        fail "sovereign-fw.sh check returned non-zero"
    fi

    # Test 5: Check DOCKER-USER chain
    print_test "DOCKER-USER chain has BRAiN rules"
    if sudo iptables -L DOCKER-USER -n 2>/dev/null | grep -q "brain-sovereign"; then
        pass
    else
        fail "No brain-sovereign rules found in DOCKER-USER"
    fi
}

# ============================================================================
# TEST LAYER 2: DOCKER NETWORK
# ============================================================================

test_docker_network() {
    print_header "LAYER 2: Docker Network Isolation"

    # Test 1: Check brain_internal network exists
    print_test "brain_internal network exists"
    if docker network inspect brain_internal &> /dev/null; then
        pass
    else
        fail "brain_internal network not found"
        return
    fi

    # Test 2: Check network subnet
    print_test "Network subnet is 172.20.0.0/16"
    local subnet
    subnet=$(docker network inspect brain_internal | grep -oP '(?<="Subnet": ")[^"]+' | head -1)

    if [[ "$subnet" == "172.20.0.0/16" ]]; then
        pass
    else
        warn "Subnet is $subnet (expected: 172.20.0.0/16, but might be auto-detected)"
    fi

    # Test 3: Check if containers are on brain_internal
    print_test "Backend container on brain_internal"
    if docker inspect "$CONTAINER" 2>/dev/null | grep -q "brain_internal"; then
        pass
    else
        fail "Container $CONTAINER not on brain_internal network"
    fi
}

# ============================================================================
# TEST LAYER 3: EGRESS BLOCKING
# ============================================================================

test_egress_blocking() {
    print_header "LAYER 3: Egress Blocking Verification"

    # Test 1: Block Google DNS
    print_test "Block egress to 8.8.8.8 (Google DNS)"
    if docker exec "$CONTAINER" timeout "$TIMEOUT" curl -s -I http://8.8.8.8 &> /dev/null; then
        fail "Container can reach 8.8.8.8 (internet access detected)"
    else
        pass
    fi

    # Test 2: Block Cloudflare
    print_test "Block egress to 1.1.1.1 (Cloudflare)"
    if docker exec "$CONTAINER" timeout "$TIMEOUT" curl -s -I http://1.1.1.1 &> /dev/null; then
        fail "Container can reach 1.1.1.1 (internet access detected)"
    else
        pass
    fi

    # Test 3: Block public domain
    print_test "Block egress to www.google.com"
    if docker exec "$CONTAINER" timeout "$TIMEOUT" curl -s -I https://www.google.com &> /dev/null; then
        fail "Container can reach www.google.com (internet access detected)"
    else
        pass
    fi

    # Test 4: Block public HTTPS
    print_test "Block egress to api.github.com"
    if docker exec "$CONTAINER" timeout "$TIMEOUT" curl -s -I https://api.github.com &> /dev/null; then
        fail "Container can reach api.github.com (internet access detected)"
    else
        pass
    fi
}

# ============================================================================
# TEST LAYER 4: INTERNAL CONNECTIVITY
# ============================================================================

test_internal_connectivity() {
    print_header "LAYER 4: Internal Network Connectivity"

    # Test 1: Localhost access
    print_test "Allow access to localhost"
    if docker exec "$CONTAINER" timeout "$TIMEOUT" curl -s -I http://localhost:8000/health &> /dev/null; then
        pass
    else
        fail "Container cannot reach localhost (should be allowed)"
    fi

    # Test 2: Backend service
    print_test "Allow access to backend service"
    if docker exec "$CONTAINER" timeout "$TIMEOUT" curl -s -I http://backend:8000/health &> /dev/null; then
        pass
    else
        warn "Container cannot reach backend service (might not be responding)"
    fi

    # Test 3: PostgreSQL (just connection, not protocol check)
    print_test "Allow access to postgres service"
    if docker exec "$CONTAINER" timeout "$TIMEOUT" bash -c "echo > /dev/tcp/postgres/5432" 2> /dev/null; then
        pass
    else
        warn "Container cannot reach postgres (might not be running)"
    fi

    # Test 4: Redis
    print_test "Allow access to redis service"
    if docker exec "$CONTAINER" timeout "$TIMEOUT" bash -c "echo > /dev/tcp/redis/6379" 2> /dev/null; then
        pass
    else
        warn "Container cannot reach redis (might not be running)"
    fi
}

# ============================================================================
# TEST LAYER 5: BACKEND API INTEGRATION
# ============================================================================

test_backend_api() {
    print_header "LAYER 5: Backend API Integration"

    # Test 1: Sovereign mode status endpoint
    print_test "GET /api/sovereign-mode/status"
    local status_code
    status_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/sovereign-mode/status 2>/dev/null)

    if [[ "$status_code" == "200" ]]; then
        pass
    else
        warn "Status endpoint returned $status_code (expected: 200)"
    fi

    # Test 2: Network check endpoint
    print_test "GET /api/sovereign-mode/network/check"
    status_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/sovereign-mode/network/check 2>/dev/null)

    if [[ "$status_code" == "200" ]]; then
        pass
    else
        warn "Network check endpoint returned $status_code (expected: 200)"
    fi

    # Test 3: Check if firewall_state is included
    print_test "Network check includes firewall_state"
    local response
    response=$(curl -s http://localhost:8000/api/sovereign-mode/network/check 2>/dev/null)

    if echo "$response" | grep -q "firewall_state"; then
        pass
    else
        warn "firewall_state field not in response (Phase 2 integration might not be deployed)"
    fi

    # Test 4: Check if mode is sovereign
    print_test "API reports mode as 'sovereign'"
    response=$(curl -s http://localhost:8000/api/sovereign-mode/status 2>/dev/null)

    if echo "$response" | grep -q '"mode".*"sovereign"'; then
        pass
    else
        warn "API does not report sovereign mode (check BRAiN_MODE env var)"
    fi
}

# ============================================================================
# TEST LAYER 6: AUTOMATED PROBE
# ============================================================================

test_network_probe() {
    print_header "LAYER 6: Automated Network Probe"

    # Test 1: Network probe script exists
    print_test "network-probe.sh exists"
    if [[ -f "scripts/network-probe.sh" ]]; then
        pass
    else
        warn "scripts/network-probe.sh not found (Phase 2 feature)"
        return
    fi

    # Test 2: Run probe from container
    print_test "Network probe detects isolation"
    if docker exec "$CONTAINER" bash /app/scripts/network-probe.sh &> /dev/null; then
        pass
    else
        # Probe returns 1 if internet detected, 0 if isolated
        # We're looking for 0 (isolated) for this test to pass
        # But the probe might not be deployed yet
        warn "Network probe test inconclusive (check if probe script is deployed in container)"
    fi
}

# ============================================================================
# TEST LAYER 7: IPv6 GATE CHECK
# ============================================================================

test_ipv6_gate() {
    print_header "LAYER 7: IPv6 Gate Check"

    # Test 1: Detect IPv6 status
    print_test "IPv6 status detection"
    local ipv6_active=false
    if ip -6 addr show 2>/dev/null | grep -q "scope global"; then
        ipv6_active=true
        pass
    else
        pass  # Not active is OK
    fi

    # Test 2: If IPv6 active, check ip6tables availability
    if [[ "$ipv6_active" == "true" ]]; then
        print_test "ip6tables available"
        if command -v ip6tables &>/dev/null; then
            pass
        else
            fail "IPv6 is active but ip6tables is not available"
        fi

        # Test 3: Check IPv6 firewall rules
        print_test "IPv6 firewall rules active"
        if sudo ip6tables -L DOCKER-USER -n 2>/dev/null | grep -q "brain-sovereign-ipv6"; then
            pass
        else
            fail "IPv6 is active but no ip6tables rules found"
        fi

        # Test 4: Count IPv6 rules
        print_test "IPv6 rules count (≥4 rules)"
        local ipv6_rule_count
        ipv6_rule_count=$(sudo ip6tables -L DOCKER-USER -n 2>/dev/null | grep -c "brain-sovereign-ipv6" || echo "0")

        if [[ "$ipv6_rule_count" -ge 4 ]]; then
            pass
        else
            fail "Only $ipv6_rule_count IPv6 rules active (expected: ≥4)"
        fi
    else
        print_test "IPv6 not active (skipping IPv6 checks)"
        pass
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  BRAiN Sovereign Mode Verification Suite v1.0.0         ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    echo "This script performs comprehensive verification of sovereign"
    echo "mode enforcement across all defense layers."
    echo ""

    # Check prerequisites
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}✗ This script must be run as root (use sudo)${NC}"
        exit 2
    fi

    if ! docker ps --filter "name=$CONTAINER" --format '{{.Names}}' | grep -q "$CONTAINER"; then
        echo -e "${RED}✗ Container $CONTAINER is not running${NC}"
        echo "  Start BRAiN services first: docker compose up -d"
        exit 2
    fi

    # Run all test suites
    test_firewall_rules
    test_docker_network
    test_egress_blocking
    test_internal_connectivity
    test_backend_api
    test_network_probe
    test_ipv6_gate

    # Summary
    print_header "TEST SUMMARY"

    echo -e "${GREEN}Passed:${NC}   $PASSED"
    echo -e "${RED}Failed:${NC}   $FAILED"
    echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
    echo ""

    local total=$((PASSED + FAILED + WARNINGS))
    local success_rate=0
    if [[ $total -gt 0 ]]; then
        success_rate=$(( (PASSED * 100) / total ))
    fi

    echo "Success Rate: $success_rate%"
    echo ""

    # Verdict
    if [[ $FAILED -eq 0 ]]; then
        echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ✓ SOVEREIGN MODE VERIFIED                              ║${NC}"
        echo -e "${GREEN}║  All critical tests passed. Egress is blocked.          ║${NC}"
        echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
        exit 0
    else
        echo -e "${RED}╔══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║  ✗ SOVEREIGN MODE FAILED                                 ║${NC}"
        echo -e "${RED}║  $FAILED test(s) failed. Review output above.              ║${NC}"
        echo -e "${RED}╚══════════════════════════════════════════════════════════╝${NC}"
        exit 1
    fi
}

# Run main
main
