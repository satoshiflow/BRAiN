# BRAiN Master Audit - Usage Guide

## Overview

The **BRAiN Master Audit** is a comprehensive stress-test and benchmark tool designed to evaluate the BRAiN Agent Orchestration Framework under extreme conditions. It validates biological plausibility, identifies bottlenecks, and provides optimization recommendations.

## What It Tests

### Phase A: Performance Stress Test
- **Exponential scaling:** Tests with 100, 250, 500, 1K, 2.5K, 5K, and 10K missions
- **Metrics:**
  - Throughput (missions/second)
  - Latency (average, P95, P99)
  - Memory usage and leak detection
  - Algorithmic complexity (O-notation)

### Phase B: Dynamic Stability Analysis
- **Sustained load test:** 60 seconds at 10 missions/second
- **Metrics:**
  - Agent utilization patterns ("firing rates")
  - Completion/failure/timeout rates
  - Synchronicity index (detects pathological patterns)
  - System entropy (information capacity)
  - Edge of chaos score (optimal: 0.5-0.7)
  - Deadlock/starvation/cascade failure detection

### Phase C: Breaking Point Definition
- **Binary search for max capacity**
- **Metrics:**
  - Maximum concurrent missions
  - Maximum throughput (missions/s)
  - Bottleneck component identification
  - Critical failure modes
  - Recovery time after overload

## Prerequisites

### 1. Backend Must Be Running

The audit script requires the BRAiN backend API to be accessible at `http://localhost:8000`.

**Start the backend:**

```bash
# Using Docker Compose (recommended)
cd /home/user/BRAiN
docker compose up -d backend redis postgres

# Verify backend is running
curl http://localhost:8000/api/health
```

**Expected response:**
```json
{
  "status": "ok",
  "timestamp": "2024-12-30T..."
}
```

### 2. Install Dependencies

The audit script requires additional Python packages:

```bash
cd /home/user/BRAiN/backend
pip install psutil numpy scipy
```

**Already installed dependencies:**
- pytest
- pytest-asyncio
- httpx

## Running the Audit

### Full Audit (All Phases)

```bash
cd /home/user/BRAiN/backend
python tests/brain_master_audit.py
```

**Expected duration:** 10-20 minutes depending on system performance

**Output:**
- Real-time console logging with progress indicators
- Final report saved to `/home/user/BRAiN/BRAIN_AUDIT_REPORT.md`

### Running Individual Phases

You can modify the script to run specific phases:

```python
# In brain_master_audit.py, modify main():

auditor = BrainMasterAuditor()

# Run only Phase A
auditor.run_phase_a()
auditor.analyze_optimizations()
report = auditor.generate_report()
auditor.save_report_markdown(report, "BRAIN_AUDIT_REPORT.md")
```

### Running as pytest

```bash
cd /home/user/BRAiN/backend
pytest tests/brain_master_audit.py::test_full_audit -v -s
```

## Interpreting Results

### Phase A Metrics

**Throughput:**
- ✅ Good: >50 missions/s
- ⚠️  Acceptable: 10-50 missions/s
- ❌ Poor: <10 missions/s

**Latency (P95):**
- ✅ Excellent: <50ms
- ⚠️  Acceptable: 50-200ms
- ❌ Poor: >200ms

**Memory Leak:**
- ✅ No leak detected
- ❌ Leak detected → Requires immediate investigation

**Complexity:**
- ✅ O(1), O(log n), O(n) → Optimal
- ⚠️  O(n log n) → Acceptable for most workloads
- ❌ O(n²), O(n³) → Requires optimization

### Phase B Metrics

**Completion Rate:**
- ✅ >95%
- ⚠️  85-95%
- ❌ <85%

**Synchronicity Index:**
- ✅ <0.7 → Healthy desynchronization
- ❌ >0.7 → Pathological synchronization (agents in lockstep)

**Entropy:**
- ✅ 2.0-4.0 bits → Good information capacity
- ⚠️  1.0-2.0 bits → Limited state space
- ❌ <1.0 bits → Very limited adaptability

**Edge of Chaos Score:**
- ✅ 0.5-0.7 → Optimal balance (order + flexibility)
- ⚠️  0.3-0.5 or 0.7-0.8 → Suboptimal
- ❌ <0.3 (too ordered) or >0.8 (too chaotic)

**Pathologies:**
- ❌ Deadlock → Critical issue, requires immediate fix
- ❌ Starvation → High priority, improve load balancing
- ❌ Cascade Failure → High priority, add circuit breakers

### Phase C Metrics

**Recovery Time:**
- ✅ <10s → Excellent resilience
- ⚠️  10-30s → Acceptable
- ❌ >30s → Poor resilience, add graceful degradation

## Example Output

