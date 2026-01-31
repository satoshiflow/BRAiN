# Learning Module - Event Charter

**Module:** `learning`
**Version:** 1.0.0
**Compliance:** Event Charter v1.0 (ADR-001)

## Events

| Event Type | Payload | Description |
|---|---|---|
| `learning.metric.recorded` | `{metric_id, agent_id, metric_type, value}` | Metric data point recorded |
| `learning.strategy.registered` | `{strategy_id, agent_id, domain, name}` | New strategy registered |
| `learning.strategy.selected` | `{strategy_id, agent_id, domain, exploration}` | Strategy selected for use |
| `learning.strategy.promoted` | `{strategy_id, name, success_rate, karma_score}` | Strategy promoted to ACTIVE |
| `learning.strategy.demoted` | `{strategy_id, name, success_rate, karma_score}` | Strategy demoted |
| `learning.outcome.recorded` | `{strategy_id, success, karma_delta}` | Strategy outcome recorded |
| `learning.experiment.created` | `{experiment_id, name, agent_id}` | A/B experiment created |
| `learning.experiment.started` | `{experiment_id, control_id, treatment_id}` | Experiment started |
| `learning.experiment.completed` | `{experiment_id, winner, p_value, effect_size}` | Experiment concluded with winner |
| `learning.experiment.cancelled` | `{experiment_id, reason}` | Experiment cancelled |
