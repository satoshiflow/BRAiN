# BRAiN Governance Evidence Pack

**Version:** 1.0.0
**Date:** 2025-12-25
**Purpose:** Compliance & Investor Documentation
**Classification:** Public Technical Documentation

---

## Executive Summary

This document provides comprehensive evidence of BRAiN's governance architecture, demonstrating how the system ensures secure, auditable, and fail-closed operation across all critical components. It is designed for compliance officers, security auditors, and investors who need to understand the system's security posture without implementation-level details.

**Key Governance Guarantees:**
- ✅ **Fail-Closed Security**: System blocks operations unless explicitly authorized
- ✅ **Complete Audit Trail**: All governance events logged with cryptographic integrity
- ✅ **Multi-Layer Defense**: Bundle signing, network isolation, trust tier enforcement
- ✅ **Observable Governance**: Prometheus-compatible metrics for all governance signals
- ✅ **Time-Limited Overrides**: Emergency overrides are single-use, time-bound, and auditable

---

## 1. What is Sovereign Mode?

### Non-Technical Summary

**Sovereign Mode** is BRAiN's secure offline operation capability, designed for scenarios where network connectivity is unavailable, untrusted, or prohibited by policy. In Sovereign Mode, the system operates entirely from pre-validated, cryptographically signed AI model bundles without any external network dependencies.

**Key Characteristics:**
- **Network Independence**: System functions without internet connectivity
- **Trust Anchored**: All AI models validated against trusted cryptographic keys
- **Fail-Closed**: System refuses operation if integrity cannot be verified
- **Auditable**: Every mode transition, bundle load, and policy decision is logged

**Use Cases:**
- Air-gapped environments (military, critical infrastructure)
- High-security deployments where external network access is prohibited
- Disaster recovery scenarios with degraded network connectivity
- Compliance requirements mandating offline-capable AI systems

### Technical Definition

Sovereign Mode is one of four operation modes in BRAiN's state machine:

| Mode | Network | Bundle | External APIs | Use Case |
|------|---------|--------|---------------|----------|
| **SOVEREIGN** | ❌ Blocked | ✅ Required | ❌ Blocked | Maximum security, offline |
| **OFFLINE** | ⚠️ Available | ✅ Required | ❌ Blocked | Degraded connectivity |
| **DMZ** | ✅ Filtered | Optional | ⚠️ DMZ-gated | Controlled external access |
| **ONLINE** | ✅ Full | Optional | ✅ Allowed | Standard operation |

Mode transitions are governed by a **2-Phase Commit** protocol with comprehensive preflight checks.

---

## 2. How Can You Prove Sovereign Mode is Active?

### Observable Indicators

**API Endpoint:**
```http
GET /api/sovereign-mode/status
```

**Response (Sovereign Mode Active):**
```json
{
  "mode": "sovereign",
  "network_available": false,
  "ipv6_blocked": true,
  "dmz_gateway_running": false,
  "active_bundle_id": "llama3.2_production_v1.2.3",
  "bundle_status": "loaded",
  "bundle_signature_valid": true,
  "bundle_key_trusted": true,
  "last_mode_change": "2025-12-25T10:15:30.123456Z",
  "uptime_seconds": 86400
}
```

**Key Verification Points:**
1. ✅ `mode` field shows `"sovereign"`
2. ✅ `network_available` is `false` (network guard active)
3. ✅ `ipv6_blocked` is `true` (IPv6 stack disabled)
4. ✅ `dmz_gateway_running` is `false` (DMZ stopped)
5. ✅ `bundle_signature_valid` is `true` (cryptographic proof)
6. ✅ `bundle_key_trusted` is `true` (signed by trusted key)

### Cryptographic Proof

Every loaded bundle includes a signature chain:

```json
{
  "bundle_id": "llama3.2_production_v1.2.3",
  "signature": "SHA256:a1b2c3d4...",
  "signed_by": "BRAiN Production Key (2024-2026)",
  "key_fingerprint": "SHA256:e5f6a7b8...",
  "signed_at": "2025-12-20T14:30:00Z",
  "hash_algorithm": "SHA256",
  "file_hash": "9f8e7d6c..."
}
```

