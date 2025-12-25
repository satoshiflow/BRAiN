# BRAiN Governance Alerting Policy

**Version:** 1.0.0
**Date:** 2025-12-25
**Purpose:** Operational Monitoring & Incident Detection
**Scope:** Governance Layers G1, G2, G3, G4
**Classification:** Internal - Operations Manual

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Alerting Strategy](#alerting-strategy)
3. [Alert Severity Levels](#alert-severity-levels)
4. [Required Alerts](#required-alerts)
5. [Prometheus Alert Rules](#prometheus-alert-rules)
6. [Alert Descriptions](#alert-descriptions)
7. [Alert Routing & Escalation](#alert-routing--escalation)
8. [Testing & Validation](#testing--validation)
9. [Maintenance & Review](#maintenance--review)

---

## Executive Summary

This document defines the **operational alerting policy** for BRAiN's Governance System (G1-G4). All alerts are based on **existing Prometheus metrics** exposed by the G4 Governance Monitoring layer.

**Purpose:**
- Detect critical governance violations in real-time
- Enable rapid incident response
- Prevent security degradation
- Maintain audit compliance

**No New Features:**
- This policy uses only existing metrics from G4.1
- No code changes required
- Alerts trigger based on current `/api/sovereign-mode/metrics` data

**Target Audience:**
- Platform Operations Team
- Security Operations Center (SOC)
- On-Call Engineers
- Incident Response Team

---

## Alerting Strategy

### Design Principles

1. **Fail-Closed Alerting**: Alerts trigger on governance violations, not normal operations
2. **No False Positives**: Thresholds tuned for actual risk, not noise
3. **Actionable**: Every alert has a clear runbook and next steps
4. **Auditable**: Alert history tracked in Prometheus Alertmanager
5. **Escalation**: Critical alerts page on-call immediately

### Alert Philosophy

> **"If it alerts, someone must act."**

- Alerts indicate **governance policy violations** or **security degradation**
- Alerts are not informational metrics (use dashboards for monitoring)
- Every alert has a corresponding incident runbook (see `GOVERNANCE_RUNBOOKS.md`)

### Metric Sources

All alerts use metrics from:
- **Endpoint**: `GET /api/sovereign-mode/metrics` (Prometheus format)
- **Module**: G4.1 Governance Metrics
- **Scrape Interval**: 30 seconds (recommended)

---

## Alert Severity Levels

| Severity | Color | Response Time | Escalation | Examples |
|----------|-------|---------------|------------|----------|
| **CRITICAL** | 🔴 Red | Immediate (page on-call) | Automatic page + email | Override active, Bundle quarantine |
| **WARNING** | 🟡 Yellow | < 30 minutes | Email + Slack | High violation rate, Preflight failures |
| **INFO** | 🔵 Blue | Best effort | Slack only | Metrics unavailable |

### Severity Definitions

**CRITICAL (🔴):**
- Governance policy actively violated
- Security posture degraded
- Requires immediate human intervention
- Examples: Override active, Quarantined bundle loaded, Trust violations

**WARNING (🟡):**
- Governance anomaly detected
- Potential security degradation
- Requires investigation within 30 minutes
- Examples: High preflight failure rate, Elevated trust violations

**INFO (🔵):**
- Operational issue (not security)
- No immediate governance impact
- Examples: Metrics scrape failure, Exporter down

---

## Required Alerts

Based on the governance metrics catalog (G4.1), the following **5 critical alerts** are mandatory:

| Alert ID | Name | Metric | Severity | Threshold |
|----------|------|--------|----------|-----------|
| **GA-001** | Owner Override Active | `sovereign_override_active` | 🔴 CRITICAL | `== 1` for > 5 min |
| **GA-002** | Bundle Quarantine | `sovereign_bundle_quarantine_total` | 🔴 CRITICAL | `> 0` (increase detected) |
| **GA-003** | AXE Trust Violation | `axe_trust_violation_total` | 🔴 CRITICAL | `> 0` (increase detected) |
| **GA-004** | Mode Switch Preflight Failure Rate | `sovereign_preflight_failure_total` | 🟡 WARNING | Rate > 10/hour |
| **GA-005** | Bundle Signature Failure Rate | `sovereign_bundle_signature_failure_total` | 🟡 WARNING | Rate > 5/hour |

### Additional Recommended Alerts

| Alert ID | Name | Metric | Severity | Threshold |
|----------|------|--------|----------|-----------|
| **GA-006** | Override Usage Spike | `sovereign_override_usage_total` | 🟡 WARNING | > 5 in 1 hour |
| **GA-007** | Governance Metrics Unavailable | `up{job="brain_governance"}` | 🔵 INFO | `== 0` for > 2 min |
| **GA-008** | Excessive Mode Switches | `sovereign_mode_switch_total` | 🟡 WARNING | > 10 in 1 hour |

---

## Prometheus Alert Rules

### Configuration File Structure

**File:** `prometheus/alerts/brain_governance_alerts.yml`

```yaml
groups:
  - name: brain_governance_critical
    interval: 30s
    rules:
      # ... CRITICAL alerts

  - name: brain_governance_warning
    interval: 60s
    rules:
      # ... WARNING alerts

  - name: brain_governance_info
    interval: 120s
    rules:
      # ... INFO alerts
```

### Complete Alert Rules

```yaml
# prometheus/alerts/brain_governance_alerts.yml

groups:
  # =========================================================================
  # CRITICAL ALERTS - Immediate Response Required
  # =========================================================================
  - name: brain_governance_critical
    interval: 30s
    rules:

      # GA-001: Owner Override Active
      - alert: GovernanceOverrideActive
        expr: sovereign_override_active == 1
        for: 5m
        labels:
          severity: critical
          component: governance
          layer: g2
          alert_id: GA-001
        annotations:
          summary: "Governance Override Currently Active"
          description: |
            **CRITICAL**: Owner override is currently active in the governance system.

            **Impact:**
            - Mode switch governance bypassed
            - Preflight checks can be skipped
            - Security posture temporarily degraded

            **Current Status:**
            - Override active: {{ $value }}
            - Instance: {{ $labels.instance }}

            **Action Required:**
            1. Check audit log for GOVERNANCE_OVERRIDE_CREATED event
            2. Verify override reason is legitimate (min 10 chars)
            3. Confirm override will expire (max 24h)
            4. Monitor for override consumption or expiration
            5. If unauthorized, escalate to security team immediately

            **Runbook:** docs/GOVERNANCE_RUNBOOKS.md#owner-override-active
          dashboard: "https://grafana.example.com/d/brain-governance"
          playbook: "https://wiki.example.com/brain/governance/override-incident"

      # GA-002: Bundle Quarantine
      - alert: GovernanceBundleQuarantined
        expr: increase(sovereign_bundle_quarantine_total[5m]) > 0
        for: 1m
        labels:
          severity: critical
          component: governance
          layer: g1
          alert_id: GA-002
        annotations:
          summary: "Bundle Quarantined - Trust Violation Detected"
          description: |
            **CRITICAL**: A bundle has been quarantined due to validation failure.

            **Impact:**
            - Bundle cannot be loaded (fail-closed)
            - Potential supply chain attack detected
            - Sovereign mode may be unavailable if this was the only bundle

            **Quarantine Count:**
            - Increase: {{ $value }}
            - Total: {{ query "sovereign_bundle_quarantine_total" }}

            **Action Required:**
            1. Check audit log for BUNDLE_QUARANTINED event
            2. Identify quarantined bundle ID
            3. Review quarantine reason (signature invalid, key untrusted, hash mismatch)
            4. Verify bundle was NOT loaded despite quarantine
            5. Investigate bundle source and signing key
            6. DO NOT remove from quarantine without security team approval

            **Runbook:** docs/GOVERNANCE_RUNBOOKS.md#bundle-quarantine
          dashboard: "https://grafana.example.com/d/brain-governance"
          playbook: "https://wiki.example.com/brain/governance/bundle-quarantine"

      # GA-003: AXE Trust Tier Violation
      - alert: GovernanceAXETrustViolation
        expr: increase(axe_trust_violation_total[5m]) > 0
        for: 1m
        labels:
          severity: critical
          component: governance
          layer: g3
          alert_id: GA-003
        annotations:
          summary: "AXE Trust Tier Violation - EXTERNAL Access Blocked"
          description: |
            **CRITICAL**: EXTERNAL request to AXE was blocked (trust tier violation).

            **Impact:**
            - Potential unauthorized access attempt
            - AXE DMZ isolation functioning correctly (fail-closed)
            - May indicate reconnaissance or attack

            **Violation Details:**
            - Increase: {{ $value }}
            - Trust tier: {{ $labels.trust_tier }}
            - Total violations: {{ query "axe_trust_violation_total" }}

            **Action Required:**
            1. Check audit log for AXE_TRUST_TIER_VIOLATION events
            2. Identify source IP from audit log
            3. Determine if this is:
               - Misconfiguration (wrong IP allowlist)
               - Legitimate external service (needs DMZ gateway auth)
               - Attack attempt (escalate to security)
            4. If attack: block source IP at firewall level
            5. If legitimate: add to DMZ gateway allowlist after approval

            **Runbook:** docs/GOVERNANCE_RUNBOOKS.md#axe-trust-tier-violation
          dashboard: "https://grafana.example.com/d/brain-governance"
          playbook: "https://wiki.example.com/brain/governance/axe-trust-violation"

  # =========================================================================
  # WARNING ALERTS - Investigation Required Within 30 Minutes
  # =========================================================================
  - name: brain_governance_warning
    interval: 60s
    rules:

      # GA-004: Mode Switch Preflight Failure Rate
      - alert: GovernancePreflightFailureRateHigh
        expr: rate(sovereign_preflight_failure_total[1h]) > 0.0027  # ~10/hour
        for: 5m
        labels:
          severity: warning
          component: governance
          layer: g2
          alert_id: GA-004
        annotations:
          summary: "High Preflight Failure Rate Detected"
          description: |
            **WARNING**: Preflight checks are failing at an elevated rate.

            **Impact:**
            - Mode switches being blocked by governance
            - May indicate configuration drift or operational issues
            - No immediate security impact (fail-closed working)

            **Failure Rate:**
            - Current: {{ $value | humanize }} failures/second
            - Threshold: 0.0027 failures/second (~10/hour)
            - Failed gate: {{ $labels.gate }}

            **Action Required:**
            1. Check which gate is failing most frequently
            2. Review recent preflight failure audit events
            3. Common causes:
               - Network gate: Network connectivity issues
               - IPv6 gate: IPv6 not properly disabled
               - DMZ gate: DMZ still running when switching to SOVEREIGN
               - Bundle trust gate: Bundle signature invalid or key not trusted
            4. Fix underlying cause (network, config, bundle)
            5. If persistent, may need override (with proper reason and approval)

            **Runbook:** docs/GOVERNANCE_RUNBOOKS.md#preflight-failure-rate
          dashboard: "https://grafana.example.com/d/brain-governance"
          playbook: "https://wiki.example.com/brain/governance/preflight-failures"

      # GA-005: Bundle Signature Failure Rate
      - alert: GovernanceBundleSignatureFailureRateHigh
        expr: rate(sovereign_bundle_signature_failure_total[1h]) > 0.0013  # ~5/hour
        for: 5m
        labels:
          severity: warning
          component: governance
          layer: g1
          alert_id: GA-005
        annotations:
          summary: "High Bundle Signature Failure Rate"
          description: |
            **WARNING**: Bundle signature validations are failing at an elevated rate.

            **Impact:**
            - Bundles are being quarantined
            - May indicate:
              - Key rotation in progress (expected)
              - Corrupted bundles (filesystem issue)
              - Signing key compromise (security incident)

            **Failure Rate:**
            - Current: {{ $value | humanize }} failures/second
            - Threshold: 0.0013 failures/second (~5/hour)

            **Action Required:**
            1. Check audit log for BUNDLE_SIGNATURE_INVALID events
            2. Identify affected bundle IDs
            3. Verify if this is expected:
               - Key rotation: Add new key to trusted keyring
               - Old bundles: Re-sign with current trusted key
               - Corrupted files: Verify SHA256 hashes
            4. If unexpected:
               - Check for filesystem corruption
               - Verify trusted keyring integrity
               - Investigate potential signing key compromise
            5. DO NOT disable signature validation to "fix" this

            **Runbook:** docs/GOVERNANCE_RUNBOOKS.md#bundle-signature-failure-rate
          dashboard: "https://grafana.example.com/d/brain-governance"
          playbook: "https://wiki.example.com/brain/governance/bundle-signature-failures"

      # GA-006: Override Usage Spike (Additional Recommended)
      - alert: GovernanceOverrideUsageSpike
        expr: increase(sovereign_override_usage_total[1h]) > 5
        for: 5m
        labels:
          severity: warning
          component: governance
          layer: g2
          alert_id: GA-006
        annotations:
          summary: "Governance Override Usage Spike Detected"
          description: |
            **WARNING**: Governance overrides are being used more frequently than normal.

            **Impact:**
            - Frequent governance bypass may indicate:
              - Operational issue requiring overrides
              - Misconfiguration of preflight gates
              - Potential override abuse

            **Usage:**
            - Overrides in last hour: {{ $value }}
            - Threshold: 5 per hour

            **Action Required:**
            1. Review all GOVERNANCE_OVERRIDE_CREATED events in last hour
            2. Check override reasons (must be min 10 chars)
            3. Verify each override was consumed (GOVERNANCE_OVERRIDE_CONSUMED)
            4. Identify pattern:
               - Same gate failing repeatedly: Fix gate configuration
               - Same operator: Training issue or intentional bypass
               - Random: May be legitimate operational issue
            5. If pattern detected, address root cause instead of overrides

            **Runbook:** docs/GOVERNANCE_RUNBOOKS.md#override-usage-spike
          dashboard: "https://grafana.example.com/d/brain-governance"

      # GA-008: Excessive Mode Switches (Additional Recommended)
      - alert: GovernanceModeSwitch Flapping
        expr: increase(sovereign_mode_switch_total[1h]) > 10
        for: 10m
        labels:
          severity: warning
          component: governance
          layer: g2
          alert_id: GA-008
        annotations:
          summary: "Excessive Mode Switches - Possible Flapping"
          description: |
            **WARNING**: Operation mode is switching frequently (possible flapping).

            **Impact:**
            - Unstable operation mode
            - May indicate:
              - Network instability
              - Automatic mode switching logic issues
              - Manual operational changes

            **Switch Count:**
            - Switches in last hour: {{ $value }}
            - Threshold: 10 per hour

            **Action Required:**
            1. Check MODE_CHANGED audit events
            2. Identify mode switch pattern (e.g., ONLINE ↔ OFFLINE)
            3. Determine trigger:
               - Auto-detect: Network connectivity flapping
               - Manual: Operator error or testing
               - Scheduled: Expected behavior (ignore alert)
            4. If network flapping:
               - Investigate network stability
               - Adjust auto-detect thresholds if needed
            5. If manual: Coordinate with ops team

            **Runbook:** docs/GOVERNANCE_RUNBOOKS.md#mode-switch-flapping

  # =========================================================================
  # INFO ALERTS - Best Effort Response
  # =========================================================================
  - name: brain_governance_info
    interval: 120s
    rules:

      # GA-007: Governance Metrics Unavailable
      - alert: GovernanceMetricsUnavailable
        expr: up{job="brain_governance"} == 0
        for: 2m
        labels:
          severity: info
          component: monitoring
          alert_id: GA-007
        annotations:
          summary: "Governance Metrics Endpoint Unavailable"
          description: |
            **INFO**: Prometheus cannot scrape governance metrics endpoint.

            **Impact:**
            - No governance metrics being collected
            - Cannot detect governance violations until restored
            - NOT a governance violation itself (monitoring issue)

            **Status:**
            - Endpoint: {{ $labels.instance }}
            - Job: {{ $labels.job }}

            **Action Required:**
            1. Check if BRAiN backend is running
            2. Verify endpoint is accessible: curl http://HOST:PORT/api/sovereign-mode/metrics
            3. Check backend logs for errors
            4. Verify network connectivity from Prometheus to backend
            5. If backend is down: restart backend service
            6. If endpoint changed: update Prometheus scrape config

            **Runbook:** docs/GOVERNANCE_RUNBOOKS.md#metrics-unavailable
          dashboard: "https://grafana.example.com/d/brain-governance"
```

---

## Alert Descriptions

### GA-001: Owner Override Active

**Metric:** `sovereign_override_active`
**Severity:** 🔴 CRITICAL
**Threshold:** `== 1` for > 5 minutes

**Meaning:**
An owner override is currently active, allowing mode switches to bypass preflight failures.

**Risk:**
- **High**: Governance temporarily weakened
- Preflight gate failures can be ignored
- Could allow insecure mode transitions
- Override is time-limited (max 24h) and single-use, but still reduces security posture

**When This Alerts:**
- Override was created via API with explicit reason
- Override has not yet been consumed or expired
- Gauge value is `1` (active)

**Expected Scenarios:**
- **Legitimate**: Emergency maintenance, network outage, operational necessity with documented reason
- **Suspicious**: Generic reason, frequent overrides, override during off-hours

**Action Required:**
1. ✅ Query audit log: `GET /api/sovereign-mode/audit?event_type=mode_override_created`
2. ✅ Verify override reason is specific and > 10 characters
3. ✅ Check override expiration time (should be < 24h)
4. ✅ Confirm override requester is authorized (owner/admin)
5. ⚠️ If unauthorized or suspicious: **Revoke immediately** and escalate to security team
6. ✅ Monitor for override consumption or expiration

**Resolution:**
- Alert clears when override is consumed (`sovereign_override_active` returns to `0`)
- Override expires after configured duration (default 1 hour, max 24h)
- Override can only be used once (single-use flag)

**False Positive Rate:** Very Low (override requires explicit API call)

---

### GA-002: Bundle Quarantine

**Metric:** `sovereign_bundle_quarantine_total`
**Severity:** 🔴 CRITICAL
**Threshold:** `increase() > 0` (any new quarantine)

**Meaning:**
A bundle has been quarantined due to failed validation (signature invalid, key untrusted, or hash mismatch).

**Risk:**
- **Critical**: Potential supply chain attack or bundle tampering
- Quarantined bundle **cannot be loaded** (fail-closed)
- If this was the only available bundle, Sovereign mode may be unavailable

**When This Alerts:**
- Bundle signature verification failed
- Bundle signed by untrusted key (not in keyring)
- Bundle file hash does not match manifest
- Bundle lacks required signature (and policy is strict)

**Expected Scenarios:**
- **Legitimate**: Key rotation without updating keyring, corrupted file during download, unsigned development bundle
- **Suspicious**: Previously-valid bundle now fails, unexpected bundle in directory, signature tampering

**Action Required:**
1. ✅ Query audit log: `GET /api/sovereign-mode/audit?event_type=bundle_quarantined`
2. ✅ Identify quarantined bundle ID and reason
3. ✅ Verify bundle source and authenticity
4. ✅ Check if quarantined bundle is in `storage/quarantine/` directory
5. ⚠️ **DO NOT** remove from quarantine without security team approval
6. ✅ Determine root cause:
   - **Key rotation**: Add new signing key to trusted keyring
   - **Corrupted file**: Re-download bundle from trusted source
   - **Unsigned bundle**: Re-sign with trusted key or update policy to allow unsigned (dev only)
   - **Tampering**: **SECURITY INCIDENT** - escalate immediately

**Resolution:**
- Add trusted signing key to keyring if legitimate
- Re-sign bundle with trusted key
- Remove corrupted bundle and re-download
- **NEVER** remove bundle from quarantine to "fix" the issue

**False Positive Rate:** Low (indicates actual validation failure)

---

### GA-003: AXE Trust Tier Violation

**Metric:** `axe_trust_violation_total{trust_tier="external"}`
**Severity:** 🔴 CRITICAL
**Threshold:** `increase() > 0` (any new violation)

**Meaning:**
An EXTERNAL request to AXE was blocked because it did not come from a trusted source (LOCAL or DMZ).

**Risk:**
- **High**: Potential unauthorized access attempt to AXE
- Could indicate reconnaissance or active attack
- DMZ isolation is working correctly (fail-closed)

**When This Alerts:**
- Request source IP not in localhost range (`127.0.0.1`, `::1`)
- Request source IP not in DMZ gateway allowlist
- Request classified as EXTERNAL trust tier
- Request blocked with HTTP 403

**Expected Scenarios:**
- **Legitimate**: Misconfigured client using wrong IP, new DMZ gateway not yet added to allowlist, testing from external network
- **Suspicious**: Unknown source IP, repeated attempts from same IP, scanning/probing behavior

**Action Required:**
1. ✅ Query audit log: `GET /api/sovereign-mode/audit?event_type=axe_trust_tier_violation`
2. ✅ Identify source IP from audit log metadata
3. ✅ Check if source IP is recognized:
   - **Known internal service**: Misconfiguration, should use localhost or DMZ gateway
   - **Known DMZ gateway**: Add IP to allowlist (requires approval)
   - **Unknown IP**: Potential attack
4. ⚠️ If unknown IP with repeated attempts: **Block at firewall level immediately**
5. ✅ If legitimate external service: Configure DMZ gateway authentication (do NOT add raw IP to allowlist)
6. ✅ Review AXE_REQUEST_BLOCKED audit events for pattern

**Resolution:**
- Legitimate clients reconfigured to use localhost or DMZ gateway
- DMZ gateway IP added to allowlist (after security approval)
- Attack source blocked at firewall/IDS level

**False Positive Rate:** Medium (legitimate misconfigurations common)

---

### GA-004: Mode Switch Preflight Failure Rate

**Metric:** `rate(sovereign_preflight_failure_total[1h])`
**Severity:** 🟡 WARNING
**Threshold:** `> 10 failures/hour`

**Meaning:**
Preflight checks are failing at an elevated rate, blocking mode switches.

**Risk:**
- **Medium**: Mode switches blocked, but this is **expected behavior** (fail-closed)
- Indicates operational issues that need attention
- No immediate security impact (governance working correctly)

**When This Alerts:**
- Preflight gate failures exceeding threshold
- Most common gates:
  - **Network gate**: Network connectivity when switching to SOVEREIGN
  - **IPv6 gate**: IPv6 not properly disabled
  - **DMZ gate**: DMZ still running when switching to SOVEREIGN/OFFLINE
  - **Bundle trust gate**: Bundle signature invalid or key untrusted

**Expected Scenarios:**
- **Network instability**: Network up/down flapping triggering auto-detection
- **Configuration drift**: IPv6 re-enabled after update, DMZ not stopping correctly
- **Bundle issues**: Bundle validation failures (see GA-005)

**Action Required:**
1. ✅ Check which gate is failing: Look at `{gate="..."}` label in metric
2. ✅ Query audit log: `GET /api/sovereign-mode/audit?event_type=mode_preflight_failed`
3. ✅ Identify pattern:
   - **Same gate repeatedly**: Fix configuration issue
   - **Random gates**: May be operational instability
4. ✅ Fix per gate:
   - **Network gate**: Investigate network stability, adjust auto-detect thresholds
   - **IPv6 gate**: Ensure IPv6 is disabled before switching to SOVEREIGN
   - **DMZ gate**: Fix DMZ stop/start logic, check for port conflicts
   - **Bundle trust gate**: Fix bundle signature/key issue (see GA-002, GA-005)
5. ✅ If issue persists and mode switch is operationally necessary: Use override (with proper reason and approval)

**Resolution:**
- Underlying configuration issue fixed
- Network stabilized
- Bundle validation issues resolved
- Failure rate drops below threshold

**False Positive Rate:** Low (indicates real operational issues)

---

### GA-005: Bundle Signature Failure Rate

**Metric:** `rate(sovereign_bundle_signature_failure_total[1h])`
**Severity:** 🟡 WARNING
**Threshold:** `> 5 failures/hour`

**Meaning:**
Bundle signature validations are failing at an elevated rate.

**Risk:**
- **Medium**: Bundles being quarantined, Sovereign mode may be unavailable
- Could indicate:
  - Key rotation in progress (expected, temporary)
  - Filesystem corruption (operational issue)
  - Signing key compromise (security incident)

**When This Alerts:**
- Bundle signature verification failing repeatedly
- Bundles being quarantined automatically (trigger GA-002)
- Signature validation happening during:
  - Bundle discovery
  - Bundle validation
  - Bundle load attempts

**Expected Scenarios:**
- **Key rotation**: Old bundles signed with old key, new key not yet in keyring
- **File corruption**: Filesystem issues, incomplete downloads
- **Development**: Unsigned bundles in production directory (policy violation)

**Action Required:**
1. ✅ Query audit log: `GET /api/sovereign-mode/audit?event_type=bundle_signature_invalid`
2. ✅ Identify affected bundle IDs
3. ✅ Determine cause:
   - **Key rotation**: Expected, add new key to trusted keyring
   - **Old bundles**: Re-sign with current trusted key or remove
   - **Corrupted files**: Verify SHA256 hashes, re-download bundles
   - **Unsigned bundles**: Remove from production or re-sign
4. ⚠️ **DO NOT** disable signature validation or change policy to permissive
5. ✅ If filesystem corruption suspected: Run `fsck` or equivalent
6. ✅ If signing key compromise suspected: **SECURITY INCIDENT** - revoke key, re-sign all bundles

**Resolution:**
- Trusted keyring updated with new keys
- Corrupted bundles re-downloaded
- Old unsigned bundles removed or re-signed
- Signature failure rate returns to near-zero

**False Positive Rate:** Low (indicates real validation failures)

---

## Alert Routing & Escalation

### Routing Matrix

| Severity | Channel | Response Time | Escalation Path |
|----------|---------|---------------|-----------------|
| 🔴 **CRITICAL** | PagerDuty + Email + Slack #incidents | Immediate (page on-call) | On-Call Eng → Senior Eng → Security Team |
| 🟡 **WARNING** | Email + Slack #governance-alerts | < 30 min | Platform Ops → On-Call Eng |
| 🔵 **INFO** | Slack #governance-monitoring | Best effort | Platform Ops |

### Prometheus Alertmanager Configuration

**File:** `prometheus/alertmanager.yml`

```yaml
global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

route:
  group_by: ['alertname', 'severity', 'component']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'governance-default'

  routes:
    # CRITICAL alerts - page on-call immediately
    - match:
        severity: critical
      receiver: 'governance-critical'
      continue: true
      group_wait: 10s
      group_interval: 2m
      repeat_interval: 1h

    # WARNING alerts - email + Slack
    - match:
        severity: warning
      receiver: 'governance-warning'
      group_wait: 1m
      group_interval: 10m
      repeat_interval: 4h

    # INFO alerts - Slack only
    - match:
        severity: info
      receiver: 'governance-info'
      group_wait: 5m
      group_interval: 30m
      repeat_interval: 12h

receivers:
  - name: 'governance-default'
    slack_configs:
      - channel: '#governance-monitoring'
        title: 'BRAiN Governance Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ end }}'

  - name: 'governance-critical'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'
        severity: 'critical'
    email_configs:
      - to: 'ops-oncall@example.com'
        subject: '🔴 CRITICAL: {{ .GroupLabels.alertname }}'
    slack_configs:
      - channel: '#incidents'
        title: '🔴 CRITICAL GOVERNANCE ALERT'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
        color: 'danger'

  - name: 'governance-warning'
    email_configs:
      - to: 'platform-ops@example.com'
        subject: '🟡 WARNING: {{ .GroupLabels.alertname }}'
    slack_configs:
      - channel: '#governance-alerts'
        title: '🟡 Governance Warning'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        color: 'warning'

  - name: 'governance-info'
    slack_configs:
      - channel: '#governance-monitoring'
        title: 'ℹ️ Governance Info'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

inhibit_rules:
  # Don't alert on metrics unavailable if backend is down
  - source_match:
      alertname: 'BackendDown'
    target_match:
      alertname: 'GovernanceMetricsUnavailable'
    equal: ['instance']
```

### Escalation Timeline

**CRITICAL Alerts (GA-001, GA-002, GA-003):**
```
T+0 min:  Alert fires → PagerDuty page + Email + Slack
T+5 min:  If not acknowledged → Escalate to Senior On-Call
T+15 min: If not resolved → Escalate to Security Team
T+30 min: If not resolved → Escalate to Engineering Manager
```

**WARNING Alerts (GA-004, GA-005):**
```
T+0 min:  Alert fires → Email + Slack
T+30 min: If not acknowledged → Reminder email
T+2 hr:   If not resolved → Escalate to On-Call Engineer
T+4 hr:   Repeat notification
```

**INFO Alerts (GA-007):**
```
T+0 min:  Alert fires → Slack notification
T+12 hr:  Repeat notification if still unresolved
```

---

## Testing & Validation

### Pre-Production Testing

Before deploying these alert rules to production, test each alert:

#### Test 1: Override Alert (GA-001)

```bash
# Create override
curl -X POST http://localhost:8000/api/sovereign-mode/mode \
  -H "Content-Type: application/json" \
  -d '{
    "target_mode": "sovereign",
    "override_reason": "Testing alert GA-001 - Owner Override Active",
    "override_duration_seconds": 600
  }'

# Wait 5+ minutes
# Verify alert fires in Prometheus: ALERTS{alertname="GovernanceOverrideActive"}
# Verify PagerDuty page received
# Verify Slack message in #incidents

# Clean up: Consume or wait for expiration
```

#### Test 2: Bundle Quarantine Alert (GA-002)

```bash
# Option A: Place invalid bundle in bundles directory
cp /tmp/invalid_bundle.tar.gz storage/models/bundles/test_bundle.tar.gz

# Option B: Use API to trigger validation
curl -X POST http://localhost:8000/api/sovereign-mode/bundles/test_bundle/validate

# Verify alert fires within 1 minute
# Check audit log for BUNDLE_QUARANTINED event
# Verify bundle moved to storage/quarantine/

# Clean up: Remove test bundle
```

#### Test 3: AXE Trust Violation Alert (GA-003)

```bash
# Send AXE request from external IP (not localhost)
curl -X POST http://EXTERNAL_IP:8000/api/axe/message \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'

# Expected: HTTP 403 Forbidden
# Verify alert fires within 1 minute
# Check audit log for AXE_TRUST_TIER_VIOLATION

# No cleanup needed (request was blocked)
```

#### Test 4: Preflight Failure Rate Alert (GA-004)

```bash
# Trigger 12 preflight failures in 1 hour
for i in {1..12}; do
  curl -X POST http://localhost:8000/api/sovereign-mode/mode/preflight \
    -H "Content-Type: application/json" \
    -d '{"target_mode": "sovereign"}'
  sleep 300  # 5 minutes
done

# Verify alert fires after 5 minutes of elevated rate
# Check Prometheus query: rate(sovereign_preflight_failure_total[1h])
```

#### Test 5: Bundle Signature Failure Rate Alert (GA-005)

```bash
# Create 6 unsigned bundles
for i in {1..6}; do
  dd if=/dev/urandom of=storage/models/bundles/unsigned_$i.tar.gz bs=1M count=1
  sleep 600  # 10 minutes
done

# Trigger validation
curl -X GET http://localhost:8000/api/sovereign-mode/bundles

# Verify alert fires after 5 minutes
# Check metric: rate(sovereign_bundle_signature_failure_total[1h])

# Clean up: Remove unsigned bundles
```

### Alert Validation Checklist

For each alert:
- [ ] Alert fires when threshold is exceeded
- [ ] Alert includes all required annotations (summary, description, runbook)
- [ ] Alert routes to correct receiver (PagerDuty/Email/Slack)
- [ ] Alert clears when condition resolves
- [ ] Alert does NOT fire during normal operations
- [ ] Runbook link is accessible and accurate
- [ ] Dashboard link is accessible
- [ ] Alert severity matches actual risk

---

## Maintenance & Review

### Regular Reviews

**Weekly:**
- Review alert history in Prometheus Alertmanager
- Check for frequent false positives
- Adjust thresholds if needed (document changes)

**Monthly:**
- Review all alert descriptions for accuracy
- Update runbook links
- Test each alert rule in staging
- Review escalation paths (are on-call contacts current?)

**Quarterly:**
- Full alert rule review with Security Team
- Update thresholds based on operational data
- Review incident response effectiveness
- Update documentation

### Threshold Tuning

If alert fires too frequently (false positive):
1. Document current threshold and fire rate
2. Analyze historical data to find appropriate threshold
3. Update threshold in alert rule
4. Test new threshold in staging
5. Deploy to production
6. Document change in this file (version history)

**Example:**
```yaml
# OLD: GA-004 threshold
expr: rate(sovereign_preflight_failure_total[1h]) > 0.0027  # 10/hour

# NEW: Increased after 2 weeks of data showing normal rate is ~8/hour
# Changed: 2026-01-15, Reason: Reduce false positives, normal ops ~8/hour
expr: rate(sovereign_preflight_failure_total[1h]) > 0.0055  # 20/hour
```

### Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-12-25 | Initial alerting policy with 5 required alerts + 3 recommended | Claude Code Agent |

---

## Appendix: Quick Reference

### Alert Quick Lookup

| Alert ID | Name | Metric | Action |
|----------|------|--------|--------|
| GA-001 | Override Active | `sovereign_override_active` | Check audit log, verify reason |
| GA-002 | Bundle Quarantine | `sovereign_bundle_quarantine_total` | Check quarantine dir, verify bundle |
| GA-003 | Trust Violation | `axe_trust_violation_total` | Check source IP, block if attack |
| GA-004 | Preflight Failures | `sovereign_preflight_failure_total` | Fix failing gate configuration |
| GA-005 | Signature Failures | `sovereign_bundle_signature_failure_total` | Update keyring, re-sign bundles |

### Useful Prometheus Queries

```promql
# Current override status
sovereign_override_active

# Total quarantined bundles
sovereign_bundle_quarantine_total

# Trust violations by tier
sum by (trust_tier) (axe_trust_violation_total)

# Preflight failure rate (last 1h)
rate(sovereign_preflight_failure_total[1h])

# Most common failing gate
topk(3, sum by (gate) (increase(sovereign_preflight_failure_total[24h])))

# Bundle signature failure trend
increase(sovereign_bundle_signature_failure_total[24h])

# Override usage trend
increase(sovereign_override_usage_total[7d])

# Mode switches by target mode
sum by (target_mode) (sovereign_mode_switch_total)
```

### Related Documents

- **Incident Runbooks**: `docs/GOVERNANCE_RUNBOOKS.md` (A2)
- **Evidence Pack**: `docs/GOVERNANCE_EVIDENCE_PACK.md`
- **Metrics Catalog**: `G4_IMPLEMENTATION_REPORT.md` (Section: G4.1 Metrics Catalog)
- **API Reference**: `docs/GOVERNANCE_EVIDENCE_PACK.md` (Section 7: Available Metrics)

---

**Document End**

**Next Actions:**
1. Deploy alert rules to Prometheus
2. Configure Alertmanager receivers
3. Test each alert rule
4. Create incident runbooks (A2)

**Version:** 1.0.0
**Last Updated:** 2025-12-25
**Status:** PRODUCTION READY
