# Sprint 10: Deployment Checklist

**Sprint:** Sprint 10 (P0)
**Target Environment:** Staging → Production
**Deployment Date:** TBD
**Deployment Owner:** DevOps Team

---

## 📋 Pre-Deployment

### Code Review
- [ ] PR approved by 2+ reviewers
- [ ] Security review completed (see SPRINT10_SECURITY_REVIEW.md)
- [ ] All tests pass in CI
- [ ] Documentation reviewed and approved

### Configuration
- [ ] `.env.example` updated with WebGenesis IR variables
- [ ] Default values reviewed:
  - [ ] `WEBGENESIS_IR_MODE=opt_in` (safe default)
  - [ ] `WEBGENESIS_DRY_RUN_DEFAULT=true` (safe default)
  - [ ] `WEBGENESIS_REQUIRE_APPROVAL_TIER=2` (medium+ approval)
  - [ ] `WEBGENESIS_MAX_BUDGET=` (unlimited, can set limit later)

### Dependencies
- [ ] No new external dependencies required
- [ ] Python dependencies unchanged (no `requirements.txt` changes)
- [ ] Docker image builds successfully
- [ ] All imports resolve correctly

### Testing
- [ ] All 13 Sprint 10 tests pass
- [ ] No regression in existing tests
- [ ] Integration tests with Sprint 9 pass

---

## 🚀 Staging Deployment

### 1. Pre-Deployment Backup

**Database Backup:**
```bash
# Backup PostgreSQL database
cd /srv/stage  # or /srv/dev
docker compose exec postgres pg_dump -U brain brain > backup_pre_sprint10_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh backup_pre_sprint10_*.sql
```

**Redis Backup:**
```bash
# Backup Redis data
docker compose exec redis redis-cli SAVE
docker compose exec redis redis-cli LASTSAVE
```

**Configuration Backup:**
```bash
# Backup current .env
cp .env .env.backup_$(date +%Y%m%d_%H%M%S)
```

### 2. Deploy Sprint 10

**Pull Latest Code:**
```bash
cd /srv/stage  # or /srv/dev
git fetch origin
git checkout v2
git pull origin v2

# Verify branch
git log -1 --oneline
# Should show Sprint 10 commits
```

**Update Environment:**
```bash
# Add Sprint 10 config to .env
cat >> .env <<'EOF'

#############################################
# WEBGENESIS IR GOVERNANCE (Sprint 10)
#############################################

# IR enforcement mode: off | opt_in | required
WEBGENESIS_IR_MODE=opt_in

# Minimum risk tier requiring approval (0-3)
WEBGENESIS_REQUIRE_APPROVAL_TIER=2

# Maximum budget in cents (optional)
WEBGENESIS_MAX_BUDGET=

# Default dry-run mode (true recommended)
WEBGENESIS_DRY_RUN_DEFAULT=true
EOF
```

**Build & Deploy:**
```bash
# Rebuild backend with new code
docker compose build backend

# Restart backend service
docker compose up -d backend

# Check logs for startup errors
docker compose logs -f backend | head -n 50
```

### 3. Verify Deployment

**Health Check:**
```bash
# Check backend health
curl http://localhost:8001/health
# Expected: {"status": "healthy", ...}

# Check all routes registered
curl http://localhost:8001/debug/routes | grep "pipeline"
# Should include: /api/pipeline/execute-ir
```

**IR Config Endpoint:**
```bash
# Test IR config endpoint
curl http://localhost:8001/api/pipeline/ir/config

# Expected response:
# {
#   "ir_mode": "opt_in",
#   "require_approval_tier": 2,
#   "max_budget_cents": null,
#   "dry_run_default": true,
#   "is_ir_enabled": true,
#   "is_ir_required": false
# }
```

**Test Suite:**
```bash
# Run Sprint 10 tests in container
docker compose exec backend pytest backend/tests/test_sprint10_webgenesis_ir.py -v

# Expected: 13 passed ✅
```