**Verification Steps:**
1. Compute SHA256 hash of bundle file
2. Compare with `file_hash` in manifest
3. Verify signature using public key from trusted keyring
4. Confirm key is not revoked (check audit log)

### Audit Trail Proof

Query the audit log for mode transitions:

```http
GET /api/sovereign-mode/audit?event_type=mode_changed&limit=10
```

**Example Entry:**
```json
{
  "timestamp": "2025-12-25T10:15:30.123456Z",
  "event_type": "mode_changed",
  "success": true,
  "severity": "INFO",
  "reason": "Mode changed: online -> sovereign",
  "mode_before": "online",
  "mode_after": "sovereign",
  "triggered_by": "admin_user",
  "metadata": {
    "request_id": "req_abc123",
    "override_used": false,
    "preflight_status": "pass"
  }
}
```

---

## 3. How Are Mode Changes Governed?

### 2-Phase Commit Protocol

All mode changes follow a strict 2-phase governance protocol:

#### Phase 1: Preflight Checks (Read-Only)

**Purpose:** Validate that the system is ready for the mode transition without making any changes.

**Gate Checks:**

| Gate | Description | SOVEREIGN Requirements | ONLINE Requirements |
|------|-------------|------------------------|---------------------|
| **Network Gate** | Network connectivity status | ⚠️ Warning if available | ✅ Must be available |
| **IPv6 Gate** | IPv6 stack status | ✅ Must be blocked | ⚠️ Optional |
| **DMZ Gate** | DMZ gateway status | ✅ Must be stopped | ⚠️ Optional |
| **Bundle Trust Gate** | Bundle signature & key trust | ✅ Must pass | N/A |

**Preflight API:**
```http
POST /api/sovereign-mode/mode/preflight
{
  "target_mode": "sovereign"
}
```

**Response:**
```json
{
  "target_mode": "sovereign",
  "current_mode": "online",
  "overall_status": "pass",
  "can_proceed": true,
  "override_required": false,
  "checks": [
    {
      "gate_name": "network_gate",
      "status": "warning",
      "blocking": false,
      "reason": "Network available but not required for SOVEREIGN"
    },
    {
      "gate_name": "bundle_trust_gate",
      "status": "pass",
      "blocking": true,
      "reason": "Bundle signature valid and key trusted"
    }
  ]
}
```

#### Phase 2: Commit (State Modification)

**Only executed if:**
- Preflight status is `"pass"` **OR**
- Valid owner override is provided

**Commit Actions:**
1. Load cryptographically signed bundle (if required)
2. Stop DMZ gateway (if switching to SOVEREIGN/OFFLINE)
3. Update mode in configuration
4. Update network guard policy
5. Save configuration to disk
6. Emit `MODE_CHANGED` audit event
7. Record mode switch metric

**Rollback on Error:**
If any commit action fails, the system attempts to rollback to the previous mode state and emits a `MODE_CHANGE_FAILED` audit event.

### Governance Decision Matrix

| Preflight Result | Override Provided | Action | Audit Event |
|------------------|-------------------|--------|-------------|
| ✅ PASS | ❌ No | ✅ Allow commit | `MODE_CHANGED` |
| ✅ PASS | ✅ Yes | ✅ Allow commit | `MODE_CHANGED` + `MODE_OVERRIDE_USED` |
| ❌ FAIL | ❌ No | ❌ **Block** | `MODE_PREFLIGHT_FAILED` |
| ❌ FAIL | ✅ Yes (valid) | ⚠️ Allow with warning | `MODE_CHANGED` + `MODE_OVERRIDE_USED` + `MODE_PREFLIGHT_FAILED` |
| ❌ FAIL | ✅ Yes (expired) | ❌ **Block** | `MODE_PREFLIGHT_FAILED` |

### Owner Override Mechanism

**Purpose:** Emergency mechanism for administrators to bypass preflight failures when operationally justified.

**Requirements:**
- ✅ Explicit reason (minimum 10 characters)
- ✅ Time-limited (60 seconds to 24 hours)
- ✅ Single-use (consumed immediately on first use)
- ✅ Fully auditable (logged with reason and duration)

