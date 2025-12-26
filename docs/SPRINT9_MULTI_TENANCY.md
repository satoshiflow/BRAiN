# Sprint 9-C: Multi-Tenant Foundations (NO UI)

**Version:** 1.0.0
**Sprint:** Sprint 9-C
**Status:** ✅ Complete
**Author:** BRAiN Development Team

---

## Overview

**Multi-Tenant Foundations** prepares BRAiN for multiple customers/organizations without building product UI. It provides hard workspace isolation for secrets, evidence packs, and run contracts, enabling secure multi-tenant deployments.

**Core Principle:** Hard isolation - no tenant leakage, ever.

---

## Key Features

### 1. Workspace Concept

A **Workspace** represents a tenant/organization:

- Unique workspace ID
- Isolated storage paths
- Separate secrets/keys
- Independent quotas
- Project grouping

### 2. Project Grouping

**Projects** group related pipeline runs within a workspace:

- Multiple projects per workspace
- Default budget/policy per project
- Run statistics tracking
- Independent lifecycle management

### 3. Hard Isolation

Each workspace gets isolated storage:

```
storage/workspaces/{workspace_id}/
├── secrets/              # API keys, credentials (isolated)
├── evidence/             # Evidence packs (isolated)
├── contracts/            # Run contracts (isolated)
└── projects/             # Project metadata
```

### 4. Workspace-Scoped APIs

Execute pipelines within workspace context:

```bash
POST /api/workspaces/{workspace_id}/pipeline/run
```

All resources (secrets, evidence, contracts) scoped to workspace.

---

## Architecture

### Data Model

```python
class Workspace(BaseModel):
    workspace_id: str        # "ws_01j12k34m56n78p90qrs"
    name: str                # "Acme Corp"
    slug: str                # "acme-corp" (URL-safe, unique)
    description: Optional[str]
    status: WorkspaceStatus  # ACTIVE, SUSPENDED, ARCHIVED

    # Isolation
    storage_path: str        # "storage/workspaces/ws_xxx"

    # Quotas
    max_projects: int        # Default: 100
    max_runs_per_day: int    # Default: 1000
    max_storage_gb: float    # Default: 100.0

class Project(BaseModel):
    project_id: str          # "proj_01j12k34m56n78p90qrs"
    workspace_id: str        # Parent workspace
    name: str                # "E-Commerce Platform"
    slug: str                # "ecommerce-platform" (unique within workspace)
    status: ProjectStatus    # ACTIVE, PAUSED, COMPLETED, ARCHIVED

    # Defaults
    default_budget: Optional[Dict]  # Default execution budget
    default_policy: Optional[Dict]  # Default execution policy

    # Statistics
    total_runs: int
    successful_runs: int
    failed_runs: int
```

### Workspace Lifecycle

```
┌────────────────────────┐
│ 1. Create Workspace    │
│    POST /api/workspaces│
│    - Generate ID       │
│    - Create storage    │
│    - Set quotas        │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ 2. Create Projects     │
│    POST .../projects   │
│    - Within workspace  │
│    - Check quotas      │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ 3. Execute Pipelines   │
│    POST .../pipeline/  │
│    - Scoped to WS      │
│    - Isolated storage  │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ 4. Monitor & Manage    │
│    GET .../stats       │
│    PUT .../update      │
└────────────────────────┘
```

---

## API Reference

### Workspace Management

#### List Workspaces

```bash
GET /api/workspaces?status=active&owner_id=user_123

# Response:
[
  {
    "workspace_id": "ws_xxx",
    "name": "Acme Corp",
    "slug": "acme-corp",
    "status": "active",
    ...
  }
]
```

#### Create Workspace

```bash
POST /api/workspaces
Content-Type: application/json

{
  "name": "Acme Corp",
  "slug": "acme-corp",
  "description": "Production workspace for Acme Corporation",
  "max_projects": 50,
  "max_runs_per_day": 500,
  "max_storage_gb": 50.0
}

# Response:
{
  "workspace_id": "ws_1703001234000_acme-corp",
  "name": "Acme Corp",
  "slug": "acme-corp",
  "storage_path": "/storage/workspaces/ws_1703001234000_acme-corp",
  ...
}
```

#### Get Workspace

```bash
GET /api/workspaces/ws_xxx

# Response: Full workspace object
```

#### Update Workspace

