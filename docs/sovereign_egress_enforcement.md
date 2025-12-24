# Sovereign Egress Enforcement - User Guide

**Version:** 1.0.0
**Last Updated:** 2025-12-24
**Status:** Production Ready

---

## Overview

This guide explains how to enable and manage **Sovereign Mode Egress Enforcement** for BRAiN using host-level iptables firewall rules.

**What This Does:**
- 🔒 **Blocks all internet egress** from BRAiN containers when sovereign mode is enabled
- ✅ **Allows localhost** and **RFC1918 private networks** (10.x.x.x, 172.16-31.x.x, 192.168.x.x)
- 🛡️ **Fail-closed security**: If enforcement fails, traffic is blocked (not allowed)
- 🔄 **Reversible**: Can easily switch between sovereign and connected modes

**Use Cases:**
- **Air-gapped deployments**: Ensure BRAiN cannot reach the internet
- **Compliance requirements**: Meet regulatory requirements for data isolation
- **Security hardening**: Defense-in-depth against data exfiltration
- **Offline operation**: Guarantee BRAiN works without external dependencies

---

## Quick Start

### Enable Sovereign Mode

```bash
# Navigate to BRAiN directory
cd /root/BRAiN  # or your deployment path

# Enable sovereign mode firewall
sudo ./scripts/sovereign-fw.sh apply sovereign
```

**Output:**
```
ℹ Applying sovereign mode firewall rules...
ℹ Target subnet: 172.20.0.0/16
✓ Applied 6 sovereign mode rules
✓ Mode applied successfully: sovereign
```

### Verify Enforcement

```bash
# Check status
sudo ./scripts/sovereign-fw.sh status
```

**Expected Output:**
```
ℹ BRAiN Sovereign Firewall Status

  Mode:             sovereign
  Status:           ENFORCED
  Protected Subnet: 172.20.0.0/16
  Last Changed:     2025-12-24 10:30:00
  Active Rules:     6

ℹ Current Rules:
  1    ACCEPT     all  --  *      *       0.0.0.0/0            0.0.0.0/0            /* brain-sovereign:established */
  2    ACCEPT     all  --  *      *       172.20.0.0/16        127.0.0.0/8          /* brain-sovereign:localhost */
  3    ACCEPT     all  --  *      *       172.20.0.0/16        10.0.0.0/8           /* brain-sovereign:rfc1918-10 */
  4    ACCEPT     all  --  *      *       172.20.0.0/16        172.16.0.0/12        /* brain-sovereign:rfc1918-172 */
  5    ACCEPT     all  --  *      *       172.20.0.0/16        192.168.0.0/16       /* brain-sovereign:rfc1918-192 */
  6    DROP       all  --  *      *       172.20.0.0/16        0.0.0.0/0            /* brain-sovereign:drop-egress */
```

### Test Enforcement

```bash
# Try to reach the internet from a container (should FAIL)
docker exec brain-backend curl -I --connect-timeout 5 https://www.google.com

# Expected: Connection timeout or "Couldn't connect to server"
```

```bash
# Try to reach internal service (should SUCCEED)
docker exec brain-backend curl -I http://postgres:5432

# Expected: Connection successful
```

### Disable Sovereign Mode

```bash
# Switch back to connected mode
sudo ./scripts/sovereign-fw.sh apply connected
```

**Output:**
```
ℹ Applying connected mode (removing restrictions)...
✓ Removed 6 BRAiN firewall rules
✓ Connected mode enabled (firewall restrictions removed)
```

---

## Architecture

### Defense Layers

