# Policy Engine Module

**Version:** 2.0.0
**Status:** ✅ Production Ready
**Location:** `backend/app/modules/policy/`

---

## Overview

The **Policy Engine** is a rule-based governance system for BRAiN that controls agent permissions, resource access, and action authorization. It provides:

- **Rule-Based Evaluation** - Priority-ordered policy rules with flexible conditions
- **Multi-Effect System** - ALLOW, DENY, WARN, AUDIT effects
- **Dynamic Policies** - Runtime policy creation, update, and deletion
- **Integration with Foundation** - Double-check safety layer
- **Comprehensive Operators** - `==`, `!=`, `>`, `<`, `contains`, `matches`, `in`
- **Default Policies** - Admin full access, Guest read-only

---

## Architecture

```
Policy Engine
├── Schemas (schemas.py)
│   ├── PolicyEffect (ALLOW, DENY, WARN, AUDIT)
│   ├── PolicyCondition (field, operator, value)
│   ├── PolicyRule (conditions + effect + priority)
│   ├── Policy (collection of rules)
│   ├── PolicyEvaluationContext (agent, action, environment)
│   └── PolicyEvaluationResult (allowed, effect, reason)
│
├── Service (service.py)
│   ├── PolicyEngine
│   │   ├── evaluate() - Main evaluation logic
│   │   ├── _rule_matches() - Condition matching
│   │   ├── _condition_matches() - Operator evaluation
│   │   └── _check_foundation() - Safety double-check
│   ├── Policy CRUD
│   │   ├── create_policy()
│   │   ├── get_policy()
│   │   ├── update_policy()
│   │   └── delete_policy()
│   └── Metrics
│       └── get_stats()
│
└── API (router.py)
    ├── POST /evaluate - Evaluate action (raises 403 on deny)
    ├── POST /test-rule - Test evaluation (no exceptions)
    ├── GET /stats - System statistics
    ├── GET /policies - List all policies
    ├── GET /policies/{id} - Get policy by ID
    ├── POST /policies - Create new policy
    ├── PUT /policies/{id} - Update policy
    └── DELETE /policies/{id} - Delete policy
```

---

## Key Concepts

### 1. Policies

A **Policy** is a collection of rules that govern agent behavior.

```python
Policy(
    policy_id="robot_safety_policy",
    name="Robot Safety Policy",
    version="1.0.0",
    description="Safety rules for robot operations",
    rules=[...],
    default_effect=PolicyEffect.DENY,
    enabled=True
)
```

### 2. Rules

A **PolicyRule** defines conditions and an effect.

```python
PolicyRule(
    rule_id="low_battery_deny",
    name="Deny Movement on Low Battery",
    effect=PolicyEffect.DENY,
    conditions=[
        PolicyCondition(
            field="environment.battery_level",
            operator=PolicyConditionOperator.LESS_THAN,
            value=20
        )
    ],
    priority=100
)
```

**Priority**: Higher priority rules are evaluated first (1000 = highest, 0 = lowest)

### 3. Conditions

**PolicyCondition** compares a field against a value using an operator.

```python
PolicyCondition(
    field="agent_role",          # Supports dot notation
    operator=PolicyConditionOperator.EQUALS,
    value="admin"
)
```

**Supported Operators**:
- `EQUALS` (`==`) - Exact match
- `NOT_EQUALS` (`!=`) - Not equal
- `GREATER_THAN` (`>`) - Numeric comparison
- `LESS_THAN` (`<`) - Numeric comparison
- `CONTAINS` - Substring match
- `MATCHES` - Regex match
- `IN` - List membership

**Field Notation**:
- Direct: `agent_role`, `action`, `resource`
- Nested: `environment.battery_level`, `params.speed`, `agent.type`

### 4. Effects

**PolicyEffect** determines the outcome when a rule matches:

- **ALLOW** - Explicitly allow the action
- **DENY** - Explicitly deny the action
- **WARN** - Allow but log a warning
- **AUDIT** - Allow but require audit trail

