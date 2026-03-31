# AXE Miniworker Pilot

Status: Pilot implementation

## Purpose

`axe_miniworker` adds a lightweight, bounded execution path for small AXE programming tasks.

The pilot keeps BRAiN as the control plane:
- AXE provides the entry point
- BRAiN decides whether the path is appropriate
- the miniworker only executes a narrow proposal task

## Runtime Position

Canonical stack:

`AXE -> AXE worker bridge / worker API -> axe_miniworker adapter -> Pi runtime -> normalized proposal -> BRAiN follow-up decision`

The miniworker is not a second runtime authority.

It does not own:
- governance
- routing truth
- SkillRun truth
- mission state
- secret management

## Scope

V1 supports only `proposal` mode.

Supported task shapes:
- small patch proposals
- constrained code analysis
- test suggestions
- instruction-bound quick repair prompts

Out of scope:
- deployment
- infra changes
- large refactors
- autonomous multi-step apply loops
- high-risk or sensitive mutations

## Pi Integration

The pilot is Pi-backed but adapter-isolated.

The adapter launches Pi as an external command with read-only tools:
- `read`
- `grep`
- `find`
- `ls`

This preserves proposal-only behavior and keeps the executor bounded.

## Config Keys

The pilot uses ControlDeck/CD3 config-vault compatible keys:
- `AXE_MINIWORKER_ENABLED`
- `AXE_MINIWORKER_COMMAND`
- `AXE_MINIWORKER_PROVIDER`
- `AXE_MINIWORKER_MODEL`
- `AXE_MINIWORKER_WORKDIR`
- `AXE_MINIWORKER_TIMEOUT_SECONDS`
- `AXE_MINIWORKER_MAX_FILES`
- `AXE_MINIWORKER_MAX_LLM_TOKENS`
- `AXE_MINIWORKER_MAX_COST_CREDITS`
- `AXE_MINIWORKER_ALLOW_BOUNDED_APPLY`

Provider keys are resolved through the same config/env path already used by CD3 secrets:
- `OPENAI_API_KEY`
- `OPENROUTER_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENWEBUI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENROUTER_BASE_URL`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `LOCAL_LLM_MODE`

## Resource Model

The pilot is designed as a resource-saving path by combining:
- smaller prompts
- narrow file scope
- low iteration count
- read-only proposal mode
- short runtime budget

Tracked metrics:
- estimated prompt tokens
- estimated completion tokens
- estimated cost credits
- approximate child-process RSS delta
- success/failure/timeout rates

## Credits and Health

Credits:
- approximate credits are tracked through the NeuroRail cost tracker
- best-effort credit consumption is attempted through the credits module

Health:
- miniworker telemetry is surfaced into `system_health.metadata.axe_miniworker`
- degraded runs include timeouts, failed executions, and credit-consumption degradation

## Repair Integration

Failed miniworker executions create best-effort repair tickets through `opencode_repair` with:
- worker run id
- prompt
- execution mode
- file scope

This keeps small failures observable without escalating every case to the heavy execution path.

## Entry Points

Current pilot entry points:
- `POST /api/axe/workers` with `worker_type="miniworker"`
- AXE slash command bridge: `/miniworker ...`

## Follow-up Work

Planned next steps after pilot validation:
- stronger routing rules from Domain Agent / RoutingDecision
- optional `bounded_apply` behind policy gate
- more precise token and memory accounting
- richer AXE rendering for inline patch artifacts
