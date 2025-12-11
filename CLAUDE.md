# CLAUDE.md - AI Assistant Guide for BRAiN v2.0

**Version:** 2.0.0
**Last Updated:** 2025-12-11
**Purpose:** Comprehensive guide for AI assistants working with the BRAiN v2.0 codebase

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Philosophy: Myzelkapitalismus](#philosophy-myzelkapitalismus)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Modular Architecture](#modular-architecture)
6. [Core Modules](#core-modules)
7. [Development Patterns & Conventions](#development-patterns--conventions)
8. [Backend Architecture](#backend-architecture)
9. [Frontend Architecture](#frontend-architecture)
10. [API Reference](#api-reference)
11. [Development Workflow](#development-workflow)
12. [Testing](#testing)
13. [CI/CD Pipeline](#cicd-pipeline)
14. [Server Deployment](#server-deployment)
15. [Critical Rules for AI Assistants](#critical-rules-for-ai-assistants)
16. [Common Tasks & Examples](#common-tasks--examples)

---

## Project Overview

**BRAiN v2.0** (Base Repository for AI Networks) is a production-ready, modular Multi-Agent System inspired by biological principles and the philosophy of **Myzelkapitalismus** (Mycelial Capitalism).

### Key Features

- **🧩 Modular Architecture** - Plugin-based system similar to Odoo
- **🧠 Bio-Inspired Design** - Cortex (decision), Limbic (emotion), Stem (execution)
- **🔄 Event-Driven** - EventBus for inter-module communication
- **📦 Registry Pattern** - Dynamic module loading and discovery
- **🐳 Docker-First** - Consistent environments from dev to production
- **⚡ Async-First** - High concurrency with FastAPI + async/await
- **🛡️ Security-First** - Built-in immune system for threat detection
- **💰 Resource Economy** - Credits and karma-based reputation system

### Core Philosophy

BRAiN implements **Myzelkapitalismus** - an economic model inspired by mycelial networks:
- **Cooperation over Competition** - Agents collaborate to achieve common goals
- **Decentralized Decision-Making** - No central authority, emergent intelligence
- **Resource Sharing** - Credits system enables fair resource distribution
- **Reputation-Based Trust** - Karma scores determine agent reliability
- **Evolutionary Adaptation** - DNA system enables agent evolution

---

## Philosophy: Myzelkapitalismus

**Myzelkapitalismus** (Mycelial Capitalism) is the foundational philosophy of BRAiN, inspired by the interconnected, cooperative nature of mycelial networks in fungi.

### Core Principles

1. **Network-Centric** - Like mycelium, agents form interconnected networks
2. **Resource Flow** - Resources (credits) flow where needed, not hoarded
3. **Mutual Support** - Strong agents support weaker ones (via karma)
4. **Emergent Intelligence** - Collective intelligence emerges from simple rules
5. **Adaptive Evolution** - System evolves through DNA mutations

### Implementation in BRAiN

- **Karma Module** - Tracks reputation, trust, and contribution
- **Credits Module** - Economic system for resource allocation
- **DNA Module** - Agent inheritance and evolution mechanisms
- **Missions Module** - Collaborative task orchestration
- **Supervisor Module** - Ensures network health and fairness

---

## Technology Stack

### Backend
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | FastAPI | 0.115+ | REST API framework |
| Language | Python | 3.11+ | Backend logic |
| ASGI Server | Uvicorn | 0.30+ | ASGI web server |
| Database | PostgreSQL | 16 | Persistent storage |
| Cache/Queue | Redis | 7 | State management, queues |
| Vector DB | Qdrant | Latest | Embeddings (optional) |
| Schema | Pydantic | 2.0+ | Data validation |
| HTTP Client | httpx | Latest | Async HTTP requests |
| Logging | JSON Logger | Latest | Structured logging |
| Scheduler | APScheduler | 3.10+ | Background tasks |
| Testing | pytest | Latest | Unit/integration tests |

### Frontend
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | Next.js | 14 | React framework (App Router) |
| Language | TypeScript | 5.4+ | Type safety |
| React | React | 19 | UI library |
| Styling | Tailwind CSS | 3.4+ | Utility-first CSS |
| UI Library | shadcn/ui | Latest | Component primitives |
| Icons | Lucide React | Latest | Icon library |
| Build Tool | Turbopack | Latest | Fast bundler |

### Infrastructure
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Container | Docker | Containerization |
| Orchestration | Docker Compose | Multi-service orchestration |
| Web Server | Nginx | Reverse proxy, SSL termination |
| CI/CD | GitHub Actions | Automated testing, deployment |

---

## Project Structure

```
BRAiN/
├── backend/                    # Python FastAPI backend
│   ├── app/                   # Main application
│   │   ├── main.py           # FastAPI entry point
│   │   ├── api/              # API layer
│   │   │   ├── routes/       # API endpoints (auto-discovered)
│   │   │   └── models/       # API models
│   │   ├── core/             # Core utilities
│   │   │   ├── config.py     # Settings management
│   │   │   ├── lifecycle.py  # App lifecycle (startup/shutdown)
│   │   │   └── events.py     # EventBus (inter-module communication)
│   │   ├── modules/          # Core modules (built-in)
│   │   │   ├── karma/        # Reputation & trust system
│   │   │   │   ├── router.py # API routes
│   │   │   │   ├── schemas.py # Pydantic models
│   │   │   │   └── core/
│   │   │   │       └── service.py # Business logic
│   │   │   ├── dna/          # Agent inheritance & evolution
│   │   │   ├── immune/       # Security & threat detection
│   │   │   ├── missions/     # Task orchestration
│   │   │   ├── credits/      # Resource economy
│   │   │   ├── policy/       # Policy management
│   │   │   ├── supervisor/   # System supervision
│   │   │   ├── threats/      # Threat tracking
│   │   │   └── metrics/      # System metrics
│   │   └── workers/          # Background workers
│   ├── modules/              # External modules (plugins)
│   │   └── example_module/
│   │       └── manifest.json # Module metadata
│   ├── tests/                # pytest test suite
│   ├── Dockerfile            # Multi-stage build
│   └── requirements.txt      # Python dependencies
│
├── frontend/                  # Frontend applications
│   ├── control_deck/         # Admin/Control Center (Next.js 14)
│   │   ├── app/              # App Router pages
│   │   │   ├── layout.tsx   # Root layout
│   │   │   ├── page.tsx     # Dashboard
│   │   │   ├── agents/      # Agents management
│   │   │   ├── missions/    # Missions dashboard
│   │   │   ├── karma/       # Karma visualization
│   │   │   └── settings/    # Settings pages
│   │   ├── components/       # React components
│   │   │   ├── ui/          # shadcn/ui primitives
│   │   │   └── features/    # Feature components
│   │   ├── lib/             # Utilities
│   │   │   ├── api.ts       # API client
│   │   │   └── utils.ts     # Helper functions
│   │   ├── Dockerfile        # Production build
│   │   └── package.json
│   │
│   └── axe_ui/              # Auxiliary Execution Engine UI
│       ├── app/             # App Router pages
│       ├── components/      # React components
│       ├── lib/             # Utilities
│       ├── Dockerfile
│       └── package.json
│
├── nginx/                    # Nginx reverse proxy
│   ├── nginx.conf
│   └── Dockerfile
│
├── docs/                     # Documentation
│   ├── ARCHITECTURE.md       # System architecture
│   └── WORKFLOWS-GUIDE.md    # CI/CD workflows
│
├── .github/                  # GitHub configuration
│   ├── workflows/           # CI/CD workflows
│   │   ├── frontend-ci.yml  # Frontend tests
│   │   ├── backend-ci.yml   # Backend tests
│   │   ├── build.yml        # Docker builds
│   │   ├── deploy.yml       # Deployment
│   │   └── release.yml      # Releases
│   ├── copilot-instructions.md # AI assistant guide
│   └── CODEOWNERS           # Code ownership
│
├── docker-compose.yml        # Development orchestration
├── .env.example              # Environment template
├── DEVELOPMENT.md            # Development setup guide
├── CHANGELOG.md              # Version history
└── README.md                 # User-facing documentation
```

---

## Modular Architecture

### Design Philosophy

BRAiN v2.0 implements a **modular plugin architecture** similar to **Odoo**:

1. **Core System** - Minimal, stable base (FastAPI, EventBus, Registry)
2. **Built-In Modules** - Essential modules in `app/modules/` (karma, dna, immune, etc.)
3. **External Modules** - Optional plugins in `backend/modules/` (community/custom)
4. **Event-Driven Communication** - Modules communicate via EventBus
5. **Dynamic Loading** - Modules auto-discovered and registered at startup

### Module Anatomy

Every module follows this structure:

```
module_name/
├── __init__.py              # Module exports
├── router.py                # FastAPI routes
├── schemas.py               # Pydantic request/response models
├── core/
│   ├── service.py          # Business logic
│   ├── models.py           # Database models (optional)
│   └── events.py           # Event handlers (optional)
├── manifest.json            # Module metadata (external modules)
└── ui_manifest.py          # Frontend integration (optional)
```

### Module Registration

**Built-In Modules** (in `app/modules/`):
```python
# app/main.py
from app.modules.karma.router import router as karma_router
from app.modules.dna.router import router as dna_router

app.include_router(karma_router)
app.include_router(dna_router)
```

**External Modules** (in `backend/modules/`):
```json
// backend/modules/my_module/manifest.json
{
  "name": "my_module",
  "version": "1.0.0",
  "description": "My custom module",
  "depends": ["karma", "dna"],
  "author": "Your Name",
  "license": "MIT"
}
```

### Inter-Module Communication

**Option 1: Direct Service Injection**
```python
# modules/karma/core/service.py
class KarmaService:
    def __init__(self, dna_service: DNAService):
        self._dna = dna_service

    def compute_score(self, agent_id: str, metrics: KarmaMetrics):
        score = self._calculate_score(metrics)
        self._dna.update_karma(agent_id, score)  # Call DNA module
        return score
```

**Option 2: Event-Driven (Recommended)**
```python
# modules/karma/core/service.py
from app.core.events import event_bus

class KarmaService:
    def compute_score(self, agent_id: str, metrics: KarmaMetrics):
        score = self._calculate_score(metrics)

        # Emit event - other modules can listen
        event_bus.emit("KARMA_UPDATED", {
            "agent_id": agent_id,
            "score": score,
            "timestamp": datetime.utcnow()
        })

        return score

# modules/dna/core/events.py
from app.core.events import event_bus

@event_bus.on("KARMA_UPDATED")
def handle_karma_update(data: dict):
    agent_id = data["agent_id"]
    score = data["score"]
    # Update DNA snapshot
    update_karma_in_dna(agent_id, score)
```

---

## Core Modules

### 1. Karma Module (`app/modules/karma/`)

**Purpose:** Reputation & trust scoring system implementing Myzelkapitalismus principles

**Features:**
- Calculate karma scores based on multiple metrics
- Track agent reputation over time
- Integrate with DNA module for evolutionary feedback

**API Endpoints:**
- `POST /api/karma/agents/{agent_id}/score` - Compute karma score

**Key Models:**
```python
class KarmaMetrics(BaseModel):
    success_rate: float              # 0.0 - 1.0
    avg_latency_ms: float            # Average response time
    policy_violations: int           # Number of policy violations
    user_rating_avg: float           # 1.0 - 5.0
    credit_consumption_per_task: float

class KarmaScore(BaseModel):
    agent_id: str
    score: float                     # 0.0 - 100.0
    computed_at: datetime
    details: KarmaMetrics
```

### 2. DNA Module (`app/modules/dna/`)

**Purpose:** Agent inheritance & evolution mechanisms

**Features:**
- Create DNA snapshots (agent state/configuration)
- Mutate agent DNA (evolution)
- Track DNA history (lineage)

**API Endpoints:**
- `POST /api/dna/snapshot` - Create DNA snapshot
- `POST /api/dna/agents/{agent_id}/mutate` - Mutate agent DNA
- `GET /api/dna/agents/{agent_id}/history` - Get DNA history

**Key Models:**
```python
class AgentDNASnapshot(BaseModel):
    agent_id: str
    version: int
    parent_version: Optional[int]
    created_at: datetime
    llm_provider: str
    model: str
    temperature: float
    system_prompt: str
    tools: List[str]
    karma_score: float

class MutateDNARequest(BaseModel):
    temperature_delta: Optional[float] = None
    system_prompt_append: Optional[str] = None
    add_tools: Optional[List[str]] = None
    remove_tools: Optional[List[str]] = None
```

### 3. Immune Module (`app/modules/immune/`)

**Purpose:** Security & threat detection system

**Features:**
- Detect malicious inputs (injection, XSS, etc.)
- Rate limiting
- Anomaly detection
- Threat scoring

**API Endpoints:**
- `POST /api/immune/validate` - Validate input
- `GET /api/immune/health` - Get immune system health

**Key Concepts:**
- **Cortex** - Decision-making layer (rules, policies)
- **Limbic** - Emotional/intuitive layer (anomaly detection)
- **Stem** - Execution layer (blocking, logging)

### 4. Missions Module (`app/modules/missions/`)

**Purpose:** Task orchestration and management

**Features:**
- Create and manage missions
- Assign agents to missions
- Track mission progress
- Mission history and analytics

**API Endpoints:**
- `POST /api/missions/create` - Create mission
- `GET /api/missions/{mission_id}` - Get mission status
- `POST /api/missions/{mission_id}/assign` - Assign agent

### 5. Credits Module (`app/modules/credits/`)

**Purpose:** Resource economy & token management

**Features:**
- Credit allocation and consumption
- Transaction history
- Budget management
- Cost estimation

**API Endpoints:**
- `POST /api/credits/allocate` - Allocate credits
- `POST /api/credits/consume` - Consume credits
- `GET /api/credits/balance/{agent_id}` - Get balance

### 6. Policy Module (`app/modules/policy/`)

**Purpose:** Policy management and enforcement

**Features:**
- Define agent policies
- Validate actions against policies
- Policy versioning
- Audit logging

### 7. Supervisor Module (`app/modules/supervisor/`)

**Purpose:** System supervision and monitoring

**Features:**
- Agent health checks
- System metrics
- Alert management
- Auto-recovery

### 8. Threats Module (`app/modules/threats/`)

**Purpose:** Threat tracking and response

**Features:**
- Log detected threats
- Threat analytics
- Response coordination
- Integration with immune system

### 9. Metrics Module (`app/modules/metrics/`)

**Purpose:** System-wide metrics and analytics

**Features:**
- Performance metrics
- Usage analytics
- Trend analysis
- Reporting

---

## Development Patterns & Conventions

### Backend Conventions

#### File Naming
- **Python files:** `snake_case.py`
- **Classes:** `PascalCase`
- **Functions/variables:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private members:** `_leading_underscore`
- **Tests:** `test_feature_name.py`

#### Import Organization
```python
# Standard library
from __future__ import annotations
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

# Third-party
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

# Local - absolute imports
from app.core.config import get_settings
from app.modules.karma.schemas import KarmaMetrics
from app.modules.dna.core.service import DNAService
```

#### Type Hints
Always include type hints for parameters and return values:
```python
async def get_mission(mission_id: str) -> Optional[Mission]:
    """Retrieve a mission by ID."""
    # ...
```

#### Async/Await Pattern
**Rule:** All I/O operations MUST be async.

```python
# ✅ GOOD
async def fetch_data() -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return response.json()

# ❌ BAD - blocking I/O
def fetch_data() -> Dict[str, Any]:
    response = requests.get(url)  # Blocks event loop!
    return response.json()
```

#### Error Handling Strategy
1. **API Routes:** Catch exceptions, return structured JSON responses
2. **Services:** Let exceptions bubble up, log at appropriate level
3. **Never expose raw exceptions to users**

```python
@router.post("/agents/{agent_id}/score")
def compute_agent_karma(agent_id: str, metrics: KarmaMetrics) -> KarmaScore:
    try:
        return karma_service.compute_score(agent_id, metrics)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to compute karma for {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

#### Logging
Use structured JSON logging:
```python
import logging

logger = logging.getLogger(__name__)

logger.info("Mission created", extra={
    "mission_id": mission.id,
    "agent_id": agent_id,
    "priority": mission.priority
})
```

### Frontend Conventions

#### File Naming
- **Components:** `PascalCase.tsx` (e.g., `AgentCard.tsx`)
- **Pages:** `page.tsx` (App Router convention)
- **Layouts:** `layout.tsx` (App Router convention)
- **Utilities:** `camelCase.ts` or `kebab-case.ts`
- **Hooks:** `useCamelCase.ts` (e.g., `useAgents.ts`)

#### Import Organization
```typescript
// React
"use client";  // If needed
import { useState, useEffect } from "react";

// Third-party
import { cn } from "@/lib/utils";

// Components
import { Button } from "@/components/ui/button";
import { AgentCard } from "@/components/features/agent-card";

// Utilities
import { api } from "@/lib/api";
```

#### Component Structure
```typescript
"use client";

import { useState } from "react";

interface MyComponentProps {
  title: string;
  onAction?: () => void;
}

export function MyComponent({ title, onAction }: MyComponentProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-2xl font-bold">{title}</h2>
      {/* ... */}
    </div>
  );
}
```

#### Styling with Tailwind
Use utility classes with semantic patterns:
```tsx
<div className="brain-card">
  <div className="brain-card-header">
    <h2 className="brain-card-title">Title</h2>
  </div>
  <div className="flex flex-col gap-4 p-4">
    {/* Content */}
  </div>
</div>
```

Common patterns:
- Spacing: `gap-2`, `gap-4`, `gap-6`, `p-4`, `px-6`, `py-3`
- Layout: `flex`, `flex-col`, `grid`, `grid-cols-2`
- Responsive: `md:flex-row`, `lg:grid-cols-3`

---

## Backend Architecture

### Auto-Discovery Pattern

**Routes:** All modules in `app/api/routes/` with a `router` attribute are automatically included.

**`app/api/routes/__init__.py`:**
```python
import importlib
import pkgutil
from fastapi import FastAPI, APIRouter

def include_all_routers(app: FastAPI, base_prefix: str = "") -> None:
    from . import health  # Ensure package is discovered
    from app.api import routes

    for _, module_name, _ in pkgutil.iter_modules(routes.__path__):
        module = importlib.import_module(f"app.api.routes.{module_name}")
        router = getattr(module, "router", None)
        if isinstance(router, APIRouter):
            app.include_router(router)
```

**Adding a new route:**
1. Create `app/api/routes/my_feature.py`
2. Define router:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/my-feature", tags=["my-feature"])

@router.get("/info")
def get_info():
    return {"name": "My Feature", "version": "1.0"}
```
3. **That's it!** The router is automatically included on startup.

### Application Lifecycle

**`app/core/lifecycle.py`:**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("BRAiN starting up...")
    await initialize_database()
    await start_background_workers()

    yield

    # Shutdown
    logger.info("BRAiN shutting down...")
    await stop_background_workers()
    await close_database_connections()
```

### Configuration Management

**`app/core/config.py`:**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # App
    app_name: str = "BRAiN v2.0"
    environment: str = "development"

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

_settings: Optional[Settings] = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

---

## Frontend Architecture

### App Router Structure (Next.js 14)

**ControlDeck** (`frontend/control_deck/app/`):
```
app/
├── layout.tsx              # Root layout
├── page.tsx                # Dashboard homepage
├── agents/
│   ├── page.tsx           # Agents list
│   └── [id]/page.tsx      # Agent detail
├── missions/
│   ├── page.tsx           # Missions dashboard
│   └── [id]/page.tsx      # Mission detail
├── karma/
│   └── page.tsx           # Karma visualization
└── settings/
    ├── page.tsx           # Settings overview
    └── llm/page.tsx       # LLM configuration
```

### API Client Pattern

**`lib/api.ts`:**
```typescript
const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

export const api = {
  get: apiGet,
  post: apiPost,
  put: apiPut,
  delete: apiDelete,
};
```

---

## API Reference

### System Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root info |
| GET | `/health` | Global health check |

### Karma System (`/api/karma`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/karma/agents/{agent_id}/score` | Compute karma score |

### DNA System (`/api/dna`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/dna/snapshot` | Create DNA snapshot |
| POST | `/api/dna/agents/{agent_id}/mutate` | Mutate agent DNA |
| GET | `/api/dna/agents/{agent_id}/history` | Get DNA history |

### Immune System (`/api/immune`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/immune/validate` | Validate input for threats |
| GET | `/api/immune/health` | Immune system health |

---

## Development Workflow

### Docker-First Development

**BRAiN v2.0 uses Docker exclusively** for development and production.

**Why Docker-First?**
- ✅ Consistent environments across all machines
- ✅ No Python virtual environment conflicts
- ✅ No Node.js version conflicts
- ✅ Matches production exactly
- ✅ Easy onboarding for new developers

**No `.venv` or `node_modules` in Git!**

### Setup

**1. Clone Repository:**
```bash
git clone https://github.com/satoshiflow/BRAiN.git
cd BRAiN
git checkout v2
```

**2. Environment Configuration:**
```bash
cp backend/.env.example backend/.env
# Edit .env with your values (defaults work for local dev)
```

**3. Start All Services:**
```bash
docker-compose up --build
```

Services available at:
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- ControlDeck: http://localhost:3000
- AXE UI: http://localhost:3001

### Development Cycle

**Backend Development:**
```bash
# 1. Make changes in backend/app/
vim backend/app/modules/karma/core/service.py

# 2. Rebuild container
docker-compose build backend

# 3. Restart service
docker-compose restart backend

# 4. Test endpoint
curl http://localhost:8000/api/karma/agents/test/score \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"success_rate": 0.95, "avg_latency_ms": 120, ...}'

# 5. Check logs
docker-compose logs -f backend
```

**Frontend Development:**
```bash
# 1. Make changes in frontend/control_deck/
vim frontend/control_deck/app/page.tsx

# 2. Rebuild container (or use hot reload)
docker-compose build control_deck

# 3. Restart
docker-compose restart control_deck

# 4. Check in browser
open http://localhost:3000
```

### Local Development Without Docker

**Only if Docker is not available:**

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ControlDeck
cd frontend/control_deck
npm install
npm run dev

# AXE UI
cd frontend/axe_ui
npm install
npm run dev
```

**Note:** You need PostgreSQL 16 and Redis 7 running locally.

### Adding Dependencies

**Backend:**
```bash
cd backend
pip install new-package
pip freeze > requirements.txt
docker-compose build --no-cache backend
```

**Frontend:**
```bash
cd frontend/control_deck
npm install new-package
docker-compose build --no-cache control_deck
```

---

## Testing

### Backend Testing

**Framework:** pytest with async support

**Running Tests:**
```bash
# All tests
docker exec brain-backend pytest

# Specific test file
docker exec brain-backend pytest tests/test_karma.py

# With coverage
docker exec brain-backend pytest --cov=app

# Verbose
docker exec brain-backend pytest -v
```

**Test Structure:**
```python
# tests/test_karma.py
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_compute_karma(client):
    """Test karma computation endpoint."""
    response = client.post(
        "/api/karma/agents/test-agent/score",
        json={
            "success_rate": 0.95,
            "avg_latency_ms": 120,
            "policy_violations": 0,
            "user_rating_avg": 4.5,
            "credit_consumption_per_task": 5.0
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert 0 <= data["score"] <= 100
```

### Frontend Testing

**Recommended:** Jest + React Testing Library (not yet implemented)

---

## CI/CD Pipeline

### GitHub Workflows

BRAiN v2.0 has **9 automated workflows**:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **frontend-ci.yml** | Push/PR to `frontend/**` | ESLint, TypeScript, Build |
| **backend-ci.yml** | Push/PR to `backend/**` | Ruff, MyPy, Pytest |
| **lint-test.yml** | Push to main/v2 | Fast validation + security |
| **build.yml** | Push/PR, Manual | Docker multi-stage builds |
| **deploy.yml** | Push to main, Manual | Deploy to staging/production |
| **release.yml** | Tag push (`v*.*.*`) | Create GitHub release |
| **code-quality.yml** | Push to main, Weekly | Code complexity analysis |
| **scheduled-maintenance.yml** | Weekly (Mon 3am) | Security audits |
| **pull-request.yml** | PR open/edit | Validation, auto-labeling |

### Commit Conventions

Use **Conventional Commits** format:

```bash
# Feature
git commit -m "feat: Add karma scoring algorithm"

# Bug fix
git commit -m "fix: Resolve DNA mutation race condition"

# Documentation
git commit -m "docs: Update API reference for karma module"

# Refactor
git commit -m "refactor: Simplify event bus implementation"

# Test
git commit -m "test: Add integration tests for immune module"

# Chore
git commit -m "chore: Update dependencies"
```

**Format:**
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`, `revert`

---

## Critical Rules for AI Assistants

### 🚨 MUST FOLLOW

1. **Always use async/await for I/O operations in backend**
   - Database queries, Redis operations, HTTP requests MUST be async
   - Never use blocking I/O (e.g., `requests` library)

2. **Follow modular architecture**
   - New features go in `app/modules/`
   - Each module has `router.py`, `schemas.py`, `core/service.py`
   - Use EventBus for inter-module communication

3. **Type everything**
   - Backend: Type hints for all function parameters and return values
   - Frontend: TypeScript interfaces for all data structures
   - Never use `Any` or `any` unless absolutely necessary

4. **Handle errors gracefully**
   - Backend: Catch exceptions in routes, return structured JSON
   - Frontend: Handle loading and error states
   - Never expose raw exception details to users

5. **Use Docker for development**
   - No `.venv` or `node_modules` in Git
   - Test changes in Docker containers
   - Match production environment

6. **Follow Myzelkapitalismus principles**
   - Cooperation over competition
   - Decentralized decision-making
   - Resource sharing via credits
   - Reputation-based trust (karma)

7. **Log appropriately**
   - Use structured JSON logging
   - Include context (agent_id, mission_id, etc.)
   - Never log sensitive data (API keys, passwords)

8. **Test before committing**
   - Backend: Run pytest
   - Frontend: Check TypeScript errors (`npm run build`)
   - Test API endpoints manually

9. **Use Conventional Commits**
   - Format: `<type>(<scope>): <description>`
   - Examples: `feat: Add karma module`, `fix: Resolve DNA bug`

10. **Never commit secrets**
    - Use `.env` for configuration
    - Never hardcode API keys, passwords
    - Check `.gitignore` before committing

### ❌ NEVER DO

1. **Never use blocking I/O in async contexts**
   ```python
   # ❌ BAD
   async def fetch_data():
       return requests.get(url)  # Blocks event loop!

   # ✅ GOOD
   async def fetch_data():
       async with httpx.AsyncClient() as client:
           return await client.get(url)
   ```

2. **Never skip error handling**
   ```python
   # ❌ BAD
   @router.get("/data")
   async def get_data():
       return await fetch_from_db()  # What if it fails?

   # ✅ GOOD
   @router.get("/data")
   async def get_data():
       try:
           return await fetch_from_db()
       except Exception as e:
           logger.error(f"Failed to fetch data: {e}")
           raise HTTPException(status_code=500, detail="Failed to fetch data")
   ```

3. **Never use `any` type in TypeScript**
   ```typescript
   // ❌ BAD
   function process(data: any) { ... }

   // ✅ GOOD
   interface Data {
       id: string;
       value: number;
   }
   function process(data: Data) { ... }
   ```

4. **Never create modules outside the pattern**
   ```
   ❌ BAD: backend/app/my_random_feature.py
   ✅ GOOD: backend/app/modules/my_feature/router.py
   ```

5. **Never expose internal errors to users**
   ```python
   # ❌ BAD
   raise HTTPException(status_code=500, detail=str(exception))

   # ✅ GOOD
   logger.error(f"Internal error: {exception}")
   raise HTTPException(status_code=500, detail="Internal server error")
   ```

### ✅ BEST PRACTICES

1. **Use consistent naming**
   - Backend: `snake_case`
   - Frontend: `camelCase` for functions/variables, `PascalCase` for components
   - Be descriptive: `compute_karma_score()` not `calc_k()`

2. **Keep functions focused**
   - Single Responsibility Principle
   - Extract complex logic into separate functions
   - Aim for functions under 50 lines

3. **Document complex logic**
   - Docstrings for public APIs
   - Comments for non-obvious code (German for business logic, English for technical)
   - Keep comments up-to-date

4. **Use constants for magic values**
   ```python
   # ❌ BAD
   if score > 75:
       send_alert()

   # ✅ GOOD
   CRITICAL_KARMA_THRESHOLD = 75
   if score > CRITICAL_KARMA_THRESHOLD:
       send_alert()
   ```

5. **Optimize for readability**
   - Code is read more than written
   - Prefer explicit over clever
   - Use meaningful variable names

---

## Common Tasks & Examples

### Task 1: Create a New Module

**Goal:** Create a new `reputation` module

**Steps:**

1. **Create module structure:**
```bash
mkdir -p backend/app/modules/reputation/core
touch backend/app/modules/reputation/__init__.py
touch backend/app/modules/reputation/router.py
touch backend/app/modules/reputation/schemas.py
touch backend/app/modules/reputation/core/service.py
```

2. **Define schemas:**
```python
# backend/app/modules/reputation/schemas.py
from pydantic import BaseModel
from datetime import datetime

class ReputationScore(BaseModel):
    agent_id: str
    score: float
    calculated_at: datetime

class ReputationRequest(BaseModel):
    agent_id: str
    actions: List[str]
```

3. **Implement service:**
```python
# backend/app/modules/reputation/core/service.py
class ReputationService:
    def calculate_reputation(self, agent_id: str, actions: List[str]) -> float:
        # Business logic
        score = len(actions) * 10.0
        return min(100.0, score)
```

4. **Create router:**
```python
# backend/app/modules/reputation/router.py
from fastapi import APIRouter
from app.modules.reputation.schemas import ReputationScore, ReputationRequest
from app.modules.reputation.core.service import ReputationService

router = APIRouter(prefix="/api/reputation", tags=["REPUTATION"])
service = ReputationService()

@router.post("/calculate", response_model=ReputationScore)
def calculate_reputation(req: ReputationRequest) -> ReputationScore:
    score = service.calculate_reputation(req.agent_id, req.actions)
    return ReputationScore(
        agent_id=req.agent_id,
        score=score,
        calculated_at=datetime.utcnow()
    )
```

5. **Register module:**
```python
# backend/app/main.py
from app.modules.reputation.router import router as reputation_router

app.include_router(reputation_router)
```

6. **Test:**
```bash
docker-compose build backend
docker-compose restart backend

curl -X POST http://localhost:8000/api/reputation/calculate \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "test", "actions": ["action1", "action2"]}'
```

### Task 2: Add Event-Driven Communication

**Goal:** Make DNA module listen to karma updates

**Steps:**

1. **Define event in karma module:**
```python
# backend/app/modules/karma/core/service.py
from app.core.events import event_bus

class KarmaService:
    def compute_score(self, agent_id: str, metrics: KarmaMetrics) -> KarmaScore:
        score = self._calculate_score(metrics)

        # Emit event
        event_bus.emit("KARMA_UPDATED", {
            "agent_id": agent_id,
            "score": score,
            "timestamp": datetime.utcnow().isoformat()
        })

        return KarmaScore(agent_id=agent_id, score=score, ...)
```

2. **Listen in DNA module:**
```python
# backend/app/modules/dna/core/events.py
from app.core.events import event_bus
from app.modules.dna.core.service import dna_service

@event_bus.on("KARMA_UPDATED")
def handle_karma_update(data: dict):
    agent_id = data["agent_id"]
    score = data["score"]

    # Update DNA snapshot
    dna_service.update_karma(agent_id, score)

    logger.info(f"Updated karma in DNA for {agent_id}: {score}")
```

3. **Register event handler on startup:**
```python
# backend/app/core/lifecycle.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from app.modules.dna.core import events  # Register handlers

    yield

    # Shutdown
    pass
```

### Task 3: Add Frontend Page

**Goal:** Add karma visualization page

**Steps:**

1. **Create page:**
```bash
mkdir -p frontend/control_deck/app/karma
touch frontend/control_deck/app/karma/page.tsx
```

2. **Implement page:**
```typescript
// frontend/control_deck/app/karma/page.tsx
"use client";

import { useState, useEffect } from "react";

interface KarmaData {
  agent_id: string;
  score: number;
  computed_at: string;
}

export default function KarmaPage() {
  const [karmaData, setKarmaData] = useState<KarmaData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:8000/api/karma/leaderboard")
      .then(res => res.json())
      .then(data => {
        setKarmaData(data);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Karma Leaderboard</h1>

      <div className="grid gap-4">
        {karmaData.map(item => (
          <div key={item.agent_id} className="p-4 border rounded-lg">
            <div className="flex justify-between">
              <span className="font-semibold">{item.agent_id}</span>
              <span className="text-lg font-bold">{item.score.toFixed(1)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

3. **Add navigation:**
```typescript
// frontend/control_deck/app/layout.tsx
<nav>
  <Link href="/karma">Karma</Link>
</nav>
```

4. **Test:**
```bash
docker-compose build control_deck
docker-compose restart control_deck
open http://localhost:3000/karma
```

---

## Environment Variables Reference

See `backend/.env.example` for complete reference. Key variables:

```bash
# App
APP_NAME=BRAiN v2.0
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://brain:brain@postgres:5432/brain

# Redis
REDIS_URL=redis://redis:6379/0

# Security
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3001"]

# Logging
LOG_LEVEL=INFO
```

---

## Server Deployment

### Deployment Architecture

BRAiN v2.0 uses a **three-environment deployment strategy**:

```
┌─────────────────────────────────────────────────────┐
│  Server: brain.falklabs.de (46.224.37.114)         │
│                                                      │
│  /srv/dev/     → Development (Port 8001, 3001)     │
│  /srv/stage/   → Staging (Port 8002, 3003)         │
│  /srv/prod/    → Production (Port 8000, 3000)      │
│                                                      │
│  /opt/brain/   → Old Production (deprecated)        │
└─────────────────────────────────────────────────────┘
```

### Environment Mapping

| Environment | Domain | Backend | Frontend | AXE | Database | Purpose |
|-------------|--------|---------|----------|-----|----------|---------|
| **Development** | dev.brain.falklabs.de | 8001 | 3001 | 3002 | brain_dev | Active development |
| **Staging** | stage.brain.falklabs.de | 8002 | 3003 | 3004 | brain_stage | Pre-production testing |
| **Production** | brain.falklabs.de | 8000 | 3000 | 3001 | brain_prod | Live system |
| **Chat** | chat.falklabs.de | 8080 | - | - | openwebui_db | Open WebUI |

### Deployment Workflow

#### 1. Initial Server Setup (One-Time)

```bash
# SSH to server
ssh root@brain.falklabs.de

# Install Docker if not present
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
apt update && apt install docker-compose-plugin

# Install Certbot for SSL
apt install certbot python3-certbot-nginx
```

#### 2. Deploy Development Environment

```bash
# Create directory
mkdir -p /srv/dev
cd /srv/dev

# Clone v2 branch
git clone -b v2 https://github.com/satoshiflow/BRAiN.git .

# Create .env.dev
cat > .env.dev <<'EOF'
ENVIRONMENT=development
APP_NAME=BRAiN v2.0 Dev
POSTGRES_DB=brain_dev
POSTGRES_USER=brain
POSTGRES_PASSWORD=brain_dev_secure_password
DATABASE_URL=postgresql://brain:brain_dev_secure_password@postgres:5432/brain_dev
REDIS_URL=redis://redis:6379/0
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:3001","https://dev.brain.falklabs.de"]
LOG_LEVEL=DEBUG
EOF

# Start services
export ENVIRONMENT=dev
export ENV_FILE=.env.dev
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Wait for services
sleep 30

# Verify
docker ps | grep brain
curl http://localhost:8001/health
```

#### 3. Deploy Staging Environment

```bash
# Create directory
mkdir -p /srv/stage
cd /srv/stage

# Clone v2 branch
git clone -b v2 https://github.com/satoshiflow/BRAiN.git .

# Create .env.stage
cat > .env.stage <<'EOF'
ENVIRONMENT=staging
APP_NAME=BRAiN v2.0 Staging
POSTGRES_DB=brain_stage
POSTGRES_USER=brain
POSTGRES_PASSWORD=brain_stage_secure_password
DATABASE_URL=postgresql://brain:brain_stage_secure_password@postgres:5432/brain_stage
REDIS_URL=redis://redis:6379/0
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["https://stage.brain.falklabs.de"]
LOG_LEVEL=INFO
EOF

# Start services
export ENVIRONMENT=stage
export ENV_FILE=.env.stage
docker-compose -f docker-compose.yml -f docker-compose.stage.yml up -d --build

# Verify
docker ps | grep brain
curl http://localhost:8002/health
```

#### 4. Deploy Production Environment

```bash
# Create directory
mkdir -p /srv/prod
cd /srv/prod

# Clone v2 branch (or specific release tag)
git clone -b v2 https://github.com/satoshiflow/BRAiN.git .

# Create .env.prod (with strong passwords)
cat > .env.prod <<'EOF'
ENVIRONMENT=production
APP_NAME=BRAiN v2.0
POSTGRES_DB=brain_prod
POSTGRES_USER=brain
POSTGRES_PASSWORD=$(openssl rand -hex 16)
DATABASE_URL=postgresql://brain:STRONG_PASSWORD@postgres:5432/brain_prod
REDIS_URL=redis://redis:6379/0
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["https://brain.falklabs.de"]
LOG_LEVEL=WARNING
JWT_SECRET_KEY=$(openssl rand -hex 32)
EOF

# Start services
export ENVIRONMENT=prod
export ENV_FILE=.env.prod
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Verify
docker ps | grep brain
curl http://localhost:8000/health
```

### Nginx Configuration

#### 1. Install Modular Nginx Config

```bash
# From /srv/dev (after git pull)
cd /srv/dev

# Backup existing config
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup

# Copy modular config
cp nginx/nginx.conf /etc/nginx/nginx.conf
cp -r nginx/snippets /etc/nginx/
cp -r nginx/conf.d /etc/nginx/

# Test configuration
nginx -t

# Reload nginx
systemctl reload nginx
```

#### 2. Get SSL Certificates

```bash
# Development
certbot --nginx -d dev.brain.falklabs.de --non-interactive --agree-tos --email admin@falklabs.de

# Staging
certbot --nginx -d stage.brain.falklabs.de --non-interactive --agree-tos --email admin@falklabs.de

# Production (if not already configured)
certbot --nginx -d brain.falklabs.de --non-interactive --agree-tos --email admin@falklabs.de
```

#### 3. Auto-Renewal

Certbot auto-renewal is configured via systemd timer:

```bash
# Check renewal timer
systemctl status certbot.timer

# Test renewal (dry-run)
certbot renew --dry-run

# Manual renewal if needed
certbot renew
```

### DNS Configuration

Ensure DNS records point to server IP:

| Subdomain | Type | Value | Purpose |
|-----------|------|-------|---------|
| `dev.brain.falklabs.de` | A | 46.224.37.114 | Development |
| `stage.brain.falklabs.de` | A | 46.224.37.114 | Staging |
| `brain.falklabs.de` | A | 46.224.37.114 | Production |
| `chat.falklabs.de` | A | 46.224.37.114 | Open WebUI |

### Update Deployment

#### Update Development

```bash
cd /srv/dev
git pull origin v2
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
docker-compose logs -f backend
```

#### Update Staging

```bash
cd /srv/stage
git pull origin v2
docker-compose -f docker-compose.yml -f docker-compose.stage.yml up -d --build
docker-compose logs -f backend
```

#### Update Production (with downtime)

```bash
cd /srv/prod

# Backup database
docker exec brain-postgres-prod pg_dump -U brain brain_prod > backup_$(date +%Y%m%d).sql

# Pull latest
git pull origin v2

# Rebuild
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Monitor logs
docker-compose logs -f backend

# Test
curl https://brain.falklabs.de/api/health
```

### Monitoring & Logs

#### View Logs

```bash
# Development
cd /srv/dev
docker-compose logs -f backend
docker-compose logs -f control_deck

# Staging
cd /srv/stage
docker-compose logs -f backend

# Production
cd /srv/prod
docker-compose logs -f backend

# Nginx logs
tail -f /var/log/nginx/dev-brain-access.log
tail -f /var/log/nginx/stage-brain-access.log
tail -f /var/log/nginx/brain-access.log
```

#### Service Status

```bash
# Docker containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Nginx
systemctl status nginx

# Disk usage
df -h
docker system df

# Database size
docker exec brain-postgres-dev psql -U brain -d brain_dev -c "SELECT pg_size_pretty(pg_database_size('brain_dev'));"
```

### Backup & Restore

#### Database Backup

```bash
# Development
docker exec brain-postgres-dev pg_dump -U brain brain_dev > /backups/dev_$(date +%Y%m%d).sql

# Staging
docker exec brain-postgres-stage pg_dump -U brain brain_stage > /backups/stage_$(date +%Y%m%d).sql

# Production
docker exec brain-postgres-prod pg_dump -U brain brain_prod > /backups/prod_$(date +%Y%m%d).sql
```

#### Database Restore

```bash
# Stop application
docker-compose stop backend

# Restore
docker exec -i brain-postgres-dev psql -U brain brain_dev < /backups/dev_20251211.sql

# Start application
docker-compose start backend
```

### Rollback Strategy

If deployment fails:

```bash
# 1. Check which commit is currently deployed
cd /srv/prod
git log -1

# 2. Rollback to previous version
git log --oneline -10  # Find previous working commit
git checkout <previous-commit-hash>

# 3. Rebuild
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 4. Verify
curl https://brain.falklabs.de/api/health
```

### Performance Optimization

#### Docker Cleanup

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove unused networks
docker network prune

# Full cleanup (careful!)
docker system prune -a --volumes
```

#### Log Rotation

Configure log rotation for nginx and Docker logs:

```bash
# /etc/logrotate.d/nginx-brain
/var/log/nginx/dev-brain-*.log
/var/log/nginx/stage-brain-*.log
/var/log/nginx/brain-*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
```

### Security Checklist

- [ ] Strong passwords in `.env.prod`
- [ ] JWT secret keys generated
- [ ] SSL certificates valid
- [ ] Firewall configured (UFW)
- [ ] Docker daemon secured
- [ ] Regular backups scheduled
- [ ] Log monitoring enabled
- [ ] Rate limiting configured
- [ ] CORS properly configured
- [ ] Debug mode disabled in production

---

## Troubleshooting

### Backend won't start
```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Port 8000 already in use
lsof -i :8000
kill -9 <PID>

# 2. Database connection failed
docker-compose up -d postgres
docker-compose logs postgres
```

### Frontend build errors
```bash
# Clear cache
docker-compose down
docker-compose build --no-cache control_deck
docker-compose up control_deck
```

---

## Additional Resources

**Documentation:**
- `DEVELOPMENT.md` - Development setup guide
- `docs/ARCHITECTURE.md` - System architecture
- `docs/WORKFLOWS-GUIDE.md` - CI/CD workflows
- `CHANGELOG.md` - Version history

**Key Technologies:**
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js Docs](https://nextjs.org/docs)
- [Pydantic](https://docs.pydantic.dev/)
- [shadcn/ui](https://ui.shadcn.com/)

---

## Version History

**2.0.0** (2025-12-11)
- Modular architecture with plugin system
- Bio-inspired design (Cortex, Limbic, Stem)
- Event-driven inter-module communication
- Docker-first development
- 9 core modules (karma, dna, immune, missions, credits, policy, supervisor, threats, metrics)
- ControlDeck + AXE UI frontends
- 9 CI/CD workflows

---

**This guide is maintained for AI assistants. When making significant architectural changes, update this file accordingly.**
