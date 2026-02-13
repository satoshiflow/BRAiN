# Planning Module - Event Charter

**Module:** `planning`
**Version:** 1.0.0
**Compliance:** Event Charter v1.0 (ADR-001)

## Events

| Event Type | Payload | Description |
|---|---|---|
| `planning.plan.created` | `{plan_id, name, total_nodes, agent_id}` | Execution plan created |
| `planning.plan.validated` | `{plan_id, valid, error_count}` | Plan validated |
| `planning.plan.started` | `{plan_id, root_nodes}` | Plan execution started |
| `planning.plan.completed` | `{plan_id, completed_nodes, failed_nodes, duration_ms}` | Plan completed |
| `planning.plan.failed` | `{plan_id, failed_nodes, error}` | Plan failed |
| `planning.node.started` | `{plan_id, node_id, node_type, agent_id}` | Node execution started |
| `planning.node.completed` | `{plan_id, node_id, duration_ms}` | Node completed |
| `planning.node.failed` | `{plan_id, node_id, error, recovery_strategy}` | Node failed |
| `planning.recovery.attempted` | `{plan_id, node_id, strategy, success}` | Recovery attempted |
| `planning.resource.budget_warning` | `{plan_id, resource_type, utilization}` | Budget >80% utilized |
