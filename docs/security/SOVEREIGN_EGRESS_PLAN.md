# Sovereign Egress Enforcement - Implementation Plan

**Version:** 1.0
**Date:** 2025-12-24
**Status:** Planning Complete

---

## Executive Summary

This plan implements **fail-closed egress enforcement** for BRAiN's Sovereign Mode using **host-level iptables rules** in the DOCKER-USER chain. This provides defense-in-depth beyond the existing application-level NetworkGuard.

**Key Objectives:**
1. ✅ Block all internet egress from BRAiN containers in sovereign mode
2. ✅ Allow localhost + RFC1918 private networks
3. ✅ Simple command interface (apply/check/status/rollback)
4. ✅ Persist rules across reboots via systemd
5. ✅ Integrate with existing `/api/sovereign-mode/network/check` endpoint

**Defense Layers:**
- **Layer 1 (existing):** Application-level NetworkGuard (Python httpx interceptor)
- **Layer 2 (NEW):** Docker network isolation (internal networks)
- **Layer 3 (NEW):** Host iptables firewall (DOCKER-USER chain)

---

## Architecture

### Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│  Host System (Linux)                                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  iptables DOCKER-USER Chain                          │   │
│  │  ┌─────────────────────────────────────────────┐     │   │
│  │  │ Rules:                                       │     │   │
│  │  │ 1. ACCEPT established,related                │     │   │
│  │  │ 2. ACCEPT to 127.0.0.0/8 (localhost)        │     │   │
│  │  │ 3. ACCEPT to 10.0.0.0/8                     │     │   │
│  │  │ 4. ACCEPT to 172.16.0.0/12                  │     │   │
│  │  │ 5. ACCEPT to 192.168.0.0/16                 │     │   │
│  │  │ 6. DROP all other egress (SOVEREIGN)        │     │   │
│  │  └─────────────────────────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Docker Networks                                      │   │
│  │  ┌──────────────────┐  ┌──────────────────┐          │   │
│  │  │ brain_internal   │  │ brain_gateway    │          │   │
│  │  │ (internal:true)  │  │ (optional)       │          │   │
│  │  │                  │  │                  │          │   │
│  │  │ - backend        │  │ - connector_hub  │          │   │
│  │  │ - postgres       │  │ - ollama (?)     │          │   │
│  │  │ - redis          │  │                  │          │   │
│  │  │ - qdrant         │  │                  │          │   │
│  │  │ - control_deck   │  │                  │          │   │
│  │  │ - axe_ui         │  │                  │          │   │
│  │  │ - openwebui      │  │                  │          │   │
│  │  └──────────────────┘  └──────────────────┘          │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Rule Logic (DOCKER-USER Chain)

```bash
# In sovereign mode, for traffic FROM BRAiN containers:

1. ACCEPT if connection is ESTABLISHED,RELATED (return traffic)
2. ACCEPT if destination is localhost (127.0.0.0/8, ::1)
3. ACCEPT if destination is RFC1918 private:
   - 10.0.0.0/8
   - 172.16.0.0/12
   - 192.168.0.0/16
4. DROP everything else (public internet)

# Traffic matching is done by:
- Source: Docker bridge subnet (e.g., 172.17.0.0/16 or brain_internal subnet)
- Direction: Egress (container -> internet)
```

---

## Phase 1: MVP (Immediate Deployment)

### Goals
- ✅ Host firewall enforcement via iptables
- ✅ Simple command-line management interface
- ✅ Docker network separation (basic)
- ✅ Manual verification procedures

### Deliverables

#### 1.1 Firewall Script: `scripts/sovereign-fw.sh`

**Location:** `/root/BRAiN/scripts/sovereign-fw.sh`

**Subcommands:**

| Command | Description | Example |
|---------|-------------|---------|
| `status` | Show current mode and rules | `sudo ./sovereign-fw.sh status` |
| `apply sovereign` | Enable sovereign mode rules | `sudo ./sovereign-fw.sh apply sovereign` |
| `apply connected` | Disable sovereign mode (allow all) | `sudo ./sovereign-fw.sh apply connected` |
| `check` | Verify firewall state (exit code 0/1) | `sudo ./sovereign-fw.sh check` |
| `rollback` | Remove all BRAiN firewall rules | `sudo ./sovereign-fw.sh rollback` |

**Features:**
- Idempotent (safe to run multiple times)
- Automatic Docker network detection
- State file tracking (`/var/lib/brain/firewall-state`)
- Comprehensive logging to `/var/log/brain-firewall.log`
- Safety checks (backup existing rules before changes)

