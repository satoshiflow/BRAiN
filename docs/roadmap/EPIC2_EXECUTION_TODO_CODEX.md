# Epic 2 Execution Todo (Codex)

Status: Completed (Phase 1-5)
Date: 2026-03-22

## Phase 1 - AXE Frontdoor Convergence

- [x] Add staged AXE -> SkillRun bridge path in `/api/axe/chat` (feature-flagged).
- [x] Keep stable direct fallback to avoid runtime breakage while bindings/skills are normalized.
- [x] Keep legacy `/api/axe/message` as compatibility wrapper while preparing full SkillRun delegation.
- [x] Extend AXE runtime response with governed binding visibility where available.
- [x] Keep router compatibility for existing test stubs and local dev without DB.
- [x] Switch default AXE execution path from `direct` to `skillrun_bridge` after canonical skill is active.
- [x] Move `/api/axe/message` from direct provider call to SkillRun-only wrapper.
- [x] Add explicit deny/redirect behavior for direct runtime bypass endpoints.

### Phase 1 Runtime Flags

- `AXE_CHAT_EXECUTION_PATH=direct|skillrun_bridge`
- `AXE_CHAT_SKILL_KEY=<skill_key>`
- `AXE_CHAT_SKILL_VERSION=<int>`
- `AXE_CHAT_BRIDGE_FALLBACK_DIRECT=true|false`

## Phase 2 - Memory Contract Hardening

- [x] Introduce explicit short-term vs long-term memory contract document and schema notes.
- [x] Add durable reference chain fields: `SkillRun -> EvaluationResult -> ExperienceRecord -> KnowledgeItem`.
- [x] Add durable provenance IDs into experience/knowledge persistence models.
- [x] Extend tenant-bound guarantees in memory module tables (`memory_entries`/`session_contexts`) without breaking legacy callers.
- [x] Define and apply retention/TTL rules for ephemeral memory read models via session TTL-based eviction.

## Phase 3 - Governed Self-Learning Pipeline

- [x] Add promotion candidate extraction from canonical Evaluation + Experience data.
- [x] Add validation gates and policy/risk blocking for non-compliant candidates.
- [x] Add promotion-decision events and controlled write paths.
- [x] Keep proposal-only mode by default (no direct auto-apply).

## Phase 4 - Controlled Self-Optimization / Self-Extension

- [x] Add adaptive freeze and kill-switch controls (global/tenant/mode).
- [x] Enforce proposal -> approval -> apply -> rollback lifecycle.
- [x] Require rollback plan metadata for mutating optimization actions.
- [x] Fail closed on missing audit/policy/approval dependencies.

## Phase 5 - Runtime and Operations Hardening

- [x] Add operations summary read model (run/eval/promotion/repair/kill-switch health).
- [x] Add incident timeline read model for correlation-based triage (recent control-plane learning events).
- [x] Add operator runbooks for provider quarantine and learning rollback.
- [x] Keep AXE as frontdoor summary channel; preserve governance truth in control-plane services.

## Verification Loop (each slice)

- Targeted pytest for touched modules
- `./scripts/local_ci_gate.sh backend-fast`
- Record evidence under `docs/roadmap/local_ci/`
