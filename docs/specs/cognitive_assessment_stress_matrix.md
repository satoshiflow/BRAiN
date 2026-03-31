# Cognitive Assessment Stress Matrix

This matrix defines high-value stress and system-interaction scenarios for the
`cognitive_assessment` + `intent_to_skill` flow across Backend, ControlDeck v3,
and AXE.

## Core scenarios

1. **Baseline matched-skill roundtrip**
   - Flow: `AXE -> Backend -> CD3`
   - Input: repeated knowledge search requests
   - Expectation: stable assessment, stable candidates, no drift in normalized intent

2. **Novel low-confidence storm**
   - Flow: `AXE/CD3 -> Backend`
   - Input: many unique custom intents with high confidence threshold
   - Expectation: `draft_required`, no hidden auto-routing, no run creation

3. **Sensitive request with policy handoff**
   - Flow: `AXE -> Backend -> Policy/Governor`
   - Input: production-affecting request with `auto_execute=true`
   - Expectation: assessment flags risk; policy/governor remains authoritative

4. **Unauthorized auto-execute attempt**
   - Flow: `CD3/AXE -> Backend`
   - Input: non-operator requests `auto_execute=true`
   - Expectation: `403`, no run creation, no governance bypass

5. **Mixed retrieval saturation**
   - Flow: `CD3 -> Backend`
   - Input: intents that hit both memory and knowledge heavily
   - Expectation: bounded associated-case list, acceptable latency, no duplicate explosion

6. **Cross-surface provenance validation**
   - Flow: `AXE -> Backend -> CD3`
   - Input: create assessment in AXE, inspect linked run/outcome in CD3
   - Expectation: same `assessment_id`, stable feedback writeback, tenant-safe visibility

7. **Tenant isolation breach test**
   - Flow: `tenant A/B -> Backend`
   - Input: fetch assessment by ID across tenants
   - Expectation: no leakage, `404` or empty result for foreign tenant

8. **Registry churn under load**
   - Flow: `CD3/AXE -> Backend`
   - Input: concurrent requests while active skill versions change
   - Expectation: deterministic resolution, no mixed-version flapping

9. **Execution failure feedback loop**
   - Flow: `AXE/CD3 -> Backend -> SkillRun -> Evaluation`
   - Input: intent resolving to failing provider path
   - Expectation: feedback persisted with `success=false`, assessment remains advisory-only

10. **Success feedback loop**
    - Flow: `CD3 -> Backend`
    - Input: repeated successful auto-execution for same intent class
    - Expectation: feedback rows accumulate cleanly, provenance remains queryable

11. **Input-boundary fuzzing**
    - Flow: `AXE/CD3 -> Backend`
    - Input: max-length strings, multiline payloads, mixed punctuation, empty invalid payloads
    - Expectation: clean `400` for invalid empty input, no crashes, no malformed assessments

12. **Backend readiness / rebuild race**
    - Flow: `Docker rebuild -> E2E bootstrap`
    - Input: rebuild stack and start tests immediately
    - Expectation: readiness gates absorb startup lag; no `socket hang up` during login bootstrap

## Metrics to track

- request success rate
- p50/p95 assessment latency
- p50/p95 login bootstrap latency after rebuild
- candidate stability for repeated intents
- false-positive match rate
- `draft_required` rate for novel prompts
- policy/governor denial rate after advisory assessment
- count and completeness of `cognitive_learning_feedback`
- tenant isolation violations (must remain zero)

## Minimum system checks before stress runs

- `./scripts/alembic_doctor.sh check`
- `./scripts/run_rc_staging_gate.sh`
- ControlDeck E2E suite
- local stack healthy via Docker healthchecks
