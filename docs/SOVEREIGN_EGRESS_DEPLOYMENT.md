# Sovereign Egress Enforcement - Deployment Guide

**Version:** 1.0.0
**Date:** 2025-12-24
**Status:** ✅ PRODUCTION READY

---

## Executive Summary

This document provides **complete deployment instructions** for BRAiN's Sovereign Mode Egress Enforcement system. All Phase 1 and Phase 2 deliverables are complete and ready for production deployment.

**What Has Been Delivered:**

✅ **Phase 1 (MVP):**
- Host firewall script with iptables enforcement
- Docker Compose network isolation
- Comprehensive user documentation

✅ **Phase 2 (Stabilization):**
- Systemd service for boot persistence
- Automated network probe script
- Backend API integration with firewall state

📋 **Phase 3 (Optional Hardening):**
- Per-service allowlists
- Connector gateway separation
- IPv6 support

---

## Files Changed/Added

### Scripts (New)

| File | Purpose | Executable | Status |
|------|---------|------------|--------|
| `scripts/sovereign-fw.sh` | Main firewall management script | ✓ | ✅ Ready |
| `scripts/network-probe.sh` | Automated network isolation test | ✓ | ✅ Ready |
| `scripts/verify-sovereign-mode.sh` | Comprehensive verification suite | ✓ | ✅ Ready |
| `scripts/brain-firewall.service` | Systemd unit file | - | ✅ Ready |

### Docker Compose (Modified)

| File | Changes | Breaking | Status |
|------|---------|----------|--------|
| `docker-compose.yml` | Added `brain_internal` network, assigned all services to it | No* | ✅ Ready |

*Breaking only if external services expect direct container access (rare)

### Documentation (New)

| File | Purpose | Status |
|------|---------|--------|
| `docs/SOVEREIGN_EGRESS_PLAN.md` | Complete implementation plan | ✅ Complete |
| `docs/sovereign_egress_enforcement.md` | User guide and troubleshooting | ✅ Complete |
| `docs/SOVEREIGN_EGRESS_DEPLOYMENT.md` | This file - deployment checklist | ✅ Complete |

### Backend Code (Modified)

| File | Changes | Breaking | Status |
|------|---------|----------|--------|
| `backend/app/modules/sovereign_mode/network_guard.py` | Added `check_host_firewall_state()` function | No | ✅ Ready |
| `backend/app/modules/sovereign_mode/schemas.py` | Added `firewall_state` field to `NetworkCheckResult` | No | ✅ Ready |
| `backend/app/modules/sovereign_mode/router.py` | Enhanced `/network/check` endpoint | No | ✅ Ready |

---

## Deployment Steps

### Prerequisites

1. **Root/sudo access** on the deployment server
2. **BRAiN services running** via Docker Compose
3. **iptables installed** (standard on most Linux systems)
4. **Docker version:** 20.10+ (for network features)

### Step 1: Update Repository

```bash
# Navigate to BRAiN directory
cd /root/BRAiN  # or your deployment path

# Pull latest changes (if deploying from git)
git pull origin main  # or your branch

# Verify scripts are present
ls -lh scripts/sovereign-fw.sh
ls -lh scripts/network-probe.sh
ls -lh scripts/verify-sovereign-mode.sh

# Make scripts executable (should already be done)
chmod +x scripts/sovereign-fw.sh
chmod +x scripts/network-probe.sh
chmod +x scripts/verify-sovereign-mode.sh
```

**Expected output:**
```
-rwxr-xr-x 1 root root  15K scripts/sovereign-fw.sh
-rwxr-xr-x 1 root root  4.2K scripts/network-probe.sh
-rwxr-xr-x 1 root root  10K scripts/verify-sovereign-mode.sh
```

### Step 2: Update Docker Compose

