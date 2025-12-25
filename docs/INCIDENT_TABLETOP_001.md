# Incident Tabletop Exercise 001: Owner Override Active → Forgotten/Misused

**Exercise Type:** Governance Incident Simulation
**Scenario ID:** TABLETOP-001
**Severity:** HIGH (SEV-1/2)
**Duration:** 60 minutes
**Participants:** On-Call Engineer, Security Lead, Platform Owner
**Prerequisites:** Access to Prometheus, audit logs, BRAiN backend API

**Version:** 1.0.0
**Last Updated:** 2025-12-25
**Related Documents:**
- `docs/GOVERNANCE_RUNBOOKS.md` (RB-1: Owner Override Active)
- `docs/ALERTING_POLICY.md` (GA-001: GovernanceOverrideActive)
- `docs/GOVERNANCE_EVIDENCE_PACK.md` (Chapter 12: Override Governance)

---

## Exercise Objectives

**Primary Goals:**
1. ✅ Practice detection and response to governance override activation
2. ✅ Validate Prometheus alerting and audit log forensics
3. ✅ Test decision-making under time pressure (legitimate vs. suspicious override)
4. ✅ Verify evidence collection procedures for post-incident review
5. ✅ Identify gaps in runbooks, alerting, or monitoring

**Secondary Goals:**
- Build muscle memory for governance incident response
- Validate cross-team communication protocols
- Test escalation procedures
- Identify automation opportunities

---

## Scenario Overview

### Situation

**Date:** 2025-12-25 14:30 UTC
**Alert:** `GovernanceOverrideActive` has been firing for 15 minutes
**Context:** Production environment, normal business hours

**Initial Information:**
- **Alert ID:** GA-001
- **Severity:** CRITICAL
- **Trigger:** `sovereign_override_active == 1`
- **Duration:** 15 minutes (since 14:15 UTC)
- **Source:** Prometheus

**Unknown at Start:**
- Who activated the override?
- Why was it activated?
- When will it expire?
- Has it been consumed yet?
- Is this legitimate or suspicious?

---

## Phase 1: Detection (0-5 Minutes)

### Trigger Event

**You receive a PagerDuty alert:**

```
CRITICAL: GovernanceOverrideActive
Time: 2025-12-25 14:15 UTC
Instance: brain-backend
Component: governance
Alert: Owner override is currently active in the governance system.

Impact:
- Mode switch governance bypassed
- Preflight checks can be skipped
- Security posture temporarily degraded

Action Required:
1. Check audit log for GOVERNANCE_OVERRIDE_CREATED event
2. Verify override reason is legitimate (min 10 chars)
3. Confirm override will expire (max 24h)
4. Monitor for override consumption or expiration
5. If unauthorized, escalate to security team immediately

Runbook: docs/GOVERNANCE_RUNBOOKS.md#owner-override-active
```

### Initial Response Actions

**What you should do (< 5 minutes):**

1. **Acknowledge alert in PagerDuty**
   - Prevents duplicate pages to on-call rotation

2. **Open incident channel**
   ```
   #incident-2025-12-25-001 (Slack/Teams/Discord)
   ```

3. **Announce incident**
   ```
   🚨 SEV-2 Incident: Governance Override Active
   Alert: GA-001 GovernanceOverrideActive
   Started: 14:15 UTC (15 minutes ago)
   On-Call: @engineer-name
   Runbook: docs/GOVERNANCE_RUNBOOKS.md#owner-override-active
   ```

4. **Access diagnostics tools**
   - Prometheus UI: `http://prometheus:9090`
   - Audit log API: `http://backend:8000/api/sovereign-mode/audit`
   - Backend health: `http://backend:8000/health`

---

## Phase 2: Investigation (5-15 Minutes)

### Step 1: Confirm Override Status

**Query Prometheus:**

```promql
sovereign_override_active
```

**Expected Output:**
```
sovereign_override_active{component="sovereign-mode",instance="backend:8000",job="brain-governance",layer="governance",module="g4-monitoring"} 1
```

**Interpretation:**
- Value `1` = Override is ACTIVE (confirm alert)
- Value `0` = Override is NOT active (false positive or already cleared)

**✅ Checkpoint:** Override confirmed active.

---

### Step 2: Find Override Creation Event