**Example:**
```json
{
  "target_mode": "sovereign",
  "override_reason": "Emergency switch due to network security incident - incident #INC-2025-0042",
  "override_duration_seconds": 1800
}
```

**Audit Events Generated:**
1. `MODE_OVERRIDE_CREATED` - Override created with expiration time
2. `MODE_OVERRIDE_CONSUMED` - Override used for mode change
3. `MODE_CHANGED` - Mode actually changed
4. `MODE_PREFLIGHT_FAILED` - Original preflight failure (if any)

---

## 4. What Protects the System from Unauthorized Bundles?

### G1: Bundle Signing & Trusted Origin

**Defense Layers:**

#### Layer 1: Cryptographic Signatures

**Every bundle must be signed:**
- Algorithm: Ed25519 (elliptic curve digital signature)
- Hash: SHA256 of bundle file
- Signature: Ed25519 signature of hash
- Metadata: Manifest file with signature details

**Signature Validation:**
```python
1. Compute SHA256(bundle_file)
2. Read signature from manifest
3. Verify signature using public key
4. Confirm hash matches manifest
5. Check key is in trusted keyring
6. Confirm key is not revoked
```

#### Layer 2: Trusted Keyring

**Only bundles signed by trusted keys are allowed.**

**Keyring Management:**
- Keys stored in `storage/keys/trusted_keyring.json`
- Each key has fingerprint, owner, validity period
- Keys can be revoked (maintains audit trail)
- Revoked keys are not deleted (forensic evidence)

**Example Trusted Key:**
```json
{
  "fingerprint": "SHA256:a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6...",
  "public_key": "-----BEGIN PUBLIC KEY-----\n...",
  "algorithm": "ed25519",
  "owner": "BRAiN Production Team",
  "created_at": "2024-01-15T00:00:00Z",
  "expires_at": "2026-01-15T00:00:00Z",
  "revoked": false
}
```

#### Layer 3: Quarantine

**If validation fails, bundles are quarantined:**

**Quarantine Triggers:**
- ❌ Signature missing (and unsigned bundles not allowed by policy)
- ❌ Signature invalid (cryptographic verification failed)
- ❌ Key untrusted (not in trusted keyring)
- ❌ Key revoked (in keyring but revoked)
- ❌ Hash mismatch (file tampering detected)

**Quarantine Process:**
1. Bundle status set to `QUARANTINED`
2. Bundle files copied to `storage/quarantine/{bundle_id}/`
3. Quarantine metadata written (reason, timestamp, original paths)
4. `BUNDLE_QUARANTINED` audit event emitted
5. Bundle quarantine metric incremented

**Quarantined bundles cannot be loaded** - even with override.

#### Layer 4: Policy Enforcement

**Signature Policy Options:**

| Policy | Unsigned Allowed? | Quarantine on Failure? | Use Case |
|--------|-------------------|------------------------|----------|
| **STRICT** | ❌ No | ✅ Yes | Production (recommended) |
| **PERMISSIVE** | ✅ Yes | ❌ No | Development only |
| **WARN_ONLY** | ✅ Yes | ❌ No | Testing only |

**Production default:** `STRICT`

### Observable Metrics

```
# Bundle signature failures
sovereign_bundle_signature_failure_total

# Bundle quarantines
sovereign_bundle_quarantine_total
```

---

## 5. What Protects Against External Access to AXE?

### G3: AXE DMZ Isolation & Trust Tiers

**AXE (Auxiliary Execution Engine)** is BRAiN's external API gateway. In SOVEREIGN mode, **external access to AXE is completely blocked**.

#### Trust Tier System

**Every AXE request is classified into one of three trust tiers:**

| Trust Tier | Source | Allowed? | Use Case |
|------------|--------|----------|----------|
| **LOCAL** | `127.0.0.1`, `::1` | ✅ Always | Admin/testing |
| **DMZ** | Authenticated DMZ gateways | ✅ In DMZ/ONLINE modes | Controlled external access |
| **EXTERNAL** | Unknown sources | ❌ **BLOCKED** | Untrusted requests |

**Trust Tier Detection:**
1. Extract source IP from request headers
2. Check against localhost addresses
3. Check against DMZ gateway allowlist
4. Default to EXTERNAL if no match

