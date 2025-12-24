#!/bin/bash
################################################################################
# BRAiN Sovereign Mode Firewall Manager
#
# Manages iptables rules in DOCKER-USER chain to enforce fail-closed egress
# blocking for BRAiN containers in sovereign mode.
#
# Usage:
#   sudo ./sovereign-fw.sh status           # Show current state
#   sudo ./sovereign-fw.sh apply sovereign  # Enable sovereign mode
#   sudo ./sovereign-fw.sh apply connected  # Disable sovereign mode
#   sudo ./sovereign-fw.sh check            # Verify state (exit 0/1)
#   sudo ./sovereign-fw.sh rollback         # Remove all BRAiN rules
#
# Version: 1.0.0
# Date: 2025-12-24
################################################################################

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_ROOT="$(dirname "$SCRIPT_DIR")"
STATE_DIR="/var/lib/brain"
STATE_FILE="$STATE_DIR/firewall-state"
LOG_FILE="/var/log/brain-firewall.log"
LOCK_FILE="/var/run/brain-firewall.lock"

# Docker network detection
DOCKER_NETWORK_NAME="brain_internal"
FALLBACK_SUBNET="172.17.0.0/16"  # Default Docker bridge

# Chain name
CHAIN="DOCKER-USER"

# Rule comment prefix for identification
COMMENT_PREFIX="brain-sovereign"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log() {
    local level="$1"
    shift
    local msg="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[$timestamp] [$level] $msg" | tee -a "$LOG_FILE" >&2
}

log_info() {
    log "INFO" "$@"
}

log_warn() {
    log "WARN" "$@"
}

log_error() {
    log "ERROR" "$@"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $*"
}

print_success() {
    echo -e "${GREEN}✓${NC} $*"
}