```bash
# Stop running containers
docker compose down

# Verify docker-compose.yml has brain_internal network
grep -A 5 "brain_internal" docker-compose.yml

# Expected output should show:
#   brain_internal:
#     driver: bridge
#     internal: false
#     ipam: ...

# Start services with new network
docker compose up -d

# Verify network created
docker network inspect brain_internal

# Verify containers are on new network
docker inspect brain-backend | grep -A 5 Networks
```

**Expected output:**
```
"Networks": {
    "brain_internal": {
        "IPAddress": "172.20.0.x",
        ...
    }
}
```

### Step 3: Test Services (Pre-Firewall)

Before applying firewall rules, ensure all services work:

```bash
# Test backend health
curl http://localhost:8000/health
# Expected: {"status":"healthy",...}

# Test Control Deck
curl -I http://localhost:3000
# Expected: HTTP/1.1 200 OK

# Test from container (should have internet BEFORE firewall)
docker exec brain-backend curl -I https://www.google.com
# Expected: HTTP/2 200 (or similar - internet access works)
```

### Step 4: Apply Sovereign Mode Firewall

```bash
# Apply sovereign mode
sudo ./scripts/sovereign-fw.sh apply sovereign
```

**Expected output:**
```
ℹ Applying sovereign mode firewall rules...
ℹ Target subnet: 172.20.0.0/16
✓ Applied 6 sovereign mode rules
✓ Mode applied successfully: sovereign
```

### Step 5: Verify Enforcement

```bash
# Check firewall status
sudo ./scripts/sovereign-fw.sh status
```

**Expected output:**
```
ℹ BRAiN Sovereign Firewall Status

  Mode:            sovereign
  Status:          ENFORCED
  Protected Subnet: 172.20.0.0/16
  Last Changed:    2025-12-24 10:30:00
  Active Rules:    6

ℹ Current Rules:
  1    ACCEPT     ...  /* brain-sovereign:established */
  2    ACCEPT     ...  /* brain-sovereign:localhost */
  3    ACCEPT     ...  /* brain-sovereign:rfc1918-10 */
  4    ACCEPT     ...  /* brain-sovereign:rfc1918-172 */
  5    ACCEPT     ...  /* brain-sovereign:rfc1918-192 */
  6    DROP       ...  /* brain-sovereign:drop-egress */
```

**Run verification check:**
```bash
sudo ./scripts/sovereign-fw.sh check
echo $?
# Expected: 0 (success)
```

### Step 6: Test Egress Blocking

```bash
# Test 1: Internet should be BLOCKED
docker exec brain-backend curl -I --connect-timeout 5 https://www.google.com
# Expected: Connection timeout or "Couldn't connect to server"

# Test 2: Localhost should still work
docker exec brain-backend curl -I http://localhost:8000/health
# Expected: HTTP/1.1 200 OK

# Test 3: Internal services should work
docker exec brain-backend curl -I http://backend:8000/health
# Expected: HTTP/1.1 200 OK
```

### Step 7: Run Comprehensive Verification

```bash
# Run full test suite
sudo ./scripts/verify-sovereign-mode.sh
```

**Expected output:**
```
╔══════════════════════════════════════════════════════════╗
║  BRAiN Sovereign Mode Verification Suite v1.0.0         ║
╚══════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAYER 1: Host Firewall (iptables DOCKER-USER)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Testing: Firewall script exists ... ✓ PASS
Testing: Firewall mode is 'sovereign' ... ✓ PASS
Testing: Firewall rules active (≥6 rules) ... ✓ PASS
Testing: Firewall self-check passes ... ✓ PASS
Testing: DOCKER-USER chain has BRAiN rules ... ✓ PASS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAYER 2: Docker Network Isolation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Testing: brain_internal network exists ... ✓ PASS
Testing: Network subnet is 172.20.0.0/16 ... ✓ PASS
Testing: Backend container on brain_internal ... ✓ PASS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAYER 3: Egress Blocking Verification
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Testing: Block egress to 8.8.8.8 (Google DNS) ... ✓ PASS
Testing: Block egress to 1.1.1.1 (Cloudflare) ... ✓ PASS
Testing: Block egress to www.google.com ... ✓ PASS
Testing: Block egress to api.github.com ... ✓ PASS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAYER 4: Internal Network Connectivity
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Testing: Allow access to localhost ... ✓ PASS
Testing: Allow access to backend service ... ✓ PASS
Testing: Allow access to postgres service ... ✓ PASS
Testing: Allow access to redis service ... ✓ PASS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Passed:   17
Failed:   0
Warnings: 0

Success Rate: 100%

╔══════════════════════════════════════════════════════════╗
║  ✓ SOVEREIGN MODE VERIFIED                              ║
║  All critical tests passed. Egress is blocked.          ║
╚══════════════════════════════════════════════════════════╝
```