### 5. Evaluation Flow

```
1. Collect active policies
2. Collect all enabled rules from active policies
3. Sort rules by priority (highest first)
4. Iterate through rules:
   a. Check if all conditions match (AND logic)
   b. If match found:
      - Apply effect (ALLOW/DENY/WARN/AUDIT)
      - Optional: Double-check with Foundation layer
      - Return result
5. If no match:
   - Apply default_effect from policy
```

---

## API Endpoints

### POST `/api/policy/evaluate`

Evaluate an action against all policies. **Raises 403 on deny.**

**Request:**
```json
{
  "agent_id": "robot_001",
  "agent_role": "fleet_member",
  "action": "robot.move",
  "resource": "warehouse_zone_a",
  "environment": {
    "battery_level": 80,
    "time": "daytime"
  },
  "params": {
    "distance": 10,
    "speed": 2
  }
}
```

**Response (200 OK - Allowed):**
```json
{
  "allowed": true,
  "effect": "allow",
  "matched_rule": "fleet_member_basic_movement",
  "matched_policy": "robot_safety_policy",
  "reason": "Allowed by rule 'Fleet Member Basic Movement'",
  "warnings": [],
  "requires_audit": false
}
```

**Response (403 Forbidden - Denied):**
```json
{
  "detail": {
    "error": "Action denied by policy",
    "reason": "Denied by rule 'Low Battery Deny'"
  }
}
```

---

### POST `/api/policy/test-rule`

Test evaluation **without raising 403**. Use for testing policies.

**Request:** Same as `/evaluate`

**Response (200 OK - Even if denied):**
```json
{
  "allowed": false,
  "effect": "deny",
  "matched_rule": "guest_write_deny",
  "matched_policy": "guest_read_only",
  "reason": "Denied by rule 'Guest Write Deny'"
}
```

---

### GET `/api/policy/stats`

Get policy system statistics.

**Response:**
```json
{
  "total_policies": 3,
  "active_policies": 3,
  "total_rules": 8,
  "total_evaluations": 1523,
  "total_allows": 1204,
  "total_denies": 315,
  "total_warnings": 4
}
```

---

### GET `/api/policy/policies`

List all policies.

**Response:**
```json
{
  "total": 2,
  "policies": [
    {
      "policy_id": "admin_full_access",
      "name": "Admin Full Access",
      "version": "1.0.0",
      "description": "Admins have unrestricted access",
      "rules": [...],
      "default_effect": "deny",
      "enabled": true,
      "created_at": "2024-12-19T10:00:00Z",
      "updated_at": "2024-12-19T10:00:00Z"
    },
    {
      "policy_id": "guest_read_only",
      "name": "Guest Read-Only Access",
      ...
    }
  ]
}
```

---

### GET `/api/policy/policies/{policy_id}`

Get a specific policy by ID.

**Response (200 OK):**
```json
{
  "policy_id": "admin_full_access",
  "name": "Admin Full Access",
  "version": "1.0.0",
  ...
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Policy not found: nonexistent_id"
}
```

---

### POST `/api/policy/policies`

Create a new policy.

**Request:**
```json
{
  "name": "Custom Policy",
  "version": "1.0.0",
  "description": "My custom policy",
  "rules": [
    {
      "rule_id": "my_rule",
      "name": "My Rule",
      "effect": "allow",
      "conditions": [
        {
          "field": "agent_role",
          "operator": "==",
          "value": "custom_role"
        }
      ],
      "priority": 50,
      "enabled": true
    }
  ],
  "default_effect": "deny",
  "enabled": true
}
```

**Response (201 Created):**
```json
{
  "policy_id": "policy_3",
  "name": "Custom Policy",
  "version": "1.0.0",
  ...
}
```

---

### PUT `/api/policy/policies/{policy_id}`

Update an existing policy.

**Request:**
```json
{
  "name": "Updated Policy Name",
  "enabled": false
}
```

