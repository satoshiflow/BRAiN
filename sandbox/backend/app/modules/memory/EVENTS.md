# Memory Module Events

**Module:** `brain.memory`
**Charter:** Event Charter v1.0 (ADR-001)
**Source:** `memory_store` / `memory_service`

## Events

| Event Type | Source | Trigger | Payload |
|---|---|---|---|
| `memory.stored` | memory_store | New memory entry created | `memory_id`, `layer`, `timestamp` |
| `memory.deleted` | memory_store | Memory entry removed | `memory_id`, `timestamp` |
| `memory.session_created` | memory_store | New session started | `session_id`, `agent_id`, `timestamp` |
| `memory.session_ended` | context_manager | Session ended, context promoted | `session_id`, `promoted_count`, `timestamp` |
| `memory.compressed` | compressor | Memories compressed | `count`, `compression_ratio`, `timestamp` |
| `memory.merged` | compressor | Episodic → Semantic merge | `agent_id`, `merged_count`, `timestamp` |
| `memory.recalled` | recall | Selective recall executed | `query`, `results_count`, `strategy`, `timestamp` |
| `memory.decayed` | recall | Importance decay applied | `agent_id`, `decayed_count`, `timestamp` |

## Compliance

- All events use `Event` envelope from `mission_control_core.core`
- Publishing is non-blocking (errors logged, never raised)
- Events are optional - system works without EventStream