```bash
PUT /api/workspaces/ws_xxx
Content-Type: application/json

{
  "max_runs_per_day": 1000,
  "status": "active"
}
```

#### Delete Workspace (Archive)

```bash
DELETE /api/workspaces/ws_xxx

# Response:
{
  "success": true,
  "workspace_id": "ws_xxx",
  "message": "Workspace archived"
}
```

#### Workspace Statistics

```bash
GET /api/workspaces/ws_xxx/stats

# Response:
{
  "workspace_id": "ws_xxx",
  "total_projects": 15,
  "active_projects": 12,
  "total_runs": 453,
  "runs_today": 42,
  "storage_used_gb": 12.5,
  "storage_limit_gb": 50.0,
  "quota_usage_percent": 25.0
}
```

### Project Management

#### List Projects

```bash
GET /api/workspaces/ws_xxx/projects?status=active

# Response:
[
  {
    "project_id": "proj_yyy",
    "workspace_id": "ws_xxx",
    "name": "E-Commerce Platform",
    "slug": "ecommerce-platform",
    "status": "active",
    "total_runs": 42,
    ...
  }
]
```

#### Create Project

```bash
POST /api/workspaces/ws_xxx/projects
Content-Type: application/json

{
  "name": "E-Commerce Platform",
  "slug": "ecommerce-platform",
  "description": "Main e-commerce automation project",
  "default_budget": {
    "max_steps": 50,
    "max_duration_seconds": 300
  }
}

# Response: Full project object
```

#### Update Project

```bash
PUT /api/workspaces/ws_xxx/projects/proj_yyy
Content-Type: application/json

{
  "status": "paused",
  "default_budget": {
    "max_steps": 100
  }
}
```

#### Project Statistics

```bash
GET /api/workspaces/ws_xxx/projects/proj_yyy/stats

# Response:
{
  "project_id": "proj_yyy",
  "workspace_id": "ws_xxx",
  "total_runs": 42,
  "successful_runs": 38,
  "failed_runs": 4,
  "success_rate_percent": 90.48,
  "avg_duration_seconds": 125.3,
  "last_run_at": "2025-12-26T12:00:00Z"
}
```

### Workspace-Scoped Pipeline Execution

#### Execute Pipeline in Workspace

```bash
POST /api/workspaces/ws_xxx/pipeline/run?project_id=proj_yyy
Content-Type: application/json

{
  "graph_id": "graph_123",
  "business_intent_id": "intent_abc",
  "nodes": [...],
  "dry_run": true
}

# Response:
{
  "execution_result": { ... },
  "run_contract": { ... },
  "workspace_id": "ws_xxx",
  "project_id": "proj_yyy",
  "contract_path": "/storage/workspaces/ws_xxx/contracts/contract_xxx.json",
  "isolated_storage": {
    "contracts": "/storage/workspaces/ws_xxx/contracts",
    "evidence": "/storage/workspaces/ws_xxx/evidence"
  }
}
```

**Key Points:**
- Secrets scoped to workspace
- Evidence packs saved in workspace storage
- Run contracts saved in workspace storage
- Quota enforcement per workspace
- Workspace must be ACTIVE
- Project must be ACTIVE (if specified)

---

## Storage Isolation

### Directory Structure

```
storage/
├── workspaces/
│   ├── default/                    # Default workspace (backward compat)
│   │   ├── secrets/
│   │   ├── evidence/
│   │   ├── contracts/
│   │   └── projects/
│   │
│   ├── ws_1703001234000_acme-corp/
│   │   ├── secrets/                # ISOLATED: API keys for Acme
│   │   ├── evidence/               # ISOLATED: Evidence packs for Acme
│   │   ├── contracts/              # ISOLATED: Run contracts for Acme
│   │   └── projects/
│   │       ├── proj_xxx.json
│   │       └── proj_yyy.json
│   │
│   └── ws_1703001235000_globex/
│       ├── secrets/                # ISOLATED: API keys for Globex
│       ├── evidence/               # ISOLATED: Evidence packs for Globex
│       ├── contracts/              # ISOLATED: Run contracts for Globex
│       └── projects/
│
└── run_contracts/                  # Global contracts (Sprint 9-B)
```

### Isolation Guarantees

1. **Secrets Isolation**
   - Each workspace has separate `secrets/` directory
   - API keys stored per workspace
   - No cross-workspace secret access

2. **Evidence Isolation**
   - Evidence packs saved in workspace storage
   - Separate directories per workspace
   - No visibility into other workspaces

