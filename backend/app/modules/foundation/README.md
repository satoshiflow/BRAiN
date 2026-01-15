# Foundation Module

**Version:** 0.1.0
**Status:** ✅ Production Ready (Skeleton)

---

## Overview

The **Foundation Module** provides core abstractions and safety mechanisms for all BRAiN agent operations. It enforces ethics rules, validates actions against safety policies, and provides behavior tree execution capabilities (with RYR integration planned).

---

## Features

### ✅ Implemented (v0.1.0)

- **Action Validation** - Validate actions against ethics/safety rules
- **Ethics Enforcement** - Block unethical operations
- **Safety Checks** - Prevent dangerous operations (filesystem, database, network)
- **Strict Mode** - Whitelist-only operation mode
- **Behavior Tree Execution** - Placeholder for ROS2/robotics integration
- **REST API** - Full HTTP API for Foundation operations
- **Metrics & Monitoring** - Track violations, overrides, uptime

### 🚧 Planned (Future)

- **ROS2 Integration** - Real behavior tree execution with robot control
- **Advanced Ethics Engine** - Rule-based system with priorities
- **Learning from violations** - Adapt rules based on feedback
- **Multi-agent coordination** - Cross-agent safety checks

---

## API Endpoints

### Status & Configuration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/foundation/status` | Get Foundation status & metrics |
| GET | `/api/foundation/config` | Get current configuration |
| PUT | `/api/foundation/config` | Update configuration (runtime) |
| GET | `/api/foundation/health` | Health check |

### Action Validation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/foundation/validate` | Validate single action |
| POST | `/api/foundation/validate-batch` | Validate multiple actions |

### Behavior Trees

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/foundation/behavior-tree/execute` | Execute behavior tree |
| POST | `/api/foundation/behavior-tree/validate` | Validate tree without executing |

---

## Usage Examples

### 1. Validate an Action

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/foundation/validate",
        json={
            "action": "robot.move",
            "params": {"distance": 10, "speed": 2},
            "context": {"agent_id": "robot_001"}
        }
    )

    if response.status_code == 200:
        print("✅ Action allowed")
    else:
        print(f"❌ Action blocked: {response.json()}")
```

### 2. Execute Behavior Tree

```python
tree = {
    "node_id": "navigation_sequence",
    "node_type": "sequence",
    "children": [
        {
            "node_id": "check_battery",
            "node_type": "condition",
            "action": "battery.check",
            "params": {"min_level": 20}
        },
        {
            "node_id": "move_to_waypoint",
            "node_type": "action",
            "action": "robot.move",
            "params": {"target": "waypoint_1"}
        }
    ]
}

response = await client.post(
    "http://localhost:8000/api/foundation/behavior-tree/execute",
    json=tree
)

result = response.json()
print(f"Status: {result['status']}")
print(f"Executed nodes: {result['executed_nodes']}")
```

### 3. Update Configuration

```python
new_config = {
    "ethics_enabled": True,
    "safety_checks": True,
    "strict_mode": True,
    "allowed_actions": ["robot.move", "robot.stop", "battery.check"],
    "blocked_actions": ["delete_all", "format_disk"]
}

response = await client.put(
    "http://localhost:8000/api/foundation/config",
    json=new_config
)
```

### 4. Check Action Authorization

```python
from backend.app.modules.foundation.service import get_foundation_service
from backend.app.modules.foundation.schemas import AuthorizationRequest

foundation = get_foundation_service()

# Check if agent is authorized to perform an action
result = foundation.authorize_action(AuthorizationRequest(
    agent_id="ops_agent",
    action="deploy_to_production",
    resource="brain-backend",
    context={"environment": "production"}
))

if not result.authorized:
    print(f"❌ Unauthorized: {result.reason}")
    print(f"📋 Audit ID: {result.audit_id}")
else:
    print(f"✅ Authorized: {result.reason}")
    print(f"📋 Audit ID: {result.audit_id}")
```

### 5. Query Audit Log

