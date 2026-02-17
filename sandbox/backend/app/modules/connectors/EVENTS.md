# Connectors Module - Event Charter

**Module:** `connectors`
**Version:** 1.0.0
**Compliance:** ADR-001 Event Charter v1.0

## Events

| Event Type | Trigger | Payload |
|-----------|---------|---------|
| `connector.registered` | Connector added to registry | `{connector_id, connector_type, display_name}` |
| `connector.unregistered` | Connector removed | `{connector_id}` |
| `connector.started` | Connector lifecycle start | `{connector_id, connector_type}` |
| `connector.stopped` | Connector lifecycle stop | `{connector_id, reason?}` |
| `connector.status_changed` | Status transition | `{connector_id, old_status, new_status}` |
| `connector.message_received` | Incoming user message | `{connector_id, user_id, content_type, message_id}` |
| `connector.message_sent` | Outgoing response | `{connector_id, user_id, message_id, duration_ms}` |
| `connector.error` | Processing error | `{connector_id, error, context?}` |
| `connector.health_check` | Health check result | `{connector_id, status, latency_ms?}` |
| `connector.brain_response` | AXE Core response | `{connector_id, mode, duration_ms, success}` |