### Step 8: Test Backend API Integration (Phase 2)

```bash
# Test network check endpoint
curl http://localhost:8000/api/sovereign-mode/network/check | jq '.'
```

**Expected output:**
```json
{
  "is_online": false,
  "latency_ms": null,
  "check_method": "http",
  "checked_at": "2025-12-24T10:30:00Z",
  "error": "Connection timeout",
  "firewall_state": {
    "firewall_enabled": true,
    "mode": "sovereign",
    "rules_count": 6,
    "last_check": "2025-12-24T10:30:00Z",
    "error": null
  }
}
```

**Key fields to verify:**
- `is_online`: should be `false` (network is blocked)
- `firewall_state.firewall_enabled`: should be `true`
- `firewall_state.mode`: should be `"sovereign"`
- `firewall_state.rules_count`: should be `6` or more

### Step 9: Enable Boot Persistence (Optional but Recommended)

```bash
# Install systemd service
sudo cp scripts/brain-firewall.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (auto-start on boot)
sudo systemctl enable brain-firewall.service

# Start service now
sudo systemctl start brain-firewall.service

# Check status
sudo systemctl status brain-firewall.service
```

**Expected output:**
```
● brain-firewall.service - BRAiN Sovereign Mode Firewall Enforcement
     Loaded: loaded (/etc/systemd/system/brain-firewall.service; enabled)
     Active: active (exited) since ...
```

**Test boot persistence:**
```bash
# Reboot server
sudo reboot

# After reboot, check if firewall is still active
sudo /root/BRAiN/scripts/sovereign-fw.sh status

# Should show: Mode: sovereign, Status: ENFORCED
```

### Step 10: Monitor and Maintain

```bash
# View firewall logs
sudo tail -f /var/log/brain-firewall.log

# View iptables backups
ls -lh /var/lib/brain/iptables-backup-*.rules

# Check systemd service logs
sudo journalctl -u brain-firewall.service -f
```

---

## Quick Command Reference

### Daily Operations

```bash
# Check status
sudo ./scripts/sovereign-fw.sh status

# Verify enforcement
sudo ./scripts/sovereign-fw.sh check

# Quick test
docker exec brain-backend curl -I --connect-timeout 5 https://1.1.1.1
# Should timeout (good)
```

### Switching Modes

```bash
# Enable sovereign mode
sudo ./scripts/sovereign-fw.sh apply sovereign

# Disable sovereign mode (allow internet)
sudo ./scripts/sovereign-fw.sh apply connected

# Emergency rollback
sudo ./scripts/sovereign-fw.sh rollback
```

### Troubleshooting

```bash
# View iptables rules
sudo iptables -L DOCKER-USER -n -v

# View logs
sudo tail -100 /var/log/brain-firewall.log

# Restore backup
sudo iptables-restore < /var/lib/brain/iptables-backup-<timestamp>.rules

# Restart Docker (if network issues)
sudo systemctl restart docker
```

---

## Rollback Procedure

If you need to rollback the deployment:

### Step 1: Remove Firewall Rules

```bash
sudo /root/BRAiN/scripts/sovereign-fw.sh rollback
```

### Step 2: Disable Systemd Service (if installed)

