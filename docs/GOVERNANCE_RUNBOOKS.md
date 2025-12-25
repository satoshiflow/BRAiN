# BRAiN Governance Incident Runbooks

**Version:** 1.0.0
**Date:** 2025-12-25
**Purpose:** Incident Response Procedures
**Scope:** Governance Layers G1, G2, G3
**Classification:** Internal - Operations Manual

---

## Table of Contents

1. [Overview](#overview)
2. [General Incident Response Process](#general-incident-response-process)
3. [Runbook 1: Owner Override Active](#runbook-1-owner-override-active)
4. [Runbook 2: Bundle Quarantine](#runbook-2-bundle-quarantine)
5. [Runbook 3: AXE Trust Tier Violation](#runbook-3-axe-trust-tier-violation)
6. [Runbook 4: Mode Switch Rollback](#runbook-4-mode-switch-rollback)
7. [Runbook 5: Audit Export Failure](#runbook-5-audit-export-failure)
8. [Post-Incident Procedures](#post-incident-procedures)
9. [Escalation Matrix](#escalation-matrix)

---

## Overview

This document provides **step-by-step incident response procedures** for BRAiN governance incidents. Each runbook follows a consistent structure:

- **Symptom**: How the incident manifests
- **Relevant Audit Events**: Which events to check
- **API Endpoints**: Diagnostic and remediation endpoints
- **Immediate Actions**: First response (< 5 minutes)
- **Decision Logic**: Triage and classification
- **Recovery Steps**: Detailed remediation procedures
- **Post-Incident Checks**: Verification and documentation

**Target Audience:**
- On-Call Engineers
- Platform Operations Team
- Security Operations Center (SOC)
- Incident Commanders

**Prerequisites:**
- Access to BRAiN backend API
- Access to Prometheus/Grafana dashboards
- Access to audit log query interface
- Understanding of governance architecture (G1-G4)

---

## General Incident Response Process

### Standard Operating Procedure

All governance incidents follow this high-level process:

```
1. DETECT     → Alert fires (see ALERTING_POLICY.md)
2. ACKNOWLEDGE → On-call acknowledges via PagerDuty/Alertmanager
3. TRIAGE     → Determine severity and runbook
4. INVESTIGATE → Gather context via API and audit log
5. CONTAIN    → Prevent escalation (if needed)
6. REMEDIATE  → Execute recovery steps
7. VERIFY     → Confirm resolution
8. DOCUMENT   → Create incident report
9. LEARN      → Post-incident review (for CRITICAL incidents)
```

### Incident Severity Matrix

| Severity | Response Time | Examples | Escalation |
|----------|---------------|----------|------------|
| **SEV-1 (CRITICAL)** | Immediate | Unauthorized override, Bundle quarantine, Trust violation | Security Team |
| **SEV-2 (HIGH)** | < 30 min | High failure rates, Mode switch issues | Senior Engineer |
| **SEV-3 (MEDIUM)** | < 2 hours | Operational anomalies | Platform Ops |
| **SEV-4 (LOW)** | Best effort | Informational | Platform Ops |

### Required Tools

**API Access:**
```bash
export BRAIN_API="http://localhost:8000"
export BRAIN_TOKEN="optional-if-auth-enabled"

# Test connectivity
curl $BRAIN_API/api/health
```

**Audit Log Query:**
```bash
# Get recent events
curl "$BRAIN_API/api/sovereign-mode/audit?limit=100"

# Filter by event type
curl "$BRAIN_API/api/sovereign-mode/audit?event_type=mode_changed"

# Export for analysis
curl -X POST "$BRAIN_API/api/sovereign-mode/audit/export" \
  -H "Content-Type: application/json" \
  -d '{"include_hash": true}'
```

**Metrics Query:**
```bash
# Prometheus metrics
curl "$BRAIN_API/api/sovereign-mode/metrics"

# JSON summary
curl "$BRAIN_API/api/sovereign-mode/metrics/summary"

# Governance status
curl "$BRAIN_API/api/sovereign-mode/governance/status"
```

---

## Runbook 1: Owner Override Active

**Alert ID:** GA-001
**Severity:** 🔴 SEV-1 (CRITICAL)
**Response Time:** Immediate (< 5 minutes)

### Symptom

- **Alert**: `GovernanceOverrideActive` firing in Prometheus
- **Metric**: `sovereign_override_active == 1`
- **Indication**: Governance 2-phase commit can be bypassed
- **Impact**: Mode switches may skip preflight checks

### Relevant Audit Events

| Event Type | Severity | Meaning |
|------------|----------|---------|
| `MODE_OVERRIDE_CREATED` | WARNING | Override created with reason and expiration |
| `MODE_OVERRIDE_CONSUMED` | WARNING | Override used for mode change |
| `MODE_OVERRIDE_EXPIRED` | INFO | Override expired without being used |
| `MODE_CHANGED` | INFO | Mode change (check if override was used) |

### API Endpoints

**Diagnostic:**
```bash
# Get governance status
GET /api/sovereign-mode/governance/status

# Query override-related audit events
GET /api/sovereign-mode/audit?event_type=mode_override_created&event_type=mode_override_consumed&limit=10

# Check metrics
GET /api/sovereign-mode/metrics/summary
```

**Remediation:**
```bash
# View current mode status
GET /api/sovereign-mode/status

# Check if override has been consumed (read-only)
# Note: No API to manually revoke override - must wait for expiration or consumption
```

### Immediate Actions (< 5 Minutes)

1. **Acknowledge Alert**
   ```bash
   # In PagerDuty or Alertmanager UI
   ```

2. **Query Audit Log for Override Creation**
   ```bash
   curl "$BRAIN_API/api/sovereign-mode/audit?event_type=mode_override_created&limit=1" | jq '.[0]'
   ```

   **Expected Output:**
   ```json
   {
     "timestamp": "2025-12-25T15:30:00.000000Z",
     "event_type": "mode_override_created",
     "severity": "WARNING",
     "reason": "Emergency network outage - switching to SOVEREIGN mode immediately",
     "metadata": {
       "override_duration_seconds": 1800,
       "expires_at": "2025-12-25T16:00:00.000000Z",
       "requested_by": "admin_user"
     }
   }
   ```

3. **Extract Key Information**
   - **Override Reason**: Must be >= 10 characters, specific
   - **Expires At**: Should be < 24 hours from creation
   - **Requested By**: Should be authorized admin/owner
   - **Duration**: Check if reasonable (1800s = 30 min is typical)

4. **Initial Risk Assessment**
   - ✅ **LOW RISK**: Legitimate reason, known admin, short duration (< 1h)
   - ⚠️ **MEDIUM RISK**: Generic reason, long duration (> 4h), off-hours
   - 🔴 **HIGH RISK**: Suspicious reason, unknown user, max duration (24h)

### Decision Logic

```
┌─────────────────────────────────────────┐
│ Override Created - Initial Assessment    │
└──────────────┬──────────────────────────┘
               │
       ┌───────▼────────┐
       │ Check Reason   │
       │ (>= 10 chars)  │
       └───────┬────────┘
               │
        ┌──────▼─────┐
        │ Legitimate?│
        └──────┬─────┘
          ┌────┴────┐
          │         │
      YES │         │ NO
          │         │
    ┌─────▼─┐   ┌──▼─────┐
    │ Monitor│   │Escalate│
    │ & Wait │   │Security│
    └─────┬──┘   └────────┘
          │
    ┌─────▼────────┐
    │ Wait for:    │
    │ - Consumption│
    │ - Expiration │
    └──────────────┘
```

**Legitimate Override Criteria:**
- **Reason**: Specific incident reference (e.g., "INC-2025-0042: Network failure")
- **User**: Authorized admin in on-call rotation
- **Duration**: Proportional to incident (emergency = short, maintenance = longer)
- **Time**: During business hours OR documented on-call incident

**Suspicious Override Criteria:**
- **Reason**: Generic ("testing", "emergency", "fix issue")
- **User**: Unknown or non-admin account
- **Duration**: Maximum 24h without justification
- **Time**: Off-hours without incident ticket

### Recovery Steps

#### Case A: Legitimate Override (Monitor)

**If override is legitimate:**

1. **Document in Incident Channel**
   ```
   Slack: #incidents
   Message: Override active - Reason: [REASON] - Expires: [TIME] - Tracking: [TICKET]
   ```

2. **Monitor Override Status**
   ```bash
   # Check every 5 minutes
   watch -n 300 "curl -s $BRAIN_API/api/sovereign-mode/metrics/summary | jq '.override_active'"
   ```

3. **Wait for Consumption or Expiration**
   - Override consumed: `MODE_OVERRIDE_CONSUMED` event will fire
   - Override expired: `MODE_OVERRIDE_EXPIRED` event will fire
   - Alert will auto-clear when `sovereign_override_active` returns to 0

4. **Verify Mode Change (if consumed)**
   ```bash
   # Check if mode changed successfully
   curl "$BRAIN_API/api/sovereign-mode/status" | jq '.mode'

   # Verify preflight was bypassed (check audit)
   curl "$BRAIN_API/api/sovereign-mode/audit?event_type=mode_changed&limit=1" | jq '.[0].metadata'
   ```

#### Case B: Suspicious Override (Investigate & Escalate)

**If override is suspicious:**

1. **Escalate to Security Team Immediately**
   ```
   Priority: P1 - SECURITY INCIDENT
   Channel: #security-incidents
   Subject: Unauthorized governance override detected
   ```

2. **Gather Evidence**
   ```bash
   # Export full audit trail
   curl -X POST "$BRAIN_API/api/sovereign-mode/audit/export" \
     -H "Content-Type: application/json" \
     -d '{
       "event_types": ["mode_override_created", "mode_override_consumed", "mode_changed"],
       "include_hash": true
     }' > /tmp/override_incident_audit.json

   # Capture current state
   curl "$BRAIN_API/api/sovereign-mode/status" > /tmp/override_incident_status.json
   curl "$BRAIN_API/api/sovereign-mode/governance/status" > /tmp/override_incident_governance.json
   ```

3. **DO NOT Attempt Manual Revocation**
   - No API exists to revoke override (by design - single-use, time-limited)
   - Override will expire automatically (max 24h)
   - If consumed, damage is already done (check MODE_CHANGED event)

4. **Containment Actions**
   - Monitor for override consumption
   - If not yet consumed and incident is severe: Consider emergency backend restart (nuclear option)
   - Document all actions in incident timeline

5. **Security Team Actions**
   - Identify user who created override
   - Verify user authorization
   - Check for account compromise
   - Review recent authentication logs
   - Initiate security investigation if unauthorized

### Post-Incident Checks

**After Override Cleared (consumed or expired):**

1. **Verify Override No Longer Active**
   ```bash
   curl "$BRAIN_API/api/sovereign-mode/metrics/summary" | jq '.override_active'
   # Expected: false
   ```

2. **Check Final Outcome**
   ```bash
   # Was override consumed?
   curl "$BRAIN_API/api/sovereign-mode/audit?event_type=mode_override_consumed&limit=1"

   # Did mode change succeed?
   curl "$BRAIN_API/api/sovereign-mode/audit?event_type=mode_changed&limit=1"
   ```

3. **Validate System State**
   ```bash
   # Check governance health
   curl "$BRAIN_API/api/sovereign-mode/governance/status" | jq '.overall_governance'
   # Expected: "healthy" or "warning" (not "critical")

   # Verify current mode is appropriate
   curl "$BRAIN_API/api/sovereign-mode/status" | jq '.mode'
   ```

4. **Document Incident**
   - **If Legitimate**: Note in ops log, no further action
   - **If Suspicious**: Create security incident report, initiate post-incident review

5. **Update Runbook (if needed)**
   - If new scenario encountered, update this runbook
   - If threshold adjustment needed, update ALERTING_POLICY.md

---

## Runbook 2: Bundle Quarantine

**Alert ID:** GA-002
**Severity:** 🔴 SEV-1 (CRITICAL)
**Response Time:** Immediate (< 5 minutes)

### Symptom

- **Alert**: `GovernanceBundleQuarantined` firing in Prometheus
- **Metric**: `increase(sovereign_bundle_quarantine_total[5m]) > 0`
- **Indication**: Bundle failed validation and was quarantined
- **Impact**: Bundle cannot be loaded; Sovereign mode may be unavailable

### Relevant Audit Events

| Event Type | Severity | Meaning |
|------------|----------|---------|
| `BUNDLE_QUARANTINED` | ERROR | Bundle quarantined due to validation failure |
| `BUNDLE_SIGNATURE_INVALID` | ERROR | Signature verification failed |
| `BUNDLE_KEY_UNTRUSTED` | WARNING | Bundle signed by key not in trusted keyring |
| `BUNDLE_UNSIGNED` | WARNING | Bundle has no signature (policy may allow) |

### API Endpoints

**Diagnostic:**
```bash
# List all bundles
GET /api/sovereign-mode/bundles

# Get bundle validation status
POST /api/sovereign-mode/bundles/{bundle_id}/validate

# Get bundle statistics
GET /api/sovereign-mode/bundles/stats

# Query quarantine events
GET /api/sovereign-mode/audit?event_type=bundle_quarantined
```

**Remediation:**
```bash
# Add trusted key to keyring
POST /api/sovereign-mode/keys

# Remove bundle (if confirmed malicious)
DELETE /api/sovereign-mode/bundles/{bundle_id}
```

### Immediate Actions (< 5 Minutes)

1. **Acknowledge Alert**

2. **Query Quarantine Event**
   ```bash
   curl "$BRAIN_API/api/sovereign-mode/audit?event_type=bundle_quarantined&limit=1" | jq '.[0]'
   ```

   **Expected Output:**
   ```json
   {
     "timestamp": "2025-12-25T15:45:00.000000Z",
     "event_type": "bundle_quarantined",
     "severity": "ERROR",
     "bundle_id": "llama3.2_prod_v1.2.3",
     "reason": "Validation failed: invalid signature",
     "metadata": {
       "quarantine_path": "storage/quarantine/llama3.2_prod_v1.2.3",
       "validation_errors": ["signature_invalid"],
       "signature_present": true,
       "key_trusted": false
     }
   }
   ```

3. **Extract Quarantine Details**
   - **Bundle ID**: Quarantined bundle identifier
   - **Quarantine Reason**: Why validation failed
   - **Quarantine Path**: Location of quarantined files
   - **Validation Errors**: Specific failures (signature, hash, key)

4. **Verify Bundle is Quarantined**
   ```bash
   # Check bundle status
   curl "$BRAIN_API/api/sovereign-mode/bundles" | jq '.[] | select(.id == "llama3.2_prod_v1.2.3")'

   # Expected: status == "quarantined"
   ```

5. **Check for Other Available Bundles**
   ```bash
   curl "$BRAIN_API/api/sovereign-mode/bundles" | jq '[.[] | select(.status == "validated" or .status == "loaded")] | length'

   # If 0: CRITICAL - No validated bundles available!
   # If > 0: WARNING - Other bundles available for Sovereign mode
   ```

### Decision Logic

```
┌──────────────────────────────┐
│ Bundle Quarantined           │
└───────────┬──────────────────┘
            │
    ┌───────▼────────┐
    │ Check Reason   │
    └───────┬────────┘
            │
     ┌──────┴──────┐
     │             │
  Signature    Hash
   Invalid    Mismatch
     │             │
┌────▼────┐   ┌────▼────┐
│Key Trust│   │File Corrupt│
│ Issue   │   │  Issue    │
└────┬────┘   └────┬──────┘
     │             │
┌────▼─────────────▼────┐
│ Investigate Source    │
└────┬──────────────────┘
     │
┌────▼─────┐
│ Legitimate│
│  or       │
│Malicious? │
└────┬──────┘
┌────┴────┐
│         │
Legit   Malicious
│         │
▼         ▼
Fix    Escalate
```

**Quarantine Reasons and Implications:**

| Reason | Likely Cause | Severity | Action |
|--------|--------------|----------|--------|
| **Signature Invalid** | Corrupted file, tampered bundle, wrong key | CRITICAL | Verify file hash, check source |
| **Key Untrusted** | Key rotation, new bundle source | WARNING | Add key to keyring if legitimate |
| **Signature Missing** | Unsigned bundle, policy violation | WARNING | Re-sign or update policy (dev only) |
| **Hash Mismatch** | File corruption, tampering | CRITICAL | Re-download from trusted source |

### Recovery Steps

#### Case A: Key Trust Issue (Legitimate New Key)

**If bundle is signed by new/rotated key:**

1. **Verify Bundle Source is Legitimate**
   ```bash
   # Check bundle origin (documentation, release notes, trusted source)
   # Verify key fingerprint matches official announcement
   ```

2. **Extract Public Key from Bundle Manifest**
   ```bash
   # Bundle is in quarantine, safe to inspect
   cd storage/quarantine/llama3.2_prod_v1.2.3
   cat manifest.json | jq '.signature.public_key'
   ```

3. **Verify Key Fingerprint**
   ```bash
   # Compute SHA256 of public key
   echo -n "<public_key_pem>" | shasum -a 256

   # Compare with official announcement/trusted source
   ```

4. **Add Trusted Key to Keyring** (if verified)
   ```bash
   curl -X POST "$BRAIN_API/api/sovereign-mode/keys" \
     -H "Content-Type: application/json" \
     -d '{
       "public_key": "-----BEGIN PUBLIC KEY-----\n...",
       "algorithm": "ed25519",
       "owner": "BRAiN Production Team",
       "expires_at": "2026-12-31T00:00:00Z"
     }'
   ```

5. **Re-Validate Bundle**
   ```bash
   # Trigger re-validation with new trusted key
   curl -X POST "$BRAIN_API/api/sovereign-mode/bundles/llama3.2_prod_v1.2.3/validate"

   # Check if quarantine cleared
   curl "$BRAIN_API/api/sovereign-mode/bundles" | jq '.[] | select(.id == "llama3.2_prod_v1.2.3") | .status'
   # Expected: "validated"
   ```

#### Case B: File Corruption (Re-Download)

**If bundle file is corrupted:**

1. **Verify Hash Mismatch**
   ```bash
   cd storage/quarantine/llama3.2_prod_v1.2.3
   sha256sum llama3.2_prod_v1.2.3.tar.gz

   # Compare with manifest.json expected hash
   cat manifest.json | jq '.hash'
   ```

2. **Remove Corrupted Bundle**
   ```bash
   curl -X DELETE "$BRAIN_API/api/sovereign-mode/bundles/llama3.2_prod_v1.2.3"
   ```

3. **Re-Download from Trusted Source**
   ```bash
   # Use official source, verify HTTPS, check certificate
   wget https://releases.brain.example.com/bundles/llama3.2_prod_v1.2.3.tar.gz \
     -O storage/models/bundles/llama3.2_prod_v1.2.3.tar.gz

   # Verify download integrity
   sha256sum storage/models/bundles/llama3.2_prod_v1.2.3.tar.gz
   ```

4. **Trigger Discovery and Validation**
   ```bash
   # Bundles are auto-discovered, or trigger via API
   curl "$BRAIN_API/api/sovereign-mode/bundles"

   # Should now show as "validated"
   ```

#### Case C: Malicious Bundle (Security Incident)

**If bundle appears tampered or malicious:**

1. **DO NOT Remove from Quarantine**
   - Preserve evidence for forensic analysis
   - Quarantined bundles cannot be loaded (fail-closed)

2. **Escalate to Security Team**
   ```
   Priority: P0 - CRITICAL SECURITY INCIDENT
   Subject: Potential supply chain attack - malicious bundle detected
   Evidence: storage/quarantine/[bundle_id]/
   ```

3. **Gather Forensic Evidence**
   ```bash
   # Export audit trail
   curl -X POST "$BRAIN_API/api/sovereign-mode/audit/export" \
     -d '{"event_types": ["bundle_quarantined", "bundle_signature_invalid"], "include_hash": true}' \
     > /tmp/bundle_quarantine_forensics.json

   # Create tarball of quarantine directory
   cd storage/quarantine
   tar -czf /tmp/quarantine_evidence_$(date +%Y%m%d_%H%M%S).tar.gz llama3.2_prod_v1.2.3/

   # DO NOT delete quarantine directory
   ```

4. **Security Team Actions**
   - Analyze bundle contents for malware
   - Trace bundle source and distribution path
   - Check for other affected bundles
   - Revoke signing key if compromised
   - Initiate incident response plan

5. **Communication**
   - Notify stakeholders of potential supply chain incident
   - Coordinate with bundle vendor/maintainer
   - Prepare public disclosure if needed

### Post-Incident Checks

1. **Verify Quarantine Cleared (if legitimate)**
   ```bash
   curl "$BRAIN_API/api/sovereign-mode/bundles/stats" | jq '.quarantined'
   # Expected: Previous count (no new quarantines)
   ```

2. **Confirm Validated Bundles Available**
   ```bash
   curl "$BRAIN_API/api/sovereign-mode/bundles" | jq '[.[] | select(.status == "validated")] | length'
   # Expected: At least 1 for Sovereign mode availability
   ```

3. **Test Sovereign Mode**
   ```bash
   # Attempt mode switch to verify bundle can load
   curl -X POST "$BRAIN_API/api/sovereign-mode/mode/preflight" \
     -d '{"target_mode": "sovereign"}'

   # Check bundle_trust_gate passes
   ```

4. **Document Incident**
   - Bundle ID and quarantine reason
   - Root cause (key rotation, corruption, attack)
   - Resolution (key added, re-download, escalated)
   - Lessons learned

---

## Runbook 3: AXE Trust Tier Violation

**Alert ID:** GA-003
**Severity:** 🔴 SEV-1 (CRITICAL)
**Response Time:** Immediate (< 5 minutes)

### Symptom

- **Alert**: `GovernanceAXETrustViolation` firing in Prometheus
- **Metric**: `increase(axe_trust_violation_total[5m]) > 0`
- **Indication**: EXTERNAL request to AXE was blocked
- **Impact**: Potential unauthorized access attempt; DMZ isolation working

### Relevant Audit Events

| Event Type | Severity | Meaning |
|------------|----------|---------|
| `AXE_TRUST_TIER_VIOLATION` | ERROR | EXTERNAL request blocked |
| `AXE_REQUEST_BLOCKED` | WARNING | Request blocked (any reason) |
| `AXE_REQUEST_RECEIVED` | INFO | Request received and classified |

### API Endpoints

**Diagnostic:**
```bash
# Query trust violations
GET /api/sovereign-mode/audit?event_type=axe_trust_tier_violation

# Get governance status (includes AXE violations count)
GET /api/sovereign-mode/governance/status

# Check DMZ status
GET /api/sovereign-mode/status
```

**Remediation:**
```bash
# Add DMZ gateway to allowlist (if legitimate)
# NOTE: No direct API for this - requires backend configuration change

# Block attacker IP at firewall level (manual)
```

### Immediate Actions (< 5 Minutes)

1. **Acknowledge Alert**

2. **Query Violation Event**
   ```bash
   curl "$BRAIN_API/api/sovereign-mode/audit?event_type=axe_trust_tier_violation&limit=5" | jq '.[]'
   ```

   **Expected Output:**
   ```json
   {
     "timestamp": "2025-12-25T16:00:00.000000Z",
     "event_type": "axe_trust_tier_violation",
     "severity": "ERROR",
     "reason": "EXTERNAL request blocked - source: 203.0.113.45",
     "metadata": {
       "source_ip": "203.0.113.45",
       "trust_tier": "external",
       "request_id": "req_abc123",
       "endpoint": "/api/axe/message"
     }
   }
   ```

3. **Extract Violation Details**
   - **Source IP**: Attacker or misconfigured client IP
   - **Trust Tier**: Should be "external"
   - **Request Count**: Single attempt or repeated scanning?
   - **Endpoint**: What AXE endpoint was targeted?

4. **Check Violation Pattern**
   ```bash
   # Count violations by source IP
   curl "$BRAIN_API/api/sovereign-mode/audit?event_type=axe_trust_tier_violation&limit=100" | \
     jq '[.[] | .metadata.source_ip] | group_by(.) | map({ip: .[0], count: length}) | sort_by(.count) | reverse'
   ```

   **Pattern Analysis:**
   - **Single violation, known IP**: Likely misconfiguration
   - **Multiple violations, same IP**: Possible attack or persistent misconfiguration
   - **Multiple violations, different IPs**: Coordinated attack or distributed scan

5. **Classify Incident**
   - 🟢 **Misconfiguration**: Known internal service, wrong IP/no DMZ auth
   - 🟡 **Reconnaissance**: External scan, low volume, no follow-up
   - 🔴 **Active Attack**: High volume, multiple IPs, persistent attempts

### Decision Logic

```
┌──────────────────────────────┐
│ AXE Trust Violation Detected │
└───────────┬──────────────────┘
            │
    ┌───────▼────────┐
    │ Check Source IP│
    └───────┬────────┘
            │
     ┌──────┴──────┐
     │             │
  Known IP    Unknown IP
     │             │
┌────▼────┐   ┌────▼────┐
│Internal │   │External │
│ Service │   │  Source │
└────┬────┘   └────┬────┘
     │             │
┌────▼────┐   ┌────▼────┐
│Misconfigured  │ Attack? │
│ Fix Config    │ Investigate
└───────────┘   └────┬────┘
                     │
              ┌──────┴──────┐
              │             │
          Low Volume   High Volume
              │             │
          ┌───▼───┐     ┌───▼───┐
          │Monitor│     │ Block │
          │ & Log │     │  IP   │
          └───────┘     └───────┘
```

### Recovery Steps

#### Case A: Misconfiguration (Known Internal Service)

**If source IP is known internal service:**

1. **Identify Service**
   ```bash
   # Check DNS reverse lookup
   dig -x 203.0.113.45

   # Check internal service registry
   # Expected: Known service name
   ```

2. **Determine Correct Configuration**
   - **Should use localhost**: If service runs on same host as BRAiN
   - **Should use DMZ gateway**: If service is external but trusted
   - **Should NOT access AXE**: If service has no legitimate need

3. **Fix Service Configuration**
   ```bash
   # Option A: Reconfigure service to use localhost
   # Edit service config: axe_endpoint = "http://127.0.0.1:8000/api/axe/message"

   # Option B: Configure DMZ gateway authentication
   # Add service to DMZ gateway allowlist (requires security approval)

   # Option C: Remove AXE integration (if not needed)
   ```

4. **Verify Fix**
   ```bash
   # Test from service host
   curl http://127.0.0.1:8000/api/axe/message \
     -H "Content-Type: application/json" \
     -d '{"message": "test"}'

   # Should succeed (source IP will be 127.0.0.1, trust tier LOCAL)
   ```

#### Case B: Reconnaissance Scan (Low Volume)

**If appears to be external reconnaissance:**

1. **Document Scan Details**
   ```bash
   # Count total violations from this IP
   curl "$BRAIN_API/api/sovereign-mode/audit?event_type=axe_trust_tier_violation" | \
     jq '[.[] | select(.metadata.source_ip == "203.0.113.45")] | length'

   # Check if scan is ongoing or completed
   # Recent violations (last 5 min)? Active scan
   # Old violations only? Completed scan
   ```

2. **Check for Other Suspicious Activity**
   ```bash
   # Query all blocked requests from this IP
   curl "$BRAIN_API/api/sovereign-mode/audit?event_type=axe_request_blocked" | \
     jq '.[] | select(.metadata.source_ip == "203.0.113.45")'
   ```

3. **Passive Monitoring** (if low volume, no escalation)
   - Trust tier enforcement is working (fail-closed)
   - No further action needed if violations stop
   - Log incident for security team awareness

4. **Optional: Block at Firewall** (if persistent)
   ```bash
   # Add iptables rule to drop packets from source
   sudo iptables -A INPUT -s 203.0.113.45 -j DROP

   # Or use cloud provider firewall/security groups
   ```

#### Case C: Active Attack (High Volume, Multiple IPs)

**If attack is detected:**

1. **IMMEDIATE: Escalate to Security Team**
   ```
   Priority: P0 - ACTIVE SECURITY INCIDENT
   Subject: Active attack on AXE endpoint detected
   Source IPs: [list]
   Volume: [count] violations in [timeframe]
   Status: Blocked by DMZ isolation (fail-closed)
   ```

2. **Gather Attack Intelligence**
   ```bash
   # Export full audit trail
   curl -X POST "$BRAIN_API/api/sovereign-mode/audit/export" \
     -d '{"event_types": ["axe_trust_tier_violation", "axe_request_blocked"], "include_hash": true}' \
     > /tmp/axe_attack_audit.json

   # Analyze source IPs
   cat /tmp/axe_attack_audit.json | jq '.metadata.source_ip' | sort | uniq -c | sort -rn

   # Check geographic distribution (if GeoIP available)
   ```

3. **Containment Actions**
   - **Firewall Block**: Block all attacker IPs at network edge
   - **Rate Limiting**: Implement rate limits at reverse proxy (Nginx)
   - **IP Allowlist**: Consider switching to allowlist-only mode
   - **DDoS Mitigation**: Activate CDN/DDoS protection if volume is extreme

4. **Security Team Actions**
   - Analyze attack vectors and techniques
   - Check for successful breaches (none expected - fail-closed)
   - Coordinate with network security team
   - File incident report
   - Consider public disclosure if severity warrants

5. **Communication**
   - Notify stakeholders of active attack
   - Update status page if service degradation
   - Coordinate with upstream providers if DDoS

### Post-Incident Checks

1. **Verify Violations Stopped**
   ```bash
   # Check last violation timestamp
   curl "$BRAIN_API/api/sovereign-mode/audit?event_type=axe_trust_tier_violation&limit=1" | jq '.[0].timestamp'

   # Should be > 10 minutes ago if attack/scan stopped
   ```

2. **Confirm AXE Availability**
   ```bash
   # Test AXE from localhost (should succeed)
   curl -X POST http://127.0.0.1:8000/api/axe/message \
     -H "Content-Type: application/json" \
     -d '{"message": "health check"}'

   # Test AXE from external (should fail with 403)
   curl -X POST http://PUBLIC_IP:8000/api/axe/message \
     -H "Content-Type: application/json" \
     -d '{"message": "test"}'

   # Expected: HTTP 403 Forbidden
   ```

3. **Review Firewall Rules**
   ```bash
   # List active blocks
   sudo iptables -L INPUT -n | grep DROP

   # Verify only attacker IPs are blocked
   # Remove temporary blocks after incident
   ```

4. **Document Incident**
   - Source IPs and attack volume
   - Classification (misconfiguration, scan, attack)
   - Actions taken (fix, monitor, block)
   - Lessons learned

---

## Runbook 4: Mode Switch Rollback

**Alert ID:** N/A (not directly alerted, but may occur during incidents)
**Severity:** 🟡 SEV-2 (HIGH)
**Response Time:** < 30 minutes

### Symptom

- **Mode change failed** and system rolled back to previous mode
- **Audit Event**: `MODE_COMMIT_FAILED` or `MODE_ROLLBACK`
- **Indication**: 2-Phase commit Phase 2 (commit) failed
- **Impact**: Mode switch did not complete, system remains in previous mode

### Relevant Audit Events

| Event Type | Severity | Meaning |
|------------|----------|---------|
| `MODE_COMMIT_FAILED` | ERROR | Commit phase failed, initiating rollback |
| `MODE_ROLLBACK` | WARNING | Rolled back to previous mode |
| `MODE_PREFLIGHT_FAILED` | WARNING | Preflight failed (before rollback) |
| `MODE_CHANGED` | INFO | Check if rollback succeeded |

### API Endpoints

**Diagnostic:**
```bash
# Get current mode status
GET /api/sovereign-mode/status

# Query mode change failures
GET /api/sovereign-mode/audit?event_type=mode_commit_failed&event_type=mode_rollback

# Run preflight check to diagnose issue
POST /api/sovereign-mode/mode/preflight
```

**Remediation:**
```bash
# Retry mode change (after fixing issue)
POST /api/sovereign-mode/mode

# Use override if critical and preflight can't be fixed quickly
POST /api/sovereign-mode/mode (with override parameters)
```

### Immediate Actions (< 5 Minutes)

1. **Query Rollback Event**
   ```bash
   curl "$BRAIN_API/api/sovereign-mode/audit?event_type=mode_rollback&limit=1" | jq '.[0]'
   ```

   **Expected Output:**
   ```json
   {
     "timestamp": "2025-12-25T16:15:00.000000Z",
     "event_type": "mode_rollback",
     "severity": "WARNING",
     "reason": "Mode change FAILED during commit - rolled back to ONLINE",
     "mode_before": "online",
     "mode_after": "online",
     "metadata": {
       "target_mode": "sovereign",
       "rollback_reason": "Failed to load bundle: llama3.2_prod_v1.2.3",
       "error": "Bundle validation failed"
     }
   }
   ```

2. **Identify Failure Point**
   - **Preflight passed** but **commit failed**: Issue occurred during commit phase
   - Common commit failures:
     - Bundle load failure
     - DMZ stop/start failure
     - Network guard configuration failure
     - Config save failure

3. **Verify Current Mode**
   ```bash
   curl "$BRAIN_API/api/sovereign-mode/status" | jq '.mode'

   # Should match mode_before (rollback successful)
   ```

4. **Check System Health**
   ```bash
   curl "$BRAIN_API/api/sovereign-mode/governance/status" | jq '.overall_governance'

   # Expected: "healthy" or "warning" (not "critical")
   ```

### Decision Logic

```
┌──────────────────────────────┐
│ Mode Change Failed - Rollback│
└───────────┬──────────────────┘
            │
    ┌───────▼────────┐
    │ Identify Cause │
    └───────┬────────┘
            │
     ┌──────┴──────┐
     │             │
  Bundle      DMZ/Network
   Failed      Failed
     │             │
┌────▼────┐   ┌────▼────┐
│Fix Bundle│  │Fix Infra│
│ or use   │  │ Config  │
│ Override │  │         │
└────┬────┘   └────┬────┘
     │             │
     └──────┬──────┘
            │
    ┌───────▼────────┐
    │ Retry Mode     │
    │ Change         │
    └────────────────┘
```

### Recovery Steps

#### Step 1: Diagnose Root Cause

1. **Check Commit Failure Details**
   ```bash
   curl "$BRAIN_API/api/sovereign-mode/audit?event_type=mode_commit_failed&limit=1" | jq '.[0].metadata'
   ```

2. **Common Failure Causes:**

   **Bundle Load Failure:**
   - Bundle validation failed during load
   - Bundle file corrupted or missing
   - Bundle quarantined (see Runbook 2)
   - Fix: Validate bundle, use alternative bundle, or re-download

   **DMZ Gateway Failure:**
   - DMZ failed to stop (switching to SOVEREIGN/OFFLINE)
   - DMZ failed to start (switching to ONLINE)
   - Fix: Check DMZ service status, restart if needed

   **Network Guard Failure:**
   - Failed to apply network blocking rules
   - IPv6 disable failed
   - Fix: Check iptables/firewall, verify permissions

   **Config Save Failure:**
   - Filesystem permission error
   - Disk full
   - Fix: Check disk space, verify write permissions

#### Step 2: Fix Underlying Issue

**Example: Bundle Load Failure**

```bash
# Identify which bundle failed
FAILED_BUNDLE=$(curl -s "$BRAIN_API/api/sovereign-mode/audit?event_type=mode_commit_failed&limit=1" | \
  jq -r '.[0].metadata.bundle_id')

# Validate bundle
curl -X POST "$BRAIN_API/api/sovereign-mode/bundles/$FAILED_BUNDLE/validate"

# Check validation result
curl "$BRAIN_API/api/sovereign-mode/bundles" | jq ".[] | select(.id == \"$FAILED_BUNDLE\")"

# If quarantined: Follow Runbook 2 (Bundle Quarantine)
# If missing: Re-download bundle
# If corrupted: Re-download bundle
```

**Example: DMZ Failure**

```bash
# Check DMZ status
curl "$BRAIN_API/api/sovereign-mode/status" | jq '.dmz_gateway_running'

# Check DMZ service logs
docker logs dmz_gateway

# Restart DMZ if needed
curl -X POST "$BRAIN_API/api/dmz/control" -d '{"action": "restart"}'
```

#### Step 3: Retry Mode Change

**After fixing the underlying issue:**

1. **Run Preflight Check**
   ```bash
   curl -X POST "$BRAIN_API/api/sovereign-mode/mode/preflight" \
     -H "Content-Type: application/json" \
     -d '{"target_mode": "sovereign"}'

   # Check if all gates pass
   ```

2. **Retry Mode Change**
   ```bash
   curl -X POST "$BRAIN_API/api/sovereign-mode/mode" \
     -H "Content-Type: application/json" \
     -d '{"target_mode": "sovereign"}'
   ```

3. **Monitor Commit Phase**
   ```bash
   # Watch for MODE_CHANGED event
   watch -n 5 "curl -s $BRAIN_API/api/sovereign-mode/audit?event_type=mode_changed&limit=1 | jq '.[0].timestamp'"

   # Should update with recent timestamp if successful
   ```

#### Step 4: Use Override (If Issue Can't Be Fixed Quickly)

**If mode change is operationally critical and issue can't be fixed immediately:**

1. **Create Override with Detailed Reason**
   ```bash
   curl -X POST "$BRAIN_API/api/sovereign-mode/mode" \
     -H "Content-Type: application/json" \
     -d '{
       "target_mode": "sovereign",
       "override_reason": "Emergency mode switch - bundle validation failing due to [SPECIFIC ISSUE] - ticket INC-2025-XXXX",
       "override_duration_seconds": 3600
     }'
   ```

2. **Monitor Override Usage**
   - This will trigger GA-001 alert (Owner Override Active)
   - Follow Runbook 1 monitoring procedures
   - Fix underlying issue while override is active

### Post-Incident Checks

1. **Verify Mode Change Succeeded**
   ```bash
   curl "$BRAIN_API/api/sovereign-mode/status" | jq '.mode'

   # Should match target mode
   ```

2. **Check for Rollback Audit Event**
   ```bash
   # Should NOT have new MODE_ROLLBACK events
   curl "$BRAIN_API/api/sovereign-mode/audit?event_type=mode_rollback&limit=1" | jq '.[0].timestamp'

   # Timestamp should be from failed attempt (not recent)
   ```

3. **Validate System Health**
   ```bash
   curl "$BRAIN_API/api/sovereign-mode/governance/status"

   # Check all components (G1, G2, G3) are healthy
   ```

4. **Document Incident**
   - Rollback reason
   - Root cause
   - Resolution steps
   - Lessons learned (update runbook if new scenario)

---

## Runbook 5: Audit Export Failure

**Alert ID:** N/A (operational issue, not security)
**Severity:** 🔵 SEV-3 (MEDIUM)
**Response Time:** < 2 hours

### Symptom

- **Audit export API fails** to complete
- **HTTP 500** or timeout when calling `/api/sovereign-mode/audit/export`
- **Indication**: Cannot export audit trail for compliance
- **Impact**: Audit trail unavailable for SIEM/compliance, but audit log still recording

### Relevant Audit Events

| Event Type | Severity | Meaning |
|------------|----------|---------|
| `GOVERNANCE_AUDIT_EXPORTED` | INFO | Audit export succeeded (won't exist if failing) |
| *(None)* | - | Export failures are NOT audited (would create recursion) |

### API Endpoints

**Diagnostic:**
```bash
# Attempt export
POST /api/sovereign-mode/audit/export

# Check audit log size
GET /api/sovereign-mode/audit?limit=1

# Check backend health
GET /api/health
```

**Remediation:**
```bash
# Retry export with smaller time window
POST /api/sovereign-mode/audit/export (with start_time/end_time filters)

# Check backend logs
docker logs brain-backend
```

### Immediate Actions (< 5 Minutes)

1. **Attempt Manual Export**
   ```bash
   curl -X POST "$BRAIN_API/api/sovereign-mode/audit/export" \
     -H "Content-Type: application/json" \
     -d '{
       "start_time": null,
       "end_time": null,
       "event_types": null,
       "include_hash": true
     }'
   ```

   **Possible Errors:**
   - **HTTP 500**: Backend error (check logs)
   - **Timeout**: Audit log too large
   - **HTTP 503**: Backend overloaded

2. **Check Error Details**
   ```bash
   # If JSON error response
   curl -X POST "$BRAIN_API/api/sovereign-mode/audit/export" -d '{}' | jq '.detail'

   # Common errors:
   # - "Failed to export audit log: list index out of range" → Empty audit log
   # - "Failed to export audit log: timeout" → Audit log too large
   # - "Failed to export audit log: database connection" → Database issue
   ```

3. **Check Audit Log Size**
   ```bash
   curl "$BRAIN_API/api/sovereign-mode/audit?limit=1" | jq 'length'

   # If 0: Audit log empty (backend issue)
   # If 1: Audit log exists, export issue is something else
   ```

4. **Check Backend Health**
   ```bash
   curl "$BRAIN_API/api/health"

   # If unhealthy: Backend issue (restart may be needed)
   # If healthy: Export-specific issue
   ```

### Decision Logic

```
┌──────────────────────────────┐
│ Audit Export Failure         │
└───────────┬──────────────────┘
            │
    ┌───────▼────────┐
    │ Check Error    │
    └───────┬────────┘
            │
     ┌──────┴──────┐
     │             │
  HTTP 500    Timeout
     │             │
┌────▼────┐   ┌────▼────┐
│Backend  │   │Audit Log│
│ Error   │   │Too Large│
└────┬────┘   └────┬────┘
     │             │
┌────▼────┐   ┌────▼────┐
│Check    │   │Use Time │
│ Logs    │   │ Filters │
└─────────┘   └─────────┘
```

### Recovery Steps

#### Case A: Backend Error (HTTP 500)

**If backend is returning 500 error:**

1. **Check Backend Logs**
   ```bash
   docker logs brain-backend --tail 100

   # Look for Python tracebacks related to audit export
   ```

2. **Common Backend Issues:**

   **Database Connection Error:**
   ```
   Failed to query audit log: connection refused
   ```
   Fix: Check database container, restart if needed
   ```bash
   docker restart brain-postgres
   ```

   **Permissions Error:**
   ```
   Failed to write export file: permission denied
   ```
   Fix: Check filesystem permissions
   ```bash
   sudo chown -R brain:brain storage/
   ```

   **Out of Memory:**
   ```
   MemoryError: cannot allocate memory
   ```
   Fix: Audit log too large, use time filters (see Case B)

3. **Restart Backend (if needed)**
   ```bash
   docker restart brain-backend

   # Wait for health check
   sleep 10
   curl "$BRAIN_API/api/health"
   ```

4. **Retry Export**
   ```bash
   curl -X POST "$BRAIN_API/api/sovereign-mode/audit/export" -d '{"include_hash": true}'
   ```

#### Case B: Timeout (Audit Log Too Large)

**If export times out due to large audit log:**

1. **Export in Chunks (Time-Based)**
   ```bash
   # Export last 7 days
   curl -X POST "$BRAIN_API/api/sovereign-mode/audit/export" \
     -H "Content-Type: application/json" \
     -d '{
       "start_time": "2025-12-18T00:00:00Z",
       "end_time": "2025-12-25T00:00:00Z",
       "include_hash": true
     }' > audit_export_week1.json

   # Repeat for older data
   curl -X POST "$BRAIN_API/api/sovereign-mode/audit/export" \
     -d '{
       "start_time": "2025-12-11T00:00:00Z",
       "end_time": "2025-12-17T23:59:59Z",
       "include_hash": true
     }' > audit_export_week2.json
   ```

2. **Export by Event Type**
   ```bash
   # Export only critical events
   curl -X POST "$BRAIN_API/api/sovereign-mode/audit/export" \
     -d '{
       "event_types": ["mode_changed", "bundle_quarantined", "axe_trust_tier_violation"],
       "include_hash": true
     }' > audit_export_critical.json
   ```

3. **Implement Audit Log Rotation** (Long-term fix)
   - Current issue: Audit log unbounded growth
   - Recommendation: Implement automatic rotation after 100,000 events or 30 days
   - Archive old logs to external storage (S3, cold storage)
   - Update GOVERNANCE_EVIDENCE_PACK.md Section 8 with rotation policy

#### Case C: Empty Audit Log

**If audit log is unexpectedly empty:**

1. **Verify Audit Log Location**
   ```bash
   # Check if audit log file exists (if file-based)
   ls -lh storage/audit_log.json

   # Or check database table (if DB-based)
   docker exec brain-postgres psql -U brain -d brain -c "SELECT COUNT(*) FROM audit_log;"
   ```

2. **Check Audit Log Initialization**
   - Backend may have restarted and lost in-memory audit log
   - If audit log is file-based, check if file was deleted
   - If database-based, check if table was dropped

3. **Trigger Test Events**
   ```bash
   # Create audit event by changing mode
   curl -X POST "$BRAIN_API/api/sovereign-mode/mode/preflight" -d '{"target_mode": "offline"}'

   # Check if audit log now has events
   curl "$BRAIN_API/api/sovereign-mode/audit?limit=1"
   ```

4. **Escalate if Persistent**
   - If audit log remains empty after generating events: Backend bug
   - File incident ticket for development team
   - Check recent code changes to audit system

### Post-Incident Checks

1. **Verify Export Succeeds**
   ```bash
   curl -X POST "$BRAIN_API/api/sovereign-mode/audit/export" \
     -d '{"include_hash": true}'

   # Should return success response with event_count, export_id, content_hash
   ```

2. **Verify Export Created Audit Event**
   ```bash
   curl "$BRAIN_API/api/sovereign-mode/audit?event_type=governance_audit_exported&limit=1"

   # Should have recent GOVERNANCE_AUDIT_EXPORTED event
   ```

3. **Validate Hash Integrity**
   ```bash
   # If export returned JSONL content (in future implementation)
   # Verify SHA256 hash matches
   shasum -a 256 export_content.jsonl

   # Compare with content_hash from export response
   ```

4. **Document Incident**
   - Export failure cause
   - Workaround used (time filters, event type filters)
   - Long-term fix needed (rotation, pagination)

---

## Post-Incident Procedures

### Standard Post-Incident Tasks

After **any** governance incident, complete these tasks:

#### 1. Incident Documentation

**Create Incident Report** (for SEV-1 and SEV-2 incidents):

**Template:**
```
Incident ID: INC-2025-XXXX
Date: 2025-12-25 16:00 UTC
Duration: 45 minutes
Severity: SEV-1 CRITICAL

Title: [Brief description]

Timeline:
- 16:00 - Alert fired (GA-002: Bundle Quarantine)
- 16:02 - On-call acknowledged
- 16:05 - Identified quarantined bundle: llama3.2_prod_v1.2.3
- 16:10 - Determined cause: Key rotation, old key removed from keyring
- 16:20 - Added new trusted key to keyring
- 16:25 - Re-validated bundle successfully
- 16:30 - Verified Sovereign mode available
- 16:45 - Alert cleared

Root Cause:
Signing key was rotated by bundle maintainer without advance notice.
Keyring was not updated before old key was removed from bundle source.

Impact:
- Quarantined bundle could not be loaded
- Sovereign mode temporarily unavailable (alternative bundle was available)
- No service outage

Resolution:
- Added new trusted key (fingerprint: SHA256:abc123...) to keyring
- Re-validated bundle, quarantine cleared
- Bundle now validated and loadable

Lessons Learned:
1. Need process for coordinated key rotation with bundle maintainers
2. Should maintain multiple validated bundles to prevent single point of failure
3. Consider automated key rotation notifications

Action Items:
1. Document key rotation procedure in GOVERNANCE_RUNBOOKS.md
2. Set up monitoring for bundle validation failures BEFORE quarantine
3. Coordinate with bundle team on key rotation schedule
```

#### 2. Metrics Review

**Check Incident Metrics:**
```bash
# Query metrics during incident window
curl "$BRAIN_API/api/sovereign-mode/metrics/summary"

# Verify metrics captured the incident:
# - bundle_quarantine_count should have increased
# - governance status should have been "critical" during incident
# - governance status should now be "healthy"
```

#### 3. Runbook Update

**If new scenario encountered:**
- Update relevant runbook with new details
- Add to "Common Issues" section
- Update decision logic if needed
- Version control: Increment version, add to changelog

#### 4. Communication

**SEV-1 Incidents:**
- Notify stakeholders via email (Ops, Security, Management)
- Update status page if customer-facing impact
- Post incident report in #incidents channel

**SEV-2 Incidents:**
- Notify Ops team via Slack
- Document in ops log

#### 5. Post-Incident Review (PIR)

**For SEV-1 CRITICAL incidents, conduct PIR within 48 hours:**

**PIR Agenda:**
1. Incident timeline review
2. What went well?
3. What could be improved?
4. Action items (owner, deadline)
5. Runbook updates needed
6. Alert tuning needed

**PIR Attendees:**
- On-call engineer (incident responder)
- Engineering manager
- Security team (if security incident)
- Product owner (if customer impact)

---

## Escalation Matrix

### Escalation Paths

| Incident Severity | Initial Response | 15 min Escalation | 30 min Escalation | 1 hour Escalation |
|-------------------|------------------|-------------------|-------------------|-------------------|
| **SEV-1 CRITICAL** | On-Call Engineer | Senior Engineer | Security Team | Engineering Manager |
| **SEV-2 HIGH** | Platform Ops | On-Call Engineer | Senior Engineer | Engineering Manager |
| **SEV-3 MEDIUM** | Platform Ops | On-Call Engineer | - | - |
| **SEV-4 LOW** | Platform Ops | - | - | - |

### Contact Information

**On-Call Rotation:**
- PagerDuty: `brain-governance-oncall`
- Backup: `brain-platform-oncall`

**Escalation Contacts:**
- Senior Engineer: See PagerDuty escalation policy
- Security Team: `security@example.com`, Slack: #security-incidents
- Engineering Manager: `eng-manager@example.com`

### When to Escalate

**Immediate Escalation (No Delay):**
- Suspected security breach
- Unauthorized governance override
- Malicious bundle detected
- Active attack on AXE
- Data breach or exfiltration

**Standard Escalation (Per Timeline):**
- Incident not resolved within timeframe
- On-call engineer needs assistance
- Decision authority needed (e.g., approve override)
- Cross-team coordination required

---

## Appendix: Quick Reference

### Runbook Quick Lookup

| Incident | Runbook | Severity | Key Actions |
|----------|---------|----------|-------------|
| **Override Active** | RB-1 | 🔴 CRITICAL | Check audit, verify reason, monitor |
| **Bundle Quarantine** | RB-2 | 🔴 CRITICAL | Identify bundle, add key OR re-download |
| **AXE Trust Violation** | RB-3 | 🔴 CRITICAL | Check source IP, block if attack |
| **Mode Switch Rollback** | RB-4 | 🟡 HIGH | Fix underlying issue, retry |
| **Audit Export Failure** | RB-5 | 🔵 MEDIUM | Use time filters, check backend logs |

### Useful Commands

```bash
# Set API endpoint
export BRAIN_API="http://localhost:8000"

# Quick health check
curl $BRAIN_API/api/health

# Governance status
curl $BRAIN_API/api/sovereign-mode/governance/status | jq '.overall_governance'

# Recent audit events
curl "$BRAIN_API/api/sovereign-mode/audit?limit=10" | jq '.[] | {timestamp, event_type, reason}'

# Metrics summary
curl $BRAIN_API/api/sovereign-mode/metrics/summary | jq '.'

# Current mode
curl $BRAIN_API/api/sovereign-mode/status | jq '.mode'

# Check override active
curl $BRAIN_API/api/sovereign-mode/metrics/summary | jq '.override_active'

# Export audit log (last 24h)
curl -X POST "$BRAIN_API/api/sovereign-mode/audit/export" \
  -d "{\"start_time\": \"$(date -u -d '24 hours ago' '+%Y-%m-%dT%H:%M:%SZ')\"}"
```

### Related Documents

- **Alerting Policy**: `docs/ALERTING_POLICY.md` (A1)
- **Evidence Pack**: `docs/GOVERNANCE_EVIDENCE_PACK.md` (G4.2)
- **G4 Implementation Report**: `G4_IMPLEMENTATION_REPORT.md`
- **Architecture Documentation**: `docs/brain_framework.md`

---

**Document End**

**Next Actions:**
1. Review runbooks with on-call team
2. Conduct runbook walk-throughs
3. Test each runbook scenario in staging
4. Integrate with incident management system

**Version:** 1.0.0
**Last Updated:** 2025-12-25
**Status:** PRODUCTION READY
