# BRAiN Master Audit Tool

## Quick Start

The BRAiN Master Audit is a comprehensive stress-test tool for evaluating the Agent Orchestration Framework.

### Prerequisites

1. **Start the backend:**
   ```bash
   docker compose up -d backend redis postgres
   ```

2. **Install dependencies:**
   ```bash
   pip install psutil numpy scipy
   ```

### Run the Audit

```bash
cd /home/user/BRAiN/backend
python tests/brain_master_audit.py
```

**Duration:** 10-20 minutes
**Output:** `/home/user/BRAiN/BRAIN_AUDIT_REPORT.md`

## What It Tests

### Phase A: Performance Stress Test
- Exponential scaling (100 → 10,000 missions)
- Throughput, latency, memory usage
- Algorithmic complexity (O-notation)
- Memory leak detection

### Phase B: Dynamic Stability Analysis
- Sustained load (60s @ 10 m/s)
- Agent utilization patterns
- Pathology detection (deadlock, starvation, cascade)
- Entropy & "edge of chaos" metrics

### Phase C: Breaking Point Definition
- Maximum throughput via binary search
- Bottleneck identification (file:line)
- Recovery time measurement

## Files

- **`brain_master_audit.py`** - Main audit script (1,200 lines)
- **`AUDIT_USAGE_GUIDE.md`** - Complete documentation
- **`test_audit_validation.py`** - pytest test suite
- **`validate_audit_simple.py`** - Quick validation
- **`README_AUDIT.md`** - This file

## Documentation

See **`AUDIT_USAGE_GUIDE.md`** for:
- Detailed usage instructions
- Result interpretation guide
- Troubleshooting
- Advanced customization
- CI/CD integration examples

See **`/home/user/BRAiN/BRAIN_AUDIT_SUMMARY.md`** for:
- Implementation summary
- Technical architecture
- Metrics & thresholds
- Validation results

## Quick Validation (No Backend Required)

```bash
python tests/validate_audit_simple.py
```

Validates the audit script structure without making API calls.

## Example Output

```
================================================================================
 BRAIN MASTER AUDIT - COMPREHENSIVE STRESS TEST & BENCHMARK
================================================================================

🔬 Testing scale: 100 missions
✅ Completed: 100/100
📊 Throughput: 42.74 missions/s
⚠️  Memory Leak: NO

[... continues through all phases ...]

📋 OPTIMIZATION RECOMMENDATIONS:
1. ⚠️  HIGH: Implement Redis pipelining...
2. ✅ Consider caching mission results...

✅ AUDIT COMPLETE
📄 Full report: BRAIN_AUDIT_REPORT.md
```

## Support

- **Issues:** https://github.com/satoshiflow/BRAiN/issues
- **Documentation:** `/home/user/BRAiN/CLAUDE.md`
- **Developer Guide:** `/home/user/BRAiN/README.dev.md`

---

**Author:** Claude (Stress Test Specialist)
**Project:** BRAiN Framework by FalkLabs / Olaf Falk
**Version:** 0.5.0
