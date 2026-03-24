# SkillRun State Machine

Status: Epic 1 implementation contract

## Allowed States

- `queued`
- `planning`
- `waiting_approval`
- `running`
- `cancel_requested`
- `succeeded`
- `failed`
- `cancelled`
- `timed_out`

Terminal states:

- `succeeded`
- `failed`
- `cancelled`
- `timed_out`

## Allowed Transitions

| From | To | Owner | Persist | Event | Audit |
|---|---|---|---|---|---|
| `queued` | `planning` | Skill Engine | yes | `skill.run.planning.started.v1` | no |
| `queued` | `cancel_requested` | caller/control plane | yes | `skill.run.cancel_requested.v1` | yes |
| `planning` | `waiting_approval` | policy/governance gate | yes | `skill.run.approval.required.v1` | yes |
| `planning` | `running` | Skill Engine | yes | `skill.run.started.v1` | no |
| `planning` | `failed` | Skill Engine | yes | `skill.run.failed.v1` | yes |
| `planning` | `cancel_requested` | caller/control plane | yes | `skill.run.cancel_requested.v1` | yes |
| `waiting_approval` | `running` | approver/control plane | yes | `skill.run.started.v1` | yes |
| `waiting_approval` | `failed` | approver/control plane | yes | `skill.run.failed.v1` | yes |
| `waiting_approval` | `cancel_requested` | caller/control plane | yes | `skill.run.cancel_requested.v1` | yes |
| `running` | `succeeded` | Skill Engine/external executor finalizer | yes | `skill.run.completed.v1` | yes |
| `running` | `failed` | Skill Engine/external executor finalizer | yes | `skill.run.failed.v1` | yes |
| `running` | `timed_out` | runtime watchdog | yes | `skill.run.timed_out.v1` | yes |
| `running` | `cancel_requested` | caller/control plane | yes | `skill.run.cancel_requested.v1` | yes |
| `cancel_requested` | `cancelled` | Skill Engine/external executor finalizer | yes | `skill.run.cancelled.v1` | yes |

## Illegal Transition Rule

- Any transition not listed above must fail with `SR-006 STATE_CONFLICT`.
- Terminal states have no outgoing transitions.

## Mission Anti-Runtime Rule

- `mission_id` is metadata and correlation only.
- Missions may create, reference, group, prioritize, and observe `SkillRun` records.
- Missions may not directly set `provider_selection_snapshot`.
- Missions may not call capability/tool execution directly.
- Missions may not bypass `SkillRun` for external execution.
