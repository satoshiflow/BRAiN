# Genesis Agent System - Phase 1

**Version:** 2.0.0
**Status:** ✅ Production-Ready
**Last Updated:** 2026-01-02

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Security](#security)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

The Genesis Agent System is the **autonomous agent creation framework** for BRAiN. It enables controlled, secure, and auditable creation of new agents from DNA templates.

### What is Genesis?

Genesis is the "Agent Factory" - a specialized agent that creates other agents according to predefined DNA templates with customizable parameters. It enforces security whitelists, validates DNA schemas, tracks template integrity, and maintains a complete audit trail.

### Why Phase 1?

Phase 1 establishes the **deterministic, secure foundation** for agent creation:
- ✅ Template-based creation (no evolution yet)
- ✅ Security whitelist enforcement
- ✅ Complete audit trail
- ✅ Idempotency guarantees
- ✅ Budget protection
- ❌ No autonomous creation (Phase 4)
- ❌ No DNA mutation (Phase 2)
- ❌ No real quarantine (Phase 3)

---

## ✨ Features

### Core Capabilities

- **Template-Based Creation**: Create agents from predefined YAML templates
- **DNA Validation**: Comprehensive schema and business rule validation
- **Customization Whitelist**: Only approved fields can be modified
- **Idempotency**: Duplicate `request_id` returns existing agent
- **Template Integrity**: SHA256 hash tracking for reproducibility
- **Event Emission**: Dual-write to Redis + Audit Log
- **Budget Protection**: 20% reserve protection
- **Kill Switch**: `GENESIS_ENABLED` flag to disable all creation
- **Role-Based Access**: Requires `SYSTEM_ADMIN` role
- **Rate Limiting**: 10 requests per minute

### DNA Schema v2.0

Complete agent definition including:
- **Metadata**: Identity, lineage, template hash
- **Traits**: Base type, autonomy level, primary function
- **Skills**: Proficiencies and domains
- **Behavior**: Communication, decision-making, collaboration
- **Ethics**: Compliance flags (IMMUTABLE)
- **Capabilities**: Tools and network permissions
- **Runtime**: LLM configuration
- **Resources**: Budget limits
- **Mission Affinity**: Preferred task types

---

## 🏗️ Architecture

### Components

```
genesis_agent/
├── dna_schema.py         # Pydantic models (AgentDNA, etc.)
├── dna_validator.py      # Validation + whitelist enforcement
├── genesis_agent.py      # Core creation logic
├── events.py             # Event emission (Redis + Audit)
├── config.py             # Settings + kill switch
└── templates/            # YAML DNA templates
    ├── worker_base.yaml
    ├── analyst_base.yaml
    ├── builder_base.yaml
    └── genesis_base.yaml
```

### Data Flow

```
1. API Request → POST /api/genesis/create
2. Auth Check → SYSTEM_ADMIN required
3. Rate Limit → 10/minute
4. Kill Switch Check → GENESIS_ENABLED
5. Budget Check → Reserve protection (20%)
6. Idempotency Check → request_id lookup
7. Template Load → YAML parsing
8. Template Hash → SHA256 computation
9. Customizations → Whitelist validation + apply
10. DNA Validation → Schema + business rules
11. Governor Approval → Phase 1: stub (auto-approve)
12. Registry → Persist agent record
13. Events → Redis pub/sub + audit log
14. Budget Deduction → Track costs
15. Response → AgentCreationResponse
```

---

## 🚀 Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (with agents table)
- Redis 7+
- FastAPI project structure

### Database Migration

```bash
cd backend
alembic upgrade head  # Runs 005_genesis_agent_support migration
```

This creates/extends the `agents` table with:
- `status` (CREATED, QUARANTINED, ACTIVE, etc.)
- `dna_schema_version` (2.0)
- `template_hash` (sha256:...)
- `request_id` (for idempotency)

### Configuration

Create or update `.env`:

```bash
# Genesis Settings
GENESIS_ENABLED=true
GENESIS_RESERVE_RATIO=0.2
GENESIS_MAX_AGENTS_PER_HOUR=10
GENESIS_TEMPLATES_DIR=/path/to/templates  # Optional
```

---

## 📖 Usage

### Programmatic Usage

```python
from brain.agents.genesis_agent import GenesisAgent, InMemoryRegistry, InMemoryBudget
from brain.agents.genesis_agent.events import SimpleAuditLog
from brain.agents.genesis_agent.config import get_genesis_settings
import redis.asyncio as redis

# Initialize components
registry = InMemoryRegistry()
budget = InMemoryBudget(initial_credits=10000)
audit_log = SimpleAuditLog()
redis_client = await redis.from_url("redis://localhost:6379")
settings = get_genesis_settings()

# Create Genesis Agent
genesis = GenesisAgent(
    registry=registry,
    redis_client=redis_client,
    audit_log=audit_log,
    budget=budget,
    settings=settings
)

# Create a worker agent
dna = await genesis.create_agent(
    request_id="req-abc123",
    template_name="worker_base",
    customizations={
        "metadata.name": "worker_api_specialist",
        "skills[].domains": ["rest_api", "graphql"]
    }
)

print(f"Created agent: {dna.metadata.id}")
print(f"Name: {dna.metadata.name}")
print(f"Type: {dna.metadata.type}")
print(f"Template Hash: {dna.metadata.template_hash}")
```

### API Usage

#### Create Agent

```bash
curl -X POST http://localhost:8000/api/genesis/create \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req-abc123",
    "template_name": "worker_base",
    "customizations": {
      "metadata.name": "worker_api_specialist",
      "skills[].domains": ["rest_api", "graphql"]
    }
  }'
```

**Response:**
```json
{
  "success": true,
  "agent_id": "agent-xyz789",
  "status": "CREATED",
  "message": "Agent 'worker_api_specialist' created successfully",
  "cost": 10,
  "dna_hash": "abc123def456...",
  "template_hash": "sha256:def456ghi789..."
}
```

#### Get System Info

```bash
curl http://localhost:8000/api/genesis/info
```

**Response:**
```json
{
  "name": "Genesis Agent System",
  "version": "2.0.0",
  "enabled": true,
  "templates_available": ["worker_base", "analyst_base", "builder_base", "genesis_base"],
  "reserve_ratio": 0.2
}
```

#### List Templates

```bash
curl http://localhost:8000/api/genesis/templates
```

#### Get Customization Help

```bash
curl http://localhost:8000/api/genesis/customizations
```

---

## 📚 API Reference

### POST /api/genesis/create

Create a new agent from template.

**Authentication:** Required (SYSTEM_ADMIN)
**Rate Limit:** 10/minute

**Request Body:**
```typescript
{
  request_id: string;        // Unique ID for idempotency
  template_name: string;     // Template name (worker_base, etc.)
  customizations?: {         // Optional customizations
    [field_path: string]: any;
  };
}
```

**Responses:**
- `200` - Agent created successfully
- `400` - Validation error
- `403` - Insufficient permissions
- `429` - Rate limit or budget exceeded
- `503` - Genesis system disabled

### GET /api/genesis/info

Get system information (public endpoint).

### GET /api/genesis/templates

List available templates (public endpoint).

### GET /api/genesis/customizations

Get customization whitelist documentation (public endpoint).

### GET /api/genesis/budget?template_name=X

Check budget availability (requires auth).

### POST /api/genesis/killswitch

Toggle Genesis kill switch (requires auth).

**Request Body:**
```json
{
  "enabled": true
}
```

---

## 🔒 Security

### Authentication & Authorization

- **JWT Bearer Token**: Required for all creation endpoints
- **Role Requirement**: `SYSTEM_ADMIN` only
- **Token Validation**: Phase 1 stub (TODO: implement real JWT validation)

### Customization Whitelist

**Allowed:**
- `metadata.name` - Agent name (alphanumeric + underscore)
- `skills[].domains` - Add skill domains (append-only)
- `memory_seeds` - Add memory seeds (append-only)

**Forbidden (IMMUTABLE):**
- `ethics_flags` - Compliance settings
- `resource_limits` - Budget controls
- `capabilities` - Security permissions
- `runtime` - LLM configuration
- `metadata.created_by` - Creator attribution
- All other fields

### Immutable Fields

Per EU AI Act Art. 16 and DSGVO Art. 25:
- `ethics_flags.human_override` must always be `"always_allowed"`
- `metadata.created_by` must always be `"genesis_agent"`

### Budget Protection

- **Reserve Ratio**: 20% of credits protected
- **Pre-Flight Check**: Budget validated before creation
- **Event Emission**: Budget exceeded events logged

### Kill Switch

```bash
# Disable Genesis system
export GENESIS_ENABLED=false

# Or via API
curl -X POST http://localhost:8000/api/genesis/killswitch \
  -H "Authorization: Bearer TOKEN" \
  -d '{"enabled": false}'
```

---

## 🧪 Testing

### Run Tests

```bash
cd backend
pytest backend/brain/agents/genesis_agent/tests/ -v
```

### Test Coverage

```bash
pytest backend/brain/agents/genesis_agent/tests/ --cov=backend.brain.agents.genesis_agent --cov-report=html
```

### Key Test Cases

- ✅ DNA schema validation
- ✅ Template loading and hash computation
- ✅ Customization whitelist enforcement
- ✅ Idempotency (duplicate request_id)
- ✅ Event emission (Redis + Audit)
- ✅ Budget reserve protection
- ✅ Kill switch enforcement
- ✅ Template integrity verification

---

## 🐛 Troubleshooting

### Genesis system disabled

**Error:** `503 Service Unavailable - Genesis system disabled`

**Solution:**
```bash
export GENESIS_ENABLED=true
# Or update .env file
```

### Insufficient budget

**Error:** `429 Too Many Requests - Insufficient budget`

**Solution:**
- Check available credits: `GET /api/genesis/budget?template_name=worker_base`
- Increase budget allocation
- Adjust reserve ratio (not recommended in production)

### Template not found

**Error:** `TemplateNotFoundError: Template not found: custom_template`

**Solution:**
- Verify template exists in `templates/` directory
- Check template name spelling
- Ensure `.yaml` extension

### Validation error

**Error:** `400 Bad Request - Customization 'ethics_flags' is FORBIDDEN`

**Solution:**
- Check customization whitelist: `GET /api/genesis/customizations`
- Only modify allowed fields
- Remove forbidden customizations

### Authentication failed

**Error:** `401 Unauthorized - Invalid token`

**Solution:**
- Verify JWT token is valid
- Check token expiration
- Ensure `SYSTEM_ADMIN` role

---

## 📊 Metrics & Monitoring

### Events Emitted

All events published to `brain.events` Redis channel:

- `genesis.agent.create.requested`
- `genesis.agent.create.validated`
- `genesis.agent.create.registered`
- `genesis.agent.create.failed`
- `genesis.agent.template.loaded`
- `genesis.agent.customizations.applied`
- `genesis.system.killswitch.triggered`
- `genesis.system.budget.exceeded`
- `genesis.agent.idempotency.hit`

### Audit Trail

All events persisted to audit log for compliance.

---

## 🗺️ Roadmap

### Phase 1 (Current)
- ✅ Template-based creation
- ✅ DNA validation
- ✅ Security whitelist
- ✅ Audit trail
- ✅ Budget protection

### Phase 2 (Future)
- ⏳ DNA mutation engine
- ⏳ Skill-based customization
- ⏳ Cost optimization

### Phase 3 (Future)
- ⏳ Real Governor approval
- ⏳ Quarantine testing
- ⏳ Population balancing

### Phase 4 (Future)
- ⏳ Autonomous creation
- ⏳ Skill-gap detection
- ⏳ KARMA inheritance

---

## 👥 Contributing

Genesis Agent is part of the BRAiN framework. For contribution guidelines, see the main BRAiN repository.

---

## 📄 License

Part of the BRAiN framework. See LICENSE file in root repository.

---

## 📞 Support

For issues and questions:
- GitHub Issues: [satoshiflow/BRAiN](https://github.com/satoshiflow/BRAiN/issues)
- Email: admin@brain.falklabs.de

---

**Built with ❤️ for the BRAiN ecosystem**
