# Operational Assurance Implementation Plan (Option 1)

**Project:** BRAiN
**Sprint:** Operations Pack - Prometheus + Evidence Export + Tabletop
**Date:** 2025-12-25
**Branch:** `claude/ops-assurance-option1`

---

## Discovery Summary

### ✅ Repository Structure
- **`ops/` directory**: ❌ Does NOT exist (will be created)
- **Backend service**: `brain-backend` (container name), `backend` (docker network alias)
- **Backend port**: 8000
- **Docker network**: `brain_internal` (subnet: 172.20.0.0/16)

### ✅ Metrics Endpoint Identified
- **Path**: `/api/sovereign-mode/metrics`
- **Full internal URL**: `http://backend:8000/api/sovereign-mode/metrics`
- **Format**: Prometheus text format (plaintext)
- **Source**: `backend/app/modules/sovereign_mode/router.py:927-970`

### ✅ Audit Export Endpoint Identified
- **Path**: `/api/sovereign-mode/audit/export` (POST)
- **Full internal URL**: `http://backend:8000/api/sovereign-mode/audit/export`
- **Request**: `AuditExportRequest` (start_time, end_time, event_types, include_hash)
- **Response**: `AuditExportResponse` (export_id, event_count, format, content_hash)
- **Source**: `backend/app/modules/sovereign_mode/router.py:1031-1164`

---

## Implementation Checklist

### ✅ Phase 0: Discovery (COMPLETED)
- [x] Check if `ops/` exists → **Result: NO, must create**
- [x] Identify metrics endpoint → **Result: `/api/sovereign-mode/metrics`**
- [x] Identify audit export endpoint → **Result: `/api/sovereign-mode/audit/export`**
- [x] Identify Docker network config → **Result: `brain_internal`**

---

### 📦 Phase 1: D1 - Prometheus Sensor (HIGH Priority)

**Goal**: Minimal Prometheus deployment that scrapes BRAiN governance metrics.

**Files to Create**:
1. `ops/prometheus/prometheus.yml`
   - scrape_config for BRAiN backend
   - scrape_interval: 30s
   - target: `backend:8000/api/sovereign-mode/metrics`
   - job_name: `brain-governance`

2. `ops/prometheus/docker-compose.prometheus.yml`
   - Prometheus service definition
   - Image: `prom/prometheus:latest`
   - Port: 9090:9090 (localhost only, or internal)
   - Network: `brain_internal` (join existing network)
   - Volume: `prometheus.yml` mount
   - Volume: prometheus data persistence

3. `ops/prometheus/README.md`
   - Quick start commands
   - Verification steps
   - Query examples

**Constraints**:
- ❌ NO new ports exposed publicly (only localhost:9090 if needed)
- ✅ MUST join existing `brain_internal` network
- ✅ MUST be read-only (no writes to backend)
- ✅ MUST NOT change governance code

**Verification**:
- `docker compose -f ops/prometheus/docker-compose.prometheus.yml up -d`
- `curl -s localhost:9090/-/ready` → should return "OK"
- `curl -s localhost:9090/api/v1/targets` → target `brain-governance` should be UP
- Query: `sovereign_override_active` → should return gauge value

---

### 📦 Phase 2: D2 - Evidence Export Automation (HIGH Priority)

**Goal**: Daily automated audit log export with SHA256 integrity.

**Files to Create**:
1. `ops/evidence/export_audit.sh`
   - Bash script (set -euo pipefail)
   - Calls `/api/sovereign-mode/audit/export` (POST)
   - Saves to `/var/lib/brain/evidence/audit-YYYY-MM-DD.jsonl`
   - Computes SHA256, saves as `audit-YYYY-MM-DD.jsonl.sha256`
   - Fail-safe: exit != 0 if API unreachable
   - No secrets in repo (read from ENV or `/usr/local/bin/config.env`)
   - Optional retention: delete files older than 90 days (commented out by default)

2. `ops/evidence/brain-evidence-export.service`
   - systemd service unit
   - Type=oneshot
   - ExecStart=/path/to/export_audit.sh
   - Environment: HOST URL, optional token

3. `ops/evidence/brain-evidence-export.timer`
   - systemd timer unit
   - OnCalendar=daily (02:00 server time)
   - Persistent=true (catch up if missed)

4. `ops/evidence/README.md`
   - Installation steps
   - Configuration guide
   - Manual testing
   - Systemd commands (enable/start/status)

**Constraints**:
- ❌ NO secrets in Git
- ✅ MUST be idempotent (safe to run multiple times)
- ✅ MUST have clear error messages (systemd journal)
- ✅ MUST NOT overwrite existing exports (append-only)
- ✅ MUST compute SHA256 for integrity

**Verification**:
- `bash ops/evidence/export_audit.sh` (manual run)
- Check `/var/lib/brain/evidence/audit-YYYY-MM-DD.jsonl` exists
- Check SHA256 file exists
- `systemctl daemon-reload`
- `systemctl enable --now brain-evidence-export.timer`
- `systemctl list-timers | grep brain-evidence` → should show next run

---

### 📦 Phase 3: D3 - Tabletop Exercise Artifact (MEDIUM Priority)

**Goal**: Documented incident simulation scenario for governance.

**File to Create**:
1. `docs/INCIDENT_TABLETOP_001.md`
   - Scenario: "Owner Override Active → Forgotten/Misused"
   - Trigger: Alert `GovernanceOverrideActive` fires
   - Detection: Prometheus query + Audit events
   - Response Steps: Investigate → Decide → Act
   - Evidence: Which logs/exports to preserve
   - Lessons Learned Checklist

