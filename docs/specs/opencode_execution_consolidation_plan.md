# OpenCode Execution Consolidation Plan

**Status**: Active Consolidation (Wave 1)  
**Owner**: BRAiN Runtime / OpenCode Integration  
**Goal**: Reduce execution-layer module duplication by establishing OpenCode as standard executor

## Executive Summary

- **Problem**: Multiple overlapping execution modules (`factory_executor`, `webgenesis` execution layer, various generators)
- **Solution**: OpenCode Worker as unified execution plane, BRAiN Runtime as control/governance plane
- **Approach**: Phased deprecation + migration (Wave 1 → Wave 2)
- **Timeline**: Wave 1 (immediate), Wave 2 (90 days)

---

## Keep vs Replace Matrix

| Module | Role | Wave 1 Action | Replacement | Rationale |
|--------|------|---------------|-------------|-----------|
| **factory_executor** | Generic execution orchestrator | **DEPRECATE** | OpenCode worker job contracts | Duplicates OpenCode's job execution capabilities |
| **webgenesis** (execution) | Website build/deploy/rollback | **DEPRECATE** (exec layer only) | OpenCode worker | Build/deploy/rollback is generic execution, not domain logic |
| **webgenesis** (specs/QA) | Domain orchestrator | **KEEP** | N/A | Website-specific quality/acceptance criteria |
| **course_factory/webgenesis_integration** | Bridge to old executor | **DEPRECATE** | Job contract dispatch | Direct coupling to deprecated executor |
| **genesis** (blueprints) | Domain models | **KEEP** (adapt Wave 2) | Partial (assembly → OpenCode) | Blueprints stay, assembly execution moves |
| **business_factory** (planning) | Business domain logic | **KEEP** | N/A | Planning/risk assessment stays in BRAiN |
| **opencode_repair** | Repair ticketing | **KEEP + EXPAND** | N/A | Gateway to OpenCode, ticket/action sink |
| **immune_orchestrator** | Incident classification | **KEEP** | N/A | Core control plane |
| **recovery_policy_engine** | Recovery decision logic | **KEEP** | N/A | Core control plane |
| **runtime_auditor** | Continuous monitoring | **KEEP** | N/A | Core control plane |

---

## Wave 1: Immediate Freeze (Completed)

### Scope
- `factory_executor/*`
- `webgenesis` execution files (`service.py`, `ops_service.py`, `releases.py`, `rollback.py`, `router.py`)
- `course_factory/webgenesis_integration.py`

### Actions
- ✅ Deprecation headers added
- ✅ Lifecycle status = `deprecated`
- ✅ `replacement_target` + `sunset_phase` set
- ⏳ Guardrail gate enforces "no new features"

### Exit Criteria
- All Wave-1 files have visible deprecation notice
- No new feature PRs accepted in Wave-1 modules
- At least 1 execution path routes through OpenCode dispatch

---

## Wave 2: Planned Consolidation (90 days)

### Scope
- Remaining `genesis` assembly logic
- `business_factory` execution (if any)
- Any other domain-specific generators

### Actions
- Assess runtime usage patterns
- Migrate high-value paths to Job Contracts
- Shadow-run + A/B verification
- Sunset when usage < 5% AND quality parity confirmed

---

## Job Contract Design

### Job Schema (Minimum Fields)
```json
{
  "job_id": "string (uuid)",
  "correlation_id": "string (uuid)",
  "mode": "plan | build | heal | evolve",
  "scope": {
    "module": "string",
    "entity_id": "string",
    "tenant_id": "string"
  },
  "constraints": {
    "timeout_seconds": "int",
    "max_iterations": "int",
    "risk_level": "low | medium | high",
    "approval_required": "bool",
    "blast_radius_limit": "int"
  },
  "context": {
    "trigger_event": "string",
    "original_request": "object"
  },
  "created_at": "timestamp",
  "created_by": "string (actor)"
}
```

### Status Lifecycle
```
requested → validated → queued → assigned → in_progress → 
  → verifying → completed | failed | timeout | cancelled
```

### Event Types
- `job.requested`
- `job.validated`
- `job.started`
- `job.artifact_produced`
- `job.verification_passed | job.verification_failed`
- `job.completed | job.failed | job.cancelled`

---

## Migration Contracts

### Phase 1: Dispatch Layer (Wave 1, now)
- Existing execution callers create Job instead of direct execution
- Job dispatched to `opencode_repair` → OpenCode Worker
- Existing code paths remain **callable** but marked deprecated

### Phase 2: Shadow Run (Wave 1+30d)
- Both old + new paths run in parallel
- Compare outcomes, collect metrics
- Alert on divergence

### Phase 3: Cutover (Wave 1+60d)
- New path becomes primary
- Old path available as fallback (manual override)

### Phase 4: Sunset (Wave 1+90d)
- Old execution modules removed
- Only stub/compatibility wrappers remain if needed

---

## Governance & Safety

### Risk Classification
| Risk Level | Auto-Execute | Approval Required | Rollback Strategy |
|------------|--------------|-------------------|-------------------|
| **Low** | ✅ Yes | No | Auto + manual |
| **Medium** | ❌ No | Yes (async) | Manual + quarantine |
| **High** | ❌ No | Yes (sync + breakglass) | Manual only |

### Guardrails
1. **Deprecation Header Enforcement**: PRs touching Wave-1 modules fail unless:
   - Header/docs only
   - Critical bugfix (tagged)
2. **Lifecycle Block**: Deprecated modules reject new feature writes via router guards
3. **Blast Radius Limit**: Jobs with `blast_radius > 10` require governance approval
4. **Tenant Isolation**: Job scope validated against caller's tenant_id

---

## Done Criteria (Per Module)

| Criterion | Wave 1 | Wave 2 |
|-----------|--------|--------|
| Deprecation header visible | ✅ | ⏳ |
| Lifecycle status = deprecated | ✅ | ⏳ |
| Guardrail gate active | ⏳ | ⏳ |
| At least 1 path via OpenCode | ⏳ | ⏳ |
| Shadow run passing (quality parity) | - | ⏳ |
| Usage < 5% of baseline | - | ⏳ |
| Module removal approved | - | ⏳ |

---

## Forbidden Actions

### In Deprecated Modules (Wave 1)
- ❌ Adding new features
- ❌ Expanding API surface
- ❌ New integrations/dependencies
- ✅ Critical bugfixes (tagged)
- ✅ Security patches
- ✅ Documentation updates

### In Control Plane Modules (Always)
- ❌ Direct execution logic (belongs in OpenCode)
- ❌ Hardcoded execution paths (use Job Contracts)
- ✅ Governance/Policy/Risk logic
- ✅ Audit/Event emission
- ✅ Verification/Quality gates

---

## References

- Runtime Deployment Contract: `docs/specs/runtime_deployment_contract.md`
- Dependency Health Policy: `docs/specs/dependency_health_policy.md`
- Module Lifecycle: `backend/app/modules/module_lifecycle/`
- OpenCode Repair: `backend/app/modules/opencode_repair/`
- Deprecation Header Script: `scripts/add_deprecation_headers.py`
- Guardrail Gate: `scripts/check_no_changes_deprecated_modules.py`