### Console Output
```
================================================================================
 BRAIN MASTER AUDIT - COMPREHENSIVE STRESS TEST & BENCHMARK
================================================================================

System Under Test: BRAiN Agent Orchestration Framework v0.5.0
Architecture: Bio-inspired multi-agent system with mission orchestration

================================================================================

================================================================================
PHASE A: PERFORMANCE STRESS TEST
================================================================================

🔬 Testing scale: 100 missions
Baseline memory: 245.32 MB
✅ Completed: 100/100
❌ Failed: 0
⏱️  Duration: 2.34s
📊 Throughput: 42.74 missions/s
🐏 Peak Memory: 248.12 MB
💾 Avg Memory: 246.45 MB
⚠️  Memory Leak: NO

🔬 Testing scale: 250 missions
...

Complexity estimation: O(n) (R²=0.987)

✅ Phase A Complete
```

### Report File (BRAIN_AUDIT_REPORT.md)
```markdown
# BRAIN Master Audit Report
================================================================================

**Generated:** 2024-12-30T14:23:45.123456
**BRAiN Version:** 0.5.0

## Test Environment

- **python_version:** 3.11.5
- **platform:** linux
- **cpu_count:** 8
- **total_memory_mb:** 16384.0

## Phase A: Performance Stress Test

| Scale | Completed | Failed | Duration (s) | Throughput (m/s) | ... |
|-------|-----------|--------|--------------|------------------|-----|
| 100   | 100       | 0      | 2.34         | 42.74            | ... |
| 250   | 250       | 0      | 5.12         | 48.83            | ... |
...

## Critical Bottlenecks

### [HIGH] Redis Queue Operations
**Location:** `backend/modules/mission_system/queue.py:160-260`
**Recommendation:** Implement Redis pipelining for batch operations

...
```

## Troubleshooting

### Error: "Backend not running"

**Problem:** The audit script cannot connect to the backend API.

**Solution:**
```bash
# Check if backend is running
curl http://localhost:8000/api/health

# If not, start it
docker compose up -d backend
```

### Error: "Import Error: No module named 'psutil'"

**Problem:** Missing dependencies.

**Solution:**
```bash
pip install psutil numpy scipy
```

### Error: "Memory Error" or "Out of Memory"

**Problem:** System doesn't have enough RAM for large-scale tests.

**Solution:**
- Reduce scale points in Phase A (edit `scale_points` list)
- Run phases individually instead of full audit
- Increase system swap space

### Slow Performance

**Problem:** Tests are taking too long.

**Solution:**
- Reduce test duration in Phase B (`test_duration_seconds`)
- Reduce scale points in Phase A
- Ensure no other heavy processes are running

## Advanced Usage

### Custom Scale Points

Edit `brain_master_audit.py`:

```python
# Change this line in run_phase_a():
scale_points = [100, 250, 500, 1000, 2500, 5000, 10000]

# To something smaller:
scale_points = [50, 100, 250, 500, 1000]
```

### Custom Sustained Load

Edit `brain_master_audit.py`:

```python
# Change these lines in run_phase_b():
test_duration_seconds = 60  # Reduce to 30 for faster tests
missions_per_second = 10    # Increase to stress test more
```

### Export Results as JSON

Add this to the end of `main()`:

```python
# Save JSON report
import json
report_dict = asdict(report)
with open("audit_report.json", "w") as f:
    json.dump(report_dict, f, indent=2, default=str)
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: BRAiN Performance Audit

on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sunday at 2 AM
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Start BRAiN Backend
        run: |
          docker compose up -d
          sleep 10  # Wait for startup

      - name: Install Dependencies
        run: |
          pip install psutil numpy scipy

      - name: Run Audit
        run: |
          cd backend
          python tests/brain_master_audit.py

      - name: Upload Report
        uses: actions/upload-artifact@v3
        with:
          name: audit-report
          path: BRAIN_AUDIT_REPORT.md
```

## Performance Benchmarks

Based on reference hardware (8-core CPU, 16GB RAM):

| Metric | Expected Range | Optimal |
|--------|----------------|---------|
| Throughput | 20-100 m/s | >50 m/s |
| P95 Latency | 50-500ms | <100ms |
| Memory per 1K missions | 10-50 MB | <20 MB |
| Recovery Time | 5-30s | <10s |

## Architecture Context

**Key Mappings:**
- **"Neurons"** = Agents (AI workers)
- **"Synaptic Activity"** = Mission throughput
- **"Firing Rates"** = Agent utilization & completion rate
- **"Network Stability"** = Queue health, no deadlocks
- **"Edge of Chaos"** = Optimal load balancing vs. saturation

**Components Tested:**
1. **Mission Queue (Redis)** - `backend/modules/mission_system/queue.py`
2. **Mission Orchestrator** - `backend/modules/mission_system/orchestrator.py`
3. **Mission Executor** - `backend/modules/mission_system/executor.py`
4. **FastAPI Routes** - `backend/api/routes/missions.py`
5. **Agent Manager** - `backend/brain/agents/agent_manager.py`

## Support

For issues or questions:
- **GitHub Issues:** https://github.com/satoshiflow/BRAiN/issues
- **Documentation:** `/home/user/BRAiN/CLAUDE.md`
- **Developer Guide:** `/home/user/BRAiN/README.dev.md`

---

**Author:** Claude (Stress Test Specialist)
**Project:** BRAiN Framework by FalkLabs / Olaf Falk
**Version:** 0.5.0
**Last Updated:** 2024-12-30