```bash
sudo systemctl stop brain-firewall.service
sudo systemctl disable brain-firewall.service
sudo rm /etc/systemd/system/brain-firewall.service
sudo systemctl daemon-reload
```

### Step 3: Revert Docker Compose (if needed)

```bash
cd /root/BRAiN

# Restore old docker-compose.yml from git
git checkout HEAD~1 -- docker-compose.yml

# Recreate networks
docker compose down
docker compose up -d
```

### Step 4: Verify Rollback

```bash
# Check firewall status (should be unknown or connected)
sudo ./scripts/sovereign-fw.sh status

# Check internet access (should work)
docker exec brain-backend curl -I https://www.google.com
# Expected: HTTP 200 OK

# Check BRAiN services
curl http://localhost:8000/health
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Read `docs/SOVEREIGN_EGRESS_PLAN.md`
- [ ] Read `docs/sovereign_egress_enforcement.md`
- [ ] Backup current Docker Compose configuration
- [ ] Backup current iptables rules: `sudo iptables-save > /tmp/iptables-backup.rules`
- [ ] Document current network topology
- [ ] Schedule maintenance window (30-60 minutes)
- [ ] Notify stakeholders of deployment

### Phase 1 Deployment

- [ ] Step 1: Update repository
- [ ] Step 2: Update Docker Compose
- [ ] Step 3: Test services (pre-firewall)
- [ ] Step 4: Apply sovereign mode firewall
- [ ] Step 5: Verify enforcement
- [ ] Step 6: Test egress blocking
- [ ] Step 7: Run comprehensive verification
- [ ] Step 8: Test backend API integration

### Phase 2 Deployment (Optional)

- [ ] Step 9: Enable boot persistence (systemd)
- [ ] Test reboot persistence
- [ ] Configure monitoring/alerts

### Post-Deployment

- [ ] Monitor logs for 24-48 hours
- [ ] Verify all BRAiN features work as expected
- [ ] Document any custom allowlists needed
- [ ] Update runbooks with sovereign mode procedures
- [ ] Schedule regular verification tests (weekly/monthly)

### Validation

- [ ] All tests in `verify-sovereign-mode.sh` pass
- [ ] Internet egress is blocked from containers
- [ ] Internal services are accessible
- [ ] Backend API reports sovereign mode correctly
- [ ] Firewall survives Docker restart
- [ ] Firewall survives server reboot (if systemd enabled)

---

## Known Limitations & Assumptions

### Limitations

1. **IPv4 Only:** Current implementation only blocks IPv4 egress. IPv6 requires `ip6tables` rules (Phase 3).

2. **Container-Level Only:** Firewall rules only affect **traffic from Docker containers**, not the host OS itself.

3. **No DNS Blocking:** DNS queries may still reach private DNS servers. For full isolation, configure `/etc/resolv.conf` in containers.

4. **VPN/Tunnels:** If containers have VPN clients, they could bypass firewall. Audit container images.

5. **Requires sudo:** All firewall operations require root privileges.

### Assumptions

1. **Docker Compose project name:** `brain` (or auto-detected)

2. **Network subnet:** `172.20.0.0/16` (or auto-detected from `brain_internal` network)

3. **Deployment path:** `/root/BRAiN` (configurable)

4. **Default Docker bridge:** `172.17.0.0/16` used as fallback if detection fails

5. **No existing DOCKER-USER rules:** Script assumes clean DOCKER-USER chain (warns if rules exist)

---

## Security Considerations

### What This Protects Against

✅ Data exfiltration via HTTP/HTTPS
✅ Unauthorized external API calls
✅ Model weight downloads from internet
✅ Command & Control (C2) communication
✅ Accidental internet access in offline mode

### What This Does NOT Protect Against

❌ Physical network access (cable plugging)
❌ Host OS compromise (can disable firewall)
❌ Container escape (can modify iptables)
❌ VPN/tunnel clients in containers
❌ Internal network attacks (RFC1918 allowed)

### Hardening Recommendations

1. **Enable Docker network isolation:**
   ```yaml
   networks:
     brain_internal:
       internal: true  # Double layer with firewall
   ```

2. **Audit container images:**
   - Scan for VPN clients, SSH clients, tunneling tools
   - Use minimal base images (Alpine, Distroless)

3. **Enable SELinux/AppArmor:**
   - Add additional MAC layer for container confinement

4. **Monitor firewall logs:**
   - Set up alerts for firewall rule changes
   - Watch for unexpected DROP events

5. **Restrict Docker socket:**
   - Never mount `/var/run/docker.sock` in containers
   - Use Docker socket proxy if needed

6. **Regular verification:**
   - Run `verify-sovereign-mode.sh` weekly
   - Alert on failures

---

## Support & Troubleshooting

### Common Issues

See `docs/sovereign_egress_enforcement.md` section "Troubleshooting" for detailed solutions.

**Quick Fixes:**

- **"Docker network not found"** → Start containers first, then apply firewall
- **"Rules disappear after reboot"** → Enable systemd service (Step 9)
- **"Internal services not reachable"** → Check RFC1918 rules, verify subnet detection
- **"Script timeout"** → Check for other instances running, remove lock file

### Getting Help

1. Check logs: `sudo tail -f /var/log/brain-firewall.log`
2. Run verification: `sudo ./scripts/verify-sovereign-mode.sh`
3. Review documentation:
   - `docs/sovereign_egress_enforcement.md`
   - `docs/SOVEREIGN_EGRESS_PLAN.md`
4. Check CLAUDE.md for architecture details
5. Contact support with logs and error messages

---

## Next Steps

### Phase 3 (Optional Future Enhancements)

1. **Per-Service Allowlists:**
   - Configuration file: `/etc/brain/firewall-allowlist.json`
   - Specific domains/CIDRs per service
   - Example: Allow Ollama to reach huggingface.co

2. **IPv6 Support:**
   - Implement `ip6tables` rules
   - Mirror IPv4 logic for IPv6

3. **Connector Gateway Network:**
   - Separate network for connectors that need internet
   - Fine-grained egress control

4. **Audit Event Integration:**
   - Log firewall changes to sovereign mode audit log
   - Alert on unauthorized changes

5. **Web UI:**
   - Control Deck integration
   - Toggle sovereign mode from UI
   - Real-time firewall status dashboard

---

## Appendix: Complete File Manifest

### Scripts

```
scripts/
├── sovereign-fw.sh            # Main firewall management (Phase 1)
├── network-probe.sh           # Automated network probe (Phase 2)
├── verify-sovereign-mode.sh   # Comprehensive verification (Phase 2)
└── brain-firewall.service     # Systemd unit file (Phase 2)
```

### Documentation

```
docs/
├── SOVEREIGN_EGRESS_PLAN.md       # Implementation plan
├── sovereign_egress_enforcement.md # User guide
└── SOVEREIGN_EGRESS_DEPLOYMENT.md  # This file
```

### Modified Files

```
docker-compose.yml                            # Added brain_internal network
backend/app/modules/sovereign_mode/
├── network_guard.py                          # Added check_host_firewall_state()
├── schemas.py                                # Added firewall_state field
└── router.py                                 # Enhanced /network/check endpoint
```

### Runtime Files (Created on Deploy)

```
/var/lib/brain/
├── firewall-state                # Current firewall mode/state
└── iptables-backup-<timestamp>.rules  # Automatic backups

/var/log/
└── brain-firewall.log            # Firewall operation logs

/etc/systemd/system/
└── brain-firewall.service        # Systemd service (if installed)
```

---

## Contact & Approval

**Developed By:** Claude DevOps Team
**Version:** 1.0.0
**Date:** 2025-12-24
**Status:** ✅ PRODUCTION READY

**Sign-Off:**
- [ ] Technical Review: _________________
- [ ] Security Review: _________________
- [ ] Deployment Approval: _________________

---

**END OF DEPLOYMENT GUIDE**