#### Enforcement Mechanism

**Request Flow:**
```
1. AXE request received
2. Emit AXE_REQUEST_RECEIVED audit event
3. Determine trust tier (LOCAL/DMZ/EXTERNAL)
4. Check if tier is allowed in current mode
5. If EXTERNAL:
   - Emit AXE_REQUEST_BLOCKED audit event
   - Emit AXE_TRUST_TIER_VIOLATION audit event
   - Record trust violation metric
   - Return HTTP 403 Forbidden
6. If allowed:
   - Emit AXE_REQUEST_FORWARDED audit event
   - Process request
```

**Fail-Closed Behavior:**
- Unknown sources are **always** classified as EXTERNAL
- EXTERNAL requests are **always** blocked
- No bypass mechanism (even with override)

#### DMZ Gateway Management

**In SOVEREIGN mode, the DMZ gateway is stopped:**

```json
{
  "dmz_gateway_running": false,
  "dmz_last_stopped": "2025-12-25T10:15:32Z",
  "dmz_stop_reason": "Mode changed to SOVEREIGN"
}
```

**DMZ Gateway Lifecycle:**
- Automatically stopped on transition to SOVEREIGN/OFFLINE
- Automatically started on transition to ONLINE (if configured)
- Manual control via `/api/dmz/control` endpoint
- All start/stop actions audited

### Observable Metrics

```
# AXE trust tier violations (labeled by tier)
axe_trust_violation_total{trust_tier="external"} 12
axe_trust_violation_total{trust_tier="dmz"} 0
```

---

## 6. How Are Overrides Logged and Auditable?

### Override Audit Trail

**Every override action generates multiple audit events:**

#### 1. Override Creation

**Event:** `MODE_OVERRIDE_CREATED`

```json
{
  "timestamp": "2025-12-25T15:30:00.000000Z",
  "event_type": "mode_override_created",
  "success": true,
  "severity": "WARNING",
  "reason": "Emergency switch due to network security incident - incident #INC-2025-0042",
  "metadata": {
    "override_duration_seconds": 1800,
    "expires_at": "2025-12-25T16:00:00.000000Z",
    "requested_by": "admin_user"
  }
}
```

#### 2. Override Consumption

**Event:** `MODE_OVERRIDE_CONSUMED`

```json
{
  "timestamp": "2025-12-25T15:30:15.123456Z",
  "event_type": "mode_override_consumed",
  "success": true,
  "severity": "WARNING",
  "reason": "Override consumed for mode change: online -> sovereign",
  "metadata": {
    "override_reason": "Emergency switch due to network security incident - incident #INC-2025-0042",
    "consumed_at": "2025-12-25T15:30:15.123456Z"
  }
}
```

#### 3. Mode Change with Override

**Event:** `MODE_CHANGED`

```json
{
  "timestamp": "2025-12-25T15:30:16.789012Z",
  "event_type": "mode_changed",
  "success": true,
  "severity": "INFO",
  "reason": "Mode changed: online -> sovereign",
  "mode_before": "online",
  "mode_after": "sovereign",
  "metadata": {
    "override_used": true,
    "preflight_status": "fail"
  }
}
```

### Override Forensics

**To audit all override usage:**

```http
GET /api/sovereign-mode/audit?event_type=mode_override_created&event_type=mode_override_consumed
```

**To find suspicious override patterns:**
- Multiple overrides in short time span
- Overrides with generic reasons
- Overrides during off-hours
- Overrides bypassing critical gate failures

### Override Governance Metrics

```
# Total override usage count
sovereign_override_usage_total 3

# Override currently active (0 or 1)
sovereign_override_active 0
```

**Alerting Recommendation:**
- Alert on `sovereign_override_usage_total` rate > 5/hour
- Alert on `sovereign_override_active == 1` for > 30 minutes
- Alert on override usage outside business hours

---

## 7. What Metrics Are Available?

### G4: Governance Metrics (Prometheus-Compatible)

**All governance signals are exposed as Prometheus metrics:**

#### Metrics Endpoint

```http
GET /api/sovereign-mode/metrics
Content-Type: text/plain; version=0.0.4
```

