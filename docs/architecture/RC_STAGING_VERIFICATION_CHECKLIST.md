# RC / Staging Verification Checklist (Stabilization Block 2)

Scope:
- auth + agent lifecycle
- incident -> immune decision
- recovery action flow
- DNA mutation -> integrity + audit

## Preflight

- [ ] `.env` uses staging-safe credentials/endpoints
- [ ] Redis + PostgreSQL reachable
- [ ] EventStream mode is `required` in staging
- [ ] DB migrations for new architecture tables are applied

## Required checks

1) Auth + Agent Lifecycle
- [ ] `PYTHONPATH=. pytest tests/test_auth_flow.py tests/test_module_auth.py -q`
- [ ] `PYTHONPATH=. pytest tests/test_supervisor_agent.py -q`

2) Immune Decision flow
- [ ] `PYTHONPATH=. pytest tests/modules/test_immune_orchestrator.py tests/modules/test_arch_event_contracts.py -q`
- [ ] Verify `immune.decision` events in stream consumer logs

3) Recovery action flow
- [ ] `PYTHONPATH=. pytest tests/modules/test_recovery_policy_engine.py -q`
- [ ] `PYTHONPATH=. pytest tests/test_enforcement_retry.py tests/test_reflex_actions.py -q`

4) DNA -> Integrity + Audit
- [ ] `PYTHONPATH=. pytest tests/test_dna_events.py tests/modules/test_genetic_integrity.py -q`
- [ ] Verify audit entries for `genetic_integrity.*` and `immune/recovery` actions

## Guardrails

- [ ] `python3 scripts/check_no_legacy_event_bus.py`
- [ ] `python3 scripts/check_no_utcnow_auth.py`
- [ ] `python3 scripts/check_no_utcnow_planning.py`
- [ ] `python3 scripts/critic_gate.py`

## Exit criteria

- [ ] All targeted tests green
- [ ] Event contract tests green
- [ ] No critical errors in staging logs for new modules
- [ ] Audit trail includes correlation IDs and decision/mutation identifiers
