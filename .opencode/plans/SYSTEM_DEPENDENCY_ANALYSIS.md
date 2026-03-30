# BRAiN System - Abhängigkeitsanalyse und Hardening Plan

**Datum:** 29.03.2026
**Status:** ✅ ABGESCHLOSSEN

---

## 1. IST-ZUSTAND: Vorhandene Tabellen (41)

```
admin_invitations
alembic_version
audit_events
axe_chat_messages
axe_chat_sessions
axe_worker_runs
brain_parameters
brain_states
capability_definitions
control_plane_events
coordination_zones
fleet_tasks
fleets
fred_patches
fred_tickets
invitations
neural_synapses
provider_bindings
purpose_evaluations
refresh_tokens
robots
routing_decisions
skill_definitions
skill_runs
skills
synapse_executions
users
```

## 2. SOLL-ZUSTAND: Fehlende Tabellen (~100)

### Kritisch (System nicht funktionsfähig)
| Tabelle | Modul | Status |
|---------|-------|--------|
| tasks | task_queue | FEHLT |
| mission_templates | missions | FEHLT |
| provider_accounts | provider_portal | FEHLT |
| provider_credentials | provider_portal | FEHLT |
| provider_models | provider_portal | FEHLT |
| agent_credentials | agent_management | FEHLT |
| agents | agent_management | FEHLT |
| service_accounts | auth | FEHLT |

### Hoch (Funktionale Einschränkungen)
| Tabelle | Modul | Status |
|---------|-------|--------|
| axe_identities | axe_identity | FEHLT |
| axe_knowledge_documents | axe_knowledge | FEHLT |
| domain_agent_configs | domain_agents | FEHLT |
| evaluation_results | skill_evaluator | FEHLT |
| skill_optimizer_recommendations | skill_optimizer | FEHLT |

### Mittel (Monitoring/Governance)
| Tabelle | Modul | Status |
|---------|-------|--------|
| health_checks | health_monitor | FEHLT |
| health_check_history | health_monitor | FEHLT |
| evolution_proposals | evolution_control | FEHLT |
| experience_records | experience_layer | FEHLT |
| insight_candidates | insight_layer | FEHLT |

---

## 3. AKTIONSP lan

### Phase 1: Kritische Tabellen erstellen

```sql
-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_key VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(64),
    owner_scope VARCHAR(100),
    payload JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    scheduled_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Mission Templates
CREATE TABLE IF NOT EXISTS mission_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(64),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template JSONB DEFAULT '{}',
    version INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Provider Accounts
CREATE TABLE IF NOT EXISTS provider_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(64),
    provider_key VARCHAR(255) NOT NULL,
    provider_name VARCHAR(255),
    account_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Provider Credentials
CREATE TABLE IF NOT EXISTS provider_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(64),
    provider_account_id UUID,
    credential_key VARCHAR(255) NOT NULL,
    encrypted_value TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Provider Models
CREATE TABLE IF NOT EXISTS provider_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(64),
    provider_key VARCHAR(255) NOT NULL,
    model_id VARCHAR(255) NOT NULL,
    model_name VARCHAR(255),
    capabilities JSONB DEFAULT '[]',
    status VARCHAR(50) DEFAULT 'active',
    cost_per_1k_input DECIMAL(10,6),
    cost_per_1k_output DECIMAL(10,6),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Service Accounts
CREATE TABLE IF NOT EXISTS service_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    public_key TEXT,
    permissions JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agents
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(64),
    agent_key VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    description TEXT,
    agent_type VARCHAR(50),
    capabilities JSONB DEFAULT '[]',
    config JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Phase 2: AXE & Domain Agents

```sql
-- AXE Identities
CREATE TABLE IF NOT EXISTS axe_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(64),
    identity_key VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    avatar_url VARCHAR(512),
    capabilities JSONB DEFAULT '[]',
    config JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Domain Agent Configs
CREATE TABLE IF NOT EXISTS domain_agent_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(64),
    domain VARCHAR(100) NOT NULL,
    agent_key VARCHAR(255) NOT NULL,
    config JSONB DEFAULT '{}',
    routing_policy JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Evaluation Results
CREATE TABLE IF NOT EXISTS evaluation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(64),
    skill_run_id UUID,
    evaluation_type VARCHAR(50),
    score DECIMAL(5,4),
    passed BOOLEAN,
    feedback JSONB DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 4. BEREITS IMPLEMENTIERTE FALLBACKS

| Variable | Wert | Status |
|----------|------|--------|
| AXE_CHAT_EXECUTION_PATH | direct | ✅ |
| AXE_CHAT_ALLOW_DIRECT_EXECUTION | true | ✅ |
| AXE_FUSION_ALLOW_LOCAL_FALLBACK | true | ✅ |
| AXE_FUSION_ALLOWED_DEV_IPS | 172.24.0.x | ✅ |

---

## 5. PRÜFLISTE

- [ ] Phase 1: Kritische Tabellen erstellen (7 Tables)
- [ ] Phase 2: AXE & Domain Agents Tabellen (3 Tables)
- [ ] ENV-Variablen für Mock-LLM setzen
- [ ] Backend neustarten
- [ ] Alle Seeders verifizieren

---

## 6. RISIKEN

1. Schema Drift zwischen Code und DB
2. Performance bei fehlenden Indizes
3. Ollama muss für echte LLM-Antworten laufen