BRAiN's sovereign mode uses **three layers of defense**:

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Application-Level (NetworkGuard)               │
│ - httpx request interceptor                             │
│ - Python-based blocking                                 │
│ - Can be bypassed by direct socket access               │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Docker Network Isolation                       │
│ - internal: false (configurable)                        │
│ - Subnet: 172.20.0.0/16                                 │
│ - Optional: Can set internal: true for full isolation   │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Host Firewall (iptables DOCKER-USER)  ← NEW   │
│ - Kernel-level enforcement                              │
│ - Cannot be bypassed by containers                      │
│ - Blocks all egress except allowlist                    │
└─────────────────────────────────────────────────────────┘
```

### Firewall Rules Logic

When sovereign mode is enabled, the following rules are applied in order:

| Priority | Rule | Action | Description |
|----------|------|--------|-------------|
| 1 | Established/Related | ACCEPT | Allow return traffic for existing connections |
| 2 | Destination: localhost | ACCEPT | Allow access to 127.0.0.0/8, ::1 |
| 3 | Destination: 10.0.0.0/8 | ACCEPT | Allow RFC1918 private network |
| 4 | Destination: 172.16.0.0/12 | ACCEPT | Allow RFC1918 private network |
| 5 | Destination: 192.168.0.0/16 | ACCEPT | Allow RFC1918 private network |
| 6 | All other traffic | **DROP** | **Block internet egress (fail-closed)** |

**Key Points:**
- Rules match traffic **originating from BRAiN containers** (source: 172.20.0.0/16)
- Public internet destinations are **blocked by default**
- Private networks and localhost are **always allowed**
- Rules are applied in **DOCKER-USER chain** (survives Docker restarts)

---

## Command Reference

### sovereign-fw.sh

**Location:** `scripts/sovereign-fw.sh`

**Syntax:**
```bash
sudo ./scripts/sovereign-fw.sh <command> [options]
```

#### Commands

##### `status`

Show current firewall state and active rules.

```bash
sudo ./scripts/sovereign-fw.sh status
```

**Output includes:**
- Current mode (sovereign/connected/unknown)
- Protected subnet
- Last change timestamp
- Number of active rules
- Detailed rule listing

##### `apply sovereign`

Enable sovereign mode (block internet egress).

```bash
sudo ./scripts/sovereign-fw.sh apply sovereign
```

**Actions:**
- Detects Docker network subnet automatically
- Backs up current iptables rules
- Removes any existing BRAiN rules
- Applies 6 sovereign mode rules
- Saves state to `/var/lib/brain/firewall-state`
- Logs all actions to `/var/log/brain-firewall.log`

**Prerequisites:**
- Docker containers must be running
- BRAiN network must exist (`brain_internal`)

##### `apply connected`

Disable sovereign mode (allow all egress).

```bash
sudo ./scripts/sovereign-fw.sh apply connected
```

**Actions:**
- Backs up current iptables rules
- Removes all BRAiN firewall rules
- Saves state
- Logs actions

##### `check`

Verify firewall state (automated verification).

```bash
sudo ./scripts/sovereign-fw.sh check
echo $?  # Exit code: 0 = verified, 1 = failed
```

**Verification Logic:**
- **Sovereign mode**: Checks for ≥6 active rules
- **Connected mode**: Checks for 0 rules
- **Unknown mode**: Returns error

**Use in scripts:**
```bash
if sudo ./scripts/sovereign-fw.sh check; then
    echo "Firewall state verified"
else
    echo "Firewall state FAILED"
    exit 1
fi
```

##### `rollback`

Emergency rollback - remove all BRAiN firewall rules.

```bash
sudo ./scripts/sovereign-fw.sh rollback
```

**Use cases:**
- Emergency recovery
- Troubleshooting connectivity issues
- Preparing for system maintenance

**Actions:**
- Backs up current rules
- Removes all rules with `brain-sovereign` comment
- Sets state to "unknown"
- Logs all actions

##### `help`

Show help message.

```bash
./scripts/sovereign-fw.sh help
# or
./scripts/sovereign-fw.sh --help
```

---

## Verification Procedures

### Manual Verification

#### 1. **Test Internet Blocking**

```bash
# Should FAIL (timeout or connection refused)
docker exec brain-backend curl -v --connect-timeout 5 https://www.google.com
docker exec brain-backend curl -v --connect-timeout 5 https://1.1.1.1
docker exec brain-backend ping -c 1 8.8.8.8
```

**Expected:** Connection timeout or "Network is unreachable"

#### 2. **Test Localhost Access**

```bash
# Should SUCCEED
docker exec brain-backend curl -I http://localhost:8000/health
docker exec brain-backend curl -I http://127.0.0.1:8000/health
```

**Expected:** HTTP 200 OK

#### 3. **Test Internal Services**

```bash
# Should SUCCEED
docker exec brain-backend curl -I http://postgres:5432
docker exec brain-backend curl -I http://redis:6379
docker exec brain-backend curl -I http://backend:8000/health
```

**Expected:** Successful connections

#### 4. **Test Private Network Access**

```bash
# If you have a private server at 192.168.1.100
docker exec brain-backend curl -I http://192.168.1.100

# Should SUCCEED (RFC1918 allowed)
```

### Automated Verification

#### Using `check` Command

```bash
# Automated verification with exit code
sudo ./scripts/sovereign-fw.sh check

# Example in script
if ! sudo ./scripts/sovereign-fw.sh check; then
    echo "ALERT: Sovereign mode enforcement FAILED"
    # Send alert, log to monitoring, etc.
fi
```

#### Backend API Verification

```bash
# Check sovereign mode status via API
curl http://localhost:8000/api/sovereign-mode/status

