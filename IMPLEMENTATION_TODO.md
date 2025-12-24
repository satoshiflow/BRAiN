# BRAiN Sovereign Mode Audit + DMZ + IPv6 Implementation TODO

**Sprint**: Audit + DMZ + IPv6 (Sovereign Hardened)
**Status**: Phase A Complete, Phase C & B Remaining
**Date**: 2025-12-24

---

## ✅ COMPLETED

### Phase A: Audit Event Integration

- [x] A.1: Extended `AuditEntry` schema with:
  - `AuditSeverity` enum (INFO, WARNING, ERROR, CRITICAL)
  - `AuditEventType` enum (17 event types)
  - `severity` field
  - `ipv6_related` boolean flag
  - Updated `__init__.py` exports

- [x] A.2: Implemented audit event emitters in `service.py`:
  - New `_audit()` method with auto-severity detection
  - Integrated events for:
    - `sovereign.mode_changed`
    - `sovereign.bundle_loaded`
    - `sovereign.network_probe_passed/failed`

- [x] A.3: Updated API endpoint documentation in `router.py`:
  - `/api/sovereign-mode/audit` endpoint documented with all new event types

- [x] C.1: Added IPv6 policy config to `.env.example`:
  - `BRAIN_SOVEREIGN_IPV6_POLICY=block`
  - `BRAIN_SOVEREIGN_IPV6_ALLOWLIST=`
  - `BRAIN_DMZ_ENABLED=false`

---

## ❌ REMAINING TASKS

### Phase C: IPv6 Hardening (CRITICAL)

#### C.2: Extend `sovereign-fw.sh` with IPv6 Support

**File**: `scripts/sovereign-fw.sh`

**Required Functions**:

```bash
detect_ipv6_active() {
    # Check if IPv6 is active on host
    if ip -6 addr show 2>/dev/null | grep -q "inet6"; then
        return 0  # IPv6 active
    else
        return 1  # IPv6 not active
    fi
}

check_ip6tables_available() {
    # Check if ip6tables command exists
    if command -v ip6tables &>/dev/null; then
        return 0
    else
        return 1
    fi
}

apply_ipv6_sovereign_rules() {
    local subnet="$1"

    print_info "Applying IPv6 sovereign mode firewall rules..."

    # Ensure DOCKER-USER chain exists (if using legacy iptables)
    if ! ip6tables -L DOCKER-USER -n &> /dev/null; then
        ip6tables -N DOCKER-USER
        ip6tables -I FORWARD -j DOCKER-USER
    fi

    # Rule 1: Allow established/related connections
    ip6tables -I DOCKER-USER 1 \
        -m conntrack --ctstate ESTABLISHED,RELATED \
        -s "$subnet" \
        -m comment --comment "brain-sovereign-ipv6:established" \
        -j ACCEPT

    # Rule 2: Allow to localhost (::1)
    ip6tables -I DOCKER-USER 2 \
        -s "$subnet" \
        -d ::1/128 \
        -m comment --comment "brain-sovereign-ipv6:localhost" \
        -j ACCEPT

    # Rule 3: Allow to ULA (Unique Local Addresses: fc00::/7)
    ip6tables -I DOCKER-USER 3 \
        -s "$subnet" \
        -d fc00::/7 \
        -m comment --comment "brain-sovereign-ipv6:ula" \
        -j ACCEPT

    # Rule 4: DROP all other egress (FAIL-CLOSED)
    ip6tables -A DOCKER-USER \
        -s "$subnet" \
        -m comment --comment "brain-sovereign-ipv6:drop-egress" \
        -j DROP

    print_success "Applied IPv6 sovereign mode rules"
}

remove_ipv6_brain_rules() {
    # Remove IPv6 rules in reverse order
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
    done
}

count_ipv6_brain_rules() {
    ip6tables -L DOCKER-USER -n --line-numbers 2>/dev/null \
        | grep -c "brain-sovereign-ipv6" || echo "0"
}
```

**Integration in `apply_sovereign_rules()`**:

```bash
apply_sovereign_rules() {
    local subnet="$1"

    # ... existing IPv4 rules ...

    # IPv6 Rules
    if detect_ipv6_active; then
        print_info "IPv6 detected as active"

        if ! check_ip6tables_available; then
            print_error "IPv6 is active but ip6tables is not available"
            print_error "Install ip6tables or disable IPv6 on the host"
            exit 1
        fi

        # Get IPv6 subnet (detect or use default)
        local ipv6_subnet
        ipv6_subnet=$(detect_docker_ipv6_network || echo "fc00::/7")

        apply_ipv6_sovereign_rules "$ipv6_subnet"
    else
        print_info "IPv6 not active, skipping IPv6 rules"
    fi

    # ... save state ...
}
```

**Integration in `apply_connected_rules()`**:

```bash
apply_connected_rules() {
    # ... remove IPv4 rules ...

    # Remove IPv6 rules if present
    remove_ipv6_brain_rules

    # ... save state ...
}
```

**Integration in `verify_sovereign_rules()`**:

```bash
verify_sovereign_rules() {
    local ipv4_count
    ipv4_count=$(count_brain_rules)

    local ipv6_count=0
    if detect_ipv6_active && check_ip6tables_available; then
        ipv6_count=$(count_ipv6_brain_rules)
    fi

    # IPv4 rules: at least 6
    if [[ $ipv4_count -lt 6 ]]; then
        return 1
    fi

    # IPv6 rules: at least 4 (if IPv6 active)
    if detect_ipv6_active; then
        if [[ $ipv6_count -lt 4 ]]; then
            return 1
        fi
    fi

    return 0
}
```

---

#### C.3: Implement IPv6 Gate Checker in Backend

**File**: `backend/app/modules/sovereign_mode/ipv6_gate.py` (NEW)

```python
"""
IPv6 Gate Checker

Verifies IPv6 enforcement in sovereign mode.
"""

import subprocess
from typing import Literal, Optional
from loguru import logger
from pydantic import BaseModel, Field
from datetime import datetime


class IPv6GateResult(BaseModel):
    """Result of IPv6 gate check."""

    status: Literal["pass", "fail", "not_applicable"]
    ipv6_active: bool
    policy: str
    firewall_rules_applied: bool = False
    ip6tables_available: bool = False
    error: Optional[str] = None
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class IPv6GateChecker:
    """
    Check IPv6 enforcement for sovereign mode.

    Verifies:
    1. IPv6 is detected (active or not)
    2. If active, ip6tables is available
    3. If active, firewall rules are applied
    """

    def __init__(self, policy: str = "block"):
        """
        Initialize IPv6 gate checker.

        Args:
            policy: IPv6 policy (block, allowlist, off)
        """
        self.policy = policy

    def _check_ipv6_active(self) -> bool:
        """
        Check if IPv6 is active on host.

        Returns:
            True if IPv6 addresses found
        """
        try:
            result = subprocess.run(
                ["ip", "-6", "addr", "show"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                # Check if there are any inet6 addresses (not just ::1)
                lines = result.stdout.splitlines()
                for line in lines:
                    if "inet6" in line and "scope global" in line:
                        return True

            return False

        except Exception as e:
            logger.warning(f"Failed to check IPv6 status: {e}")
            return False

    def _check_ip6tables_available(self) -> bool:
        """
        Check if ip6tables command is available.

        Returns:
            True if ip6tables exists
        """
        try:
            result = subprocess.run(
                ["which", "ip6tables"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0

        except Exception:
            return False

    def _check_ipv6_rules_applied(self) -> bool:
        """
        Check if IPv6 firewall rules are applied.

        Returns:
            True if brain-sovereign-ipv6 rules found
        """
        try:
            result = subprocess.run(
                ["ip6tables", "-L", "DOCKER-USER", "-n"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                return "brain-sovereign-ipv6" in result.stdout

            return False

        except Exception:
            return False

    async def check(self) -> IPv6GateResult:
        """
        Perform IPv6 gate check.

        Returns:
            IPv6GateResult with status and details
        """
        ipv6_active = self._check_ipv6_active()

        # If IPv6 not active, gate check not applicable
        if not ipv6_active:
            logger.info("IPv6 not active, gate check not applicable")
            return IPv6GateResult(
                status="not_applicable",
                ipv6_active=False,
                policy=self.policy,
            )

        # If policy is "off", also not applicable
        if self.policy == "off":
            logger.warning("IPv6 is active but policy is 'off' (security risk)")
            return IPv6GateResult(
                status="not_applicable",
                ipv6_active=True,
                policy=self.policy,
            )

        # IPv6 is active and policy requires blocking
        # Check if ip6tables is available
        ip6tables_available = self._check_ip6tables_available()

        if not ip6tables_available:
            error_msg = (
                "IPv6 is active but ip6tables is not available. "
                "Cannot enforce IPv6 blocking. "
                "Install iptables package or disable IPv6 on the host."
            )
            logger.error(error_msg)
            return IPv6GateResult(
                status="fail",
                ipv6_active=True,
                policy=self.policy,
                ip6tables_available=False,
                error=error_msg,
            )

        # Check if rules are applied
        rules_applied = self._check_ipv6_rules_applied()

        if not rules_applied:
            error_msg = (
                "IPv6 is active and ip6tables is available, "
                "but firewall rules are not applied. "
                "Run: sudo scripts/sovereign-fw.sh apply sovereign"
            )
            logger.error(error_msg)
            return IPv6GateResult(
                status="fail",
                ipv6_active=True,
                policy=self.policy,
                ip6tables_available=True,
                firewall_rules_applied=False,
                error=error_msg,
            )

        # All checks passed
        logger.info("IPv6 gate check passed: IPv6 is blocked")
        return IPv6GateResult(
            status="pass",
            ipv6_active=True,
            policy=self.policy,
            ip6tables_available=True,
            firewall_rules_applied=True,
        )


# Singleton
_ipv6_gate_checker: Optional[IPv6GateChecker] = None


def get_ipv6_gate_checker() -> IPv6GateChecker:
    """Get singleton IPv6 gate checker instance."""
    global _ipv6_gate_checker
    if _ipv6_gate_checker is None:
        # Get policy from environment
        import os
        policy = os.getenv("BRAIN_SOVEREIGN_IPV6_POLICY", "block")
        _ipv6_gate_checker = IPv6GateChecker(policy=policy)
    return _ipv6_gate_checker
```