**Response (200 OK):**
```json
{
  "policy_id": "policy_3",
  "name": "Updated Policy Name",
  "enabled": false,
  ...
}
```

---

### DELETE `/api/policy/policies/{policy_id}`

Delete a policy.

**Response (204 No Content):**
(Empty body)

**Response (404 Not Found):**
```json
{
  "detail": "Policy not found: nonexistent_id"
}
```

---

### GET `/api/policy/default-policies`

Get list of default policy IDs.

**Response:**
```json
["admin_full_access", "guest_read_only"]
```

---

## Default Policies

### 1. Admin Full Access

**Policy ID:** `admin_full_access`

Admins can do anything.

```python
PolicyRule(
    rule_id="admin_allow_all",
    name="Admin Allow All",
    effect=PolicyEffect.ALLOW,
    conditions=[
        PolicyCondition(field="agent_role", operator="==", value="admin")
    ],
    priority=1000  # Highest priority
)
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/policy/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "admin_001",
    "agent_role": "admin",
    "action": "delete_everything"
  }'
# ✅ ALLOWED (admin can do anything)
```

---

### 2. Guest Read-Only

**Policy ID:** `guest_read_only`

Guests can only read data, no modifications allowed.

**Rules:**
1. **Guest Read Allow** (priority 50):
   - Conditions: role="guest" AND action contains "read"
   - Effect: ALLOW

2. **Guest Write Deny** (priority 100):
   - Conditions: role="guest" AND action in ["write", "delete", "update", "create"]
   - Effect: DENY

**Examples:**
```bash
# ✅ ALLOWED (guest can read)
curl -X POST http://localhost:8000/api/policy/evaluate \
  -d '{"agent_id": "guest_001", "agent_role": "guest", "action": "data.read"}'

# ❌ DENIED (guest cannot write)
curl -X POST http://localhost:8000/api/policy/evaluate \
  -d '{"agent_id": "guest_001", "agent_role": "guest", "action": "data.write"}'
# Returns 403 Forbidden
```

---

## Usage Examples

### Example 1: Battery Safety Policy

Create a policy that denies robot movement when battery is low.

```python
from app.modules.policy.service import get_policy_engine
from app.modules.policy.schemas import (
    PolicyCreateRequest,
    PolicyRule,
    PolicyCondition,
    PolicyConditionOperator,
    PolicyEffect,
)

engine = get_policy_engine()

# Create policy
request = PolicyCreateRequest(
    name="Battery Safety Policy",
    version="1.0.0",
    description="Prevent movement on low battery",
    rules=[
        PolicyRule(
            rule_id="low_battery_deny",
            name="Deny Movement on Low Battery",
            effect=PolicyEffect.DENY,
            conditions=[
                PolicyCondition(
                    field="action",
                    operator=PolicyConditionOperator.CONTAINS,
                    value="move"
                ),
                PolicyCondition(
                    field="environment.battery_level",
                    operator=PolicyConditionOperator.LESS_THAN,
                    value=20
                )
            ],
            priority=200
        )
    ],
    default_effect=PolicyEffect.DENY
)

policy = await engine.create_policy(request)
```

**Test:**
```python
from app.modules.policy.schemas import PolicyEvaluationContext

# Battery = 15% → DENIED
context = PolicyEvaluationContext(
    agent_id="robot_001",
    action="robot.move",
    environment={"battery_level": 15}
)
result = await engine.evaluate(context)
# result.allowed = False
# result.reason = "Denied by rule 'Deny Movement on Low Battery'"

# Battery = 80% → Default effect (DENY if no other rules match)
context2 = PolicyEvaluationContext(
    agent_id="robot_001",
    action="robot.move",
    environment={"battery_level": 80}
)
result2 = await engine.evaluate(context2)
# result2.allowed = False (default_effect = DENY)
```

---

### Example 2: Time-Based Access Control

Create a policy that only allows operations during business hours.