**Query Audit Log API:**

```bash
curl -s http://localhost:8000/api/sovereign-mode/audit?limit=100 | \
  jq '.[] | select(.event_type == "sovereign.governance_override_created")' | \
  jq -s 'sort_by(.timestamp) | reverse | first'
```

**Sample Output:**

```json
{
  "timestamp": "2025-12-25T14:15:23.456789Z",
  "event_type": "sovereign.governance_override_created",
  "severity": "WARNING",
  "success": true,
  "reason": "Emergency mode switch for production deployment - DR failover to sovereign mode required",
  "metadata": {
    "override_id": "ovr_a1b2c3d4e5f6",
    "reason": "Emergency mode switch for production deployment - DR failover to sovereign mode required",
    "ttl_seconds": 3600,
    "expires_at": "2025-12-25T15:15:23.456789Z",
    "created_by": "api",
    "single_use": true,
    "consumed": false
  }
}
```

**Extract Key Information:**

| Field | Value | Assessment |
|-------|-------|------------|
| **Override ID** | `ovr_a1b2c3d4e5f6` | ✅ Valid format |
| **Reason** | "Emergency mode switch... DR failover..." | ✅ Detailed (> 10 chars) |
| **TTL** | 3600 seconds (1 hour) | ✅ Reasonable (< 24h max) |
| **Expires At** | 15:15 UTC (45 min from now) | ✅ Time-limited |
| **Created By** | `api` | ⚠️ Unknown requester (investigate) |
| **Single Use** | `true` | ✅ Fail-safe enabled |
| **Consumed** | `false` | ⚠️ Not yet used (45 min remaining) |

**✅ Checkpoint:** Override details extracted.

---

### Step 3: Risk Assessment

**Decision Tree:**

```
Is the override reason >= 10 characters?
├─ NO → 🔴 SUSPICIOUS (skip to Phase 3: Escalation)
└─ YES → Continue
         │
         Is the TTL <= 24 hours?
         ├─ NO → 🔴 SUSPICIOUS (skip to Phase 3: Escalation)
         └─ YES → Continue
                  │
                  Is the override consumed?
                  ├─ YES → 🟢 LEGITIMATE (skip to Phase 4: Monitoring)
                  └─ NO → Continue
                          │
                          Can you identify the requester?
                          ├─ YES → 🟡 LIKELY LEGITIMATE (verify with requester)
                          └─ NO → 🟠 SUSPICIOUS (investigate further)
```

**Your Assessment:**

- ✅ Reason is detailed (> 10 chars): "Emergency mode switch for production deployment..."
- ✅ TTL is reasonable (1 hour < 24h max)
- ⚠️ Not yet consumed (45 minutes remaining)
- ⚠️ Created by "api" (unknown requester)

**Initial Classification:** 🟠 **SUSPICIOUS** (proceed with caution)

**Next Action:** Verify if there's an ongoing deployment or known DR scenario.

---

### Step 4: Contextual Verification

**Check for ongoing deployments:**

```bash
# Check recent git commits
git log --since="2 hours ago" --oneline

# Check deployment logs
kubectl logs -n brain deployment/brain-backend --since=2h | grep -i "deploy\|release"

# Check incident channel history
# (Slack: search for "deploy", "DR", "failover" in last 2 hours)
```

**Check for known incidents:**

```bash
# Query incident management system (PagerDuty, Opsgenie)
pd incident list --since="2 hours ago"

# Check status page
curl https://status.brain.example.com/api/incidents
```

**Scenario Result (for this tabletop):**

```
❌ No recent deployments found
❌ No active incidents related to DR or failover
❌ No announcements in #deployments or #incidents channels
```

**Updated Classification:** 🔴 **HIGHLY SUSPICIOUS** (escalate immediately)

**✅ Checkpoint:** Contextual verification complete. Override appears unauthorized.

---

## Phase 3: Escalation (15-20 Minutes)

### Immediate Actions

**1. Escalate to Security Team**