**Legacy Compatibility:**
```bash
# Test legacy endpoint (should still work)
curl -X POST http://localhost:8001/api/pipeline/execute \
  -H "Content-Type: application/json" \
  -d '{
    "graph_spec": {
      "graph_id": "test_legacy_$(date +%s)",
      "business_intent_id": "intent_test",
      "nodes": [],
      "dry_run": true
    }
  }'

# Expected: 200 OK (executes without IR governance)
```

### 4. Smoke Tests

**Smoke Test 1: IR Config**
```bash
curl http://localhost:8001/api/pipeline/ir/config
# Expected: JSON with ir_mode, require_approval_tier, etc.
```

**Smoke Test 2: Legacy Request**
```bash
curl -X POST http://localhost:8001/api/pipeline/execute \
  -H "Content-Type: application/json" \
  -d '{
    "graph_spec": {
      "graph_id": "smoke_legacy",
      "business_intent_id": "intent_smoke",
      "nodes": [],
      "dry_run": true
    }
  }'
# Expected: 200 OK
```

**Smoke Test 3: New IR Endpoint**
```bash
curl -X POST http://localhost:8001/api/pipeline/execute-ir \
  -H "Content-Type: application/json" \
  -d '{
    "graph_spec": {
      "graph_id": "smoke_ir",
      "business_intent_id": "intent_smoke",
      "nodes": [],
      "dry_run": true
    },
    "tenant_id": "tenant_smoke",
    "execute": false
  }'
# Expected: 200 OK or 400 (depending on IR validation)
```

---

## 📊 Monitoring & Validation (24-48h)

### Monitor Audit Events

**Setup Monitoring:**
```bash
# Terminal 1: Watch all IR events
docker compose logs -f backend | grep "webgenesis.ir"

# Terminal 2: Watch approvals
docker compose logs -f backend | grep "approval"

# Terminal 3: Watch errors
docker compose logs -f backend | grep -i "error\|exception"
```

**Create Monitoring Script:**
```bash
cat > /tmp/monitor_sprint10.sh <<'EOF'
#!/bin/bash
echo "=== Sprint 10 Monitoring Dashboard ==="
echo "Time: $(date)"
echo ""
echo "📊 IR Events (last 1 hour):"
echo "  IR Received:      $(docker compose logs --since 1h backend 2>/dev/null | grep -c 'webgenesis.ir_received')"
echo "  Legacy Allowed:   $(docker compose logs --since 1h backend 2>/dev/null | grep -c 'webgenesis.ir_legacy_allowed')"
echo "  PASS:             $(docker compose logs --since 1h backend 2>/dev/null | grep -c 'webgenesis.ir_validated_pass')"
echo "  ESCALATE:         $(docker compose logs --since 1h backend 2>/dev/null | grep -c 'webgenesis.ir_validated_escalate')"
echo "  REJECT:           $(docker compose logs --since 1h backend 2>/dev/null | grep -c 'webgenesis.ir_validated_reject')"
echo ""
echo "🔐 Approval Events (last 1 hour):"
echo "  Created:          $(docker compose logs --since 1h backend 2>/dev/null | grep -c 'ir.approval_created')"
echo "  Consumed:         $(docker compose logs --since 1h backend 2>/dev/null | grep -c 'ir.approval_consumed')"
echo "  Invalid:          $(docker compose logs --since 1h backend 2>/dev/null | grep -c 'ir.approval_invalid')"
echo ""
echo "✅ Diff-Audit Events (last 1 hour):"
echo "  PASS:             $(docker compose logs --since 1h backend 2>/dev/null | grep -c 'webgenesis.diff_audit_pass')"
echo "  FAIL:             $(docker compose logs --since 1h backend 2>/dev/null | grep -c 'webgenesis.diff_audit_fail')"
echo ""
echo "⚠️  Errors (last 1 hour):"
echo "  Errors:           $(docker compose logs --since 1h backend 2>/dev/null | grep -ci 'error')"
echo "  Exceptions:       $(docker compose logs --since 1h backend 2>/dev/null | grep -ci 'exception')"
echo ""
EOF

chmod +x /tmp/monitor_sprint10.sh

# Run monitoring every 30 minutes
watch -n 1800 /tmp/monitor_sprint10.sh
```

### Test Scenarios

