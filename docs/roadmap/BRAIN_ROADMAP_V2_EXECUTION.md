# BRAiN Roadmap v2 Execution Plan

Date: 2026-03-07
Owner: OpenCode (Explorer/Dev/Repair agent)

## Mission framing

- BRAiN decides, prioritizes, approves, and governs.
- OpenCode explores, implements, tests, and reports.
- No governance bypass, no sovereign behavior, no hidden orchestration forks.

## Phase A - Hardening and Baseline Freeze

Goals:
- close high-priority runtime blockers from prior roadmap
- remove startup/runtime regressions that block controlled evolution

Execution items:
1. Auth token branch migration reliability
2. Worker startup/runtime compatibility fixes
3. Event + audit + persistence path reliability
4. Migration hygiene and replayability in dev stack

Current status: In progress

## Phase B - Runtime Operational Readiness Gate 2.0

Goals:
- reproducible local runtime gate with evidence

Execution items:
1. infra health checks (postgres/redis/qdrant/mock-llm/backend)
2. migration/table verification
3. smoke flow: immune -> recovery -> unified audit -> event stream
4. evidence capture and runbook output

Current status: In progress

## Phase C - Genetic Quarantine Manager (prep + implementation)

Goals:
- safe mutation isolation and approval pipeline

Execution items:
1. schema and state model (`candidate/quarantined/probation/approved/rejected`)
2. immune/recovery trigger integration points
3. governance-gated promotion/reject workflow
4. event + audit contracts

Current status: Not started (after Phase A/B freeze)

## Phase D - OpenCode Repair Loop integration

Goals:
- controlled incident-to-repair workflow

Execution items:
1. incident -> repair ticket bridge
2. patch/test/audit evidence package format
3. governance hook on merge/deploy handoff
4. rollback metadata and replay safety

Current status: Not started (after Phase C baseline)

## Phase E - Post-integration hardening

Goals:
- remove residual drift and stabilize for sustained evolution

Execution items:
1. legacy path freeze/migration backlog reduction
2. reliability/security debt closure
3. contract/regression/chaos validation
4. docs consolidation and release gate update

Current status: Not started

## Parallel analysis track

- AXE_UI frontend analysis runs after Phase A/B blockers are reduced.
