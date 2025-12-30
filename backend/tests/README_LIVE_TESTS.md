# 🧪 BRAiN Credit System — Live Tests

**Quick Start Guide for Live System Testing**

---

## 🚀 Quick Start (5 Minutes)

```bash
# 1. Start backend
cd /home/user/BRAiN
docker compose up -d backend

# 2. Run all tests
docker compose exec backend python backend/tests/run_live_credit_tests.py --full

# 3. Check results
echo "Status: $(cat reports/live_test_report.json | jq -r '.overall_status')"
echo "Recommendation: $(cat reports/live_test_report.json | jq -r '.recommendation')"
```

**Expected Output:** `Status: GO` (if all tests pass)

---

## 📁 Files Overview

| File | Purpose | Lines |
|------|---------|-------|
| **run_live_credit_tests.py** | Test harness with 6 scenarios | 900+ |
| **live_invariants.py** | Invariants checker (5 hard gates) | 400+ |
| **live_credit_system_playbook.md** | Detailed test instructions | 700 |
| **DOCKER_SETUP_ANALYSIS.md** | Docker setup analysis | 350 |
| **LIVE_TEST_REPORT_TEMPLATE.md** | Report template | 300 |
| **LIVE_TEST_DELIVERABLES.md** | Complete documentation | 500 |

---

## 🎯 Test Scenarios

1. **Credit Storm** — Concurrency & idempotency
2. **Synergy Anti-Gaming** — Reward caps
3. **Approval Race** — OCC serialization
4. **KARMA Blackout** — Resilience
5. **ML Chaos** — Anomaly detection
6. **Crash/Replay** — Deterministic recovery

---

## 📊 Success Criteria

**GO (Production-Ready):**
- ✅ All 6 scenarios: PASS
- ✅ All 5 gates: PASS
- ✅ P95 latency < 500ms
- ✅ No critical failures

**Result:** Phase 5a (Postgres Event Store) approved

---

## 📖 Full Documentation

Read `LIVE_TEST_DELIVERABLES.md` for complete guide.

---

**Status:** ✅ Ready for execution
**Last Updated:** 2024-12-30