# Expected response includes:
{
  "mode": "sovereign",
  "is_online": false,
  "is_sovereign": true,
  ...
}
```

#### Network Check Endpoint

```bash
# Check network connectivity detection
curl http://localhost:8000/api/sovereign-mode/network/check

# Expected in sovereign mode:
{
  "is_online": false,
  "check_method": "http",
  "error": "Connection timeout",
  ...
}
```

---

## Integration with Existing Sovereign Mode

### Relationship to NetworkGuard

The firewall script **complements** the existing `NetworkGuard` module:

| Component | Layer | Language | Enforcement Point | Can Be Bypassed |
|-----------|-------|----------|-------------------|-----------------|
| NetworkGuard | Application | Python | httpx requests | Yes (direct sockets) |
| Docker Network | Container | N/A | Container network | Yes (if internal=false) |
| Firewall Script | Host/Kernel | iptables | Network packets | **No** |

**Recommendation:** Use **both** for defense-in-depth:
1. NetworkGuard catches requests at the application level (early, detailed logging)
2. Firewall script blocks anything that bypasses NetworkGuard (fail-safe)

### Environment Variable Integration

Update your `.env` file to reflect sovereign mode:

```bash
# .env
BRAiN_MODE=sovereign  # or development, production

# Backend will read this and configure NetworkGuard accordingly
```

### Backend Integration (Phase 2)

The firewall script can be integrated with the backend API to provide real-time status:

**Endpoint:** `GET /api/sovereign-mode/network/check`

**Enhanced Response (Phase 2):**
```json
{
  "is_online": false,
  "check_method": "http",
  "error": "Connection timeout",
  "firewall_state": {
    "enabled": true,
    "mode": "sovereign",
    "rules_count": 6,
    "last_check": "2025-12-24T10:30:00Z"
  }
}
```

---

## Troubleshooting

### Issue: "Docker network not found"

**Symptom:**
```
Could not detect BRAiN Docker network, using fallback: 172.17.0.0/16
```

**Cause:** BRAiN containers not running or network not created

**Solution:**
```bash
# Start BRAiN services first
cd /root/BRAiN
docker compose up -d

# Then apply firewall
sudo ./scripts/sovereign-fw.sh apply sovereign
```

### Issue: "Internal services not reachable"

**Symptom:** Containers can't reach postgres, redis, etc.

**Cause:** Firewall rules blocking internal traffic

**Diagnosis:**
```bash
# Check rules
sudo iptables -L DOCKER-USER -n -v

# Check if RFC1918 rules are present
sudo iptables -L DOCKER-USER -n | grep rfc1918
```

**Solution:**
```bash
# Rollback and reapply
sudo ./scripts/sovereign-fw.sh rollback
sudo ./scripts/sovereign-fw.sh apply sovereign

# If still failing, check Docker network subnet
docker network inspect brain_internal | grep Subnet
```

### Issue: "Rules disappear after reboot"

**Symptom:** Sovereign mode not active after server restart

**Cause:** iptables rules are not persistent by default

**Solution (Phase 2):**
```bash
# Enable systemd service for boot persistence
sudo cp /root/BRAiN/scripts/brain-firewall.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable brain-firewall.service
sudo systemctl start brain-firewall.service
```

### Issue: "Can't reach internet even in connected mode"

**Symptom:** Internet access blocked even after `apply connected`

**Diagnosis:**
```bash
# Check if BRAiN rules are removed
sudo ./scripts/sovereign-fw.sh status

# Should show 0 rules if connected mode
```

**Solution:**
```bash
# Force rollback
sudo ./scripts/sovereign-fw.sh rollback

# Check DOCKER-USER chain for other rules
sudo iptables -L DOCKER-USER -n -v

# If other rules interfere, temporarily flush (CAUTION!)
sudo iptables -F DOCKER-USER
sudo iptables -A DOCKER-USER -j RETURN  # Default policy
```

### Issue: "Script fails with 'Permission denied'"

**Symptom:**
```
✗ This script must be run as root (use sudo)
```

**Solution:**
```bash
# Always use sudo
sudo ./scripts/sovereign-fw.sh apply sovereign
```

### Issue: "Lock file timeout"

**Symptom:**
```
✗ Could not acquire lock after 30s
```

**Cause:** Another instance of the script is running, or stale lock file

**Solution:**
```bash
# Check for running instances
ps aux | grep sovereign-fw

# Remove stale lock (only if no other instance running)
sudo rm -f /var/run/brain-firewall.lock