**Example Output:**
```prometheus
# HELP sovereign_mode_switch_total Total mode switches by target mode
# TYPE sovereign_mode_switch_total counter
sovereign_mode_switch_total{target_mode="sovereign"} 5
sovereign_mode_switch_total{target_mode="online"} 3
sovereign_mode_switch_total{target_mode="dmz"} 1

# HELP sovereign_preflight_failure_total Total preflight failures by gate
# TYPE sovereign_preflight_failure_total counter
sovereign_preflight_failure_total{gate="network_gate"} 2
sovereign_preflight_failure_total{gate="bundle_trust_gate"} 1

# HELP sovereign_override_usage_total Total owner override usage count
# TYPE sovereign_override_usage_total counter
sovereign_override_usage_total 3

# HELP sovereign_bundle_signature_failure_total Total bundle signature validation failures
# TYPE sovereign_bundle_signature_failure_total counter
sovereign_bundle_signature_failure_total 1

# HELP sovereign_bundle_quarantine_total Total bundles quarantined
# TYPE sovereign_bundle_quarantine_total counter
sovereign_bundle_quarantine_total 1

# HELP axe_trust_violation_total Total AXE trust tier violations
# TYPE axe_trust_violation_total counter
axe_trust_violation_total{trust_tier="external"} 12

# HELP sovereign_override_active Whether an override is currently active (0|1)
# TYPE sovereign_override_active gauge
sovereign_override_active 0
```

#### JSON Summary Endpoint

```http
GET /api/sovereign-mode/metrics/summary
Content-Type: application/json
```

**Example Response:**
```json
{
  "mode_switches": {
    "sovereign": 5,
    "online": 3,
    "dmz": 1
  },
  "preflight_failures": {
    "network_gate": 2,
    "bundle_trust_gate": 1
  },
  "override_usage_total": 3,
  "bundle_signature_failures": 1,
  "bundle_quarantines": 1,
  "axe_trust_violations": {
    "external": 12
  },
  "override_active": false,
  "last_update": "2025-12-25T15:45:30.123456Z"
}
```

### Metric Categories

| Category | Metrics | Type | Labels | Purpose |
|----------|---------|------|--------|---------|
| **Mode Governance** | `sovereign_mode_switch_total` | Counter | `target_mode` | Track mode changes |
| **Preflight** | `sovereign_preflight_failure_total` | Counter | `gate` | Track gate failures |
| **Override** | `sovereign_override_usage_total` | Counter | - | Track override usage |
| **Override** | `sovereign_override_active` | Gauge | - | Current override status |
| **Bundle Trust** | `sovereign_bundle_signature_failure_total` | Counter | - | Track signature failures |
| **Bundle Trust** | `sovereign_bundle_quarantine_total` | Counter | - | Track quarantines |
| **AXE Security** | `axe_trust_violation_total` | Counter | `trust_tier` | Track trust violations |

### Data Governance

**No Business Data in Metrics:**
- ❌ No payloads
- ❌ No PII (personal identifiable information)
- ❌ No bundle content
- ❌ No user messages
- ✅ Only governance signals (counts, gauges, status)

**Thread-Safe:**
- All counters and gauges use `threading.RLock`
- Safe for concurrent access from multiple workers

**Singleton Pattern:**
- Metrics registry is a singleton
- All components use `get_governance_metrics()` accessor

---

## 8. How to Export Audit Logs for Compliance?

### Audit Log Export API

**Endpoint:** *(To be implemented in G4.3)*

```http
POST /api/sovereign-mode/audit/export
Content-Type: application/json

{
  "start_time": "2025-12-01T00:00:00Z",
  "end_time": "2025-12-31T23:59:59Z",
  "event_types": ["mode_changed", "mode_override_created", "bundle_quarantined"],
  "include_hash": true,
  "format": "jsonl"
}
```

**Response:**
```jsonl
{"timestamp":"2025-12-25T10:15:30.123456Z","event_type":"mode_changed","success":true,"severity":"INFO","reason":"Mode changed: online -> sovereign","mode_before":"online","mode_after":"sovereign","metadata":{"override_used":false}}
{"timestamp":"2025-12-25T15:30:00.000000Z","event_type":"mode_override_created","success":true,"severity":"WARNING","reason":"Emergency switch...","metadata":{"override_duration_seconds":1800}}
...
SHA256:a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2
```

