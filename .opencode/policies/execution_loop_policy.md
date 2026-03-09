# Execution Loop Policy

Principle:

Mission loop, not roadmap loop.

Possible missions:

- roadmap
- audit
- bugfix
- migration
- refactor
- architecture
- docs

Loop behavior:

1 analyze mission
2 choose next step
3 execute
4 validate
5 update state
6 continue

Stop only if:

- blocker
- unclear structure
- destructive change
- human decision needed

Otherwise continue automatically.

Stability:

- preserve repo stability
- avoid rewrites
- prefer incremental work
- validate changes

Mission state tracked in:

.opencode/state/current_loop.md

State format:

- must be valid YAML
- keep stable top-level keys:
  - version
  - last_updated
  - loop_status
  - mission
  - current_subtask
  - completed
  - next_candidates
  - blockers
  - validation
  - notes
  - stop_condition
- mission.type must be one of:
  - roadmap
  - audit
  - bugfix
  - migration
  - refactor
  - architecture
  - docs

State update rules:

- update last_updated on every executed step
- append exactly one completed entry per finished step
- keep next_candidates prioritized
- write explicit blocker reason to stop_condition when blocked