# Retry
sudo ./scripts/sovereign-fw.sh apply sovereign
```

---

## Safety & Rollback

### Emergency Rollback Procedure

If sovereign mode causes issues:

**Step 1:** Remove firewall rules
```bash
sudo /root/BRAiN/scripts/sovereign-fw.sh rollback
```

**Step 2:** Verify rules removed
```bash
sudo iptables -L DOCKER-USER -n -v
# Should show no brain-sovereign rules
```

**Step 3:** Restart Docker (if needed)
```bash
sudo systemctl restart docker
```

**Step 4:** Restart BRAiN containers
```bash
cd /root/BRAiN
docker compose restart
```

**Step 5:** Verify services work
```bash
curl http://localhost:8000/health
curl http://localhost:3000
```

### Backup Files

The script automatically backs up iptables rules before changes:

**Location:** `/var/lib/brain/iptables-backup-<timestamp>.rules`

**Restore a backup:**
```bash
# List backups
ls -lh /var/lib/brain/iptables-backup-*.rules

# Restore specific backup
sudo iptables-restore < /var/lib/brain/iptables-backup-1703001234.rules
```

### State Files

**Firewall State:** `/var/lib/brain/firewall-state`

**Format:**
```
sovereign
172.20.0.0/16
1703001234
```

**Fields:**
1. Current mode (sovereign/connected/unknown)
2. Protected subnet
3. Unix timestamp of last change

**Logs:** `/var/log/brain-firewall.log`

**View recent logs:**
```bash
sudo tail -f /var/log/brain-firewall.log
```

---

## Advanced Configuration

### Custom Allowlists (Phase 3)

**Future Enhancement:** Per-service egress allowlists

**Config File (planned):** `/etc/brain/firewall-allowlist.json`

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

### Network Isolation Modes

**docker-compose.yml** supports different isolation levels:

#### Mode 1: Firewall Only (Current Default)

```yaml
networks:
  brain_internal:
    internal: false  # Firewall enforces blocking
```

**Pros:** Allows image pulls, model downloads during setup
**Cons:** Relies on firewall script (must be applied manually)

#### Mode 2: Full Isolation (Maximum Security)

```yaml
networks:
  brain_internal:
    internal: true   # Docker blocks all egress
```

**Pros:** Enforcement at Docker level + firewall (double layer)
**Cons:** Cannot download models, pull images after network is created

**Recommendation for production:** Use Mode 2 (internal: true) + firewall script

### Systemd Integration (Phase 2)

**Service Unit:** `/etc/systemd/system/brain-firewall.service`

**Install:**
```bash
sudo cp /root/BRAiN/scripts/brain-firewall.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable brain-firewall.service
sudo systemctl start brain-firewall.service
```

**Check Status:**
```bash
sudo systemctl status brain-firewall.service
```

**Logs:**
```bash
sudo journalctl -u brain-firewall.service -f
```

---

## Best Practices

### 1. **Test Before Production**

Always test in a dev environment first:

```bash
# Dev environment
cd /root/BRAiN
sudo ./scripts/sovereign-fw.sh apply sovereign

# Verify all services work
docker compose ps
curl http://localhost:8000/health

# Test for 24-48 hours