**Dependencies:**
- `iptables` (required)
- `docker` command (to inspect networks)
- `jq` (for JSON parsing - optional, falls back to grep)

#### 1.2 Docker Compose Update

**File:** `docker-compose.yml`

**Changes:**
```yaml
# Add at bottom
networks:
  brain_internal:
    driver: bridge
    internal: true  # NO direct internet access
    ipam:
      config:
        - subnet: 172.20.0.0/16

  brain_gateway:  # Optional - for services that NEED egress
    driver: bridge
    internal: false

# Update all core services
services:
  backend:
    networks:
      - brain_internal

  postgres:
    networks:
      - brain_internal

  redis:
    networks:
      - brain_internal

  # ... etc
```

**Impact:**
- ⚠️ Breaking change if external services expect to reach containers directly
- Requires testing inter-service communication
- May need port mapping adjustments

#### 1.3 Documentation

**File:** `docs/sovereign_egress_enforcement.md`

**Sections:**
1. **Overview** - Why host firewall is needed
2. **Quick Start** - Enable/disable commands
3. **Verification** - How to test sovereign mode
4. **Rollback** - Emergency procedures
5. **Troubleshooting** - Common issues
6. **Integration** - How it works with NetworkGuard

---

## Phase 2: Stabilization (Follow-up)

### Goals
- ✅ Persist rules across reboots
- ✅ Automated network probing
- ✅ Backend integration with gate status

### Deliverables

#### 2.1 Systemd Service

**File:** `/etc/systemd/system/brain-firewall.service`

**Purpose:**
- Auto-apply sovereign mode rules on boot
- Optionally read mode from `/etc/brain/firewall.conf`

**Example:**
```ini
[Unit]
Description=BRAiN Sovereign Mode Firewall
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/root/BRAiN/scripts/sovereign-fw.sh apply sovereign
RemainAfterExit=yes
ExecStop=/root/BRAiN/scripts/sovereign-fw.sh rollback

[Install]
WantedBy=multi-user.target
```

#### 2.2 Automated Network Probe

**Script:** `scripts/network-probe.sh`

**Purpose:**
- Curl to known public IPs (1.1.1.1, 8.8.8.8)
- Should FAIL in sovereign mode
- Returns exit code 0 (isolated) or 1 (has internet)

**Usage:**
```bash
docker exec brain-backend-dev bash /app/scripts/network-probe.sh
# Exit 0 = sovereign enforced
# Exit 1 = has internet access (BAD in sovereign)
```

#### 2.3 Backend Integration

**File:** `backend/app/modules/sovereign_mode/network_guard.py`

**New Method:**
```python
async def check_host_firewall_state() -> dict:
    """
    Check if host firewall is enforcing sovereign mode.

    Executes sovereign-fw.sh check command via subprocess.

    Returns:
        {
            "firewall_enabled": bool,
            "mode": "sovereign" | "connected" | "unknown",
            "rules_count": int,
            "last_check": datetime
        }
    """
```

**Update Endpoint:**
- `GET /api/sovereign-mode/network/check`
- Add `firewall_state` to response

---

## Phase 3: Hardening (Optional)

### Goals
- ✅ Separate connector services to gateway network
- ✅ Per-service egress exceptions (allowlists)
- ✅ Audit events for firewall changes

### Deliverables

#### 3.1 Connector Separation

**Purpose:** Allow ONLY connector services to access internet

**Implementation:**
```yaml
# docker-compose.yml
services:
  connector_hub:
    networks:
      - brain_internal  # Can talk to backend
      - brain_gateway   # Can reach internet (if needed)

  # Firewall rules allow brain_gateway subnet to egress
```

#### 3.2 Per-Service Allowlists

**Config File:** `/etc/brain/firewall-allowlist.json`

**Example:**
```json
{
  "services": {
    "ollama": {
      "allowed_domains": ["huggingface.co", "ollama.ai"],
      "allowed_cidrs": ["104.26.0.0/20"]
    },
    "connector_hub": {
      "allowed_domains": ["api.github.com", "*.openai.com"]
    }
  }
}
```

**Implementation:**
- Parse allowlist file
- Generate specific iptables rules per service IP

#### 3.3 Audit Logging

**Integration:** Sovereign mode audit log

**Events:**
- `firewall_apply_sovereign` - Rules enabled
- `firewall_apply_connected` - Rules disabled
- `firewall_rollback` - Rules removed
- `firewall_check_failed` - Verification failed

---

## Implementation Assumptions

