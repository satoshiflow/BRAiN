# Shadow Model Reduction Plan

Status: Epic 1 implementation work document

## Priority 1

- `SkillRun.evaluation_summary`
  - keep as read projection only
  - source truth becomes `EvaluationResult`

- `InMemoryProviderBindingRegistry`
  - keep as explicit compatibility fallback only
  - persistent provider bindings become primary source

## Priority 2

- AXE `provider_selector`
  - keep local runtime convenience behavior
  - progressively align to governed `ProviderBinding` resolution
  - do not let AXE become routing truth

- external run finalization paths
  - must pass through the same `SkillRun` state machine contract

## Priority 3

- legacy mission or agent paths with direct execution
  - keep only as compatibility wrappers
  - mark and route toward `SkillRun`

## Reduction Strategy

1. degrade to projection or compatibility wrapper
2. bind to canonical object
3. mark deprecated in code/docs
4. remove only after coverage and runtime parity exist