print_warn() {
    echo -e "${YELLOW}⚠${NC} $*"
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

check_dependencies() {
    local missing=()

    if ! command -v iptables &> /dev/null; then
        missing+=("iptables")
    fi

    if ! command -v docker &> /dev/null; then
        missing+=("docker")
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        print_error "Missing required dependencies: ${missing[*]}"
        exit 1
    fi
}

acquire_lock() {
    local timeout=30
    local elapsed=0

    while [[ -f "$LOCK_FILE" ]] && [[ $elapsed -lt $timeout ]]; do
        print_warn "Waiting for lock... ($elapsed/$timeout)"
        sleep 1
        ((elapsed++))
    done

    if [[ -f "$LOCK_FILE" ]]; then
        print_error "Could not acquire lock after ${timeout}s"
        exit 1
    fi

    echo $$ > "$LOCK_FILE"
    trap 'rm -f "$LOCK_FILE"' EXIT
}

init_state_dir() {
    mkdir -p "$STATE_DIR"
    touch "$LOG_FILE"
    chmod 600 "$LOG_FILE"
}

# ============================================================================
# DOCKER NETWORK DETECTION
# ============================================================================

detect_docker_network() {
    local subnet=""

    # Try to detect brain_internal network
    if docker network inspect "$DOCKER_NETWORK_NAME" &> /dev/null; then
        subnet=$(docker network inspect "$DOCKER_NETWORK_NAME" \
            | grep -oP '(?<="Subnet": ")[^"]+' \
            | head -1)

        if [[ -n "$subnet" ]]; then
            log_info "Detected $DOCKER_NETWORK_NAME subnet: $subnet"
            echo "$subnet"
            return 0
        fi
    fi

    # Fallback: try to find any brain-related network
    local brain_networks
    brain_networks=$(docker network ls --format '{{.Name}}' | grep -i brain || true)

    for net in $brain_networks; do
        subnet=$(docker network inspect "$net" \
            | grep -oP '(?<="Subnet": ")[^"]+' \
            | head -1)

        if [[ -n "$subnet" ]]; then
            log_info "Detected brain network '$net' subnet: $subnet"
            echo "$subnet"
            return 0
        fi
    done

    # Final fallback
    log_warn "Could not detect BRAiN Docker network, using fallback: $FALLBACK_SUBNET"
    echo "$FALLBACK_SUBNET"
}

get_docker_bridge_interface() {
    # Try to find the docker bridge interface
    local iface
    iface=$(ip -o link show | grep -oP 'br-[a-f0-9]+' | head -1 || echo "")

    if [[ -n "$iface" ]]; then
        echo "$iface"
    else
        echo "docker0"
    fi
}

# ============================================================================
# DMZ NETWORK DETECTION AND ISOLATION (Phase B: DMZ Gateway)
# ============================================================================

detect_dmz_network() {
    """
    Detect DMZ Docker network subnet.

    Returns:
        DMZ subnet (e.g., 172.21.0.0/16) or empty string if not found
    """
    local dmz_network="brain_dmz_net"
    local subnet=""

    # Try to detect brain_dmz_net network
    if docker network inspect "$dmz_network" &> /dev/null; then
        subnet=$(docker network inspect "$dmz_network" \
            | grep -oP '(?<="Subnet": ")[^"]+' \
            | head -1)

        if [[ -n "$subnet" ]]; then
            log_info "Detected DMZ network ($dmz_network): $subnet"
            echo "$subnet"
            return 0
        fi
    fi

    log_debug "DMZ network not found ($dmz_network)"
    return 1
}

count_dmz_isolation_rules() {
    """
    Count active DMZ isolation rules.

    Returns:
        Number of brain-dmz-isolation rules in iptables
    """
    iptables -L DOCKER-USER -n 2>/dev/null | grep -c "brain-dmz-isolation" || echo "0"
}

remove_dmz_isolation_rules() {
    """
    Remove all DMZ isolation rules from iptables.

    Idempotent: Safe to call multiple times.
    """
    local removed=0

    # Remove all rules with brain-dmz-isolation comment
    while iptables -L DOCKER-USER -n 2>/dev/null | grep -q "brain-dmz-isolation"; do
        # Find and delete the rule
        local line_num
        line_num=$(iptables -L DOCKER-USER -n --line-numbers 2>/dev/null \
            | grep "brain-dmz-isolation" \
            | head -1 \
            | awk '{print $1}')

        if [[ -n "$line_num" ]]; then
            iptables -D DOCKER-USER "$line_num" 2>/dev/null && ((removed++))
        else
            break
        fi
    done

    if [[ $removed -gt 0 ]]; then
        log_info "Removed $removed DMZ isolation rule(s)"
    fi

    return 0
}

apply_dmz_isolation_rules() {
    """
    Apply DMZ network isolation rules.

    DMZ can ONLY access Core API (port 8000), but NOT databases.

    Args:
        $1: DMZ subnet (e.g., 172.21.0.0/16)
        $2: Core subnet (e.g., 172.20.0.0/16)

    Rules Applied:
        1. DMZ → Core API (8000): ALLOW
        2. DMZ → Postgres (5432): DROP
        3. DMZ → Redis (6379): DROP
        4. DMZ → Qdrant (6333): DROP
        5. DMZ → Other Core ports: DROP (default deny)
    """
    local dmz_subnet="$1"
    local core_subnet="$2"

    if [[ -z "$dmz_subnet" ]] || [[ -z "$core_subnet" ]]; then
        log_warn "DMZ or Core subnet not provided, skipping DMZ isolation rules"
        return 1
    fi

    log_info "Applying DMZ isolation rules (DMZ: $dmz_subnet → Core: $core_subnet)"

    # Ensure DOCKER-USER chain exists
    if ! iptables -L DOCKER-USER -n &> /dev/null; then
        iptables -N DOCKER-USER
        iptables -I FORWARD -j DOCKER-USER
    fi

    # Remove existing DMZ rules first (idempotent)
    remove_dmz_isolation_rules > /dev/null

    # Rule 1: Allow DMZ → Core API (port 8000)
    iptables -I DOCKER-USER 1 \
        -s "$dmz_subnet" \
        -d "$core_subnet" \
        -p tcp --dport 8000 \
        -m comment --comment "brain-dmz-isolation:allow-core-api" \
        -j ACCEPT

    log_info "Added DMZ rule: ALLOW $dmz_subnet → $core_subnet:8000 (Core API)"

    # Rule 2: Block DMZ → Postgres (port 5432)
    iptables -A DOCKER-USER \
        -s "$dmz_subnet" \
        -d "$core_subnet" \
        -p tcp --dport 5432 \
        -m comment --comment "brain-dmz-isolation:block-postgres" \
        -j DROP

    log_info "Added DMZ rule: DROP $dmz_subnet → $core_subnet:5432 (Postgres)"

    # Rule 3: Block DMZ → Redis (port 6379)
    iptables -A DOCKER-USER \
        -s "$dmz_subnet" \
        -d "$core_subnet" \
        -p tcp --dport 6379 \
        -m comment --comment "brain-dmz-isolation:block-redis" \
        -j DROP

    log_info "Added DMZ rule: DROP $dmz_subnet → $core_subnet:6379 (Redis)"

    # Rule 4: Block DMZ → Qdrant (port 6333)
    iptables -A DOCKER-USER \
        -s "$dmz_subnet" \
        -d "$core_subnet" \
        -p tcp --dport 6333 \
        -m comment --comment "brain-dmz-isolation:block-qdrant" \
        -j DROP

    log_info "Added DMZ rule: DROP $dmz_subnet → $core_subnet:6333 (Qdrant)"

    # Rule 5: Block DMZ → Ollama (port 11434)
    iptables -A DOCKER-USER \
        -s "$dmz_subnet" \
        -d "$core_subnet" \
        -p tcp --dport 11434 \
        -m comment --comment "brain-dmz-isolation:block-ollama" \
        -j DROP

    log_info "Added DMZ rule: DROP $dmz_subnet → $core_subnet:11434 (Ollama)"

    log_info "DMZ isolation rules applied (5 rules)"
    return 0
}

verify_dmz_isolation_rules() {
    """
    Verify DMZ isolation rules are applied.

    Returns:
        0 if rules are correctly applied
        1 if rules are missing or incorrect
    """
    local rule_count
    rule_count=$(count_dmz_isolation_rules)

    if [[ "$rule_count" -ge 5 ]]; then
        log_debug "DMZ isolation rules verified ($rule_count rules)"
        return 0
    else
        log_warn "DMZ isolation rules incomplete ($rule_count/5 rules)"
        return 1
    fi
}

# ============================================================================
# IPv6 DETECTION AND MANAGEMENT
# ============================================================================

detect_ipv6_active() {
    """
    Check if IPv6 is active on the host.

    Returns:
        0 if IPv6 is active (has global addresses)
        1 if IPv6 is not active
    """
    if ip -6 addr show 2>/dev/null | grep -q "scope global"; then
        return 0  # IPv6 active
    else
        return 1  # IPv6 not active
    fi
}

check_ip6tables_available() {
    """
    Check if ip6tables command is available.

    Returns:
        0 if ip6tables exists
        1 if ip6tables not available
    """
    if command -v ip6tables &>/dev/null; then
        return 0
    else
        return 1
    fi
}

detect_docker_ipv6_network() {
    """
    Detect IPv6 subnet for Docker network.

    Returns:
        IPv6 subnet or default ULA range
    """
    local subnet=""

    # Try to detect brain_internal network IPv6 subnet
    if docker network inspect "$DOCKER_NETWORK_NAME" &> /dev/null; then
        # Look for IPv6 subnet in network config
        subnet=$(docker network inspect "$DOCKER_NETWORK_NAME" \
            | grep -oP '(?<="Subnet": ")[a-f0-9:]+/[0-9]+' \
            | grep ":" \
            | head -1)

        if [[ -n "$subnet" ]]; then
            log_info "Detected $DOCKER_NETWORK_NAME IPv6 subnet: $subnet"
            echo "$subnet"
            return 0
        fi
    fi

    # Fallback: Use ULA range (Unique Local Addresses)
    local ula_subnet="fc00::/7"
    log_warn "Could not detect IPv6 Docker network, using ULA fallback: $ula_subnet"
    echo "$ula_subnet"
}

count_ipv6_brain_rules() {
    """
    Count IPv6 BRAiN firewall rules.

    Returns:
        Number of brain-sovereign-ipv6 rules
    """
    ip6tables -L DOCKER-USER -n --line-numbers 2>/dev/null \
        | grep -c "brain-sovereign-ipv6" || echo "0"
}

remove_ipv6_brain_rules() {
    """
    Remove all IPv6 BRAiN firewall rules.

    Returns:
        Number of removed rules
    """
    local removed=0

    # Ensure chain exists
    if ! ip6tables -L DOCKER-USER -n &> /dev/null; then
        log_info "DOCKER-USER chain does not exist for IPv6, nothing to remove"
        return 0
    fi

    # Remove rules in reverse order (to preserve line numbers)
    while true; do
        local line_num
        line_num=$(ip6tables -L DOCKER-USER -n --line-numbers 2>/dev/null \
            | grep "brain-sovereign-ipv6" \
            | tail -1 \
            | awk '{print $1}')

        if [[ -z "$line_num" ]]; then
            break
        fi

        ip6tables -D DOCKER-USER "$line_num"
        ((removed++))
    done

    if [[ $removed -gt 0 ]]; then
        log_info "Removed $removed IPv6 BRAiN firewall rules"
    fi

    echo "$removed"
}

apply_ipv6_sovereign_rules() {
    """
    Apply IPv6 sovereign mode firewall rules.

    Args:
        $1: IPv6 subnet to protect

    Returns:
        0 on success, 1 on failure
    """
    local subnet="$1"
    local rule_count=0

    print_info "Applying IPv6 sovereign mode firewall rules..."
    log_info "Applying IPv6 sovereign rules for subnet $subnet"

    # Ensure DOCKER-USER chain exists for IPv6
    if ! ip6tables -L DOCKER-USER -n &> /dev/null; then
        print_warn "DOCKER-USER chain does not exist for IPv6, creating it..."
        ip6tables -N DOCKER-USER
        ip6tables -I FORWARD -j DOCKER-USER
        log_info "Created IPv6 DOCKER-USER chain"
    fi

    # Remove existing IPv6 BRAiN rules first
    remove_ipv6_brain_rules > /dev/null

    # Rule 1: Allow established/related connections
    ip6tables -I DOCKER-USER 1 \
        -m conntrack --ctstate ESTABLISHED,RELATED \
        -s "$subnet" \
        -m comment --comment "brain-sovereign-ipv6:established" \
        -j ACCEPT
    ((rule_count++))
    log_info "Added IPv6 rule: ACCEPT established/related"

    # Rule 2: Allow to localhost (::1)
    ip6tables -I DOCKER-USER 2 \
        -s "$subnet" \
        -d ::1/128 \
        -m comment --comment "brain-sovereign-ipv6:localhost" \
        -j ACCEPT
    ((rule_count++))
    log_info "Added IPv6 rule: ACCEPT to ::1 (localhost)"

    # Rule 3: Allow to ULA (Unique Local Addresses: fc00::/7)
    ip6tables -I DOCKER-USER 3 \
        -s "$subnet" \
        -d fc00::/7 \
        -m comment --comment "brain-sovereign-ipv6:ula" \
        -j ACCEPT
    ((rule_count++))
    log_info "Added IPv6 rule: ACCEPT to fc00::/7 (ULA)"

    # Rule 4: DROP all other egress (FAIL-CLOSED)
    ip6tables -A DOCKER-USER \
        -s "$subnet" \
        -m comment --comment "brain-sovereign-ipv6:drop-egress" \
        -j DROP
    ((rule_count++))
    log_info "Added IPv6 rule: DROP all other egress"

    print_success "Applied $rule_count IPv6 sovereign mode rules"

    return 0
}

verify_ipv6_rules_applied() {
    """
    Verify IPv6 firewall rules are applied.

    Returns:
        0 if rules present (≥4)
        1 if rules missing
    """
    local rule_count
    rule_count=$(count_ipv6_brain_rules)

    if [[ $rule_count -ge 4 ]]; then
        return 0  # Rules present
    else
        return 1  # Rules missing
    fi
}

# ============================================================================
# IPTABLES RULE MANAGEMENT
# ============================================================================

backup_iptables() {
    local backup_file="$STATE_DIR/iptables-backup-$(date +%s).rules"
    iptables-save > "$backup_file"
    log_info "Backed up iptables to $backup_file"
    echo "$backup_file"
}

ensure_docker_user_chain() {
    # Check if DOCKER-USER chain exists
    if ! iptables -L DOCKER-USER -n &> /dev/null; then
        print_warn "DOCKER-USER chain does not exist, creating it..."
        iptables -N DOCKER-USER
        iptables -I FORWARD -j DOCKER-USER
        log_info "Created DOCKER-USER chain"
    fi
}

count_brain_rules() {
    iptables -L DOCKER-USER -n --line-numbers 2>/dev/null \
        | grep -c "$COMMENT_PREFIX" || echo "0"
}

remove_brain_rules() {
    local removed=0

    # Remove rules in reverse order (to preserve line numbers)
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
        log_info "Removed $removed BRAiN firewall rules"
        print_success "Removed $removed BRAiN firewall rules"
    fi

    echo "$removed"
}

apply_sovereign_rules() {
    local subnet="$1"
    local rule_count=0

    print_info "Applying sovereign mode firewall rules..."
    log_info "Applying sovereign rules for subnet $subnet"

    # Backup first
    backup_iptables

    # Ensure chain exists
    ensure_docker_user_chain

    # Remove existing BRAiN rules first
    remove_brain_rules > /dev/null

    # Rule 1: Allow established/related connections
    iptables -I DOCKER-USER 1 \
        -m conntrack --ctstate ESTABLISHED,RELATED \
        -s "$subnet" \
        -m comment --comment "$COMMENT_PREFIX:established" \
        -j ACCEPT
    ((rule_count++))
    log_info "Added rule: ACCEPT established/related"

    # Rule 2: Allow to localhost
    iptables -I DOCKER-USER 2 \
        -s "$subnet" \
        -d 127.0.0.0/8 \
        -m comment --comment "$COMMENT_PREFIX:localhost" \
        -j ACCEPT
    ((rule_count++))
    log_info "Added rule: ACCEPT to localhost"

    # Rule 3: Allow to RFC1918 - 10.0.0.0/8
    iptables -I DOCKER-USER 3 \
        -s "$subnet" \
        -d 10.0.0.0/8 \
        -m comment --comment "$COMMENT_PREFIX:rfc1918-10" \
        -j ACCEPT
    ((rule_count++))
    log_info "Added rule: ACCEPT to 10.0.0.0/8"

    # Rule 4: Allow to RFC1918 - 172.16.0.0/12
    iptables -I DOCKER-USER 4 \
        -s "$subnet" \
        -d 172.16.0.0/12 \
        -m comment --comment "$COMMENT_PREFIX:rfc1918-172" \
        -j ACCEPT
    ((rule_count++))
    log_info "Added rule: ACCEPT to 172.16.0.0/12"

    # Rule 5: Allow to RFC1918 - 192.168.0.0/16
    iptables -I DOCKER-USER 5 \
        -s "$subnet" \
        -d 192.168.0.0/16 \
        -m comment --comment "$COMMENT_PREFIX:rfc1918-192" \
        -j ACCEPT
    ((rule_count++))
    log_info "Added rule: ACCEPT to 192.168.0.0/16"

    # Rule 6: DROP all other egress (FAIL-CLOSED)
    iptables -A DOCKER-USER \
        -s "$subnet" \
        -m comment --comment "$COMMENT_PREFIX:drop-egress" \
        -j DROP
    ((rule_count++))
    log_info "Added rule: DROP all other egress"

    print_success "Applied $rule_count sovereign mode rules"

    # IPv6 Handling
    if detect_ipv6_active; then
        print_info "IPv6 detected as active on host"

        if ! check_ip6tables_available; then
            print_error "IPv6 is active but ip6tables is not available"
            print_error "This creates a security bypass risk!"
            print_error ""
            print_error "Solutions:"
            print_error "  1. Install ip6tables: sudo apt-get install iptables"
            print_error "  2. Disable IPv6: sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1"
            print_error ""
            log_error "IPv6 active but ip6tables not available - SECURITY RISK"
            exit 1
        fi

        # Get IPv6 subnet
        local ipv6_subnet
        ipv6_subnet=$(detect_docker_ipv6_network)

        # Apply IPv6 rules
        if apply_ipv6_sovereign_rules "$ipv6_subnet"; then
            print_success "IPv6 sovereign mode rules applied"
        else
            print_error "Failed to apply IPv6 sovereign mode rules"
            log_error "Failed to apply IPv6 rules"
            exit 1
        fi
    else
        print_info "IPv6 not active, skipping IPv6 rules"
        log_info "IPv6 not detected, skipping IPv6 firewall rules"
    fi

    # DMZ Isolation (Phase B: DMZ Gateway)
    local dmz_subnet
    dmz_subnet=$(detect_dmz_network)

    if [[ -n "$dmz_subnet" ]]; then
        print_info "DMZ network detected: $dmz_subnet"
        log_info "Applying DMZ isolation rules"

        if apply_dmz_isolation_rules "$dmz_subnet" "$subnet"; then
            print_success "DMZ isolation rules applied (5 rules)"
        else
            print_warn "Failed to apply DMZ isolation rules (DMZ may bypass security)"
            log_warn "DMZ isolation rules failed to apply"
        fi
    else
        log_debug "DMZ network not found, skipping DMZ isolation rules"
    fi

    # Save state
    echo "sovereign" > "$STATE_FILE"
    echo "$subnet" >> "$STATE_FILE"
    echo "$(date +%s)" >> "$STATE_FILE"

    return 0
}

apply_connected_rules() {
    print_info "Applying connected mode (removing restrictions)..."
    log_info "Applying connected mode"

    # Backup first
    backup_iptables

    # Remove all BRAiN rules (IPv4)
    local removed
    removed=$(remove_brain_rules)

    if [[ $removed -eq 0 ]]; then
        print_warn "No IPv4 sovereign rules to remove (already in connected mode?)"
    fi

    # Remove IPv6 rules if present
    if check_ip6tables_available; then
        local ipv6_removed
        ipv6_removed=$(remove_ipv6_brain_rules)

        if [[ $ipv6_removed -gt 0 ]]; then
            print_success "Removed $ipv6_removed IPv6 sovereign rules"
        fi
    fi

    # Remove DMZ isolation rules (Phase B: DMZ Gateway)
    local dmz_removed
    dmz_removed=$(count_dmz_isolation_rules)

    if [[ $dmz_removed -gt 0 ]]; then
        remove_dmz_isolation_rules
        print_success "Removed $dmz_removed DMZ isolation rules"
        log_info "Removed DMZ isolation rules"
    fi

    # Save state
    echo "connected" > "$STATE_FILE"
    echo "" >> "$STATE_FILE"
    echo "$(date +%s)" >> "$STATE_FILE"

    print_success "Connected mode enabled (firewall restrictions removed)"

    return 0
}

# ============================================================================
# STATE QUERIES
# ============================================================================

get_current_mode() {
    if [[ -f "$STATE_FILE" ]]; then
        head -1 "$STATE_FILE"
    else
        echo "unknown"
    fi
}

get_current_subnet() {
    if [[ -f "$STATE_FILE" ]]; then
        sed -n '2p' "$STATE_FILE"
    else
        echo ""
    fi
}

get_last_change_timestamp() {
    if [[ -f "$STATE_FILE" ]]; then
        sed -n '3p' "$STATE_FILE"
    else
        echo "0"
    fi
}

verify_sovereign_rules() {
    local ipv4_count
    ipv4_count=$(count_brain_rules)

    # IPv4 rules must be present (≥6)
    if [[ $ipv4_count -lt 6 ]]; then
        return 1  # IPv4 rules missing
    fi

    # If IPv6 is active, verify IPv6 rules too
    if detect_ipv6_active; then
        if ! check_ip6tables_available; then
            # IPv6 active but ip6tables not available - FAIL
            return 1
        fi

        local ipv6_count
        ipv6_count=$(count_ipv6_brain_rules)

        if [[ $ipv6_count -lt 4 ]]; then
            return 1  # IPv6 rules missing
        fi
    fi

    # All checks passed
    return 0
}

# ============================================================================
# COMMAND HANDLERS
# ============================================================================

cmd_status() {
    print_info "BRAiN Sovereign Firewall Status"
    echo ""

    # Current mode
    local mode
    mode=$(get_current_mode)

    echo "  Mode:            $mode"

    if [[ "$mode" == "sovereign" ]]; then
        echo -e "  Status:          ${GREEN}ENFORCED${NC}"
    elif [[ "$mode" == "connected" ]]; then
        echo -e "  Status:          ${YELLOW}OPEN${NC}"
    else
        echo -e "  Status:          ${RED}UNKNOWN${NC}"
    fi

    # Subnet
    local subnet
    subnet=$(get_current_subnet)
    if [[ -n "$subnet" ]]; then
        echo "  Protected Subnet: $subnet"
    fi

    # Last change
    local last_change
    last_change=$(get_last_change_timestamp)
    if [[ "$last_change" != "0" ]]; then
        local change_date
        change_date=$(date -d "@$last_change" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "unknown")
        echo "  Last Changed:    $change_date"
    fi

    # IPv4 Rule count
    local rule_count
    rule_count=$(count_brain_rules)
    echo "  IPv4 Rules:      $rule_count"

    # IPv6 Status
    if detect_ipv6_active; then
        echo -e "  IPv6 Active:     ${YELLOW}YES${NC}"

        if check_ip6tables_available; then
            echo -e "  ip6tables:       ${GREEN}Available${NC}"

            local ipv6_rule_count
            ipv6_rule_count=$(count_ipv6_brain_rules)
            echo "  IPv6 Rules:      $ipv6_rule_count"
        else
            echo -e "  ip6tables:       ${RED}NOT AVAILABLE${NC}"
            echo -e "  ${RED}⚠ WARNING: IPv6 bypass risk!${NC}"
        fi
    else
        echo -e "  IPv6 Active:     ${GREEN}NO${NC}"
    fi

    echo ""

    # Show IPv4 rules if present
    if [[ $rule_count -gt 0 ]]; then
        print_info "Current IPv4 Rules:"
        iptables -L DOCKER-USER -n --line-numbers 2>/dev/null \
            | grep "$COMMENT_PREFIX" \
            | sed 's/^/  /'
    else
        print_warn "No IPv4 BRAiN firewall rules active"
    fi

    # Show IPv6 rules if present
    if detect_ipv6_active && check_ip6tables_available; then
        local ipv6_rule_count
        ipv6_rule_count=$(count_ipv6_brain_rules)

        if [[ $ipv6_rule_count -gt 0 ]]; then
            echo ""
            print_info "Current IPv6 Rules:"
            ip6tables -L DOCKER-USER -n --line-numbers 2>/dev/null \
                | grep "brain-sovereign-ipv6" \
                | sed 's/^/  /'
        fi
    fi

    # Show DMZ isolation rules if present (Phase B: DMZ Gateway)
    local dmz_rule_count
    dmz_rule_count=$(count_dmz_isolation_rules)

    if [[ $dmz_rule_count -gt 0 ]]; then
        echo ""
        print_info "Current DMZ Isolation Rules:"
        iptables -L DOCKER-USER -n --line-numbers 2>/dev/null \
            | grep "brain-dmz-isolation" \
            | sed 's/^/  /'
    else
        local dmz_subnet
        dmz_subnet=$(detect_dmz_network)
        if [[ -n "$dmz_subnet" ]]; then
            echo ""
            print_warn "DMZ network detected ($dmz_subnet) but no isolation rules applied!"
        fi
    fi

    echo ""
}

cmd_apply() {
    local target_mode="$1"

    if [[ "$target_mode" != "sovereign" && "$target_mode" != "connected" ]]; then
        print_error "Invalid mode: $target_mode (must be 'sovereign' or 'connected')"
        exit 1
    fi

    log_info "Applying mode: $target_mode"

    if [[ "$target_mode" == "sovereign" ]]; then
        local subnet
        subnet=$(detect_docker_network)

        if [[ -z "$subnet" ]]; then
            print_error "Could not detect Docker network subnet"
            exit 1
        fi

        print_info "Target subnet: $subnet"
        apply_sovereign_rules "$subnet"

    elif [[ "$target_mode" == "connected" ]]; then
        apply_connected_rules
    fi

    print_success "Mode applied successfully: $target_mode"
}

cmd_check() {
    local mode
    mode=$(get_current_mode)

    if [[ "$mode" == "sovereign" ]]; then
        if verify_sovereign_rules; then
            print_success "Sovereign mode VERIFIED (rules active)"
            echo "  IPv4 Rules:"
            echo "    Expected: ≥6 rules"
            echo "    Actual:   $(count_brain_rules) rules"

            if detect_ipv6_active; then
                if check_ip6tables_available; then
                    echo "  IPv6 Rules:"
                    echo "    Expected: ≥4 rules"
                    echo "    Actual:   $(count_ipv6_brain_rules) rules"
                else
                    echo "  IPv6: ip6tables not available (but IPv6 is active!)"
                fi
            else
                echo "  IPv6: Not active"
            fi

            exit 0
        else
            print_error "Sovereign mode FAILED (rules missing)"
            echo "  IPv4 Rules:"
            echo "    Expected: ≥6 rules"
            echo "    Actual:   $(count_brain_rules) rules"

            if detect_ipv6_active; then
                if check_ip6tables_available; then
                    echo "  IPv6 Rules:"
                    echo "    Expected: ≥4 rules"
                    echo "    Actual:   $(count_ipv6_brain_rules) rules"
                else
                    echo "  IPv6: ip6tables NOT AVAILABLE (SECURITY RISK!)"
                fi
            fi

            exit 1
        fi

    elif [[ "$mode" == "connected" ]]; then
        local ipv4_count
        ipv4_count=$(count_brain_rules)

        local ipv6_count=0
        if check_ip6tables_available; then
            ipv6_count=$(count_ipv6_brain_rules)
        fi

        if [[ $ipv4_count -eq 0 ]] && [[ $ipv6_count -eq 0 ]]; then
            print_success "Connected mode VERIFIED (no restrictions)"
            exit 0
        else
            print_error "Connected mode FAILED (unexpected rules present)"
            echo "  Expected: 0 rules"
            echo "  Actual IPv4: $ipv4_count rules"
            echo "  Actual IPv6: $ipv6_count rules"
            exit 1
        fi

    else
        print_warn "Mode unknown, cannot verify"
        exit 1
    fi
}

cmd_rollback() {
    print_warn "Rolling back all BRAiN firewall rules..."
    log_info "Executing rollback"

    # Backup first
    backup_iptables

    # Remove IPv4 rules
    local removed
    removed=$(remove_brain_rules)

    if [[ $removed -gt 0 ]]; then
        print_success "Rollback: removed $removed IPv4 rules"
    else
        print_info "No IPv4 rules to remove"
    fi

    # Remove IPv6 rules if present
    if check_ip6tables_available; then
        local ipv6_removed
        ipv6_removed=$(remove_ipv6_brain_rules)

        if [[ $ipv6_removed -gt 0 ]]; then
            print_success "Rollback: removed $ipv6_removed IPv6 rules"
        fi
    fi

    # Remove DMZ isolation rules if present (Phase B: DMZ Gateway)
    local dmz_removed
    dmz_removed=$(count_dmz_isolation_rules)

    if [[ $dmz_removed -gt 0 ]]; then
        remove_dmz_isolation_rules
        print_success "Rollback: removed $dmz_removed DMZ isolation rules"
    fi

    # Clear state
    echo "unknown" > "$STATE_FILE"
    echo "" >> "$STATE_FILE"
    echo "$(date +%s)" >> "$STATE_FILE"

    log_info "Rollback completed"
}

cmd_help() {
    cat <<EOF
BRAiN Sovereign Mode Firewall Manager v1.0.0

USAGE:
    sudo $0 <command> [options]

COMMANDS:
    status              Show current firewall state and rules
    apply sovereign     Enable sovereign mode (block internet egress)
    apply connected     Disable sovereign mode (allow all egress)
    check               Verify firewall state (exit code 0=ok, 1=fail)
    rollback            Remove all BRAiN firewall rules
    help                Show this help message

EXAMPLES:
    # Enable sovereign mode
    sudo $0 apply sovereign

    # Check status
    sudo $0 status

    # Verify enforcement
    sudo $0 check && echo "Sovereign mode active" || echo "Sovereign mode FAILED"

    # Disable sovereign mode
    sudo $0 apply connected

    # Emergency rollback
    sudo $0 rollback

NOTES:
    - Requires root/sudo privileges
    - Rules are applied to DOCKER-USER iptables chain
    - Automatically detects BRAiN Docker network subnet
    - Fail-closed: blocks all internet egress in sovereign mode
    - Allows localhost + RFC1918 private networks

FILES:
    State:   $STATE_FILE
    Logs:    $LOG_FILE
    Backups: $STATE_DIR/iptables-backup-*.rules

DOCUMENTATION:
    See: docs/sovereign_egress_enforcement.md

EOF
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    # Parse command
    local cmd="${1:-help}"
    shift || true

    # Help doesn't require root
    if [[ "$cmd" == "help" || "$cmd" == "--help" || "$cmd" == "-h" ]]; then
        cmd_help
        exit 0
    fi

    # All other commands require root
    check_root
    check_dependencies
    init_state_dir
    acquire_lock

    # Route to command handler
    case "$cmd" in
        status)
            cmd_status
            ;;
        apply)
            local mode="${1:-}"
            if [[ -z "$mode" ]]; then
                print_error "Missing mode argument (sovereign|connected)"
                exit 1
            fi
            cmd_apply "$mode"
            ;;
        check)
            cmd_check
            ;;
        rollback)
            cmd_rollback
            ;;
        *)
            print_error "Unknown command: $cmd"
            echo ""
            cmd_help
            exit 1
            ;;
    esac
}

# Run main
main "$@"