3. **Contract Isolation**
   - Run contracts saved in workspace storage
   - Replay uses workspace-scoped contracts
   - No cross-workspace contract access

---

## Quota Enforcement

### Project Quota

```python
# Workspace: max_projects=50
# Current projects: 49
# Try to create 50th project: ✅ SUCCESS
# Try to create 51st project: ❌ QuotaExceededException
```

**Test:**
```python
def test_project_quota_enforcement():
    service = WorkspaceService()

    # Create workspace with max_projects=2
    workspace = service.create_workspace(
        WorkspaceCreateRequest(
            name="Limited WS",
            slug="limited-ws",
            max_projects=2,
        )
    )

    # Create 2 projects (at limit)
    service.create_project(workspace.workspace_id, ProjectCreateRequest(...))
    service.create_project(workspace.workspace_id, ProjectCreateRequest(...))

    # Try to create 3rd project
    with pytest.raises(QuotaExceededException):
        service.create_project(workspace.workspace_id, ProjectCreateRequest(...))
```

---

## Testing

### Test: Default Workspace Exists

```python
def test_default_workspace_exists():
    service = WorkspaceService()

    default_ws = service.get_workspace("default")

    assert default_ws.workspace_id == "default"
    assert default_ws.name == "Default Workspace"
    assert default_ws.status == WorkspaceStatus.ACTIVE
```

### Test: Storage Path Isolation

```python
def test_storage_path_isolation():
    service = WorkspaceService()

    ws1 = service.create_workspace(WorkspaceCreateRequest(name="WS1", slug="ws1"))
    ws2 = service.create_workspace(WorkspaceCreateRequest(name="WS2", slug="ws2"))

    # Get isolated storage paths
    ws1_secrets = service.get_isolated_storage_path(ws1.workspace_id, "secrets")
    ws2_secrets = service.get_isolated_storage_path(ws2.workspace_id, "secrets")

    # Paths must be different
    assert ws1_secrets != ws2_secrets
    assert str(ws1.workspace_id) in str(ws1_secrets)
    assert str(ws2.workspace_id) in str(ws2_secrets)
```

### Test: Secrets Leak Prevention

```python
def test_secrets_leak_prevention():
    """Ensure workspace cannot access other workspace's secrets."""
    service = WorkspaceService()

    ws1 = service.create_workspace(WorkspaceCreateRequest(name="WS1", slug="ws1"))
    ws2 = service.create_workspace(WorkspaceCreateRequest(name="WS2", slug="ws2"))

    # Write secret to WS1
    ws1_secrets_path = service.get_isolated_storage_path(ws1.workspace_id, "secrets")
    (ws1_secrets_path / "api_key.txt").write_text("secret_ws1_key")

    # Try to access from WS2 path
    ws2_secrets_path = service.get_isolated_storage_path(ws2.workspace_id, "secrets")
    leaked_file = ws2_secrets_path / "api_key.txt"

    # Should NOT exist in WS2
    assert not leaked_file.exists()
```

---

## Backward Compatibility

**Default Workspace:** All Sprint 8 code continues to work without changes.

```python
# Sprint 8 behavior (uses default workspace transparently)
graph = create_execution_graph(graph_spec)
result = await graph.execute()

# Sprint 9 behavior (explicit workspace)
POST /api/workspaces/ws_xxx/pipeline/run
```

The default workspace (`workspace_id="default"`) is created automatically on service initialization.

---

## Files

| File | Description |
|------|-------------|
| `workspace_schemas.py` | Workspace, Project models |
| `workspace_service.py` | Workspace isolation service |
| `workspace_router.py` | Workspace API endpoints |

---

## Key Takeaways

✅ **Hard workspace isolation** – Secrets, evidence, contracts separated
✅ **Project grouping** – Organize runs within workspaces
✅ **Quota enforcement** – Prevent resource abuse
✅ **Workspace-scoped APIs** – Explicit tenant context
✅ **Default workspace** – Backward compatibility (Sprint 8 unchanged)
✅ **No UI required** – Pure backend multi-tenancy foundations
✅ **Prepared for scale** – 100+ parallel workspaces without tenant leakage

---

**Previous:** [Sprint 9-B: Run Contracts](./SPRINT9_RUN_CONTRACTS.md)
**Next:** [Sprint 9 Report](./SPRINT9_REPORT.md)