**Scenario 1: Legacy Request (No IR)**
```bash
curl -X POST http://localhost:8001/api/pipeline/execute \
  -H "Content-Type: application/json" \
  -d '{
    "graph_spec": {
      "graph_id": "test_legacy_scenario",
      "business_intent_id": "intent_001",
      "nodes": [{
        "node_id": "webgen_0",
        "node_type": "webgenesis",
        "depends_on": [],
        "capabilities": [],
        "executor_class": "WebGenesisNode",
        "executor_params": {
          "website_template": "static-landing",
          "domain": "test.example.com",
          "title": "Test Site",
          "pages": ["home"],
          "business_intent_id": "intent_001"
        }
      }],
      "dry_run": true
    }
  }'

# Expected: 200 OK, execution successful, no IR governance
# Check logs for: "webgenesis.ir_legacy_allowed"
```

**Scenario 2: IR Request (PASS)**
```bash
curl -X POST http://localhost:8001/api/pipeline/execute-ir \
  -H "Content-Type: application/json" \
  -d '{
    "graph_spec": {
      "graph_id": "test_ir_pass",
      "business_intent_id": "intent_002",
      "nodes": [{
        "node_id": "webgen_0",
        "node_type": "webgenesis",
        "depends_on": [],
        "capabilities": [],
        "executor_class": "WebGenesisNode",
        "executor_params": {
          "website_template": "static-landing",
          "domain": "dev.example.com",
          "title": "Dev Site",
          "pages": ["home"],
          "business_intent_id": "intent_002"
        }
      }],
      "dry_run": true
    },
    "tenant_id": "tenant_demo",
    "ir": {
      "tenant_id": "tenant_demo",
      "steps": [{
        "action": "webgenesis.site.create",
        "provider": "webgenesis.v1",
        "resource": "site:dev.example.com",
        "params": {},
        "idempotency_key": "test_ir_pass:webgen_0",
        "constraints": {"env": "dev"}
      }]
    },
    "execute": false
  }'

# Expected: 200 OK, IR validation PASS
# Check logs for: "webgenesis.ir_validated_pass"
```

**Scenario 3: IR Request (ESCALATE)**
```bash
# Step 1: Request that will ESCALATE (production)
curl -X POST http://localhost:8001/api/pipeline/execute-ir \
  -H "Content-Type: application/json" \
  -d '{
    "graph_spec": {
      "graph_id": "test_ir_escalate",
      "business_intent_id": "intent_003",
      "nodes": [{
        "node_id": "webgen_0",
        "node_type": "webgenesis",
        "depends_on": [],
        "capabilities": [],
        "executor_class": "WebGenesisNode",
        "executor_params": {
          "website_template": "nextjs-business",
          "domain": "example.com",
          "title": "Production Site",
          "pages": ["home"],
          "business_intent_id": "intent_003"
        }
      }],
      "dry_run": false
    },
    "tenant_id": "tenant_demo",
    "ir": {
      "tenant_id": "tenant_demo",
      "steps": [{
        "action": "webgenesis.site.create",
        "provider": "webgenesis.v1",
        "resource": "site:example.com",
        "params": {},
        "idempotency_key": "test_ir_escalate:webgen_0",
        "constraints": {"env": "production"}
      }]
    },
    "execute": false
  }'

# Expected: 403 "Approval required"
# Check logs for: "webgenesis.ir_validated_escalate"

# Step 2: Get IR hash from response, create approval (manual)
# Step 3: Retry with token (test approval consumption)
```

### Performance Validation

**Measure Overhead:**
```bash
# Legacy request timing
time curl -X POST http://localhost:8001/api/pipeline/execute \
  -H "Content-Type: application/json" \
  -d '{"graph_spec": {...}, "dry_run": true}'

# IR request timing
time curl -X POST http://localhost:8001/api/pipeline/execute-ir \
  -H "Content-Type: application/json" \
  -d '{"graph_spec": {...}, "tenant_id": "...", "ir": {...}, "execute": false}'

# Expected: IR overhead <25ms
```

**Monitor Execution Times:**
```bash
# Check execution durations in logs
docker compose logs backend | grep "duration_seconds" | tail -n 20
```

---