**Content Structure**:
- **Scenario Overview**: What happened
- **Trigger**: Alert or event that starts the incident
- **Detection**: How to detect (Prometheus queries, audit log queries)
- **Immediate Actions** (< 5 min): First responder steps
- **Investigation**: Forensic steps
- **Decision Tree**: Legitimate vs. Suspicious override
- **Response Actions**: Containment, recovery
- **Evidence Collection**: What to preserve for post-mortem
- **Lessons Learned**: Checklist for post-incident review

**Constraints**:
- ✅ MUST be realistic (based on actual governance capabilities)
- ✅ MUST reference existing runbooks (from A2)
- ✅ MUST reference existing alerting policy (from A1)

**Verification**:
- Document is complete and readable
- Cross-references work (runbooks, alerts)

---

### 📦 Phase 4: D4 - Alerting Policy Verification (LOW Priority)

**Goal**: Verify existing alerting policy covers required alerts.

**Action**:
- Check if `docs/ALERTING_POLICY.md` exists (✅ already created in previous sprint)
- Verify it includes:
  - `override_active_gauge == 1`
  - `bundle_quarantine_count > 0`
  - `axe_trust_violation_count > 0`
  - `preflight_failures rate > threshold`
- If missing: Add Prometheus rule examples (YAML)

**Expected Outcome**:
- Alerting policy already exists from previous sprint → **VERIFY ONLY**
- If gaps found → Add missing rules

---

### ✅ Phase 5: Verification & Testing

**Tasks**:
1. **Prometheus**:
   - Start: `docker compose -f ops/prometheus/docker-compose.prometheus.yml up -d`
   - Check: `curl localhost:9090/-/ready`
   - Check target: `curl localhost:9090/api/v1/targets`
   - Query metric: `curl 'localhost:9090/api/v1/query?query=sovereign_override_active'`

2. **Evidence Export**:
   - Manual run: `bash ops/evidence/export_audit.sh`
   - Check file exists: `ls /var/lib/brain/evidence/`
   - Verify SHA256: `sha256sum -c audit-YYYY-MM-DD.jsonl.sha256`
   - Enable timer: `systemctl enable --now brain-evidence-export.timer`
   - Check timer: `systemctl list-timers | grep brain`

3. **Documentation**:
   - Tabletop document is complete
   - Alerting policy is up-to-date

---

### 📝 Phase 6: Completion Report

**File**: `OPS_ASSURANCE_COMPLETION_REPORT.md`

**Content**:
- Files added/changed
- Deploy commands (copy-paste ready)
- Verification output (screenshots/console dumps)
- Risks closed:
  - ✅ Prometheus missing → Prometheus deployed
  - ✅ SIEM manual → Daily automated export
  - ✅ Tabletop missing → Incident simulation documented
- Git: Branch, commit message, push confirmation

---

## Git Workflow

**Branch**: `claude/ops-assurance-option1`

**Commit Message**:
```
feat(ops): operational assurance pack (prometheus + evidence export + tabletop)

Operational Assurance Pack - minimal changes, maximum stability.
No governance code changes. Documentation and automation only.

Deliverables:
- D1: Prometheus governance sensor (Docker Compose + config)
- D2: Evidence export automation (daily systemd timer + SHA256)
- D3: Tabletop exercise artifact (incident simulation)
- D4: Alerting policy verification (Prometheus rules)

New files:
- ops/prometheus/prometheus.yml
- ops/prometheus/docker-compose.prometheus.yml
- ops/prometheus/README.md
- ops/evidence/export_audit.sh
- ops/evidence/brain-evidence-export.service
- ops/evidence/brain-evidence-export.timer
- ops/evidence/README.md
- docs/INCIDENT_TABLETOP_001.md
- OPS_ASSURANCE_COMPLETION_REPORT.md

Result: BRAiN governance now has production-ready monitoring,
automated compliance export, and incident response capability.

Sprint: Operational Assurance (Option 1)
Priority: HIGH (D1, D2), MEDIUM (D3), LOW (D4)
Definition of Done: ✅ All deliverables implemented and tested
```

**Push**:
```bash
git push -u origin claude/ops-assurance-option1
```

---

## Definition of Done

- ✅ D1: Prometheus sensor deployed and scraping metrics
- ✅ D2: Evidence export automation working (systemd timer)
- ✅ D3: Tabletop document complete and cross-referenced
- ✅ D4: Alerting policy verified/updated
- ✅ All verification steps passed
- ✅ Completion report written
- ✅ Git committed and pushed
- ✅ NO governance code changes
- ✅ NO secrets in repo
- ✅ NO breaking changes

---

## Risk Mitigation

**Risks Closed**:
1. ✅ **Prometheus missing** → Prometheus deployed with governance metrics
2. ✅ **SIEM manual export** → Daily automated export with SHA256 integrity
3. ✅ **Tabletop missing** → Incident simulation documented and tested

**Remaining Risks** (out of scope):
- ⏸ Alertmanager not deployed (Prometheus rules only, no paging)
- ⏸ Grafana dashboards not deployed (metrics available, visualization optional)
- ⏸ SIEM integration not configured (export automation ready, SIEM ingestion pending)

---

## Next Steps

### ✅ Immediate (This Sprint)
1. Implement D1 - Prometheus sensor
2. Implement D2 - Evidence export automation
3. Implement D3 - Tabletop artifact
4. Verify D4 - Alerting policy
5. Test all components
6. Write completion report
7. Commit and push

### ⏸ Future Sprints (Out of Scope)
- **Infrastructure Sprint**: Alertmanager deployment + PagerDuty integration
- **Observability Sprint**: Grafana dashboards for governance metrics
- **Compliance Sprint**: SIEM integration (Splunk HEC / ELK)
- **Training Sprint**: Quarterly tabletop exercises with on-call team

---

**End of Implementation Plan**
