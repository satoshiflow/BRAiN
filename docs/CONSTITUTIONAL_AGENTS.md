# Constitutional Agents - Complete Guide

**Version:** 1.0.0
**Last Updated:** 2025-12-30
**Purpose:** Complete documentation for BRAiN's Constitutional Agent Framework

---

## Overview

The Constitutional Agent Framework implements DSGVO and EU AI Act compliance at the agent level. All agents follow constitutional principles and integrate with the SupervisorAgent for ethical oversight.

### Constitutional Principles

1. **Menschenwürde > Effizienz** - Human dignity over efficiency
2. **Privacy by Design** (DSGVO Art. 25) - Data protection built-in
3. **Human Oversight** (EU AI Act Art. 16) - Human-in-the-loop for HIGH/CRITICAL risk
4. **Transparency & Auditability** - All decisions must be traceable
5. **EU Sovereignty** - No US cloud dependencies without DPA

---

## Agents

### 1. SupervisorAgent 🛡️

**Location:** `backend/brain/agents/supervisor_agent.py` (665 lines)

**Purpose:** Constitutional Framework Guardian - oversees all agent actions

**Capabilities:**
- Risk-based supervision (LOW/MEDIUM/HIGH/CRITICAL)
- Policy Engine integration
- LLM constitutional checks
- Human-in-the-loop workflows
- Comprehensive audit trails

**Risk Levels:**
- **LOW**: Read-only operations, no side effects → Auto-approve via LLM
- **MEDIUM**: Write operations, reversible → Policy + LLM check
- **HIGH**: Critical operations, personal data → **Human approval required**
- **CRITICAL**: Irreversible, system-wide impact → **Human approval required**

**API Endpoints:**
```
POST /api/agent-ops/supervisor/supervise
GET  /api/agent-ops/supervisor/metrics
```

**Usage Example:**
```python
from backend.brain.agents.supervisor_agent import get_supervisor_agent
from backend.app.modules.supervisor.schemas import RiskLevel, SupervisionRequest

supervisor = get_supervisor_agent()

request = SupervisionRequest(
    requesting_agent="CoderAgent",
    action="generate_odoo_module",
    context={"uses_personal_data": True},
    risk_level=RiskLevel.HIGH,
    reason="Generate customer portal module"
)

response = await supervisor.supervise_action(request)

if response.approved:
    # Proceed with action
    pass
elif response.human_oversight_required:
    # Wait for human approval
    token = response.human_oversight_token
else:
    # Action denied
    print(f"Denied: {response.reason}")
```

**Compliance:**
- DSGVO Art. 22 (No automated decisions for HIGH risk)
- EU AI Act Art. 16 (Human oversight)

---

### 2. CoderAgent 💻

**Location:** `backend/brain/agents/coder_agent.py` (623 lines)

**Purpose:** Secure Code Generation with DSGVO Compliance

**Capabilities:**
- Odoo module generation (DSGVO-compliant)
- FastAPI endpoint generation
- Code validation (forbidden patterns)
- Risk assessment (personal data detection)
- Supervisor integration

**Forbidden Patterns:**
- `eval()`, `exec()`
- Hardcoded passwords/API keys
- Personal data storage without legal basis

**API Endpoints:**
```
POST /api/agent-ops/coder/generate-code
POST /api/agent-ops/coder/generate-odoo-module
```

**Usage Example:**
```python
from backend.brain.agents.coder_agent import get_coder_agent

coder = get_coder_agent()

result = await coder.generate_odoo_module({
    "name": "customer_portal",
    "purpose": "Customer self-service portal",
    "data_types": ["customer_email", "order_history"],
    "models": ["CustomerAccount", "OrderHistory"],
    "views": ["customer_portal_view"]
})

if result["success"]:
    code = result["meta"]["code"]
    # Code includes DSGVO header comments
else:
    print(f"Error: {result['error']}")
    # May require human approval if HIGH risk
```

**Compliance:**
- DSGVO Art. 5 (Data minimization)
- DSGVO Art. 6 (Legal basis for processing)
- DSGVO Art. 25 (Privacy by Design)

---

### 3. OpsAgent ⚙️

