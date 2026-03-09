# OpenCode Help: Mission Loop

This folder contains the mission-loop command, policy, and runtime state file used for continuous autonomous execution.

## Files

- `.opencode/commands/help.md`: slash-command definition for `/help`.
- `.opencode/commands/loop.md`: slash-command definition for `/loop`.
- `.opencode/policies/execution_loop_policy.md`: mission-loop execution policy.
- `.opencode/state/current_loop.md`: current mission state snapshot (strict YAML).

## Command Help

`/loop` is an OpenCode slash command.

Syntax:

`/loop <mission scope>`

Related help command:

`/help`

What it does:

- Runs a mission continuously in incremental steps.
- Keeps mission state in `.opencode/state/current_loop.md`.
- Stops only for real blockers (technical blocker, unclear repository context, destructive change requirement, or external/human decision).

## Usage

Run a mission in loop mode with the slash command:

`/loop <mission scope>`

Examples:

- `/loop Implement auth refactor`
- `/loop Continue roadmap implementation`
- `/loop Audit repository architecture`
- `/loop Fix failing tests`

## Operating Model

The loop repeats this cycle:

1. analyze current state
2. choose next smallest meaningful step
3. execute
4. validate
5. update mission state
6. continue

It stops only for real blockers (technical blocker, unclear repository context, destructive change requirement, or external/human decision).

## State Contract

`.opencode/state/current_loop.md` must remain valid YAML with these stable top-level keys:

- `version`
- `last_updated`
- `loop_status`
- `mission`
- `current_subtask`
- `completed`
- `next_candidates`
- `blockers`
- `validation`
- `notes`
- `stop_condition`

Allowed mission types (`mission.type`):

- `roadmap`
- `audit`
- `bugfix`
- `migration`
- `refactor`
- `architecture`
- `docs`

Update rules:

- refresh `last_updated` on every executed step
- append one `completed` entry per finished step
- keep `next_candidates` prioritized
- set `stop_condition` to a specific reason when blocked
