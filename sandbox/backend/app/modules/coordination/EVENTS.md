# Coordination Module - Event Charter

**Module:** `coordination`
**Version:** 1.0.0
**Compliance:** Event Charter v1.0 (ADR-001)

## Events

| Event Type | Payload | Description |
|---|---|---|
| `coordination.message.sent` | `{message_id, sender_id, target_id, message_type}` | Agent message dispatched |
| `coordination.message.delivered` | `{message_id, target_id}` | Message delivered to agent inbox |
| `coordination.task.delegated` | `{task_id, task_name, assigned_to, score}` | Task assigned to agent |
| `coordination.task.completed` | `{task_id, agent_id, duration_ms}` | Task completed successfully |
| `coordination.task.failed` | `{task_id, agent_id, error, attempts}` | Task failed |
| `coordination.vote.initiated` | `{vote_id, proposal, voter_count}` | Vote started |
| `coordination.vote.completed` | `{vote_id, outcome, approve_count, reject_count}` | Vote concluded |
| `coordination.knowledge.contributed` | `{entry_id, key, contributed_by, confidence}` | Knowledge entry added |
| `coordination.conflict.reported` | `{conflict_id, severity, agent_ids}` | Conflict reported |
| `coordination.conflict.resolved` | `{conflict_id, resolution, resolved_by}` | Conflict resolved |