```
@security-team 🚨 URGENT: Suspicious governance override detected

Override ID: ovr_a1b2c3d4e5f6
Created: 14:15 UTC (30 minutes ago)
Reason: "Emergency mode switch... DR failover..." (suspicious - no known DR event)
Created By: API (unknown requester)
Expires: 15:15 UTC (15 minutes from now)
Consumed: NO (override still active, not yet used)

No evidence of:
- Recent deployments
- Active DR scenarios
- Announced maintenance

Recommendation: Treat as potential unauthorized access attempt.
Runbook: RB-1 (Owner Override Active) → Case B (Suspicious Override)

@security-lead please advise on next steps.
```

**2. Increase Monitoring Frequency**

```promql
# Check override status every 30 seconds
sovereign_override_active
```

**3. Gather Forensic Evidence**

```bash
# Export full audit log for last 2 hours
curl -s http://localhost:8000/api/sovereign-mode/audit?limit=1000 > /tmp/audit-forensics-$(date +%s).jsonl

# Capture current system state
curl -s http://localhost:8000/api/sovereign-mode/status > /tmp/status-forensics-$(date +%s).json
curl -s http://localhost:8000/api/sovereign-mode/governance/status > /tmp/governance-forensics-$(date +%s).json

# Capture Prometheus metrics snapshot
curl -s http://prometheus:9090/api/v1/query?query=sovereign_override_active > /tmp/prometheus-override-$(date +%s).json
```

**4. Document Timeline**

| Time (UTC) | Event | Source | Action Taken |
|------------|-------|--------|--------------|
| 14:15:23 | Override created | Audit log | - |
| 14:15:30 | Alert fired | Prometheus | - |
| 14:30:00 | Alert acknowledged | PagerDuty | Incident channel created |
| 14:35:00 | Override details extracted | Audit API | Risk assessment: SUSPICIOUS |
| 14:40:00 | Contextual verification | Git/K8s/Incidents | No matching deployment/DR |
| 14:45:00 | Escalated to security | Slack | Forensic evidence collected |

**✅ Checkpoint:** Escalation complete. Awaiting security team guidance.

---

### Security Team Response (Simulated)

**Security Lead confirms:**
```
@on-call-engineer Confirmed: No authorized override request on record.
This appears to be an unauthorized access attempt.

DO NOT attempt to manually revoke the override (could alert attacker).
Continue monitoring until expiration (15:15 UTC, 10 minutes).
If override is consumed before expiration, treat as SEV-1 security breach.

I'm initiating parallel investigation:
- Reviewing API access logs for source IP
- Checking for credential compromise
- Coordinating with infrastructure team

Stay on standby. Report immediately if override status changes.
```

**✅ Checkpoint:** Security team engaged. Monitoring phase begins.

---

## Phase 4: Monitoring & Containment (20-45 Minutes)

### Active Monitoring

**Monitor override consumption every 60 seconds:**

```bash
while true; do
  STATUS=$(curl -s http://localhost:8000/api/sovereign-mode/audit?limit=1 | \
    jq -r '.[] | select(.event_type == "sovereign.governance_override_consumed") | .timestamp')

  if [[ -n "$STATUS" ]]; then
    echo "🚨 OVERRIDE CONSUMED AT: $STATUS"
    echo "ESCALATE TO SEV-1 IMMEDIATELY"
    break
  fi

  echo "[$(date -Iseconds)] Override not consumed. Waiting..."
  sleep 60
done
```

**Monitor mode switches:**

```promql
increase(sovereign_mode_switch_total[5m])
```

**If mode switch detected while override is active:**
```
🚨 MODE SWITCH DETECTED USING OVERRIDE
Escalate to SEV-1 security breach
Runbook: RB-4 (Mode Switch Rollback) + Security Incident Response Plan
```

---

### Containment Actions (If Override is Consumed)

**Scenario A: Override consumed (SEV-1 breach)**

```
1. Immediate Actions:
   - Page security team lead
   - Activate security incident response plan
   - Freeze current system state (no further changes)
   - Capture full memory dump (if forensics team requests)

2. Forensic Evidence Collection:
   - Full audit log export (last 24 hours)
   - System state snapshot
   - Network flow logs (source IP of override creation)
   - Database transaction logs

3. Containment:
   - Isolate affected systems (network segmentation)
   - Rotate all API keys and credentials
   - Review all mode switches in last 2 hours
   - Check for data exfiltration (egress logs)

4. Communication:
   - Notify executive team (CISO, CTO)
   - Prepare incident report for legal/compliance
   - Do NOT communicate externally until approved
```