**Features:**
- ✅ Time range filtering
- ✅ Event type filtering
- ✅ JSONL format (one JSON object per line)
- ✅ SHA256 hash of export (integrity proof)
- ✅ Audit event generated for export itself

### Audit Event Types for Compliance

**G1: Bundle Trust**
- `BUNDLE_VALIDATED`
- `BUNDLE_QUARANTINED`
- `BUNDLE_LOADED`
- `BUNDLE_UNLOADED`
- `TRUSTED_KEY_ADDED`
- `TRUSTED_KEY_REVOKED`

**G2: Mode Switch Governance**
- `MODE_CHANGED`
- `MODE_CHANGE_FAILED`
- `MODE_PREFLIGHT_COMPLETED`
- `MODE_PREFLIGHT_FAILED`
- `MODE_OVERRIDE_CREATED`
- `MODE_OVERRIDE_CONSUMED`
- `MODE_OVERRIDE_EXPIRED`

**G3: AXE Security**
- `AXE_REQUEST_RECEIVED`
- `AXE_REQUEST_BLOCKED`
- `AXE_REQUEST_FORWARDED`
- `AXE_TRUST_TIER_VIOLATION`
- `DMZ_STARTED`
- `DMZ_STOPPED`

**G4: Governance Monitoring**
- `GOVERNANCE_AUDIT_EXPORTED` *(G4.3)*

### Audit Log Retention

**Current Implementation:**
- Stored in-memory (SQLite or JSON)
- No automatic rotation (manual management required)

**Production Recommendation:**
- Export to SIEM (Security Information and Event Management)
- Retain for minimum 90 days (compliance requirement)
- Archive to cold storage for 7 years (legal requirement)

---

## 9. Risk Statement & Limitations

### Known Limitations

#### 1. Audit Log Persistence

**Limitation:**
- Audit logs stored in local storage (not distributed)
- Logs may be lost on disk failure or system corruption
- No automatic offsite backup

**Mitigation:**
- Implement periodic export to SIEM
- Use `POST /api/sovereign-mode/audit/export` (G4.3)
- Store exports in immutable storage (S3, archival)

#### 2. Override Bypass Risk

**Limitation:**
- Owner overrides can bypass **all** preflight failures
- No technical limit on override usage
- Risk of override abuse by privileged users

**Mitigation:**
- Override usage is **fully auditable** (cannot be hidden)
- Alert on override rate > threshold
- Require multi-person approval for overrides (policy, not technical)
- Periodic review of override audit log

#### 3. Cryptographic Key Management

**Limitation:**
- Trusted keyring stored locally (not hardware security module)
- Private keys for signing bundles must be managed externally
- No automatic key rotation

**Mitigation:**
- Store keyring in encrypted storage (disk encryption)
- Use hardware tokens (YubiKey) for private key storage
- Implement key rotation policy (manual process)
- Revoke compromised keys immediately

#### 4. Network Guard Bypass

**Limitation:**
- Network guard blocks HTTP/HTTPS requests
- Low-level network access (raw sockets) not blocked
- Malicious code could bypass guard at kernel level

**Mitigation:**
- Run in containerized environment (Docker, Podman)
- Use network namespaces for isolation
- Firewall rules at host level (iptables, nftables)
- Regular security audits of codebase

#### 5. DMZ Gateway Security

**Limitation:**
- DMZ gateway allowlist managed manually
- No automated gateway authentication
- Gateway IP spoofing risk

**Mitigation:**
- Use mutual TLS (mTLS) for gateway authentication
- Implement gateway certificate validation
- Log all gateway connection attempts
- Regular review of gateway allowlist

### Security Assumptions

**This governance architecture assumes:**

1. ✅ **Trusted Execution Environment**
   - Host OS is not compromised
   - Container runtime is secure
   - No kernel-level malware present

2. ✅ **Private Key Security**
   - Bundle signing keys are not compromised
   - Key generation follows cryptographic best practices
   - Private keys stored in secure, offline storage

