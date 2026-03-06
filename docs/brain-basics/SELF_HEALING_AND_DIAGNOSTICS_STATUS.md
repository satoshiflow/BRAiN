# BRAiN Self-Healing and Diagnostics Status

Date: 2026-03-04

## Short answer

Yes, BRAiN already has parts of a self-healing system in runtime modules.
No, it did not yet have a robust build/test/script continuation and diagnosis pipeline.

## What already exists (runtime)

- Immune self-protection actions:
  - `backend/app/modules/immune/core/service.py`
  - backpressure, circuit breaker, GC trigger, agent restart hooks, safe event emit.
- Health monitor with status transitions and recovery/degradation events:
  - `backend/app/modules/health_monitor/service.py`
- Task queue retries with backoff and retry state:
  - `backend/app/modules/task_queue/service.py`

## Gap identified

- CI/dev execution layer had no single resilient runner to:
  - keep pipeline running after failures,
  - collect structured diagnosis for later fix,
  - support anamnese/diagnose history in one report.

## What was added now

- Resilient pipeline runner:
  - `scripts/resilient_pipeline_runner.py`
- Example plan:
  - `scripts/pipeline_plan.example.json`

Key behavior:

- Step retries
- continue-on-error per step
- timeout per step
- log files per step
- JSON diagnosis report with failure tags and recommendations

Output location:

- `reports/self_healing/<run_id>/diagnosis_report.json`

## Example usage

```bash
python3 scripts/resilient_pipeline_runner.py --plan scripts/pipeline_plan.example.json
```

Always-success exit mode (if desired for long autonomous chains):

```bash
python3 scripts/resilient_pipeline_runner.py --plan scripts/pipeline_plan.example.json --always-zero
```