1. **Docker Compose project name:** `brain` (or auto-detected via `docker network ls`)
2. **Network subnet:** Auto-detected via `docker network inspect brain_internal`
3. **User has sudo:** Required for iptables modifications
4. **Fallback subnet:** If detection fails, assume `172.17.0.0/16` (default Docker bridge)
5. **No existing DOCKER-USER rules:** Script will warn if rules exist
6. **Internet access for localhost:** Always allowed (127.0.0.0/8, ::1)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaks internal service comms | HIGH | Allowlist RFC1918 + test thoroughly |
| Can't detect Docker network | MEDIUM | Fallback to default bridge subnet |
| Rules persist incorrectly | MEDIUM | Rollback command removes all BRAiN rules |
| Containers bypass via VPN | LOW | Out of scope - physical network isolation needed |
| User accidentally locks themselves out | LOW | SSH access unaffected (not Docker traffic) |

---

## Testing Strategy

### Phase 1 Tests

1. **Baseline Test (Connected Mode)**
   ```bash
   # Start with internet access
   sudo ./sovereign-fw.sh apply connected
   docker exec brain-backend-dev curl -I https://www.google.com
   # Expected: HTTP 200 OK
   ```

2. **Sovereign Mode Test**
   ```bash
   # Enable sovereign
   sudo ./sovereign-fw.sh apply sovereign
   docker exec brain-backend-dev curl -I https://www.google.com
   # Expected: Connection timeout or refused
   ```

3. **Localhost Test**
   ```bash
   # Sovereign mode enabled
   docker exec brain-backend-dev curl -I http://localhost:8000/health
   # Expected: HTTP 200 OK (localhost allowed)
   ```

4. **Internal Network Test**
   ```bash
   # Sovereign mode enabled
   docker exec brain-backend-dev curl -I http://postgres:5432
   # Expected: Success (internal network allowed)
   ```

5. **Status Check**
   ```bash
   sudo ./sovereign-fw.sh status
   # Expected: Show current mode + rule count
   ```

### Phase 2 Tests

6. **Boot Persistence Test**
   ```bash
   # Enable systemd service
   sudo systemctl enable brain-firewall.service
   sudo reboot

   # After reboot
   sudo ./sovereign-fw.sh status
   # Expected: Sovereign mode still active
   ```

7. **Automated Probe Test**
   ```bash
   docker exec brain-backend-dev bash /app/scripts/network-probe.sh
   echo $?
   # Expected: Exit 0 (no internet)
   ```

8. **Backend Integration Test**
   ```bash
   curl http://localhost:8000/api/sovereign-mode/network/check
   # Expected: JSON with firewall_state.firewall_enabled: true
   ```

---

## Rollback Plan

### Emergency Rollback (If Things Break)

```bash
# Step 1: Remove all firewall rules
sudo /root/BRAiN/scripts/sovereign-fw.sh rollback

# Step 2: Verify rules removed
sudo iptables -L DOCKER-USER -n -v

# Step 3: Restart Docker if needed
sudo systemctl restart docker

# Step 4: Restart BRAiN containers
cd /root/BRAiN
docker compose restart

# Step 5: Verify services work
curl http://localhost:8000/health
```

### Restore Default Docker Compose

```bash
# If network changes break things
cd /root/BRAiN
git checkout docker-compose.yml
docker compose down
docker compose up -d
```

---

## Success Criteria

### Phase 1 (MVP)
- ✅ `sovereign-fw.sh` script created and tested
- ✅ Can apply/remove rules without errors
- ✅ Containers CANNOT reach internet in sovereign mode
- ✅ Containers CAN reach internal services in sovereign mode
- ✅ Documentation complete with examples
- ✅ Manual verification tests pass

### Phase 2 (Stabilization)
- ✅ Systemd service persists rules across reboot
- ✅ Automated probe test works
- ✅ Backend endpoint shows real firewall state

### Phase 3 (Hardening)
- ✅ Connector services can egress selectively
- ✅ Audit log captures firewall changes

---

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1 | Immediate | Script + docs + basic network isolation |
| Phase 2 | +1 day | Systemd service + backend integration |
| Phase 3 | Optional | Advanced allowlists + audit |

---

## Next Steps

1. ✅ Review and approve this plan
2. ➡️ Proceed to Phase 1 implementation
3. ➡️ Test thoroughly in dev environment
4. ➡️ Document findings
5. ➡️ Deploy to production (if approved)

---

**Plan Status:** ✅ COMPLETE
**Ready for Implementation:** YES
**Approver:** Claude DevOps Team
**Date:** 2025-12-24