---

#### C.4: Integrate IPv6 Gate Check in Mode Change

**File**: `backend/app/modules/sovereign_mode/service.py`

**Modifications**:

1. Import IPv6 gate checker:
```python
from backend.app.modules.sovereign_mode.ipv6_gate import (
    get_ipv6_gate_checker,
    IPv6GateResult,
)
```

2. Add IPv6 check in `change_mode()`:
```python
async def change_mode(
    self,
    request: ModeChangeRequest,
    triggered_by: str = "manual",
) -> SovereignMode:
    # ... existing code ...

    # If switching to SOVEREIGN mode, verify IPv6 gate
    if new_mode == OperationMode.SOVEREIGN and not request.force:
        ipv6_checker = get_ipv6_gate_checker()
        ipv6_result = await ipv6_checker.check()

        # Audit IPv6 gate check
        self._audit(
            event_type=AuditEventType.IPV6_GATE_CHECKED.value,
            success=(ipv6_result.status in ["pass", "not_applicable"]),
            severity=AuditSeverity.INFO if ipv6_result.status == "pass" else AuditSeverity.ERROR,
            reason=f"IPv6 gate check: {ipv6_result.status}",
            ipv6_related=True,
            ipv6_active=ipv6_result.ipv6_active,
            policy=ipv6_result.policy,
            ip6tables_available=ipv6_result.ip6tables_available,
            rules_applied=ipv6_result.firewall_rules_applied,
        )

        if ipv6_result.status == "fail":
            # Emit critical audit event
            self._audit(
                event_type=AuditEventType.IPV6_GATE_FAILED.value,
                success=False,
                severity=AuditSeverity.CRITICAL,
                reason="IPv6 gate check failed",
                error=ipv6_result.error,
                ipv6_related=True,
            )

            raise ValueError(
                f"Cannot activate Sovereign Mode: IPv6 gate check failed. "
                f"Reason: {ipv6_result.error}"
            )

    # ... rest of existing code ...
```

---

#### C.5: Extend `verify-sovereign-mode.sh` with IPv6 Tests

**File**: `scripts/verify-sovereign-mode.sh`

**Add new test layer**:

```bash
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
```

**Add to main execution**:

```bash
main() {
    # ... existing tests ...

    test_firewall_rules
    test_docker_network
    test_egress_blocking
    test_internal_connectivity
    test_backend_api
    test_network_probe
    test_ipv6_gate  # NEW

    # ... summary ...
}
```

---

#### C.6: Error Messages & User Guidance

**Display when IPv6 gate check fails**:

```
❌ ERROR: Cannot activate Sovereign Mode

Reason: IPv6 is active on the host but ip6tables is not available.

This creates a security bypass risk - IPv6 traffic would not be blocked.

Solutions:
1. Install ip6tables:
   sudo apt-get update && sudo apt-get install iptables

2. Disable IPv6 on host:
   sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1
   sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1

   Make persistent: Add to /etc/sysctl.conf:
   net.ipv6.conf.all.disable_ipv6 = 1
   net.ipv6.conf.default.disable_ipv6 = 1

3. Change policy to 'off' (NOT RECOMMENDED - security bypass risk):
   Edit .env: BRAIN_SOVEREIGN_IPV6_POLICY=off
   Restart backend

Current Status:
- IPv6 Active: Yes
- ip6tables Available: No
- Policy: block
- Rules Applied: N/A
```

---

### Phase B: DMZ Gateway Architecture

#### B.1: Create `docker-compose.dmz.yml`

**File**: `docker-compose.dmz.yml` (NEW)

```yaml
# BRAiN DMZ Gateway Services
# Separate compose project for internet-facing connectors

version: '3.8'

services:
  telegram_gateway:
    build:
      context: ./dmz/telegram_gateway
      dockerfile: Dockerfile
    container_name: brain-dmz-telegram
    environment:
      - BRAIN_API_URL=http://host.docker.internal:8000
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - DMZ_MODE=enabled
    restart: unless-stopped
    networks:
      - dmz_network
    # NO ACCESS to brain_internal network

  # Future: Add more DMZ services (WhatsApp, Discord, etc.)

networks:
  dmz_network:
    driver: bridge
    internal: false  # Allows internet access
```