**Location:** `backend/brain/agents/ops_agent.py` (647 lines)

**Purpose:** Safe Operations & Deployment

**Capabilities:**
- Application deployment
- Database migrations
- Service configuration
- Health monitoring
- Automatic rollback

**Risk Assessment:**
- Production → CRITICAL
- Staging → HIGH
- Development → MEDIUM

**API Endpoints:**
```
POST /api/agent-ops/ops/deploy
POST /api/agent-ops/ops/rollback
GET  /api/agent-ops/ops/health/{app}/{env}
```

**Usage Example:**
```python
from backend.brain.agents.ops_agent import get_ops_agent

ops = get_ops_agent()

result = await ops.deploy_application(
    app_name="brain-backend",
    version="2.0.0",
    environment="production",
    config={"workers": 4}
)

if result["success"]:
    print(f"Deployed successfully")
    print(f"Backup ID: {result['meta']['backup_id']}")
else:
    print(f"Deployment failed: {result['error']}")
    # Automatic rollback triggered if health check fails
```

**Deployment Pipeline:**
1. Pre-deployment checks (disk, memory, dependencies)
2. Backup creation
3. Deployment execution
4. Health check
5. Rollback on failure (automatic)

---

### 4. ArchitectAgent 🏛️

**Location:** `backend/brain/agents/architect_agent.py` (662 lines)

**Purpose:** System Architecture & EU Compliance Auditor

**Capabilities:**
- Architecture review
- EU AI Act compliance checking
- DSGVO Privacy by Design validation
- Scalability assessment
- Security audit

**Compliance Checks:**
- EU AI Act Art. 5 (Prohibited practices)
- EU AI Act Art. 9-13 (High-risk AI requirements)
- DSGVO Art. 25 (Privacy by Design)
- DSGVO Art. 44-46 (International data transfers)

**API Endpoints:**
```
POST /api/agent-ops/architect/review
POST /api/agent-ops/architect/compliance-check
POST /api/agent-ops/architect/scalability-assessment
POST /api/agent-ops/architect/security-audit
```

**Usage Example:**
```python
from backend.brain.agents.architect_agent import get_architect_agent

architect = get_architect_agent()

result = await architect.review_architecture(
    system_name="ai-chatbot",
    architecture_spec={
        "uses_ai": True,
        "uses_personal_data": True,
        "components": ["chatbot-api", "nlp-engine", "database"],
        "external_dependencies": [
            {"name": "OpenAI", "location": "US", "has_dpa": False}
        ],
        "privacy_by_design": False,
        "risk_management_system": False
    },
    high_risk_ai=True
)

print(f"Compliance Score: {result['meta']['compliance_score']}/100")
print(f"Risk Level: {result['meta']['risk_level']}")

for violation in result['meta']['violations']:
    print(f"- {violation['regulation']}: {violation['description']}")
    print(f"  Recommendation: {violation['recommendation']}")
```

**Compliance Score:**
- 95-100: Excellent compliance
- 80-94: Good compliance, minor issues
- 60-79: Moderate compliance, several violations
- 0-59: Poor compliance, critical violations

---

### 5. AXEAgent 🤖

**Location:** `backend/brain/agents/axe_agent.py` (444 lines)

**Purpose:** Conversational System Assistant

**Capabilities:**
- Natural language chat
- System status monitoring
- Mission queries
- Log analysis
- Safe command execution

**API Endpoints:**
```
POST   /api/agent-ops/axe/chat
GET    /api/agent-ops/axe/system-status
DELETE /api/agent-ops/axe/history
```

**Usage Example:**
```python
from backend.brain.agents.axe_agent import get_axe_agent

axe = get_axe_agent()

result = await axe.chat(
    message="Wie viele Missionen laufen aktuell?",
    context={"user": "admin"},
    include_history=True
)

print(result["message"])
# → "Aktuell laufen 3 Missionen. Alle im Status 'running'..."
```

**Safe Commands:**
Only whitelisted commands allowed:
- `docker compose ps`
- `docker compose logs`
- `curl localhost:8000/health`
- `systemctl status`

---

## Agent Blueprints

