# Runtime Control Release / Migration Hardening (2026-04-01)

## Scope

Diese Spezifikation haertet den Runtime-Control-Plane Rollout fuer lokale Staging/RC-Verifikation und kontrollierte Promotion.

## Release Safety Gates

1. **Schema/DB Compatibility**
   - Keine neuen Pflichtspalten fuer bestehende Runtime-Pfade ohne Backfill.
   - Runtime-Control nutzt bestehende `control_plane_events` als Event-Sourcing-Layer.

2. **Fail-Closed Governance**
   - Mutierende Override-/Registry-Endpunkte sind rollenbasiert abgesichert.
   - Approval/Reject nur fuer `admin`/`system_admin`.

3. **Deterministic Resolver**
   - Feste Prioritaetskette:
     - emergency -> governor -> manual approved -> policy -> feature flags -> registry -> defaults.
   - Resolver liefert immer `decision_id`, Explain-Trace und Validation-Block.

4. **Promotion Guardrail**
   - Nur `draft` Registry-Versionen sind promotable.
   - Vorherige `promoted` Version desselben Scopes wird `superseded`.

5. **Rollback Strategy**
   - Rollback = neue Registry-Version auf bekannte stabile Konfiguration erstellen + promoten.
   - Keine in-place Mutation auf historischer promoted Version.

## Migration Playbook

1. Create draft registry version (`POST /api/runtime-control/registry/versions`).
2. Validate via resolver (`POST /api/runtime-control/resolve`) in representative contexts.
3. Optional manual override CRs erstellen und nur bei Bedarf approven.
4. Promote registry version (`POST /api/runtime-control/registry/versions/{id}/promote`).
5. Audit timeline pruefen (`GET /api/runtime-control/timeline`).
6. RC staging gate ausfuehren.

## Evidence Requirements

- API evidence:
  - override requests created/approved/rejected
  - active overrides list
  - registry versions list + promotion
  - timeline entries enthalten correlation/request/version IDs
- Test evidence:
  - runtime-control router tests
  - enforcement tests (LLM/SkillRun/TaskLease)
  - RC staging gate output

## Operational Runbook Hooks

- Incident: falsch gerouteter Provider/Worker
  - active overrides prüfen
  - letzte promoted registry version prüfen
  - timeline nach letzter mutation filtern
  - fallback promotion auf known-good version

- Incident: approval backlog
  - pending override requests prüfen
  - stale requests rejecten oder gezielt approven

- Incident: connector containment
  - security.allowed_connectors per promoted registry patch einschränken
  - Resolver-Ausgabe in ControlDeck verifizieren