```python
from backend.app.modules.foundation.schemas import AuditLogRequest

# Retrieve recent validation/authorization events
result = foundation.query_audit_log(AuditLogRequest(
    agent_id="ops_agent",
    outcome="blocked",
    limit=50
))

print(f"Found {result.total} blocked actions for ops_agent")
for entry in result.entries:
    print(f"{entry.timestamp}: {entry.action} - {entry.outcome} - {entry.reason}")

# Filter by event type
auth_events = foundation.query_audit_log(AuditLogRequest(
    event_type="authorization",
    limit=100
))

print(f"\nAuthorization Events: {auth_events.total}")
```

---

## Configuration

### Default Settings

```python
{
    "ethics_enabled": true,
    "safety_checks": true,
    "strict_mode": false,
    "blocked_actions": [
        "delete_all",
        "format_disk",
        "sudo_rm_rf",
        "drop_database"
    ]
}
```

### Strict Mode

When `strict_mode` is enabled, ONLY actions in `allowed_actions` are permitted. All others are blocked.

---

## Safety Rules

### Blacklist (Always Blocked)

- `delete_all` - Mass deletion
- `format_disk` - Disk formatting
- `sudo_rm_rf` - Recursive deletion
- `drop_database` - Database destruction

### Pattern Detection

Foundation automatically detects dangerous patterns:

- **Filesystem**: `rm -rf`, `del /f`, `shred`, `wipe`
- **Database**: `drop database`, `truncate table`
- **Network**: Connections to suspicious domains

---

## Testing

Run Foundation tests:

```bash
# All Foundation tests
pytest backend/tests/test_foundation.py -v

# Specific test class
pytest backend/tests/test_foundation.py::TestFoundationService -v

# Coverage
pytest backend/tests/test_foundation.py --cov=app.modules.foundation
```

---

## Integration with RYR

The Foundation module is designed as the safety layer for RYR (Robot Your Robot) integration:

1. **Behavior Trees** → Control robot actions
2. **Safety Checks** → Prevent dangerous movements
3. **Ethics Rules** → Ensure ethical operation
4. **Action Validation** → Pre-validate all robot commands

### Planned RYR Integration

```python
# Future: Real ROS2 behavior tree execution
from ros2_integration import BehaviorTreeExecutor

class FoundationService:
    async def execute_behavior_tree(self, tree: BehaviorTreeNode):
        # Validate all actions first
        validation = await self.validate_tree(tree)
        if not validation["valid"]:
            raise SafetyViolation(validation["issues"])

        # Execute on real robot
        executor = BehaviorTreeExecutor()
        return await executor.execute(tree)
```

---

## Architecture

```
foundation/
├── __init__.py          # Module exports
├── schemas.py           # Pydantic models
├── service.py           # Business logic
├── router.py            # API endpoints
├── core/                # Future: Advanced features
│   ├── ethics_engine.py # Rule-based ethics system
│   └── bt_executor.py   # Real behavior tree execution
└── README.md            # This file
```

---

## Development

### Adding Custom Ethics Rules

```python
from app.modules.foundation.schemas import EthicsRule

rule = EthicsRule(
    rule_id="no_unauthorized_access",
    name="Prevent Unauthorized Access",
    description="Block access to restricted resources",
    pattern=".*admin.*|.*sudo.*",
    action_type="block",
    priority=100
)

service = get_foundation_service()
service.ethics_rules.append(rule)
```

---

## Metrics

Foundation tracks these metrics:

- `ethics_violations` - Actions blocked by ethics rules
- `safety_overrides` - Actions blocked by safety checks
- `total_validations` - Total validation requests
- `uptime_seconds` - Service uptime

Access via `/api/foundation/status`

---

## Future Enhancements

1. **Machine Learning** - Learn safe/unsafe patterns from data
2. **Multi-agent Coordination** - Cross-agent safety verification
3. **Real-time Monitoring** - WebSocket stream of violations
4. **Audit Log** - Persistent log of all validations
5. **ROS2 Integration** - Full robotics stack integration

---

## Contributors

- Initial implementation: Phase 1 of BRAiN Evolution
- Version: 0.1.0
- Date: 2024-12-19

---

## License

Part of BRAiN project - See root LICENSE file
