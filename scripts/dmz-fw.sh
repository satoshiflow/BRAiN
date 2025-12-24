#!/bin/bash
################################################################################
# BRAiN DMZ Firewall Isolation
#
# Ensures DMZ network cannot access core internal services (DB/Redis/Qdrant)
# but CAN access Core API (host.docker.internal:8000).
#
# Usage:
#   sudo ./dmz-fw.sh apply     # Apply DMZ isolation rules
#   sudo ./dmz-fw.sh remove    # Remove DMZ isolation rules
#   sudo ./dmz-fw.sh status    # Check DMZ isolation status
#
# Version: 1.0.0
# Date: 2025-12-24
################################################################################

set -euo pipefail

# Configuration
DMZ_SUBNET="172.25.0.0/16"
CORE_SUBNET="172.20.0.0/16"
CORE_API_PORT="8000"

CHAIN="DOCKER-USER"
COMMENT_PREFIX="brain-dmz"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ${NC} $*"
}

print_success() {
    echo -e "${GREEN}✓${NC} $*"
}

print_error() {
    echo -e "${RED}✗${NC} $*"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

ensure_docker_user_chain() {
    if ! iptables -L DOCKER-USER -n &> /dev/null; then
        iptables -N DOCKER-USER
        iptables -I FORWARD -j DOCKER-USER
    fi
}

count_dmz_rules() {
    iptables -L DOCKER-USER -n --line-numbers 2>/dev/null \
        | grep -c "$COMMENT_PREFIX" || echo "0"
}

remove_dmz_rules() {
    local removed=0

    while true; do
        local line_num
        line_num=$(iptables -L DOCKER-USER -n --line-numbers 2>/dev/null \
            | grep "$COMMENT_PREFIX" \
            | tail -1 \
            | awk '{print $1}')

        if [[ -z "$line_num" ]]; then
            break
        fi

        iptables -D DOCKER-USER "$line_num"
        ((removed++))
    done

    if [[ $removed -gt 0 ]]; then
        print_success "Removed $removed DMZ isolation rules"
    fi

    echo "$removed"
}

apply_dmz_rules() {
    print_info "Applying DMZ isolation firewall rules..."

    ensure_docker_user_chain

    # Remove existing DMZ rules first
    remove_dmz_rules > /dev/null

    # Rule 1: ALLOW DMZ → Core API (port 8000)
    # This allows DMZ services to call the Core HTTP API
    iptables -I DOCKER-USER 1 \
        -s "$DMZ_SUBNET" \
        -d "$CORE_SUBNET" \
        -p tcp --dport "$CORE_API_PORT" \
        -m comment --comment "$COMMENT_PREFIX:allow-core-api" \
        -j ACCEPT

    print_success "Rule 1: ALLOW DMZ → Core API (port $CORE_API_PORT)"

    # Rule 2: DROP DMZ → Core Internal Services (all other traffic to core subnet)
    # This prevents DMZ from accessing Postgres/Redis/Qdrant directly
    iptables -A DOCKER-USER \
        -s "$DMZ_SUBNET" \
        -d "$CORE_SUBNET" \
        -m comment --comment "$COMMENT_PREFIX:drop-core-internal" \
        -j DROP

    print_success "Rule 2: DROP DMZ → Core Internal Services"

    print_success "DMZ isolation rules applied"
}

cmd_apply() {
    print_info "Applying DMZ firewall isolation..."
    apply_dmz_rules
    echo ""
    cmd_status
}

cmd_remove() {
    print_info "Removing DMZ firewall isolation..."
    local removed
    removed=$(remove_dmz_rules)

    if [[ $removed -eq 0 ]]; then
        print_info "No DMZ isolation rules to remove"
    fi

    echo ""
    cmd_status
}

cmd_status() {
    print_info "DMZ Firewall Isolation Status"
    echo ""

    local rule_count
    rule_count=$(count_dmz_rules)

    echo "  DMZ Subnet:       $DMZ_SUBNET"
    echo "  Core Subnet:      $CORE_SUBNET"
    echo "  Core API Port:    $CORE_API_PORT"
    echo "  Active Rules:     $rule_count"

    echo ""

    if [[ $rule_count -gt 0 ]]; then
        echo -e "  Status:           ${GREEN}ISOLATED${NC}"
        echo ""
        print_info "Current Rules:"
        iptables -L DOCKER-USER -n --line-numbers 2>/dev/null \
            | grep "$COMMENT_PREFIX" \
            | sed 's/^/  /'
    else
        echo -e "  Status:           ${YELLOW}NOT ISOLATED${NC}"
        echo ""
        print_info "No DMZ isolation rules active"
    fi

    echo ""
}

cmd_help() {
    cat <<EOF
BRAiN DMZ Firewall Isolation

Ensures DMZ network cannot access core internal services.

USAGE:
    sudo $0 <command>

COMMANDS:
    apply               Apply DMZ isolation rules
    remove              Remove DMZ isolation rules
    status              Show isolation status
    help                Show this help message

ISOLATION RULES:
    1. ALLOW: DMZ → Core API (port $CORE_API_PORT)
    2. DROP:  DMZ → Core Internal Services (DB/Redis/Qdrant)

EXAMPLES:
    # Apply isolation
    sudo $0 apply

    # Check status
    sudo $0 status

    # Remove isolation
    sudo $0 remove

NOTES:
    - Requires root/sudo privileges
    - Rules are applied to DOCKER-USER iptables chain
    - Idempotent (safe to run multiple times)

EOF
}

main() {
    local cmd="${1:-help}"
    shift || true

    if [[ "$cmd" == "help" || "$cmd" == "--help" || "$cmd" == "-h" ]]; then
        cmd_help
        exit 0
    fi

    check_root

    case "$cmd" in
        apply)
            cmd_apply
            ;;
        remove)
            cmd_remove
            ;;
        status)
            cmd_status
            ;;
        *)
            print_error "Unknown command: $cmd"
            echo ""
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"