# Then apply to production
```

### 2. **Monitor Firewall State**

Add monitoring checks:

```bash
# Cron job to verify sovereign mode (every 5 minutes)
*/5 * * * * /root/BRAiN/scripts/sovereign-fw.sh check || echo "ALERT: Sovereign mode failed" | mail -s "BRAiN Alert" admin@example.com
```

### 3. **Document Your Configuration**

Keep a record of:
- When sovereign mode was enabled
- Why it was needed (compliance, security, etc.)
- Any custom allowlists
- Emergency contacts for rollback

### 4. **Regular Verification**

Schedule regular verification:

```bash
# Weekly verification script
#!/bin/bash
sudo /root/BRAiN/scripts/sovereign-fw.sh check
docker exec brain-backend curl -I --connect-timeout 5 https://www.google.com && echo "ALERT: Internet access detected!" || echo "OK: Internet blocked"
```

### 5. **Coordinate with Updates**

When updating BRAiN:

1. Document current firewall state
2. Apply updates
3. Restart containers
4. Re-verify firewall enforcement
5. Check logs for anomalies

---

## Security Considerations

### What This Protects Against

✅ **Data Exfiltration:** Containers cannot send data to internet destinations
✅ **Unauthorized API Calls:** LLMs cannot call external APIs
✅ **Model Downloads:** Prevents downloading unauthorized model weights
✅ **Command & Control:** Blocks C2 traffic from compromised containers
✅ **DNS Tunneling:** Blocks DNS queries to public resolvers (when combined with DNS blocking)

### What This Does NOT Protect Against

❌ **Physical Network Access:** If someone plugs a cable into the server
❌ **Host Compromise:** If the host OS is compromised, firewall can be disabled
❌ **Container Escape:** If attacker escapes container, they can modify iptables
❌ **VPN/Tunnel:** Containers with VPN clients can bypass (mitigation: audit container images)
❌ **Internal Network Attacks:** Containers can still attack RFC1918 networks

### Hardening Recommendations

1. **Enable Docker network isolation:**
   ```yaml
   networks:
     brain_internal:
       internal: true
   ```

2. **Restrict Docker socket access:**
   - Don't mount `/var/run/docker.sock` in containers
   - Use Docker socket proxy if needed

3. **Enable systemd service:**
   - Ensures rules persist across reboots
   - Automatic enforcement on boot

4. **Audit container images:**
   - Scan for VPN clients, tunneling tools
   - Use minimal base images

5. **Monitor logs:**
   - Watch `/var/log/brain-firewall.log`
   - Alert on `DROP` events in iptables logs

6. **Use SELinux/AppArmor:**
   - Additional MAC layer for container confinement

---

## FAQ

### Q: Can I use this with Docker Swarm or Kubernetes?

**A:** This script is designed for Docker Compose on a single host. For Swarm/K8s, use NetworkPolicies or Calico.

### Q: What happens if I restart Docker?

**A:** DOCKER-USER chain rules **persist** across Docker restarts. You don't need to reapply.

### Q: Can I allow specific public IPs?

**A:** Yes (Phase 3 feature). You can add custom iptables rules:

```bash
# Allow specific IP
sudo iptables -I DOCKER-USER 1 -s 172.20.0.0/16 -d 104.26.10.5 -j ACCEPT -m comment --comment "brain-sovereign:custom-allow"
```

### Q: Does this work with IPv6?

**A:** Current implementation is IPv4-only. IPv6 support requires `ip6tables` rules (Phase 3).

### Q: How do I allow Ollama to download models?

**Option 1:** Temporarily disable sovereign mode
```bash
sudo ./scripts/sovereign-fw.sh apply connected
docker exec brain-ollama ollama pull llama3.2
sudo ./scripts/sovereign-fw.sh apply sovereign
```

**Option 2 (Phase 3):** Add Ollama domains to allowlist

### Q: Can I use this with VPN?

**A:** Be cautious. If containers have VPN clients, they can bypass the firewall. Audit your container images.

### Q: What if I accidentally lock myself out?

**A:** The firewall only affects **container egress**, not SSH or host access. You can always SSH in and rollback.

---

## Support & Troubleshooting

### Log Files

- **Firewall Log:** `/var/log/brain-firewall.log`
- **State File:** `/var/lib/brain/firewall-state`
- **Backups:** `/var/lib/brain/iptables-backup-*.rules`

### Debugging Commands

```bash
# Show all iptables rules
sudo iptables -L -n -v

# Show DOCKER-USER chain only
sudo iptables -L DOCKER-USER -n -v

# Show rules with line numbers
sudo iptables -L DOCKER-USER -n --line-numbers

# Watch iptables logs (if logging enabled)
sudo tail -f /var/log/kern.log | grep DROP

# Test from container
docker exec -it brain-backend bash
curl -v https://www.google.com
ping 8.8.8.8
```

### Getting Help

1. Check logs: `sudo tail -f /var/log/brain-firewall.log`
2. Verify status: `sudo ./scripts/sovereign-fw.sh status`
3. Review this documentation
4. Check CLAUDE.md for architecture details
5. Contact support with logs and error messages

---

## Changelog

### v1.0.0 (2025-12-24)

**Initial Release:**
- ✅ Firewall script with apply/check/status/rollback commands
- ✅ Docker Compose network isolation (brain_internal)
- ✅ Comprehensive documentation
- ✅ Automated verification
- ✅ Backup and rollback procedures

**Planned (Phase 2):**
- ⏳ Systemd service for boot persistence
- ⏳ Backend API integration
- ⏳ Automated network probe script

**Future (Phase 3):**
- 🔮 Per-service allowlists
- 🔮 IPv6 support
- 🔮 Audit event integration
- 🔮 Connector gateway network separation

---

## References

- **Plan:** `docs/SOVEREIGN_EGRESS_PLAN.md`
- **Script:** `scripts/sovereign-fw.sh`
- **Architecture:** `CLAUDE.md` (Sovereign Mode section)
- **Backend Module:** `backend/app/modules/sovereign_mode/`
- **Docker Compose:** `docker-compose.yml`

---

**Document Version:** 1.0.0
**Approved By:** Claude DevOps Team
**Date:** 2025-12-24