```python
request = PolicyCreateRequest(
    name="Business Hours Policy",
    version="1.0.0",
    rules=[
        PolicyRule(
            rule_id="business_hours_allow",
            name="Allow During Business Hours",
            effect=PolicyEffect.ALLOW,
            conditions=[
                PolicyCondition(
                    field="environment.hour",
                    operator=PolicyConditionOperator.GREATER_THAN,
                    value=8
                ),
                PolicyCondition(
                    field="environment.hour",
                    operator=PolicyConditionOperator.LESS_THAN,
                    value=18
                )
            ],
            priority=100
        ),
        PolicyRule(
            rule_id="after_hours_deny",
            name="Deny After Hours",
            effect=PolicyEffect.DENY,
            conditions=[
                PolicyCondition(
                    field="environment.hour",
                    operator=PolicyConditionOperator.IN,
                    value=[0, 1, 2, 3, 4, 5, 6, 7, 19, 20, 21, 22, 23]
                )
            ],
            priority=150  # Higher priority than allow
        )
    ],
    default_effect=PolicyEffect.DENY
)
```

---

### Example 3: Dangerous Action Blacklist

Prevent specific dangerous actions.

```python
request = PolicyCreateRequest(
    name="Dangerous Actions Policy",
    version="1.0.0",
    rules=[
        PolicyRule(
            rule_id="blacklist_deny",
            name="Deny Blacklisted Actions",
            effect=PolicyEffect.DENY,
            conditions=[
                PolicyCondition(
                    field="action",
                    operator=PolicyConditionOperator.IN,
                    value=[
                        "delete_all",
                        "format_disk",
                        "drop_database",
                        "sudo_rm_rf"
                    ]
                )
            ],
            priority=1000  # Highest priority
        )
    ],
    default_effect=PolicyEffect.DENY
)
```

---

### Example 4: Regex Pattern Matching

Use regex to match action patterns.

```python
PolicyRule(
    rule_id="api_write_deny",
    name="Deny API Write Operations",
    effect=PolicyEffect.DENY,
    conditions=[
        PolicyCondition(
            field="action",
            operator=PolicyConditionOperator.MATCHES,
            value=r"^api\.(create|update|delete)"  # Matches api.create, api.update, api.delete
        )
    ],
    priority=100
)
```

---

### Example 5: Multi-Condition AND Logic

All conditions must match (AND logic).

```python
PolicyRule(
    rule_id="restricted_zone_deny",
    name="Deny Access to Restricted Zone",
    effect=PolicyEffect.DENY,
    conditions=[
        PolicyCondition(field="resource", operator="==", value="restricted_zone"),
        PolicyCondition(field="agent_role", operator="!=", value="security"),
        PolicyCondition(field="environment.clearance_level", operator="<", value=5)
    ],
    priority=200
)
# Only denies if ALL three conditions match
```

---

## Integration with Foundation Layer

The Policy Engine can **double-check** decisions with the Foundation layer for safety.

**How it works:**
1. Policy evaluates and returns ALLOW
2. Policy Engine calls Foundation `validate_action()`
3. If Foundation denies, override Policy decision to DENY

**Code:**
```python
# In service.py
async def evaluate(self, context: PolicyEvaluationContext) -> PolicyEvaluationResult:
    # ... policy evaluation ...

    if result.allowed and FOUNDATION_AVAILABLE:
        foundation_check = await self._check_foundation(context)
        if not foundation_check:
            logger.warning("⚠️ Policy allowed but Foundation blocked - DENY")
            result.allowed = False
            result.effect = PolicyEffect.DENY
            result.reason += " (overridden by Foundation safety check)"

    return result
```

**Use Case:**
- Policy: "Admin can do anything" → ALLOW
- Foundation: "Action 'format_disk' is blacklisted" → DENY
- **Final Result:** DENY (Foundation overrides)

---

## Testing

### Run All Tests

```bash
# All policy tests
pytest backend/tests/test_policy_engine.py -v

# Specific test
pytest backend/tests/test_policy_engine.py::TestPolicyEngine::test_admin_allow_all -v

# With coverage
pytest backend/tests/test_policy_engine.py --cov=app.modules.policy
```

