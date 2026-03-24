# BRAiN Ist/Soll Status - 2026-03-22

## Soll-Zustand (vereinbart)

- AXE ist die primäre Kommunikations-Frontdoor.
- SkillRun ist die einzige Runtime-Wahrheit.
- Mission ist nie Runtime.
- EvaluationResult ist kanonische Bewertungswahrheit.
- ProviderBinding ist persistent, governbar und auditierbar.
- Postgres ist kanonisch; Redis ist ephemer.
- Selbstlernen und Selbstoptimierung laufen nur governbar (proposal/validation/approval), nicht direkt mutierend.

## Ist-Zustand (umgesetzt)

- Epic 1 Kernobjekte normalisiert:
  - SkillRun, EvaluationResult, SkillDefinition, CapabilityDefinition, ProviderBinding
- SkillRun-State-Machine + Transition-Historie + Control-Plane-Events vorhanden.
- ProviderBinding-Definition + Resolver + Health-Projektion (Redis) vorhanden.
- AXE-Bridge auf SkillRun vorhanden und standardmaessig aktiviert (`AXE_CHAT_EXECUTION_PATH=skillrun_bridge`).
- Legacy `/api/axe/message` nutzt keine direkte Provider-Ausfuehrung mehr, sondern SkillRun-Bridge (fail-closed wenn unkonfiguriert).
- Direkte Capability-Runtime-Ausfuehrung ist standardmaessig geblockt (`BRAIN_BLOCK_DIRECT_CAPABILITY_EXECUTE=true`).
- Memory Contract gehaertet:
  - durable Referenzkette `SkillRun -> EvaluationResult -> ExperienceRecord -> KnowledgeItem`
  - tenant-boundaries in memory/session Tabellen
  - Session-TTL-Eviction fuer ephemere Schicht
- Governed Learning Pipeline (proposal-only) umgesetzt:
  - Kandidat aus SkillRun
  - Validation Gates
  - Promotion-Decision Events
- Adaptive Freeze + Safe-Mode Apply-Block + Rollback-Metadatenpflicht umgesetzt.
- Ops Summary + Incident/Event Timeline + Runbook vorhanden.

## Roadmap-Status

- Epic 1: abgeschlossen (mit kompatiblen Uebergangspfaden, keine neue Parallel-Runtime)
- Epic 2:
  - Phase 1: abgeschlossen
  - Phase 2: abgeschlossen
  - Phase 3: abgeschlossen
  - Phase 4: abgeschlossen
  - Phase 5: abgeschlossen

## Verbleibende Restpunkte (non-blocking)

- Einige lokale Evidence-/Manual-Test-Artefakte sind bewusst unversioniert.
- Fuer Merge-Reife weiterhin RC-Gate und ggf. Full-Scope-Tests vor Release fahren.