Pre-configured templates for quick agent instantiation.

**Location:** `backend/brain/agents/agent_blueprints/`

**Available Blueprints:**
1. `supervisor_blueprint.py`
2. `coder_blueprint.py`
3. `ops_blueprint.py`
4. `architect_blueprint.py`

**Usage:**
```python
from backend.brain.agents.agent_blueprints.coder_blueprint import get_coder_config
from backend.brain.agents.coder_agent import CoderAgent

config = get_coder_config()
coder = CoderAgent(config=config)
```

---

## Testing

**Location:** `backend/tests/test_*_agent.py`

**Test Coverage:**
- `test_supervisor_agent.py` - 20+ tests
- `test_coder_agent.py` - 15+ tests
- `test_ops_agent.py` - 12+ tests
- `test_architect_agent.py` - 12+ tests

**Run Tests:**
```bash
# All agent tests
pytest backend/tests/test_*_agent.py

# Specific agent
pytest backend/tests/test_supervisor_agent.py -v

# With coverage
pytest backend/tests/test_*_agent.py --cov=backend/brain/agents
```

---

## Frontend Integration

**React Hooks:** (See Step 5)

```typescript
import { useSupervisor, useCoder, useOps, useArchitect, useAXE } from '@/hooks/useAgents';

// Example: Code generation
const { generateCode, isGenerating } = useCoder();

const handleGenerate = async () => {
  const result = await generateCode({
    spec: "Create a user authentication module",
    risk_level: "medium"
  });

  if (result.success) {
    console.log(result.meta.code);
  }
};
```

---

## Compliance Matrix

| Agent | DSGVO Arts. | EU AI Act Arts. | Risk Levels |
|-------|-------------|-----------------|-------------|
| Supervisor | 22 | 16 | LOW-CRITICAL |
| Coder | 5, 6, 17, 25 | - | LOW-HIGH |
| Ops | - | - | MEDIUM-CRITICAL |
| Architect | 25, 32, 35, 44-46 | 5, 9-16, 52 | - |
| AXE | - | - | LOW |

---

## Best Practices

### 1. Always Use Supervisor for HIGH/CRITICAL

```python
# ❌ BAD - Direct high-risk action
await ops.deploy_application(..., environment="production")

# ✅ GOOD - Via supervisor approval
request = SupervisionRequest(
    requesting_agent="OpsAgent",
    action="deploy_to_production",
    risk_level=RiskLevel.CRITICAL,
    ...
)
response = await supervisor.supervise_action(request)

if response.approved:
    await ops.deploy_application(...)
```

### 2. Validate Generated Code

```python
# Always validate before using
result = await coder.generate_code(spec)

validation = await coder.validate_code(result["meta"]["code"])

if not validation["valid"]:
    print(f"Issues: {validation['issues']}")
```

### 3. Check Compliance Before Deployment

```python
# Run architect review first
review = await architect.review_architecture(
    system_name="my-app",
    architecture_spec={...}
)

if review["meta"]["compliance_score"] < 80:
    print("Fix compliance issues before deploying")
```

---

## Troubleshooting

### Issue: Supervisor denies all actions

**Cause:** Policy Engine misconfigured or LLM offline

**Solution:**
```bash
# Check Policy Engine
curl http://localhost:8000/api/policy/stats

# Check LLM config
curl http://localhost:8000/api/llm/config
```

### Issue: Human approval stuck

**Cause:** No HITL workflow implemented yet

**Solution:** Check `response.human_oversight_token` and implement approval UI

### Issue: Code generation fails validation

**Cause:** Generated code contains forbidden patterns

**Solution:** Review validation errors and regenerate with stricter prompt

---

## Roadmap

- [ ] HITL approval UI in Control Deck
- [ ] Postgres storage for audit trails
- [ ] Policy Engine database integration
- [ ] Multi-language code generation
- [ ] Architecture visualization

---

## Resources

- EU AI Act: https://eur-lex.europa.eu/eli/reg/2024/1689
- DSGVO: https://eur-lex.europa.eu/eli/reg/2016/679
- BRAiN Documentation: `/docs/CLAUDE.md`