---

#### B.2: Network Isolation

**Modify `docker-compose.yml`**:

Ensure DMZ services **cannot** access `brain_internal` network.

DMZ services communicate with Core only via HTTP API at `http://host.docker.internal:8000`.

---

#### B.3: Create `backend/app/modules/dmz_control/`

**Files**:
- `__init__.py`
- `service.py`
- `router.py`
- `schemas.py`

**`service.py`**:

```python
"""
DMZ Control Service

Manages DMZ gateway services lifecycle.
"""

import subprocess
from loguru import logger
from typing import Optional


class DMZControlService:
    """Control DMZ gateway docker compose."""

    COMPOSE_FILE = "docker-compose.dmz.yml"

    async def get_status(self) -> dict:
        """Get DMZ gateway status."""
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", self.COMPOSE_FILE, "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                # Parse container status
                # ... implementation ...
                return {"enabled": True, "containers": []}
            else:
                return {"enabled": False, "containers": []}

        except Exception as e:
            logger.error(f"Failed to get DMZ status: {e}")
            return {"enabled": False, "error": str(e)}

    async def stop_dmz(self):
        """Stop DMZ gateway services."""
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", self.COMPOSE_FILE, "down"],
                capture_output=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.info("DMZ gateway stopped")
                return True
            else:
                logger.error(f"Failed to stop DMZ: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to stop DMZ: {e}")
            return False

    async def start_dmz(self):
        """Start DMZ gateway services."""
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", self.COMPOSE_FILE, "up", "-d"],
                capture_output=True,
                timeout=60,
            )

            if result.returncode == 0:
                logger.info("DMZ gateway started")
                return True
            else:
                logger.error(f"Failed to start DMZ: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to start DMZ: {e}")
            return False


# Singleton
_dmz_control_service: Optional[DMZControlService] = None


def get_dmz_control_service() -> DMZControlService:
    """Get singleton DMZ control service."""
    global _dmz_control_service
    if _dmz_control_service is None:
        _dmz_control_service = DMZControlService()
    return _dmz_control_service
```

---

#### B.4: Implement Sovereign Mode DMZ Enforcement

**Modify `backend/app/modules/sovereign_mode/service.py`**:

```python
from backend.app.modules.dmz_control.service import get_dmz_control_service

async def change_mode(
    self,
    request: ModeChangeRequest,
    triggered_by: str = "manual",
) -> SovereignMode:
    # ... existing code ...

    # Stop DMZ if switching to SOVEREIGN
    if new_mode == OperationMode.SOVEREIGN:
        dmz_service = get_dmz_control_service()
        dmz_stopped = await dmz_service.stop_dmz()

        if dmz_stopped:
            self._audit(
                event_type=AuditEventType.DMZ_STOPPED.value,
                success=True,
                reason="DMZ stopped for sovereign mode",
                severity=AuditSeverity.INFO,
            )
        else:
            logger.warning("Failed to stop DMZ gateway")

    # Start DMZ if switching to CONNECTED (and enabled)
    elif new_mode == OperationMode.ONLINE:
        import os
        if os.getenv("BRAIN_DMZ_ENABLED", "false").lower() == "true":
            dmz_service = get_dmz_control_service()
            dmz_started = await dmz_service.start_dmz()

            if dmz_started:
                self._audit(
                    event_type=AuditEventType.DMZ_STARTED.value,
                    success=True,
                    reason="DMZ started for connected mode",
                    severity=AuditSeverity.INFO,
                )

    # ... rest of existing code ...
```

---

## 📝 NOTES

### Assumptions
1. IPv6 is currently NOT active on the host (no addresses, ip6tables missing)
2. DMZ services do not exist yet (Telegram bot, etc.)
3. Physical Gateway module is **internal** (not DMZ)
4. Redaction security is implicit (no secrets in event reasons/metadata)

### Security Principles
- **Fail-Closed**: If IPv6 active but cannot be blocked → reject Sovereign Mode
- **No Silent Failures**: Clear error messages with remediation steps
- **Audit Everything**: All gate checks, mode changes, DMZ operations logged

### Testing Requirements
- Run `scripts/verify-sovereign-mode.sh` after implementation
- Test IPv6 gate check with and without IPv6 active
- Test DMZ stop/start in sovereign mode transitions

---

## 🚀 NEXT STEPS

1. **Implement C.2-C.6** (IPv6 Firewall & Gate Check)
2. **Implement B.1-B.4** (DMZ Gateway)
3. **Run Verification Suite**
4. **Update Documentation**
5. **Final Commit & PR**

---

**END OF IMPLEMENTATION TODO**
