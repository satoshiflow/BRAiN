# Repair Workflow

## Objective

Define a repeatable repair workflow for BRAiN where OpenCode acts as internal repair runtime under Dev Layer supervision.

## Workflow stages

1. Intake
- receive repair signal (test failure, runtime alert, policy violation, regression)
- classify severity and blast radius

2. Diagnosis
- reproduce issue
- identify root cause
- define minimal safe fix scope

3. Patch design
- prepare focused patch plan
- identify required tests and guard checks
- confirm boundary constraints (no identity/governance takeover)

4. Implementation
- apply smallest viable code change
- avoid unrelated refactors
- keep module boundaries clear

5. Verification
- run targeted tests first
- run relevant guard scripts
- run broader regression when risk requires it

6. Packaging
- document what changed and why
- include risk and rollback notes
- update handoff artifacts

## Self-healing integration (future-compatible)

When Immune/Healthcare systems flag incidents, Repair Workflow accepts machine-generated tickets and executes the same stages with audit trail.

## Repair principles

- minimal change first
- verify before declare fixed
- preserve API contracts
- preserve BRAiN Core authority boundaries