**Scenario B: Override expires without consumption (preferred outcome)**

```
1. Verify Expiration:
   - Query Prometheus: sovereign_override_active == 0
   - Query audit log for GOVERNANCE_OVERRIDE_EXPIRED event

2. Post-Incident Actions:
   - Complete forensic analysis (why was override created?)
   - Review API access logs for anomalies
   - Check for credential compromise
   - Update runbooks if gaps found

3. Documentation:
   - Write post-mortem (template below)
   - Update incident timeline
   - Share lessons learned with team
```

**For this tabletop, assume:** Override expires at 15:15 UTC without being consumed.

---

## Phase 5: Resolution & Post-Mortem (45-60 Minutes)

### Verify Override Cleared

**Query Prometheus:**

```promql
sovereign_override_active
```

**Expected Output (after 15:15 UTC):**
```
sovereign_override_active{...} 0
```

**Query Audit Log:**

```bash
curl -s http://localhost:8000/api/sovereign-mode/audit?limit=10 | \
  jq '.[] | select(.event_type == "sovereign.governance_override_expired")'
```

**Expected Output:**

```json
{
  "timestamp": "2025-12-25T15:15:23.456789Z",
  "event_type": "sovereign.governance_override_expired",
  "severity": "INFO",
  "success": true,
  "reason": "Override expired without consumption",
  "metadata": {
    "override_id": "ovr_a1b2c3d4e5f6",
    "consumed": false,
    "expired_at": "2025-12-25T15:15:23.456789Z"
  }
}
```

**✅ Checkpoint:** Override cleared successfully. No mode switch occurred.

---

### Final System Health Check

**1. Governance Status:**

```bash
curl -s http://localhost:8000/api/sovereign-mode/governance/status | jq
```

**Expected:**
```json
{
  "overall_governance": "healthy",
  "g1_bundle_trust": {"status": "healthy"},
  "g2_mode_governance": {"status": "healthy", "override_active": false},
  "g3_axe_security": {"status": "healthy"}
}
```

**2. Metrics Summary:**

```bash
curl -s http://localhost:8000/api/sovereign-mode/metrics/summary | jq
```

**Expected:**
```json
{
  "override_active": false,
  "override_usage_total": 1,
  ...
}
```

**3. Alert Status:**

```
Check PagerDuty/Prometheus: GovernanceOverrideActive should be RESOLVED
```

**✅ Checkpoint:** System health confirmed. Incident resolved.

---

### Evidence Collection for Post-Mortem

**Files to preserve:**

```bash
# Audit log export
/var/lib/brain/evidence/audit-2025-12-25.jsonl
/var/lib/brain/evidence/audit-2025-12-25.jsonl.sha256

# Forensic captures
/tmp/audit-forensics-*.jsonl
/tmp/status-forensics-*.json
/tmp/governance-forensics-*.json
/tmp/prometheus-override-*.json

# Prometheus query results
# (Export as screenshots or JSON dumps)
```

**Timeline documentation:**

```markdown
## Incident Timeline

| Time (UTC) | Event | Actor | Evidence |
|------------|-------|-------|----------|
| 14:15:23 | Override created | Unknown (API) | audit-2025-12-25.jsonl:1234 |
| 14:15:30 | Alert GA-001 fired | Prometheus | prometheus-override-*.json |
| 14:30:00 | Alert acknowledged | On-Call Engineer | PagerDuty incident #12345 |
| 14:35:00 | Override details extracted | On-Call Engineer | audit-forensics-*.jsonl |
| 14:40:00 | Classified as SUSPICIOUS | On-Call Engineer | Incident channel #001 |
| 14:45:00 | Escalated to security | On-Call Engineer | Slack message timestamp |
| 14:50:00 | Security confirms unauthorized | Security Lead | Slack message timestamp |
| 15:15:23 | Override expired (not consumed) | System | audit-2025-12-25.jsonl:1245 |
| 15:20:00 | System health verified | On-Call Engineer | status-forensics-*.json |
| 15:30:00 | Incident resolved | On-Call Engineer | PagerDuty incident #12345 |
```

---

### Post-Mortem Document (Template)

