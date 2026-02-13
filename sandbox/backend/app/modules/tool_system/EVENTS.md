# Tool System Events

**Module:** `brain.tool_system`
**Charter:** Event Charter v1.0 (ADR-001)
**Source:** `tool_registry` / `tool_system`

## Events

| Event Type | Source | Trigger | Payload |
|---|---|---|---|
| `tool.registered` | tool_registry | New tool registered | `tool_id`, `name`, `timestamp` |
| `tool.updated` | tool_registry | Tool metadata changed | `tool_id`, `timestamp` |
| `tool.deleted` | tool_registry | Tool removed | `tool_id`, `name`, `timestamp` |
| `tool.status_changed` | tool_registry | Status transition | `tool_id`, `old_status`, `new_status`, `reason`, `timestamp` |
| `tool.version_added` | tool_registry | New version registered | `tool_id`, `version`, `timestamp` |
| `tool.executed` | tool_system | Tool execution completed | `tool_id`, `success`, `duration_ms`, `agent_id`, `mission_id`, `timestamp` |
| `tool.execution_failed` | tool_system | Tool execution failed | `tool_id`, `error`, `agent_id`, `timestamp` |
| `tool.suspended` | accumulation | Auto-suspended by maintenance | `tool_id`, `retention_score`, `reason`, `timestamp` |
| `tool.deprecated` | accumulation | Auto-deprecated (idle) | `tool_id`, `days_idle`, `timestamp` |
| `tool.synergy_detected` | accumulation | Cross-tool synergy found | `tool_a`, `tool_b`, `cooccurrences`, `timestamp` |

## Compliance

- All events use `Event` envelope from `mission_control_core.core`
- Publishing is non-blocking (errors logged, never raised)
- Events are optional - system works without EventStream
