# OpenCode Integration in BRAiN Dev Layer

## Integration statement

OpenCode is integrated as BRAiN's internal:
- Dev system
- Repair system
- Evolution system

OpenCode is not:
- system sovereign
- identity authority
- governance authority

Those remain in BRAiN Core.

## Collaboration model

### With Immune System
- receives anomaly and policy violation signals
- performs code/runtime diagnostics for suspected root causes
- proposes and applies bounded fixes

### With Healthcare
- consumes health telemetry and incident trends
- prioritizes stabilization and resilience patches
- feeds back repair outcomes for health scoring

### With Governance
- aligns risky changes with policy constraints
- enforces release/merge gates for sensitive paths
- emits auditable evidence for approvals

## Typical OpenCode workflows

1. Code writing
- implement scoped features against API contracts

2. Refactoring
- improve structure without changing intended behavior

3. Diagnosis
- analyze failing tests, logs, and runtime behavior

4. Repair
- patch defects with minimal risk surface

5. Patch creation
- produce reviewable, traceable, and test-backed change sets

6. Self-healing support
- execute repair requests triggered by health/immune signals
- report outcomes for learning and prevention

## Local Micro operating mode

For small machines, OpenCode integration should remain:
- lightweight
- modular
- test-verified
- API-first for LLM backend swap