### Test Categories

1. **Service Tests (Unit)**
   - Engine initialization
   - Admin allow all
   - Guest read/write
   - Custom policies
   - Priority ordering
   - Condition operators
   - CRUD operations
   - Statistics

2. **API Tests (Integration)**
   - GET /stats
   - GET /policies
   - POST /policies
   - POST /evaluate (allow)
   - POST /evaluate (deny - 403)
   - POST /test-rule (no 403)
   - GET /policies/{id}
   - GET /default-policies

3. **Edge Cases**
   - No policies configured
   - Empty conditions (always match)
   - Non-existent policy

---

## Performance Considerations

### In-Memory Storage

**Current:** Policies stored in-memory (dict)

**Limitations:**
- Lost on restart
- No persistence
- Not suitable for production at scale

**TODO:** Migrate to PostgreSQL with SQLAlchemy

### Evaluation Performance

**Complexity:** O(n * m) where:
- n = number of active policies
- m = average rules per policy

**Optimization:**
- Rules sorted once per evaluation (not per policy)
- Short-circuit evaluation (first match wins)
- Conditions evaluated lazily (stop on first false)

**Benchmark (rough):**
- 10 policies, 5 rules each → ~0.5ms per evaluation
- 100 policies, 10 rules each → ~5ms per evaluation

---

## Migration Path

### Current (v2.0.0)
- In-memory storage
- Singleton PolicyEngine
- Manual policy creation via API

### Future (v2.1.0+)
- PostgreSQL storage via SQLAlchemy
- Policy versioning (migrations)
- Policy import/export (JSON/YAML)
- Policy templates
- Audit log for all evaluations
- WebSocket notifications on policy changes

---

## Security Considerations

### 1. Default Deny

Always use `default_effect=PolicyEffect.DENY` unless you have a specific reason.

```python
# ✅ GOOD - Secure by default
Policy(
    default_effect=PolicyEffect.DENY,
    ...
)

# ❌ BAD - Insecure default
Policy(
    default_effect=PolicyEffect.ALLOW,  # Everything allowed if no rules match!
    ...
)
```

### 2. Priority Ordering

**Critical:** Higher priority rules override lower priority.

```python
# ❌ DANGEROUS - Low priority deny can be bypassed
PolicyRule(rule_id="deny_dangerous", effect=DENY, priority=10)
PolicyRule(rule_id="allow_admin", effect=ALLOW, priority=100)
# Admin rule matches first → dangerous action allowed!

# ✅ SAFE - High priority deny
PolicyRule(rule_id="deny_dangerous", effect=DENY, priority=1000)
PolicyRule(rule_id="allow_admin", effect=ALLOW, priority=100)
```

### 3. Regex Safety

Use anchors in regex patterns to avoid partial matches.

```python
# ❌ DANGEROUS - Matches "my_api.delete" as well as "api.delete"
PolicyCondition(field="action", operator=MATCHES, value="api.delete")

# ✅ SAFE - Only matches "api.delete"
PolicyCondition(field="action", operator=MATCHES, value=r"^api\.delete$")
```

### 4. Foundation Integration

Always enable Foundation double-check for critical systems.

```python
# In config
FOUNDATION_AVAILABLE = True  # Enable safety double-check
```

---

## Troubleshooting

### Issue 1: Policy Not Matching

**Symptom:** Expected rule doesn't match

**Debug:**
1. Check rule priority (higher priority rules may match first)
2. Check ALL conditions (must all be true)
3. Check field names (case-sensitive, use dot notation correctly)
4. Enable debug logging:
   ```python
   logger.setLevel("DEBUG")
   ```

**Example:**
```python
# Wrong field name
PolicyCondition(field="agent.role", ...)  # ❌ Should be "agent_role"

# Correct
PolicyCondition(field="agent_role", ...)  # ✅
```

---

### Issue 2: 403 Error on Valid Request