## 🔄 Rollback Plan

### If Critical Issues Found

**Rollback Steps:**
```bash
# 1. Stop backend
docker compose stop backend

# 2. Checkout previous version
git log -5 --oneline  # Find commit before Sprint 10
git checkout <previous_commit_hash>

# 3. Remove Sprint 10 config from .env
nano .env
# Delete WEBGENESIS_IR_GOVERNANCE section

# 4. Rebuild and restart
docker compose build backend
docker compose up -d backend

# 5. Verify rollback
curl http://localhost:8001/health
curl http://localhost:8001/api/pipeline/ir/config
# Should return 404 (endpoint doesn't exist)
```

**Restore Database (if needed):**
```bash
# Restore from backup
docker compose exec -T postgres psql -U brain brain < backup_pre_sprint10_*.sql

# Verify restoration
docker compose exec postgres psql -U brain brain -c "\dt"
```

---

## 🚀 Production Deployment

### Prerequisites
- [ ] Staging validation successful (24-48h)
- [ ] No critical issues found
- [ ] Performance validated (<25ms overhead)
- [ ] Audit events verified
- [ ] Team approval obtained
- [ ] Deployment window scheduled

### Production Deployment Steps

**Same as staging, but:**
1. Use production server (`brain.falklabs.de`)
2. Use production environment file (`.env.prod`)
3. Schedule during low-traffic window
4. Have rollback plan ready
5. Monitor closely for first 1-2 hours

**Production Checklist:**
- [ ] Backup database
- [ ] Backup Redis
- [ ] Backup .env
- [ ] Deploy code
- [ ] Update .env
- [ ] Rebuild backend
- [ ] Restart services
- [ ] Run smoke tests
- [ ] Monitor for 1-2 hours
- [ ] If stable, monitor for 24h

---

## 📊 Post-Deployment

### Week 1 Monitoring

**Daily Tasks:**
- [ ] Run monitoring script (`/tmp/monitor_sprint10.sh`)
- [ ] Review error logs
- [ ] Track IR adoption rate
- [ ] Track approval rate (ESCALATE events)
- [ ] Monitor performance (execution times)

**Metrics to Track:**
```bash
# IR Adoption Rate
total_requests=$(docker compose logs backend | grep -c "pipeline/execute")
ir_requests=$(docker compose logs backend | grep -c "webgenesis.ir_received")
echo "IR Adoption: $ir_requests / $total_requests"

# Approval Rate
escalate=$(docker compose logs backend | grep -c "webgenesis.ir_validated_escalate")
approve=$(docker compose logs backend | grep -c "webgenesis.ir_approval_consumed")
echo "Approval Rate: $approve / $escalate"

# Rejection Rate
reject=$(docker compose logs backend | grep -c "webgenesis.ir_validated_reject")
total_validations=$((ir_requests))
echo "Rejection Rate: $reject / $total_validations"
```

### Week 2 Analysis

**Tasks:**
- [ ] Analyze audit data
- [ ] Identify edge cases
- [ ] Document learnings
- [ ] Plan improvements for Sprint 11
- [ ] Gather team feedback

**Analysis Questions:**
- How many IR requests vs legacy?
- How many ESCALATE requests?
- How many rejections? (What caused them?)
- Any diff-audit failures?
- Any performance issues?
- Any user complaints?

---

## ✅ Sign-Off

### Deployment Approval

**Staging Deployment:**
- [ ] DevOps Lead: _______________
- [ ] Security Team: _______________
- [ ] Date: _______________

**Production Deployment:**
- [ ] DevOps Lead: _______________
- [ ] Security Team: _______________
- [ ] Product Owner: _______________
- [ ] Date: _______________

---

## 📋 Contact & Escalation

**Deployment Owner:** DevOps Team
**Security Contact:** Security Team
**Emergency Rollback Authority:** DevOps Lead

**Escalation Path:**
1. DevOps Team (first response)
2. Security Team (if security issue)
3. Development Team (if critical bug)

---

**Checklist Version:** 1.0
**Last Updated:** 2025-12-26
**Status:** ✅ Ready for Deployment

---

**END OF DEPLOYMENT CHECKLIST**