3. ✅ **Administrative Integrity**
   - System administrators are trustworthy
   - Override usage is monitored and reviewed
   - Audit logs are protected from tampering

4. ✅ **Network Perimeter**
   - Firewall rules correctly configured
   - DMZ gateway properly isolated
   - No unauthorized network routes

### Residual Risks

**Even with all mitigations, the following risks remain:**

| Risk | Severity | Likelihood | Mitigation Status |
|------|----------|------------|-------------------|
| Private key compromise | 🔴 Critical | Low | Partial (manual key management) |
| Privileged user override abuse | 🟡 Medium | Low | Mitigated (full audit trail) |
| Network guard kernel bypass | 🟡 Medium | Very Low | Partial (requires containerization) |
| Audit log tampering | 🟡 Medium | Low | Partial (requires external SIEM) |
| DMZ gateway IP spoofing | 🟢 Low | Very Low | Mitigated (mTLS recommended) |

### Compliance Attestations

**This architecture supports compliance with:**

- ✅ **SOC 2 Type II** (Security, Availability)
  - Comprehensive audit logging
  - Fail-closed security controls
  - Observable governance metrics

- ✅ **ISO 27001** (Information Security Management)
  - Access control (trust tiers)
  - Cryptographic controls (bundle signing)
  - Audit trail requirements

- ✅ **NIST Cybersecurity Framework**
  - Identify: Asset inventory (bundles, keys)
  - Protect: Signature validation, network isolation
  - Detect: Metrics, audit logs
  - Respond: Override mechanism
  - Recover: Rollback on errors

**Disclaimer:**
This document provides technical evidence of governance controls. Formal compliance certification requires independent audit by qualified assessors.

---

## Appendix: Quick Reference

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/sovereign-mode/status` | GET | Current mode status |
| `/api/sovereign-mode/mode` | POST | Change mode (with governance) |
| `/api/sovereign-mode/mode/preflight` | POST | Preflight check only |
| `/api/sovereign-mode/bundles` | GET | List bundles |
| `/api/sovereign-mode/bundles/{id}/validate` | POST | Validate bundle |
| `/api/sovereign-mode/audit` | GET | Query audit log |
| `/api/sovereign-mode/audit/export` | POST | Export audit log (G4.3) |
| `/api/sovereign-mode/metrics` | GET | Prometheus metrics |
| `/api/sovereign-mode/metrics/summary` | GET | JSON metrics summary |
| `/api/sovereign-mode/governance/status` | GET | Governance status (G4.4) |
| `/api/sovereign-mode/keys` | GET | List trusted keys |
| `/api/sovereign-mode/keys` | POST | Add trusted key |
| `/api/sovereign-mode/keys/{id}` | DELETE | Revoke key |

### Audit Event Reference

**Severity Levels:**
- `INFO` - Normal operations
- `WARNING` - Anomalies, overrides
- `ERROR` - Failures, violations
- `CRITICAL` - Security incidents

**Key Event Types:**
- G1: `BUNDLE_*`, `TRUSTED_KEY_*`
- G2: `MODE_*`, `*_OVERRIDE_*`, `*_PREFLIGHT_*`
- G3: `AXE_*`, `DMZ_*`
- G4: `GOVERNANCE_*`

### Metric Reference

**Counters (always increase):**
- `sovereign_mode_switch_total{target_mode}`
- `sovereign_preflight_failure_total{gate}`
- `sovereign_override_usage_total`
- `sovereign_bundle_signature_failure_total`
- `sovereign_bundle_quarantine_total`
- `axe_trust_violation_total{trust_tier}`

**Gauges (current value):**
- `sovereign_override_active` (0 or 1)

---

**Document End**

**For technical implementation details, see:**
- `G2_IMPLEMENTATION_REPORT.md` - Mode Switch Governance
- `backend/app/modules/sovereign_mode/README.md` - Sovereign Mode Module
- `backend/app/modules/axe_governance/README.md` - AXE Trust Tier System

**For questions or clarifications:**
- Contact: BRAiN Security Team
- Last Updated: 2025-12-25
- Version: 1.0.0