```markdown
# Post-Mortem: Governance Override Incident 2025-12-25

## Summary
- **Incident ID:** 2025-12-25-001
- **Severity:** SEV-2 (degraded security posture)
- **Duration:** 60 minutes (14:15 - 15:15 UTC)
- **Impact:** Governance override active for 1 hour (not consumed)
- **Root Cause:** Unauthorized API access (TBD - under investigation)

## What Happened
1. Governance override was created at 14:15 UTC via API
2. Alert GA-001 fired within 15 seconds
3. On-call engineer investigated and classified as SUSPICIOUS
4. Security team engaged at 14:45 UTC
5. Override expired at 15:15 UTC without being consumed
6. No mode switches occurred during override period
7. No data exfiltration detected

## What Went Well
- ✅ Alert fired within 15 seconds of override creation
- ✅ Runbook (RB-1) provided clear investigation steps
- ✅ Audit log contained all necessary forensic data
- ✅ Security team responded within 10 minutes of escalation
- ✅ Override expired as designed (fail-safe worked)

## What Went Wrong
- ❌ Requester identity not captured in audit event ("api" is too generic)
- ❌ No source IP logging for API requests
- ❌ No automated notification to platform owner on override creation
- ❌ Escalation criteria unclear (when to page security vs. wait?)

## Action Items
| Action | Owner | Due Date | Priority |
|--------|-------|----------|----------|
| Add source IP logging to audit events | Platform Team | 2025-12-30 | HIGH |
| Implement automated Slack notification on override creation | DevOps | 2025-12-31 | HIGH |
| Add requester identity capture (API key, user, etc.) | Backend Team | 2026-01-05 | MEDIUM |
| Clarify escalation criteria in runbook RB-1 | Security Team | 2025-12-27 | HIGH |
| Review API access controls for override endpoint | Security Team | 2026-01-10 | CRITICAL |

## Lessons Learned
1. **Detection worked:** Prometheus alerting and audit logging performed as expected
2. **Investigation tools adequate:** Runbook provided clear steps, audit API had all necessary data
3. **Escalation effective:** Security team engaged quickly, containment plan clear
4. **Fail-safes effective:** Override expired without consumption (single-use + TTL worked)
5. **Gaps identified:** Requester identity, source IP, automated notifications needed

## Follow-Up
- Security team to complete forensic analysis by 2025-12-27
- Platform team to implement action items by priority
- Repeat tabletop exercise after action items complete (2026-01-15)
```

---

## Lessons Learned Checklist

**For Participants:**

- [ ] Can you describe the override lifecycle (creation → expiration/consumption)?
- [ ] Can you query Prometheus for override status?
- [ ] Can you extract override details from audit log API?
- [ ] Can you assess override legitimacy using decision tree?
- [ ] Can you escalate to security team with correct context?
- [ ] Can you collect forensic evidence for post-mortem?
- [ ] Can you verify system health after incident resolution?
- [ ] Can you write a concise post-mortem document?

**For Facilitators:**

- [ ] Did the runbook provide sufficient guidance?
- [ ] Were Prometheus queries accurate and complete?
- [ ] Was audit log API accessible and queryable?
- [ ] Did participants make correct escalation decisions?
- [ ] Were evidence collection procedures followed?
- [ ] Did participants identify gaps in monitoring/alerting?
- [ ] Was the timeline documented accurately?
- [ ] Were action items specific and actionable?

---

## Variations for Future Exercises

**Scenario 2:** Override consumed + mode switch (SEV-1 breach)
**Scenario 3:** Override created by legitimate requester (known deployment)
**Scenario 4:** Override expired + immediate re-creation (potential bypass attempt)
**Scenario 5:** Multiple overrides created in quick succession (automation attack)

---

## References

- **Runbook:** `docs/GOVERNANCE_RUNBOOKS.md` (RB-1: Owner Override Active)
- **Alerting Policy:** `docs/ALERTING_POLICY.md` (GA-001: GovernanceOverrideActive)
- **Evidence Pack:** `docs/GOVERNANCE_EVIDENCE_PACK.md` (Chapter 12: Override Governance)
- **Prometheus Docs:** `ops/prometheus/README.md`
- **Evidence Export:** `ops/evidence/README.md`

---

**End of Tabletop Exercise**
