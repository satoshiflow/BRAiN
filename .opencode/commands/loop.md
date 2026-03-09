---
description: Run any mission in continuous execution loop mode
agent: build
---

# Continuous Mission Loop

Mission / scope:
$ARGUMENTS

Operate in continuous mission-loop mode.

Core behavior:

1. analyze the current state
2. identify the next smallest meaningful step
3. execute it
4. validate the result
5. update mission state
6. continue

Stop only if:

- blocking technical error
- repository context unclear
- destructive change required
- external decision needed

Rules:

- incremental steps
- repository stability
- minimal rewrites
- batch updates

Use policy:

.opencode/policies/execution_loop_policy.md

Track state:

.opencode/state/current_loop.md