**Symptom:** `/evaluate` returns 403 but should allow

**Debug:**
1. Use `/test-rule` instead to see decision without 403
2. Check matched_rule and reason in response
3. Verify default_effect (may be DENY)

**Example:**
```bash
# Use test-rule endpoint for debugging
curl -X POST http://localhost:8000/api/policy/test-rule \
  -d '{"agent_id": "test", "action": "test"}'

# Returns decision without raising 403
```

---

### Issue 3: Foundation Override

**Symptom:** Policy allows but final result is DENY

**Reason:** Foundation layer blocked the action

**Solution:** Check Foundation blacklist and safety patterns

```bash
curl http://localhost:8000/api/foundation/config
# Check "blocked_actions" list
```

---

## Best Practices

### 1. Start with Default Deny
```python
Policy(default_effect=PolicyEffect.DENY)
```

### 2. Use Descriptive Names
```python
# ✅ GOOD
PolicyRule(
    rule_id="fleet_member_basic_movement",
    name="Fleet Member Basic Movement",
    description="Allow fleet members to move within assigned zones"
)

# ❌ BAD
PolicyRule(rule_id="rule1", name="Rule 1")
```

### 3. Organize by Priority Ranges
- 900-1000: Critical security rules (blacklists)
- 500-899: Role-based access rules
- 100-499: Resource-specific rules
- 0-99: Default/fallback rules

### 4. Test Policies Before Deployment
```python
# Always test with /test-rule before using /evaluate
```

### 5. Document Complex Conditions
```python
PolicyRule(
    rule_id="complex_rule",
    description="Deny API writes during maintenance window (2-4 AM) except for admins"
)
```

---

## API Client Examples

### Python
```python
import httpx

async def check_permission(agent_id: str, action: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/policy/evaluate",
            json={
                "agent_id": agent_id,
                "action": action
            }
        )

        if response.status_code == 200:
            print("✅ ALLOWED")
            return True
        elif response.status_code == 403:
            print("❌ DENIED")
            print(response.json()["detail"])
            return False
```

### JavaScript
```javascript
async function checkPermission(agentId, action) {
  const response = await fetch("http://localhost:8000/api/policy/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_id: agentId, action })
  });

  if (response.ok) {
    console.log("✅ ALLOWED");
    return true;
  } else if (response.status === 403) {
    const error = await response.json();
    console.log("❌ DENIED:", error.detail.reason);
    return false;
  }
}
```

### cURL
```bash
# Check permission
curl -X POST http://localhost:8000/api/policy/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "robot_001",
    "agent_role": "fleet_member",
    "action": "robot.move",
    "environment": {"battery_level": 80}
  }'

# Get statistics
curl http://localhost:8000/api/policy/stats

# List policies
curl http://localhost:8000/api/policy/policies

# Create policy
curl -X POST http://localhost:8000/api/policy/policies \
  -H "Content-Type: application/json" \
  -d @policy.json
```

---

## Changelog

### v2.0.0 (2024-12-19)
- ✅ Complete rule-based policy engine
- ✅ Default policies (admin, guest)
- ✅ 7 condition operators
- ✅ ALLOW, DENY, WARN, AUDIT effects
- ✅ Priority-based rule matching
- ✅ Foundation layer integration
- ✅ Full CRUD API
- ✅ Comprehensive test suite (20+ tests)
- ✅ In-memory storage (TODO: PostgreSQL)

### v1.0.0 (Previous)
- Legacy health/info endpoints only

---

## Resources

- **Tests:** `backend/tests/test_policy_engine.py`
- **Service:** `backend/app/modules/policy/service.py`
- **API:** `backend/app/modules/policy/router.py`
- **Schemas:** `backend/app/modules/policy/schemas.py`

---

**Version:** 2.0.0
**Last Updated:** 2024-12-19
**Author:** BRAiN Team

**Status:** ✅ Production Ready (in-memory mode)
**TODO:** Migrate to PostgreSQL for persistence
