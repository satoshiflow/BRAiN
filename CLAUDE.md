# CLAUDE.md - AI Assistant Guide for BRAiN

**Version:** 0.5.0
**Last Updated:** 2025-12-20
**Purpose:** Comprehensive guide for AI assistants working with the BRAiN codebase

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Development Patterns & Conventions](#development-patterns--conventions)
5. [Backend Architecture](#backend-architecture)
6. [Frontend Architecture](#frontend-architecture)
7. [API Reference](#api-reference)
8. [Development Workflow](#development-workflow)
9. [Testing](#testing)
10. [Critical Rules for AI Assistants](#critical-rules-for-ai-assistants)
11. [Common Tasks & Examples](#common-tasks--examples)

---

## Project Overview

**BRAiN** (Base Repository for AI Networks) is a production-ready AI agent framework featuring:

- **Multi-Agent System** with supervisor orchestration
- **Mission Queue System** with Redis-based priority scheduling
- **Conversational Interface** with multiple frontend applications
- **Modular Architecture** with 17+ specialized modules
- **LLM Integration** with runtime-configurable providers
- **Fleet Management** for multi-robot coordination (RYR integration)
- **Policy Engine** for rule-based governance and authorization
- **Generic API Client Framework** for external integrations
- **Real-time Updates** via WebSocket support
- **Database Migrations** with Alembic version control

**Core Philosophy:**
- Async-first design for high concurrency
- Type-safe end-to-end (Pydantic + TypeScript)
- Modular and extensible by design
- Event-driven architecture
- Observable with comprehensive health checks
- Enterprise-grade resilience patterns (circuit breaker, retry, rate limiting)

---

## Technology Stack

### Backend
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | FastAPI | Latest | REST API framework |
| Language | Python | 3.11+ | Backend logic |
| ASGI Server | Uvicorn | Latest | ASGI web server |
| Database | PostgreSQL | 15+ (pgvector) | Persistent storage + vectors |
| Migrations | Alembic | Latest | Database schema versioning |
| Cache/Queue | Redis | 7+ | Mission queue, state management |
| Vector DB | Qdrant | Latest | Embeddings and semantic memory |
| Schema | Pydantic | 2.0+ | Data validation |
| HTTP Client | httpx | Latest | Async HTTP requests |
| Logging | loguru | 0.7.3 | Structured logging |
| Testing | pytest | Latest | Unit/integration tests |

### Frontend
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | Next.js | 14.2.33 | React framework (App Router) |
| Language | TypeScript | 5.4+ | Type safety |
| State (Server) | TanStack React Query | 5.90+ | Server state management |
| State (Client) | Zustand | 4.5.2 | Client state management |
| UI Library | shadcn/ui | Latest | Component primitives (Radix UI) |
| Styling | Tailwind CSS | 3.4+ | Utility-first CSS |
| Icons | lucide-react | Latest | Icon library |
| Charts | recharts | Latest | Data visualization |

### Infrastructure
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Container | Docker | Containerization |
| Orchestration | Docker Compose | Multi-service orchestration |
| Web Server | Nginx | Reverse proxy, SSL termination |
| SSL | Let's Encrypt | Free SSL certificates |

---

## Project Structure

```
BRAiN/
├── backend/                    # Python FastAPI backend
│   ├── main.py                # UNIFIED FastAPI entry point (v0.3.0+)
│   │                          # Single entry point with auto-discovery
│   ├── api/routes/            # Legacy API routes (auto-discovered)
│   │   ├── agent_manager.py   # /api/agents/* endpoints
│   │   ├── missions.py        # /api/missions/* endpoints (legacy)
│   │   ├── axe.py            # /api/axe/* endpoints
│   │   ├── connectors.py      # /api/connectors/* endpoints
│   │   ├── debug_llm.py       # /api/debug/* endpoints
│   │   └── llm_config.py      # /api/llm/config endpoints
│   │
│   ├── app/                   # NEW: Modern app structure (v0.3.0+)
│   │   ├── main.py            # Deprecated entry point (backward compat)
│   │   ├── core/              # Core infrastructure
│   │   │   ├── config.py      # Settings management
│   │   │   ├── logging.py     # Structured logging setup
│   │   │   ├── redis_client.py # Async Redis client
│   │   │   └── lifecycle.py   # App startup/shutdown
│   │   │
│   │   ├── modules/           # 17+ Specialized modules
│   │   │   ├── policy/        # 🆕 Policy Engine (Phase 2)
│   │   │   │   ├── service.py    # Rule evaluation, ALLOW/DENY/WARN
│   │   │   │   ├── router.py     # /api/policy/* endpoints
│   │   │   │   ├── schemas.py    # PolicyRule, PolicyEffect models
│   │   │   │   └── README.md     # Full documentation
│   │   │   │
│   │   │   ├── fleet/         # 🆕 Fleet Management (Phase 2)
│   │   │   │   ├── service.py    # Multi-robot coordination
│   │   │   │   ├── router.py     # /api/fleet/* endpoints
│   │   │   │   └── schemas.py    # Robot, Fleet models
│   │   │   │
│   │   │   ├── foundation/    # 🆕 Foundation Layer (Phase 2)
│   │   │   │   ├── service.py    # Safety verification, auth checks
│   │   │   │   ├── router.py     # /api/foundation/* endpoints
│   │   │   │   ├── schemas.py    # SafetyCheck, Authorization models
│   │   │   │   └── README.md
│   │   │   │
│   │   │   ├── karma/         # 🆕 KARMA Framework (Phase 2)
│   │   │   │   ├── router.py     # /api/karma/* endpoints
│   │   │   │   └── schemas.py    # Reasoning models
│   │   │   │
│   │   │   ├── integrations/  # 🆕 Generic API Client (Phase 5.1)
│   │   │   │   ├── base_client.py  # BaseAPIClient abstract class
│   │   │   │   ├── auth.py         # Multi-auth (OAuth, API Key, etc.)
│   │   │   │   ├── retry.py        # Exponential backoff + jitter
│   │   │   │   ├── circuit_breaker.py # Cascading failure prevention
│   │   │   │   ├── rate_limit.py   # Token bucket algorithm
│   │   │   │   ├── schemas.py      # Integration models
│   │   │   │   ├── exceptions.py   # Custom exceptions
│   │   │   │   └── examples/       # OAuth, rate-limited clients
│   │   │   │
│   │   │   ├── missions/      # Mission system v2
│   │   │   ├── supervisor/    # Supervisor v2
│   │   │   ├── dna/           # Genetic optimization
│   │   │   ├── immune/        # Security & threat detection
│   │   │   ├── credits/       # Resource management
│   │   │   ├── threats/       # Threat detection
│   │   │   ├── telemetry/     # System monitoring
│   │   │   ├── metrics/       # Performance metrics
│   │   │   ├── hardware/      # Hardware resource mgmt
│   │   │   ├── ros2_bridge/   # ROS2 integration
│   │   │   ├── slam/          # Localization & mapping
│   │   │   └── vision/        # Computer vision
│   │   │
│   │   └── api/routes/        # Modern API routes
│   │       └── *.py           # Auto-discovered route modules
│   │
│   ├── brain/agents/          # Agent system
│   │   ├── base_agent.py      # BaseAgent abstract class
│   │   ├── agent_manager.py   # Agent CRUD operations
│   │   ├── supervisor_agent.py # Supervisor
│   │   ├── coder_agent.py     # Code specialist
│   │   ├── ops_agent.py       # Operations specialist
│   │   ├── architect_agent.py # Architecture decisions
│   │   ├── axe_agent.py       # Auxiliary Execution Engine
│   │   │
│   │   ├── fleet_agent.py     # 🆕 Fleet coordinator (Phase 3 - RYR)
│   │   ├── safety_agent.py    # 🆕 Safety monitor (Phase 3 - RYR)
│   │   ├── navigation_agent.py # 🆕 Path planner (Phase 3 - RYR)
│   │   │
│   │   ├── agent_blueprints/  # Predefined agent configs
│   │   │   ├── default.py
│   │   │   ├── code_specialist.py
│   │   │   ├── ops_specialist.py
│   │   │   ├── fleet_coordinator.py  # 🆕
│   │   │   ├── navigation_planner.py # 🆕
│   │   │   └── safety_monitor.py     # 🆕
│   │   │
│   │   ├── webdev/            # 🆕 WebDev Agent Cluster
│   │   │   ├── cli.py         # Command-line interface
│   │   │   ├── coding/        # Code generation & review
│   │   │   │   ├── code_generator.py
│   │   │   │   ├── code_completer.py
│   │   │   │   └── code_reviewer.py
│   │   │   ├── core/          # Core utilities
│   │   │   │   ├── error_handler.py
│   │   │   │   ├── self_healing.py
│   │   │   │   └── token_manager.py
│   │   │   ├── integration_core/ # External integrations
│   │   │   │   ├── claude_bridge.py
│   │   │   │   ├── github_connector.py
│   │   │   │   └── language_parser.py
│   │   │   ├── server_admin/  # Infrastructure
│   │   │   │   ├── deployment_agent.py
│   │   │   │   ├── infrastructure_agent.py
│   │   │   │   └── monitoring_agent.py
│   │   │   └── web_grafik/    # UI/UX design
│   │   │       ├── component_generator.py
│   │   │       └── ui_designer.py
│   │   │
│   │   └── repositories*.py   # Agent storage abstraction
│   │
│   ├── modules/               # Legacy modules (still used)
│   │   ├── missions/          # Mission system v1 (legacy)
│   │   ├── supervisor/        # Supervisor v1 (legacy)
│   │   ├── connector_hub/     # External integrations gateway
│   │   ├── llm_client.py      # LLMClient (Ollama-compatible)
│   │   └── llm_config.py      # LLMConfig runtime configuration
│   │
│   ├── alembic/               # 🆕 Database Migrations
│   │   ├── versions/          # Migration scripts
│   │   │   └── 001_initial_schema.py
│   │   ├── env.py             # Migration environment
│   │   └── alembic.ini        # Alembic configuration
│   │
│   ├── mission_control_core/  # 🆕 Mission Control Core
│   │   ├── api/routes.py      # REST + WebSocket endpoints
│   │   ├── core/              # Core services
│   │   └── README.md          # Documentation
│   │
│   ├── brain_api/             # 🆕 Separate API server
│   │   └── app/               # Independent FastAPI instance
│   │
│   ├── brain_cli/             # 🆕 CLI utilities
│   │
│   ├── core/                  # Legacy core utilities
│   │   ├── module_loader.py   # Module auto-discovery
│   │   └── app.py             # App initialization
│   │
│   ├── tests/                 # pytest test suite
│   │   ├── test_axe_endpoints.py
│   │   ├── test_connectors_and_agents.py
│   │   └── test_mission_system.py
│   │
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                  # Frontend applications
│   ├── control_deck/          # 🆕 NEW Control Dashboard (Next.js)
│   │   ├── app/               # App Router (14 pages)
│   │   │   ├── page.tsx           # Landing page
│   │   │   ├── dashboard/page.tsx # Main dashboard
│   │   │   ├── core/
│   │   │   │   ├── agents/page.tsx       # Agent management
│   │   │   │   ├── agents/[agentId]/page.tsx # Agent details
│   │   │   │   └── modules/page.tsx      # Module registry
│   │   │   ├── missions/page.tsx  # Mission control
│   │   │   ├── supervisor/page.tsx # Supervisor panel
│   │   │   ├── immune/page.tsx     # Security dashboard
│   │   │   └── settings/page.tsx   # Settings
│   │   ├── components/        # React components
│   │   ├── lib/               # Utilities
│   │   ├── Dockerfile
│   │   └── package.json
│   │
│   ├── brain_control_ui/      # Admin/Control Center (Next.js)
│   │   ├── src/
│   │   │   ├── app/           # App Router pages
│   │   │   │   ├── (control-center)/  # Route group
│   │   │   │   │   ├── page.tsx         # Dashboard
│   │   │   │   │   ├── agents/page.tsx  # Agents deck
│   │   │   │   │   ├── missions/page.tsx # Missions deck
│   │   │   │   │   ├── lifecycle/page.tsx # Agent lifecycle
│   │   │   │   │   ├── supervisor/page.tsx # Supervisor deck
│   │   │   │   │   └── settings/        # Settings pages
│   │   │   │   ├── brain/debug/page.tsx
│   │   │   │   ├── debug/llm/page.tsx
│   │   │   │   ├── layout.tsx
│   │   │   │   └── providers.tsx  # React Query provider
│   │   │   ├── components/
│   │   │   │   ├── ui/        # shadcn/ui primitives
│   │   │   │   ├── control-center/ # Feature components
│   │   │   │   └── layout/    # Layout components
│   │   │   ├── hooks/         # React Query hooks
│   │   │   │   ├── useAgents.ts
│   │   │   │   ├── useMissions.ts
│   │   │   │   ├── useSupervisor.ts
│   │   │   │   └── useLLMConfig.ts
│   │   │   └── lib/
│   │   │       ├── api.ts     # Base HTTP client
│   │   │       ├── brainApi.ts # Type-safe API wrapper
│   │   │       └── utils.ts   # Utility functions
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   ├── brain_ui/              # Chat Interface (Next.js)
│   │   ├── app/               # App Router pages
│   │   ├── src/
│   │   │   ├── brain-ui/
│   │   │   │   ├── components/
│   │   │   │   │   ├── BrainPresence.tsx  # Avatar/circle
│   │   │   │   │   ├── ChatShell.tsx      # Chat container
│   │   │   │   │   ├── CanvasPanel.tsx    # Context panel
│   │   │   │   │   └── ChatSidebar.tsx    # Navigation
│   │   │   │   └── state/
│   │   │   │       └── presenceStore.ts   # Zustand store
│   │   │   └── lib/
│   │   │       └── brainApi.ts # API client
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   └── axe_ui/                # AXE Interface (Next.js)
│       ├── app/               # App Router pages
│       └── package.json
│
├── docs/                      # Documentation
│   ├── BRAIN_SERVER_DATASHEET_FOR_CHATGPT.md
│   ├── brain_framework.md
│   ├── BRAIN_ImmuneSystem_and_External_Defense.md
│   └── DEV_LINE_LAST_UPDATE.txt
│
├── nginx/                     # Nginx configuration
├── src/                       # Additional source files
├── .env.example               # Environment template
├── .gitignore
├── docker-compose.yml         # Service orchestration
├── docker-compose.dev.yml     # Development overrides
├── docker-compose.prod.yml    # Production overrides
├── Dockerfile                 # Root Dockerfile
├── nginx.conf                 # Nginx config
├── requirements.txt           # Root Python requirements
├── CHANGELOG.md               # Version history
├── CLAUDE.md                  # This file - AI assistant guide
├── README.md                  # User-facing documentation
└── README.dev.md              # Developer documentation
```

**Legend:**
- 🆕 = New in v0.3.0 or later
- **(Phase X)** = Development phase identifier

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
from typing import Any, Dict, List, Optional

# Third-party
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import redis.asyncio as redis

# Local
from backend.modules.missions.models import Mission
from backend.modules.llm_client import get_llm_client
```

#### Module Structure Pattern
Every module should follow this structure:
```
module_name/
├── __init__.py           # Exports
├── models.py             # Pydantic models
├── schemas.py            # API response schemas (optional)
├── api.py or router.py   # FastAPI routes
├── service.py            # Business logic
├── queue.py or client.py # External integrations
└── manifest.json         # Module metadata (optional)
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
1. **API Routes:** Catch broad exceptions, return structured JSON responses
2. **Services:** Let exceptions bubble up, log at appropriate level
3. **Never expose raw exceptions to users**

```python
# API route error handling
@router.get("/missions/{mission_id}")
async def get_mission(mission_id: str):
    try:
        mission = await mission_service.get_mission(mission_id)
        if not mission:
            raise HTTPException(status_code=404, detail="Mission not found")
        return mission
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error fetching mission {mission_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

#### Dependency Injection
Use FastAPI's dependency injection system:
```python
def get_mission_service() -> MissionService:
    return MissionService()

@router.get("/missions")
async def list_missions(
    service: MissionService = Depends(get_mission_service)
):
    return await service.list_missions()
```

#### Logging
Use `loguru` with appropriate log levels:
```python
from loguru import logger

logger.info("Mission system initialized")
logger.warning("Queue capacity at 90%")
logger.error(f"Failed to process mission: {error}")
logger.debug(f"Mission payload: {payload}")
```

### Frontend Conventions

#### File Naming
- **Components:** `PascalCase.tsx` (e.g., `AgentCard.tsx`)
- **Utilities:** `camelCase.ts` or `kebab-case.ts`
- **Hooks:** `useCamelCase.ts` (e.g., `useMissions.ts`)
- **Types:** `types.ts` or inline with components

#### Import Organization
```typescript
// React
"use client";  // If needed
import { useState, useEffect } from "react";

// Third-party
import { useQuery, useMutation } from "@tanstack/react-query";
import { cn } from "@/lib/utils";

// Components
import { Button } from "@/components/ui/button";
import { AgentCard } from "@/components/control-center/agent-card";

// Utilities
import { api } from "@/lib/api";
import type { Mission } from "@/types";
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
      <h2>{title}</h2>
      {/* ... */}
    </div>
  );
}
```

#### React Query Pattern
**Query hooks:**
```typescript
export function useMissionsInfo() {
  return useQuery<MissionsInfo>({
    queryKey: ["missions", "info"],
    queryFn: () => brainApi.missions.info(),
    refetchInterval: 30_000,  // Refetch every 30s
  });
}
```

**Mutation hooks:**
```typescript
export function useMissionEnqueue() {
  const queryClient = useQueryClient();

  return useMutation<MissionEnqueueResponse, Error, MissionEnqueuePayload>({
    mutationKey: ["missions", "enqueue"],
    mutationFn: (payload) => brainApi.missions.enqueue(payload),
    onSuccess: () => {
      // Invalidate related queries to refetch
      queryClient.invalidateQueries({ queryKey: ["missions", "queue"] });
      queryClient.invalidateQueries({ queryKey: ["missions", "stats"] });
    },
  });
}
```

#### Styling with Tailwind
Use utility classes with semantic custom classes:
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
- Dark mode: `dark:bg-gray-800`, `dark:text-white`

---

## Backend Architecture

### Auto-Discovery Pattern

**Routes:** All modules in `backend/api/routes/` with a `router` attribute are automatically included in the app.

**`backend/main.py`:**
```python
def include_all_routers(app_instance: FastAPI):
    routes_dir = Path(__file__).parent / "api" / "routes"

    for file in routes_dir.glob("*.py"):
        if file.stem.startswith("_"):
            continue

        module_name = f"backend.api.routes.{file.stem}"
        module = importlib.import_module(module_name)

        if hasattr(module, "router"):
            app_instance.include_router(module.router)
```

**Adding a new route:**
1. Create `backend/api/routes/my_feature.py`
2. Define router:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/my-feature", tags=["my-feature"])

@router.get("/info")
def get_info():
    return {"name": "My Feature", "version": "1.0"}
```
3. **That's it!** The router is automatically included on startup.

### Agent System

**BaseAgent Abstract Class:**
```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Protocol

class LLMClient(Protocol):
    async def generate(self, prompt: str, **kwargs) -> str: ...

class BaseAgent(ABC):
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.tools: Dict[str, callable] = {}

    @abstractmethod
    async def run(self, task: str) -> AgentResult:
        """Execute the agent's main task."""
        pass

    async def call_llm(self, prompt: str, **kwargs) -> str:
        """Call the LLM with the given prompt."""
        return await self.llm.generate(prompt, **kwargs)

    def register_tool(self, name: str, func: callable):
        """Register a tool function."""
        self.tools[name] = func
```

**Creating a new agent:**
```python
from backend.brain.agents.base_agent import BaseAgent
from backend.modules.llm_client import get_llm_client

class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(llm_client=get_llm_client())
        self.register_tool("search", self._search_tool)

    async def run(self, task: str) -> AgentResult:
        # Agent logic
        response = await self.call_llm(f"Research task: {task}")
        return AgentResult(success=True, data={"response": response})

    async def _search_tool(self, query: str) -> str:
        # Tool implementation
        pass
```

### Mission System

**Mission Lifecycle:**
```
PENDING → QUEUED → RUNNING → COMPLETED
                           → FAILED
                           → CANCELLED
```

**Mission Model:**
```python
from pydantic import BaseModel
from enum import Enum

class MissionStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class MissionPriority(int, Enum):
    LOW = 10
    NORMAL = 20
    HIGH = 30
    CRITICAL = 40

class Mission(BaseModel):
    id: str
    name: str
    description: str
    status: MissionStatus
    priority: MissionPriority
    payload: Dict[str, Any]
    created_at: float
    updated_at: float
    max_retries: int = 3
    retry_count: int = 0
```

**Mission Queue (Redis ZSET):**
```python
class MissionQueue:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.queue_key = "brain:missions:queue"

    async def enqueue(self, mission: Mission) -> bool:
        """Add mission to queue with priority scoring."""
        age_bonus = (time.time() - mission.created_at) / 3600  # Age in hours
        score = mission.priority.value + age_bonus

        await self.redis.zadd(
            self.queue_key,
            {mission.id: score}
        )
        return True

    async def pop_next(self) -> Optional[Mission]:
        """Get highest-priority mission (highest score)."""
        result = await self.redis.zpopmax(self.queue_key)
        if not result:
            return None

        mission_id, score = result[0]
        # Fetch mission data and return
        return mission
```

**Mission Worker:**
```python
class MissionWorker:
    def __init__(self, queue: MissionQueue, poll_interval: float = 2.0):
        self.queue = queue
        self.poll_interval = poll_interval
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the worker background task."""
        self.running = True
        self.task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stop the worker gracefully."""
        self.running = False
        if self.task:
            await self.task

    async def _run_loop(self):
        """Main worker loop."""
        while self.running:
            try:
                mission = await self.queue.pop_next()
                if mission:
                    await self.execute_mission(mission)
            except Exception as e:
                logger.error(f"Worker error: {e}")

            await asyncio.sleep(self.poll_interval)

    async def execute_mission(self, mission: Mission):
        """Execute a single mission."""
        try:
            mission.status = MissionStatus.RUNNING
            # Execute mission logic
            # ...
            mission.status = MissionStatus.COMPLETED
        except Exception as e:
            mission.retry_count += 1
            if mission.retry_count < mission.max_retries:
                mission.status = MissionStatus.QUEUED
                await self.queue.enqueue(mission)
            else:
                mission.status = MissionStatus.FAILED
            logger.error(f"Mission {mission.id} failed: {e}")
```

### LLM Integration

**LLM Client (Ollama-compatible):**
```python
import httpx

class LLMClient:
    def __init__(self, host: str, model: str):
        self.host = host
        self.model = model
        self.client = httpx.AsyncClient()

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate completion from prompt."""
        response = await self.client.post(
            f"{self.host}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                **kwargs
            }
        )
        return response.json()["response"]

    async def simple_chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> tuple[str, Dict]:
        """Chat completion with messages."""
        response = await self.client.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                **kwargs
            }
        )
        data = response.json()
        return data["message"]["content"], data

# Singleton pattern
_llm_client: Optional[LLMClient] = None

def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        config = get_llm_config()
        _llm_client = LLMClient(host=config.host, model=config.model)
    return _llm_client
```

**Runtime LLM Configuration:**
```python
import json
from threading import RLock

class LLMConfig(BaseModel):
    provider: str = "ollama"
    host: str = "http://localhost:11434"
    model: str = "llama3.2:latest"
    temperature: float = 0.7
    max_tokens: int = 2000
    enabled: bool = True

class LLMConfigManager:
    def __init__(self, config_path: str = "storage/llm_config.json"):
        self.config_path = config_path
        self.lock = RLock()
        self.config = self._load()

    def _load(self) -> LLMConfig:
        """Load config from JSON file."""
        if not Path(self.config_path).exists():
            return LLMConfig()

        with open(self.config_path) as f:
            data = json.load(f)
        return LLMConfig(**data)

    def _save(self):
        """Save config to JSON file."""
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.config.model_dump(), f, indent=2)

    def get(self) -> LLMConfig:
        """Get current config."""
        with self.lock:
            return self.config.model_copy()

    def update(self, **kwargs):
        """Update config fields."""
        with self.lock:
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            self._save()

# Singleton
_config_manager: Optional[LLMConfigManager] = None

def get_llm_config() -> LLMConfig:
    global _config_manager
    if _config_manager is None:
        _config_manager = LLMConfigManager()
    return _config_manager.get()
```

### Policy Engine (Phase 2)

**Purpose:** Rule-based governance system for agent permissions and action authorization.

**Location:** `backend/app/modules/policy/`

**Core Concepts:**

```python
from enum import Enum
from pydantic import BaseModel

class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"
    AUDIT = "audit"

class PolicyRule(BaseModel):
    id: str
    name: str
    description: str
    effect: PolicyEffect
    priority: int = 100
    conditions: Dict[str, Any]
    enabled: bool = True
```

**Rule Evaluation:**
```python
from backend.app.modules.policy.service import PolicyService

policy_service = PolicyService()

# Evaluate action against policies
result = await policy_service.evaluate(
    agent_id="ops_agent",
    action="deploy_application",
    context={"environment": "production"}
)

if result.effect == PolicyEffect.DENY:
    raise PermissionError(f"Action denied: {result.reason}")
```

**Operators Supported:**
- `==`, `!=` - Equality checks
- `>`, `<`, `>=`, `<=` - Numeric comparisons
- `contains` - Substring/list membership
- `matches` - Regex pattern matching
- `in` - List membership

**Example Policy:**
```python
{
    "id": "prod-deploy-restriction",
    "name": "Production Deployment Restriction",
    "description": "Only senior agents can deploy to production",
    "effect": "deny",
    "priority": 200,
    "conditions": {
        "action": {"==": "deploy_application"},
        "context.environment": {"==": "production"},
        "agent_role": {"!=": "senior"}
    },
    "enabled": true
}
```

### ML Gateway & Risk Scoring (Sprint 17)

**Purpose:** Machine Learning integration for governance augmentation with fail-closed architecture.

**Location:** `backend/app/modules/ml_gateway/`, `backend/app/modules/risk_scoring/`

**Design Principles:**
1. **Determinism First:** ML scores are INPUTS to policy decisions, never decisions themselves
2. **Fail-Closed:** Service unavailability doesn't compromise safety (uses fallback scores)
3. **Optional Provider:** BRAiN Core functions fully without ML
4. **Auditability:** All ML outputs are logged, versioned, and reproducible

**Architecture:**

```
BRAiN Core (Governance Kernel)
    ↓
ML Gateway (Optional Provider)
    ↓
Risk Scoring Sidecar (Baseline→PyTorch)
```

**ML Gateway Service:**

```python
from app.modules.ml_gateway.service import get_ml_gateway_service
from app.modules.ml_gateway.schemas import RiskScoreRequest

ml_gateway = get_ml_gateway_service()

# Get risk score (with automatic fallback)
request = RiskScoreRequest(
    context={
        "action": "deploy_application",
        "environment": "production",
        "dag": {"nodes": [...], "edges": [...]},
    },
    agent_id="ops_agent",
    action="deploy_application"
)

score_response = await ml_gateway.get_risk_score(request)
# Returns: RiskScoreResponse(
#     risk_score=0.82,
#     confidence=0.75,
#     top_factors=[...],
#     model_version="baseline-v1",
#     is_fallback=False
# )
```

**Risk Scoring Features:**

- **DAG/IR Anomaly Detection:** Detects unusual execution patterns (excessive nodes, depth, branching)
- **Payload Analysis:** Analyzes payload size, nesting depth, complexity
- **Resource Validation:** Checks budget realism, retry limits
- **Baseline Implementation:** Pure Python heuristics (upgrade path to PyTorch models)

**Policy Integration:**

ML scores automatically enrich policy evaluation context:

```python
# Policy rule using ML risk score
{
    "id": "high-risk-escalation",
    "name": "Escalate High-Risk Operations",
    "effect": "audit",
    "conditions": {
        "ml_risk_score": {">": 0.75},
        "ml_confidence": {">": 0.6}
    },
    "priority": 150
}
```

**PolicyEvaluationContext** now includes optional ML fields:
- `ml_risk_score`: float [0.0, 1.0]
- `ml_confidence`: float [0.0, 1.0]
- `ml_model_version`: str
- `ml_is_fallback`: bool

**Failure Modes (Fail-Closed):**

| Scenario | Behavior |
|----------|----------|
| Sidecar Down | Use fallback score (0.5), confidence=0.0 |
| Timeout (>200ms) | Cancel request, use fallback |
| Invalid Output | Reject score, use fallback |
| Model Version Mismatch | Warn and continue (don't block) |

**API Endpoints:**

```python
GET  /api/ml/health       # ML Gateway health status
GET  /api/ml/info         # Configuration and version
POST /api/ml/score        # Get risk score for context
POST /api/ml/enrich       # Enrich context with ML scores
```

**Environment Configuration:**

```bash
# .env
ENABLE_ML_GATEWAY=true   # Enable ML Gateway (default: true)
```

**Metrics & Monitoring:**

```python
health = await ml_gateway.get_health()
# Returns: MLGatewayHealth(
#     status="available",
#     total_requests=1523,
#     successful_requests=1489,
#     fallback_requests=34,
#     avg_inference_time_ms=42.3
# )
```

### Fleet Management System (Phase 2 & 3 - RYR Integration)

**Purpose:** Multi-robot fleet coordination and management.

**Location:** `backend/app/modules/fleet/`

**Architecture:**

```
Fleet Module (Phase 2)         RYR Agents (Phase 3)
├── service.py                 ├── fleet_agent.py
├── router.py                  ├── safety_agent.py
└── schemas.py                 └── navigation_agent.py
```

**Fleet Service:**
```python
from backend.app.modules.fleet.service import FleetService

fleet_service = FleetService()

# Register robot in fleet
robot = await fleet_service.register_robot({
    "id": "robot_001",
    "name": "Delivery Bot Alpha",
    "capabilities": ["navigation", "package_delivery"],
    "max_payload": 50.0,  # kg
    "battery_capacity": 100.0
})

# Get fleet statistics
stats = await fleet_service.get_fleet_stats()
# {
#   "total_robots": 10,
#   "active": 7,
#   "idle": 2,
#   "charging": 1,
#   "total_tasks_completed": 453
# }

# Assign task to optimal robot
assignment = await fleet_service.assign_task({
    "task_id": "delivery_123",
    "requirements": ["navigation", "package_delivery"],
    "priority": "high"
})
```

**RYR Agents:**

1. **FleetAgent** (`backend/brain/agents/fleet_agent.py`)
   - Fleet-level coordination
   - Task distribution and load balancing
   - Health monitoring across robots

2. **SafetyAgent** (`backend/brain/agents/safety_agent.py`)
   - Real-time safety rule enforcement
   - Collision avoidance validation
   - Risk assessment for operations

3. **NavigationAgent** (`backend/brain/agents/navigation_agent.py`)
   - Path planning and optimization
   - Real-time obstacle avoidance
   - Route coordination across fleet

**Usage Example:**
```python
from backend.brain.agents.fleet_agent import FleetAgent
from backend.brain.agents.safety_agent import SafetyAgent
from backend.brain.agents.navigation_agent import NavigationAgent

# Initialize agents
fleet_agent = FleetAgent()
safety_agent = SafetyAgent()
nav_agent = NavigationAgent()

# Fleet coordination
result = await fleet_agent.run("Coordinate delivery of 5 packages")

# Safety check before movement
safety_check = await safety_agent.run(
    "Validate path from warehouse to customer location"
)

# Navigate robot
path = await nav_agent.run(
    "Plan optimal route avoiding construction zone"
)
```

### Generic API Client Framework (Phase 5.1)

**Purpose:** Enterprise-grade framework for external API integrations with resilience patterns.

**Location:** `backend/app/modules/integrations/`

**Components:**

```
integrations/
├── base_client.py       # BaseAPIClient abstract class
├── auth.py              # AuthenticationManager
├── retry.py             # RetryHandler with exponential backoff
├── circuit_breaker.py   # CircuitBreaker pattern
├── rate_limit.py        # RateLimiter (token bucket)
├── schemas.py           # Integration models
├── exceptions.py        # Custom exceptions
└── examples/            # Example implementations
    ├── oauth_client.py
    ├── rate_limited_client.py
    └── simple_rest_client.py
```

**BaseAPIClient Usage:**

```python
from backend.app.modules.integrations.base_client import BaseAPIClient
from backend.app.modules.integrations.auth import APIKeyAuth

class GitHubAPIClient(BaseAPIClient):
    def __init__(self, api_key: str):
        super().__init__(
            base_url="https://api.github.com",
            auth_manager=APIKeyAuth(
                api_key=api_key,
                header_name="Authorization",
                prefix="Bearer"
            ),
            timeout=30.0,
            max_retries=3,
            enable_circuit_breaker=True,
            enable_rate_limiter=True,
            rate_limit_calls=5000,  # GitHub API limit
            rate_limit_period=3600.0  # 1 hour
        )

    async def get_user(self, username: str) -> dict:
        """Get GitHub user information."""
        return await self.get(f"/users/{username}")

    async def create_issue(self, repo: str, data: dict) -> dict:
        """Create GitHub issue."""
        return await self.post(f"/repos/{repo}/issues", json=data)

# Usage
client = GitHubAPIClient(api_key="ghp_xxxxx")
user = await client.get_user("octocat")
```

**Resilience Patterns:**

1. **Retry with Exponential Backoff:**
```python
from backend.app.modules.integrations.retry import RetryHandler

retry_handler = RetryHandler(
    max_retries=3,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True  # Add randomness to prevent thundering herd
)
```

2. **Circuit Breaker:**
```python
from backend.app.modules.integrations.circuit_breaker import CircuitBreaker

circuit_breaker = CircuitBreaker(
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=60.0,    # Try again after 60s
    expected_exception=Exception
)

# Circuit states: CLOSED → OPEN → HALF_OPEN → CLOSED
```

3. **Rate Limiting:**
```python
from backend.app.modules.integrations.rate_limit import RateLimiter

rate_limiter = RateLimiter(
    max_calls=100,
    time_period=60.0,  # 100 calls per minute
    burst_size=10      # Allow bursts up to 10
)
```

**Authentication Support:**
- API Key (header or query parameter)
- OAuth 2.0 (authorization code, client credentials)
- Bearer Token
- Basic Auth
- Custom auth schemes

### Database Migrations (Alembic)

**Purpose:** Version-controlled database schema management.

**Location:** `backend/alembic/`

**Structure:**
```
alembic/
├── versions/
│   └── 001_initial_schema.py
├── env.py          # Migration environment config
└── alembic.ini     # Alembic configuration
```

**Creating a Migration:**

```bash
# Generate migration from models
cd backend
alembic revision --autogenerate -m "Add user_roles table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# Current version
alembic current
```

**Migration File Example:**

```python
# alembic/versions/002_add_user_roles.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(50), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('idx_user_roles_user_id', 'user_roles', ['user_id'])

def downgrade():
    op.drop_index('idx_user_roles_user_id')
    op.drop_table('user_roles')
```

### Mission Control Core with WebSocket Support

**Purpose:** Enhanced mission control with real-time updates.

**Location:** `backend/mission_control_core/`

**WebSocket Endpoint:**

```python
# mission_control_core/api/routes.py
from fastapi import WebSocket, WebSocketDisconnect

class MissionControlWS:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

ws_manager = MissionControlWS()

@router.websocket("/ws/missions")
async def mission_updates(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.active_connections.remove(websocket)
```

**Frontend WebSocket Consumer:**

```typescript
// hooks/useMissionUpdates.ts
export function useMissionUpdates() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/missions");

    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);

      // Invalidate queries to refetch
      queryClient.invalidateQueries({
        queryKey: ["missions", "queue"]
      });
    };

    return () => ws.close();
  }, [queryClient]);
}
```

### WebDev Agent Cluster

**Purpose:** Full-stack web development agent system with specialized sub-agents.

**Location:** `backend/brain/agents/webdev/`

**Architecture:**

```
webdev/
├── cli.py                     # Command-line interface
├── coding/                    # Code generation & review
│   ├── code_generator.py
│   ├── code_completer.py
│   └── code_reviewer.py
├── core/                      # Core utilities
│   ├── error_handler.py
│   ├── self_healing.py
│   └── token_manager.py
├── integration_core/          # External integrations
│   ├── claude_bridge.py       # Claude API integration
│   ├── github_connector.py    # GitHub operations
│   └── language_parser.py     # AST parsing
├── server_admin/              # Infrastructure
│   ├── deployment_agent.py
│   ├── infrastructure_agent.py
│   └── monitoring_agent.py
└── web_grafik/                # UI/UX design
    ├── component_generator.py
    └── ui_designer.py
```

**Usage Example:**

```python
from backend.brain.agents.webdev.coding.code_generator import CodeGenerator
from backend.brain.agents.webdev.coding.code_reviewer import CodeReviewer

# Generate code
generator = CodeGenerator()
result = await generator.run(
    "Create a React component for user authentication form"
)

# Review generated code
reviewer = CodeReviewer()
review = await reviewer.run(result.code)

if review.has_issues:
    print(f"Issues found: {review.issues}")
```

**Sub-Agent Capabilities:**

| Sub-Agent | Purpose | Tools |
|-----------|---------|-------|
| CodeGenerator | Generate code from specs | AST, Templates, LLM |
| CodeCompleter | Auto-completion | Language models, Context |
| CodeReviewer | Code quality review | Linters, Security scanners |
| DeploymentAgent | Deploy applications | Docker, K8s, Cloud APIs |
| InfrastructureAgent | Manage infrastructure | Terraform, Ansible |
| MonitoringAgent | Monitor systems | Prometheus, Logs |
| ComponentGenerator | Generate UI components | React, Vue templates |
| UIDesigner | Design interfaces | Design systems, A11y |

---

## Frontend Architecture

### API Client Pattern

**Base HTTP Client (`src/lib/api.ts`):**
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

export async function apiPost<T, B = unknown>(
  path: string,
  body?: B
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
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

**Type-Safe API Wrapper (`src/lib/brainApi.ts`):**
```typescript
import { api } from "./api";
import type {
  AgentsInfo,
  ChatPayload,
  ChatResponse,
  MissionsInfo,
  MissionEnqueuePayload,
  MissionQueueEntry,
  // ... other types
} from "@/types";

export const brainApi = {
  agents: {
    info: () => api.get<AgentsInfo>("/api/agents/info"),
    chat: (payload: ChatPayload) =>
      api.post<ChatResponse>("/api/agents/chat", payload),
  },

  missions: {
    info: () => api.get<MissionsInfo>("/api/missions/info"),
    health: () => api.get<MissionHealthResponse>("/api/missions/health"),
    enqueue: (payload: MissionEnqueuePayload) =>
      api.post("/api/missions/enqueue", payload),
    queuePreview: () =>
      api.get<MissionQueueEntry[]>("/api/missions/queue"),
    workerStatus: () =>
      api.get<WorkerStatusResponse>("/api/missions/worker/status"),
  },

  llm: {
    getConfig: () => api.get<LLMConfig>("/api/llm/config"),
    updateConfig: (config: Partial<LLMConfig>) =>
      api.put<LLMConfig>("/api/llm/config", config),
  },
};
```

### React Query Hooks

**Query Hook Pattern:**
```typescript
// hooks/useMissions.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { brainApi } from "@/lib/brainApi";
import type { MissionEnqueuePayload } from "@/types";

export function useMissionsInfo() {
  return useQuery({
    queryKey: ["missions", "info"],
    queryFn: () => brainApi.missions.info(),
    refetchInterval: 30_000,  // Auto-refetch every 30 seconds
  });
}

export function useMissionQueue() {
  return useQuery({
    queryKey: ["missions", "queue"],
    queryFn: () => brainApi.missions.queuePreview(),
    refetchInterval: 5_000,  // More frequent for queue
  });
}

export function useMissionEnqueue() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: ["missions", "enqueue"],
    mutationFn: (payload: MissionEnqueuePayload) =>
      brainApi.missions.enqueue(payload),
    onSuccess: () => {
      // Invalidate to trigger refetch
      queryClient.invalidateQueries({ queryKey: ["missions", "queue"] });
      queryClient.invalidateQueries({ queryKey: ["missions", "stats"] });
    },
    onError: (error) => {
      console.error("Failed to enqueue mission:", error);
    },
  });
}
```

**Usage in Component:**
```typescript
"use client";

import { useMissionsInfo, useMissionEnqueue } from "@/hooks/useMissions";
import { Button } from "@/components/ui/button";

export function MissionsDashboard() {
  const { data: info, isLoading, error } = useMissionsInfo();
  const enqueueMutation = useMissionEnqueue();

  const handleEnqueue = () => {
    enqueueMutation.mutate({
      name: "Test Mission",
      description: "Testing mission queue",
      priority: "NORMAL",
      payload: { task: "test" },
    });
  };

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-2xl font-bold">{info?.name}</h2>
      <p>Version: {info?.version}</p>
      <Button onClick={handleEnqueue} disabled={enqueueMutation.isPending}>
        {enqueueMutation.isPending ? "Enqueueing..." : "Enqueue Mission"}
      </Button>
    </div>
  );
}
```

### State Management Strategy

**Server State:** React Query (for API data)
- Automatic caching
- Background refetching
- Optimistic updates
- Request deduplication

**Client State:** Zustand (for UI state)
```typescript
// state/presenceStore.ts
import { create } from "zustand";

interface PresenceState {
  mode: "circle" | "avatar";
  affect: "neutral" | "alert" | "happy" | "thinking";
  isSpeaking: boolean;
  isCanvasOpen: boolean;
  activeCanvasTab: string | null;

  setMode: (mode: "circle" | "avatar") => void;
  setAffect: (affect: PresenceState["affect"]) => void;
  toggleSpeaking: () => void;
  toggleCanvas: () => void;
  setActiveCanvasTab: (tab: string | null) => void;
}

export const usePresenceStore = create<PresenceState>((set) => ({
  mode: "circle",
  affect: "neutral",
  isSpeaking: false,
  isCanvasOpen: false,
  activeCanvasTab: null,

  setMode: (mode) => set({ mode }),
  setAffect: (affect) => set({ affect }),
  toggleSpeaking: () => set((state) => ({ isSpeaking: !state.isSpeaking })),
  toggleCanvas: () => set((state) => ({ isCanvasOpen: !state.isCanvasOpen })),
  setActiveCanvasTab: (tab) => set({ activeCanvasTab: tab }),
}));
```

**URL State:** Next.js router (for page state, filters, etc.)

---

## API Reference

### System Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root info |
| GET | `/api/health` | Global health check |
| GET | `/debug/routes` | List all registered routes |

### Agent System (`/api/agents`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agents/info` | Agent system information |
| POST | `/api/agents/chat` | Chat with agent |

**Chat Request:**
```json
{
  "agent_id": "ops_specialist",
  "message": "Deploy the application",
  "context": {}
}
```

### Mission System (`/api/missions`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/missions/info` | Mission system info |
| GET | `/api/missions/health` | Health status |
| POST | `/api/missions/enqueue` | Enqueue new mission |
| GET | `/api/missions/queue` | Queue preview (upcoming missions) |
| GET | `/api/missions/events/history` | Event history |
| GET | `/api/missions/events/stats` | Event statistics |
| GET | `/api/missions/worker/status` | Worker status |
| GET | `/api/missions/agents/info` | Mission agents info |

**Enqueue Request:**
```json
{
  "name": "Deploy Application",
  "description": "Deploy to production environment",
  "priority": "HIGH",
  "payload": {
    "environment": "production",
    "version": "1.2.3"
  },
  "max_retries": 3
}
```

### Supervisor System (`/api/supervisor`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/supervisor/status` | Supervisor status |
| GET | `/api/supervisor/agents` | List supervised agents |
| POST | `/api/supervisor/control` | Control agent (start/stop/restart) |

**Control Request:**
```json
{
  "agent_id": "coder_agent",
  "action": "restart"
}
```

### LLM Configuration (`/api/llm`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/llm/config` | Get current LLM config |
| PUT | `/api/llm/config` | Update LLM config |
| POST | `/api/llm/config/reset` | Reset to defaults |

**Update Config Request:**
```json
{
  "provider": "ollama",
  "host": "http://localhost:11434",
  "model": "llama3.2:latest",
  "temperature": 0.7,
  "max_tokens": 2000,
  "enabled": true
}
```

### AXE Engine (`/api/axe`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/axe/info` | AXE engine info |
| POST | `/api/axe/message` | Execute via gateway or LLM fallback |

### Policy Engine (`/api/policy`) 🆕

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/policy/evaluate` | Evaluate action against policies |
| POST | `/api/policy/test-rule` | Test rule evaluation (no exceptions) |
| GET | `/api/policy/stats` | Policy system statistics |
| GET | `/api/policy/policies` | List all policies |
| POST | `/api/policy/policies` | Create new policy |
| GET | `/api/policy/policies/{id}` | Get policy by ID |
| PUT | `/api/policy/policies/{id}` | Update policy |
| DELETE | `/api/policy/policies/{id}` | Delete policy |

**Evaluate Request:**
```json
{
  "agent_id": "ops_agent",
  "action": "deploy_application",
  "context": {
    "environment": "production",
    "version": "1.2.3"
  }
}
```

**Evaluate Response:**
```json
{
  "effect": "deny",
  "reason": "Production deployment requires senior agent role",
  "matched_rule": "prod-deploy-restriction"
}
```

### ML Gateway (`/api/ml`) 🆕

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ml/health` | ML Gateway health status with metrics |
| GET | `/api/ml/info` | ML Gateway system information |
| POST | `/api/ml/score` | Get risk score for context |
| POST | `/api/ml/enrich` | Enrich context with ML scores |

**Score Request:**
```json
{
  "context": {
    "action": "deploy_application",
    "priority": "HIGH",
    "dag": {
      "nodes": ["node1", "node2", "node3"],
      "edges": ["edge1", "edge2"]
    }
  },
  "agent_id": "ops_agent",
  "action": "deploy_application"
}
```

**Score Response:**
```json
{
  "risk_score": 0.82,
  "confidence": 0.75,
  "top_factors": [
    {
      "factor": "dag_complexity",
      "weight": 0.65,
      "description": "High DAG complexity detected"
    }
  ],
  "model_version": "baseline-v1",
  "inference_time_ms": 42.3,
  "is_fallback": false,
  "timestamp": "2025-12-27T14:30:00Z"
}
```

**Health Response:**
```json
{
  "status": "available",
  "provider_available": true,
  "model_version": "baseline-v1",
  "uptime_seconds": 3600.5,
  "total_requests": 1523,
  "successful_requests": 1489,
  "failed_requests": 0,
  "fallback_requests": 34,
  "avg_inference_time_ms": 42.3
}
```

### Fleet Management (`/api/fleet`) 🆕

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/fleet/info` | Fleet system information |
| GET | `/api/fleet/stats` | Fleet statistics |
| GET | `/api/fleet/robots` | List all robots |
| POST | `/api/fleet/robots` | Register new robot |
| GET | `/api/fleet/robots/{id}` | Get robot details |
| PUT | `/api/fleet/robots/{id}` | Update robot |
| DELETE | `/api/fleet/robots/{id}` | Deregister robot |
| POST | `/api/fleet/assign-task` | Assign task to robot |
| GET | `/api/fleet/zones` | List coordination zones |

**Register Robot Request:**
```json
{
  "id": "robot_001",
  "name": "Delivery Bot Alpha",
  "capabilities": ["navigation", "package_delivery"],
  "max_payload": 50.0,
  "battery_capacity": 100.0,
  "location": {"x": 0.0, "y": 0.0, "z": 0.0}
}
```

### Foundation Layer (`/api/foundation`) 🆕

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/foundation/info` | Foundation system info |
| POST | `/api/foundation/safety-check` | Perform safety verification |
| POST | `/api/foundation/authorize` | Check action authorization |
| GET | `/api/foundation/audit-log` | Retrieve audit trail |

**Safety Check Request:**
```json
{
  "action": "move_robot",
  "parameters": {
    "robot_id": "robot_001",
    "target_position": {"x": 10.0, "y": 5.0}
  }
}
```

### KARMA Framework (`/api/karma`) 🆕

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/karma/info` | KARMA system information |
| POST | `/api/karma/reason` | Execute reasoning task |
| GET | `/api/karma/reasoning-history` | Get reasoning history |

### Mission Control WebSocket 🆕

| Protocol | Endpoint | Description |
|----------|----------|-------------|
| WS | `/ws/missions` | Real-time mission updates |

**WebSocket Message Format:**
```json
{
  "type": "mission_update",
  "mission_id": "mission_123",
  "status": "completed",
  "timestamp": 1703001234.56
}
```

---

## Development Workflow

### Local Development Setup

**1. Clone and Navigate:**
```bash
git clone <repository-url>
cd BRAiN
```

**2. Environment Configuration:**
```bash
cp .env.example .env
# Edit .env with your values (defaults work for local dev)
```

**3. Start Services (Docker):**
```bash
# Full stack
docker compose up -d

# View logs
docker compose logs -f backend

# Rebuild after changes
docker compose build backend
docker compose restart backend
```

**4. Start Frontend (Development):**
```bash
# Control UI
cd frontend/brain_control_ui
npm install
npm run dev  # http://localhost:3000

# Chat UI
cd frontend/brain_ui
npm install
npm run dev  # http://localhost:3002
```

### Development Cycle

**Backend Development:**
```bash
# 1. Make changes in backend/
vim backend/api/routes/my_feature.py

# 2. Rebuild container
docker compose build backend

# 3. Restart service
docker compose restart backend

# 4. Test endpoint
curl http://localhost:8000/api/my-feature/info

# 5. Check logs
docker compose logs -f backend
```

**Frontend Development:**
```bash
# Next.js has hot reload - just edit files
vim frontend/brain_control_ui/src/app/page.tsx
# Browser auto-refreshes
```

### Adding Dependencies

**Backend:**
```bash
# Edit requirements.txt
echo "new-package==1.0.0" >> backend/requirements.txt

# Rebuild
docker compose build backend
docker compose up -d backend
```

**Frontend:**
```bash
cd frontend/brain_control_ui
npm install new-package
# or
npm install --save-dev @types/new-package
```

### Database Migrations

**Framework:** Alembic (version-controlled migrations)

**Location:** `backend/alembic/`

**Common Operations:**

```bash
# Generate new migration
cd backend
alembic revision --autogenerate -m "Description of change"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# Check current version
alembic current

# Rollback to specific version
alembic downgrade <revision_id>
```

**Migration File Structure:**
```python
# backend/alembic/versions/xxx_description.py
def upgrade():
    # Apply changes
    op.create_table(...)

def downgrade():
    # Rollback changes
    op.drop_table(...)
```

### Git Workflow

**Branch Naming:**
- Feature: `feature/feature-name`
- Bugfix: `bugfix/bug-description`
- Hotfix: `hotfix/critical-fix`
- Claude sessions: `claude/claude-md-<session-id>`

**Commit Messages:**
```
Type: Brief description

- Detailed change 1
- Detailed change 2

Examples:
- feat: Add mission retry logic with exponential backoff
- fix: Resolve race condition in mission worker
- refactor: Extract LLM client to separate module
- docs: Update API documentation for mission endpoints
```

---

## Testing

### Backend Testing

**Framework:** pytest with pytest-asyncio

**Running Tests:**
```bash
# All tests
docker compose exec backend pytest

# Specific test file
docker compose exec backend pytest tests/test_mission_system.py

# With coverage
docker compose exec backend pytest --cov=backend

# Verbose
docker compose exec backend pytest -v
```

**Test Structure:**
```python
# tests/test_my_feature.py
import sys
import os

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_feature_endpoint():
    """Test feature endpoint returns expected data."""
    response = client.get("/api/my-feature/info")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "My Feature"
    assert "version" in data

def test_feature_create():
    """Test feature creation."""
    payload = {"name": "Test", "value": 42}
    response = client.post("/api/my-feature/create", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
```

**Testing Patterns:**
- Use `TestClient` for API testing (synchronous)
- Test actual endpoints, not internal functions directly
- Prefer integration tests over unit tests
- Mock external services (LLM, external APIs)
- Use fixtures for common setup

**Example Fixture:**
```python
import pytest

@pytest.fixture
def sample_mission():
    return {
        "name": "Test Mission",
        "description": "Testing",
        "priority": "NORMAL",
        "payload": {"key": "value"},
    }

def test_enqueue_mission(sample_mission):
    response = client.post("/api/missions/enqueue", json=sample_mission)
    assert response.status_code == 200
```

### Frontend Testing

**Currently:** No formal testing setup

**Recommended Stack:**
- Jest
- React Testing Library
- MSW (Mock Service Worker) for API mocking

**Future Test Example:**
```typescript
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MissionsDashboard } from "./missions-dashboard";

const queryClient = new QueryClient();

test("renders missions dashboard", async () => {
  render(
    <QueryClientProvider client={queryClient}>
      <MissionsDashboard />
    </QueryClientProvider>
  );

  await waitFor(() => {
    expect(screen.getByText(/Missions/i)).toBeInTheDocument();
  });
});
```

---

## Critical Rules for AI Assistants

### 🚨 MUST FOLLOW

1. **Always use async/await for I/O operations in backend**
   - Database queries, Redis operations, HTTP requests MUST be async
   - Never use blocking I/O (e.g., `requests` library)

2. **Type everything**
   - Backend: Type hints for all function parameters and return values
   - Frontend: TypeScript interfaces for all data structures
   - Never use `Any` or `any` unless absolutely necessary

3. **Handle errors gracefully**
   - Backend: Catch exceptions in routes, return structured JSON
   - Frontend: Handle loading and error states in React Query
   - Never expose raw exception details to users

4. **Follow the module pattern**
   - Backend routes auto-discovered from `backend/api/routes/`
   - Each module has models, schemas, router, service
   - Keep business logic out of route handlers

5. **Use dependency injection**
   - Backend: FastAPI `Depends()` for services
   - Frontend: React Query hooks for data, Zustand for client state

6. **Maintain type safety end-to-end**
   - Backend Pydantic models → Frontend TypeScript types
   - Use shared type definitions when possible

7. **Log appropriately**
   - Backend: Use `logger.info/warning/error` with context
   - Include relevant IDs (mission_id, agent_id, etc.)
   - Never log sensitive data (passwords, tokens)

8. **Test before committing**
   - Backend: Run pytest
   - Frontend: Check for TypeScript errors (`npm run build`)
   - Test API endpoints manually if needed

9. **Update invalidation in mutations**
   - Frontend: Always invalidate related queries after mutations
   - Ensures UI stays in sync with backend state

10. **Never commit secrets**
    - Use `.env` for configuration
    - Never hardcode API keys, passwords, tokens
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

2. **Never mutate state directly in React**
   ```typescript
   // ❌ BAD
   state.items.push(newItem);

   // ✅ GOOD
   setState({ items: [...state.items, newItem] });
   ```

3. **Never skip error handling**
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

4. **Never use `any` type in TypeScript**
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
   - Be descriptive: `get_mission_by_id()` not `get_m()`

2. **Keep functions focused**
   - Single Responsibility Principle
   - Extract complex logic into separate functions
   - Aim for functions under 50 lines

3. **Document complex logic**
   - Docstrings for public APIs
   - Comments for non-obvious code
   - Keep comments up-to-date

4. **Use constants for magic values**
   ```python
   # ❌ BAD
   if priority > 30:
       send_alert()

   # ✅ GOOD
   CRITICAL_PRIORITY_THRESHOLD = 30
   if priority > CRITICAL_PRIORITY_THRESHOLD:
       send_alert()
   ```

5. **Optimize for readability**
   - Code is read more than written
   - Prefer explicit over clever
   - Use meaningful variable names

6. **Leverage TypeScript inference**
   ```typescript
   // ✅ Type is inferred from React Query
   const { data } = useMissionsInfo();
   // data is automatically typed as MissionsInfo | undefined
   ```

7. **Use React Query optimally**
   - Set appropriate `refetchInterval` for live data
   - Use `staleTime` to reduce unnecessary refetches
   - Implement optimistic updates for better UX

---

## Common Tasks & Examples

### Task 1: Add a New API Endpoint

**Goal:** Add `/api/my-feature/hello` endpoint

**Steps:**

1. **Create router file:**
```python
# backend/api/routes/my_feature.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/my-feature", tags=["my-feature"])

class HelloResponse(BaseModel):
    message: str
    timestamp: float

@router.get("/hello")
async def hello() -> HelloResponse:
    """Say hello."""
    import time
    return HelloResponse(
        message="Hello from BRAiN!",
        timestamp=time.time()
    )
```

2. **Test endpoint:**
```bash
docker compose restart backend
curl http://localhost:8000/api/my-feature/hello
```

3. **Add frontend hook:**
```typescript
// frontend/brain_control_ui/src/hooks/useMyFeature.ts
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface HelloResponse {
  message: string;
  timestamp: number;
}

export function useHello() {
  return useQuery<HelloResponse>({
    queryKey: ["my-feature", "hello"],
    queryFn: () => api.get("/api/my-feature/hello"),
  });
}
```

4. **Use in component:**
```typescript
// frontend/brain_control_ui/src/components/hello-card.tsx
"use client";

import { useHello } from "@/hooks/useMyFeature";

export function HelloCard() {
  const { data, isLoading } = useHello();

  if (isLoading) return <div>Loading...</div>;

  return (
    <div className="brain-card">
      <p>{data?.message}</p>
      <p className="text-sm text-muted-foreground">
        Timestamp: {data?.timestamp}
      </p>
    </div>
  );
}
```

### Task 2: Create a New Agent

**Goal:** Create a `DataAnalystAgent`

**Steps:**

1. **Create agent class:**
```python
# backend/brain/agents/data_analyst_agent.py
from backend.brain.agents.base_agent import BaseAgent, AgentResult
from backend.modules.llm_client import get_llm_client

class DataAnalystAgent(BaseAgent):
    """Agent specialized in data analysis tasks."""

    def __init__(self):
        super().__init__(llm_client=get_llm_client())
        self.register_tool("analyze_csv", self._analyze_csv)
        self.register_tool("generate_chart", self._generate_chart)

    async def run(self, task: str) -> AgentResult:
        """Analyze data based on task description."""
        prompt = f"""You are a data analyst. Analyze this task:

        {task}

        Available tools:
        - analyze_csv: Analyze CSV data
        - generate_chart: Generate visualizations

        Provide your analysis:"""

        try:
            response = await self.call_llm(prompt)
            return AgentResult(
                success=True,
                data={"analysis": response},
                agent_id="data_analyst"
            )
        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e),
                agent_id="data_analyst"
            )

    async def _analyze_csv(self, file_path: str) -> dict:
        """Analyze CSV file."""
        # Implementation
        pass

    async def _generate_chart(self, data: list, chart_type: str) -> str:
        """Generate chart from data."""
        # Implementation
        pass
```

2. **Create blueprint (optional):**
```python
# backend/brain/agents/agent_blueprints/data_analyst.py
BLUEPRINT = {
    "id": "data_analyst",
    "name": "Data Analyst",
    "description": "Specialized in data analysis and visualization",
    "capabilities": [
        "csv_analysis",
        "chart_generation",
        "statistical_analysis"
    ],
    "tools": [
        "analyze_csv",
        "generate_chart"
    ]
}
```

3. **Register in agent manager:**
```python
# backend/api/routes/agent_manager.py (add to existing code)
from backend.brain.agents.data_analyst_agent import DataAnalystAgent

# In the agent registry
AGENTS = {
    "data_analyst": DataAnalystAgent(),
    # ... other agents
}
```

### Task 3: Add Mission Type

**Goal:** Add "data_analysis" mission type

**Steps:**

1. **Update mission models (if needed):**
```python
# backend/modules/missions/models.py
class MissionType(str, Enum):
    GENERAL = "general"
    CODE_REVIEW = "code_review"
    DEPLOYMENT = "deployment"
    DATA_ANALYSIS = "data_analysis"  # Add this

class Mission(BaseModel):
    # ... existing fields
    mission_type: MissionType = MissionType.GENERAL
```

2. **Add execution handler:**
```python
# backend/modules/missions/worker.py
class MissionWorker:
    async def execute_mission(self, mission: Mission):
        """Execute mission based on type."""
        handlers = {
            MissionType.GENERAL: self._execute_general,
            MissionType.CODE_REVIEW: self._execute_code_review,
            MissionType.DATA_ANALYSIS: self._execute_data_analysis,
        }

        handler = handlers.get(mission.mission_type, self._execute_general)
        return await handler(mission)

    async def _execute_data_analysis(self, mission: Mission):
        """Execute data analysis mission."""
        from backend.brain.agents.data_analyst_agent import DataAnalystAgent

        agent = DataAnalystAgent()
        result = await agent.run(mission.description)

        if result.success:
            mission.status = MissionStatus.COMPLETED
            mission.result = result.data
        else:
            raise Exception(f"Analysis failed: {result.error}")
```

3. **Update frontend types:**
```typescript
// frontend/brain_control_ui/src/types/missions.ts
export type MissionType =
  | "general"
  | "code_review"
  | "deployment"
  | "data_analysis";

export interface MissionEnqueuePayload {
  name: string;
  description: string;
  priority: MissionPriority;
  mission_type?: MissionType;
  payload: Record<string, unknown>;
}
```

### Task 4: Add Real-Time Updates

**Goal:** Add WebSocket for real-time mission updates

**Backend:**
```python
# backend/api/routes/missions.py
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/missions")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# In mission worker, after status update:
await manager.broadcast({
    "type": "mission_update",
    "mission_id": mission.id,
    "status": mission.status
})
```

**Frontend:**
```typescript
// hooks/useMissionUpdates.ts
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

export function useMissionUpdates() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/api/missions/ws/missions");

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "mission_update") {
        // Invalidate queries to refetch
        queryClient.invalidateQueries({ queryKey: ["missions", "queue"] });
      }
    };

    return () => ws.close();
  }, [queryClient]);
}

// In component:
export function MissionsDashboard() {
  useMissionUpdates();  // Automatically updates on WebSocket messages
  // ... rest of component
}
```

### Task 5: Update LLM Configuration

**Via API:**
```bash
# Get current config
curl http://localhost:8000/api/llm/config

# Update config
curl -X PUT http://localhost:8000/api/llm/config \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:latest",
    "temperature": 0.8,
    "max_tokens": 3000
  }'

# Reset to defaults
curl -X POST http://localhost:8000/api/llm/config/reset
```

**Via Frontend UI:**
Navigate to Settings > LLM Configuration and use the form.

### Task 6: Add a New shadcn/ui Component

**Steps:**

1. **Install component:**
```bash
cd frontend/brain_control_ui
npx shadcn-ui@latest add dialog
```

2. **Use component:**
```typescript
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export function MyDialog() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline">Open Dialog</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Are you sure?</DialogTitle>
          <DialogDescription>
            This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2">
          <Button variant="outline">Cancel</Button>
          <Button>Confirm</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

---

## Environment Variables Reference

See `.env.example` for complete reference. Key variables:

```bash
# App
ENVIRONMENT=development
VERSION=0.3.0

# API
API_HOST=0.0.0.0
API_PORT=8000
UVICORN_WORKERS=1

# Database
DATABASE_URL=postgresql://brain:brain@postgres:5432/brain
REDIS_URL=redis://redis:6379/0
QDRANT_HOST=http://qdrant
QDRANT_PORT=6333

# LLM
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:latest

# Supervisor
SUPERVISOR_HEARTBEAT_INTERVAL=10
SUPERVISOR_AGENT_TIMEOUT=30

# Mission System
MISSION_WORKER_POLL_INTERVAL=2.0
MISSION_DEFAULT_MAX_RETRIES=3

# Security
JWT_SECRET_KEY=<random-string>
POSTGRES_PASSWORD=<secure-password>

# Logging
LOG_LEVEL=INFO
```

---

## Troubleshooting

### Backend won't start
```bash
# Check logs
docker compose logs backend

# Common issues:
# 1. Port 8000 already in use
lsof -i :8000
kill -9 <PID>

# 2. Database connection failed
docker compose up -d postgres
docker compose logs postgres

# 3. Redis connection failed
docker compose up -d redis
docker compose logs redis
```

### Frontend build errors
```bash
# Clear cache
rm -rf .next node_modules
npm install
npm run build

# TypeScript errors
npm run type-check
```

### Mission worker not processing
```bash
# Check worker status
curl http://localhost:8000/api/missions/worker/status

# Check Redis
docker compose exec redis redis-cli
> ZRANGE brain:missions:queue 0 -1 WITHSCORES
> PING
```

### LLM not responding
```bash
# Check LLM config
curl http://localhost:8000/api/llm/config

# Test Ollama directly
curl http://localhost:11434/api/tags

# Check if Ollama is running
docker ps | grep ollama
# or
systemctl status ollama
```

---

## Server Deployment

### Deployment Architecture

BRAiN v2.0 uses a **three-environment deployment strategy** on server `brain.falklabs.de` (46.224.37.114):

| Environment | Path | Backend Port | Frontend Port | Domain |
|-------------|------|--------------|---------------|---------|
| Development | `/srv/dev/` | 8001 | 3001 | dev.brain.falklabs.de |
| Staging | `/srv/stage/` | 8002 | 3003 | stage.brain.falklabs.de |
| Production | `/srv/prod/` | 8000 | 3000 | brain.falklabs.de |

### Deployment Scripts

Two automated scripts handle deployment:

#### 1. Pre-Deployment Check

```bash
bash /root/brain-v2-precheck.sh
```

Verifies:
- ✅ SSH key exists at `/root/.ssh/ssh_key_github`
- ✅ SSH key has correct permissions (600)
- ✅ GitHub SSH authentication works
- ✅ Target directory state
- ✅ Docker installation
- ✅ Disk space (>10GB recommended)
- ✅ Port availability (8001, 3001, 3002)

#### 2. Main Setup Script

```bash
bash /root/brain-v2-setup.sh
```

Performs:
1. **Directory Preparation** - Creates/backs up `/srv/dev/`
2. **Repository Clone** - Clones via SSH from `git@github.com:satoshiflow/BRAiN.git` (branch: `v2`)
3. **Environment Files** - Generates `.env.dev`, `.env.stage`, `.env.prod` with secure passwords
4. **Docker Setup** - Installs/verifies Docker and Docker Compose
5. **Container Build** - Builds and starts development containers
6. **Service Verification** - Tests backend and frontend health
7. **Nginx Configuration** - Installs modular nginx config
8. **SSL Certificates** - Obtains Let's Encrypt certificates

### Nginx Configuration Structure

The modular nginx setup separates concerns:

```
nginx/
├── nginx.conf              # Host system config (includes snippets & conf.d)
├── nginx.docker.conf       # Docker container config (internal routing)
├── Dockerfile              # Uses nginx.docker.conf
├── README.md               # Configuration documentation
├── snippets/
│   ├── proxy-params.conf   # Standard proxy headers & timeouts
│   └── rate-limits.conf    # Rate limiting zones
└── conf.d/
    ├── upstream.conf       # All environment upstreams
    ├── dev.brain.conf      # Development server block
    ├── stage.brain.conf    # Staging server block
    └── brain.conf          # Production server block
```

**Key Points:**
- `nginx.docker.conf` uses container names (e.g., `brain-backend:8000`)
- `nginx.conf` + `conf.d/*` use localhost ports (e.g., `localhost:8001`)
- Snippets provide reusable proxy settings (avoid duplicate directives)

### Common Deployment Issues & Solutions

#### Issue 1: Frontend TypeScript Build Errors

**Error:**
```
Module '@/components/ui/sidebar' has no exported member 'SidebarProvider'
```

**Solution:**
The sidebar component was missing `SidebarProvider`, `SidebarInset`, and `SidebarTrigger` exports. This has been fixed in recent commits. If you encounter this:

```bash
# Ensure you're on latest v2 branch
cd /srv/dev
git pull origin v2

# Rebuild frontend
docker compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache control_deck
```

#### Issue 2: Nginx Duplicate Directive Errors

**Error:**
```
'proxy_connect_timeout' directive is duplicate
```

**Solution:**
This occurred when proxy timeouts were defined both in snippets and server blocks. The modular config now centralizes these in `snippets/proxy-params.conf`:

```nginx
# snippets/proxy-params.conf already includes:
proxy_connect_timeout 75s;
proxy_send_timeout 300s;
proxy_read_timeout 300s;
```

Remove duplicate directives from server blocks.

#### Issue 3: Old Containers Blocking Ports

**Error:**
```
Bind for 0.0.0.0:8000 failed: port is already allocated
```

**Solution:**
Stop old containers from previous deployment:

```bash
# Check what's using the ports
docker ps -a | grep brain
netstat -tuln | grep -E ":(8000|8001|3001|3002)"

# Stop old deployment
cd /opt/brain && docker-compose down  # if old version exists

# Or stop specific containers
docker stop brain-backend brain-control-deck brain-axe-ui
docker rm brain-backend brain-control-deck brain-axe-ui
```

#### Issue 4: npm Dependency Conflicts During Build

**Error:**
```
ERESOLVE unable to resolve dependency tree
```

**Solution:**
Frontend Dockerfiles use `--legacy-peer-deps` flag:

```dockerfile
RUN npm install --legacy-peer-deps
```

If you modify `package.json`, ensure this flag remains.

#### Issue 5: Missing docker-compose.dev.yml

**Error:**
```
open /srv/dev/docker-compose.dev.yml: no such file or directory
```

**Solution:**
Create the file with development port mappings:

```yaml
# docker-compose.dev.yml
services:
  backend:
    ports:
      - "8001:8000"

  control_deck:
    ports:
      - "3001:3000"

  axe_ui:
    ports:
      - "3002:3000"
```

Then run:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Manual Deployment Steps

If automated scripts fail, perform manual deployment:

```bash
# 1. Clone repository
export GIT_SSH_COMMAND="ssh -i /root/.ssh/ssh_key_github -o StrictHostKeyChecking=no"
git clone -b v2 git@github.com:satoshiflow/BRAiN.git /srv/dev

# 2. Create environment file
cd /srv/dev
cat > .env.dev <<EOF
ENVIRONMENT=development
DATABASE_URL=postgresql://brain:YOUR_PASSWORD@postgres:5432/brain_dev
REDIS_URL=redis://redis:6379/0
CORS_ORIGINS=["http://localhost:3001","https://dev.brain.falklabs.de"]
LOG_LEVEL=DEBUG
EOF

# 3. Build and start
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# 4. Verify
curl http://localhost:8001/health
curl http://localhost:3001

# 5. Configure nginx
cp nginx/nginx.conf /etc/nginx/nginx.conf
cp -r nginx/snippets /etc/nginx/
cp -r nginx/conf.d /etc/nginx/
nginx -t && systemctl reload nginx

# 6. Get SSL certificate
certbot --nginx -d dev.brain.falklabs.de --non-interactive --agree-tos --email admin@falklabs.de
```

### Updating Deployed Environment

```bash
cd /srv/dev

# Pull latest changes
git pull origin v2

# Rebuild and restart
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Check logs
docker compose logs -f backend
```

### Environment File Reference

Generated `.env.dev` contains:

```bash
ENVIRONMENT=development
APP_NAME=BRAiN v2.0 Dev

# Database (password auto-generated)
POSTGRES_DB=brain_dev
POSTGRES_USER=brain
POSTGRES_PASSWORD=brain_dev_<random>
DATABASE_URL=postgresql://brain:<password>@postgres:5432/brain_dev

# Redis
REDIS_URL=redis://redis:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000

# CORS
CORS_ORIGINS=["http://localhost:3001","http://dev.brain.falklabs.de","https://dev.brain.falklabs.de"]

# Logging
LOG_LEVEL=DEBUG

# LLM (optional)
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:latest
```

### Workflow: Local → GitHub → Server

1. **Local Development** (Windows PC: `D:\BRAiN-V2\`)
   - Make changes on feature branches
   - Test locally
   - Push to GitHub

2. **GitHub PR Review**
   - Create PR to `v2` branch
   - Code review
   - Merge when approved

3. **Server Deployment**
   ```bash
   ssh root@brain.falklabs.de
   cd /srv/dev
   git pull origin v2
   docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
   ```

4. **Verify Deployment**
   - Backend: https://dev.brain.falklabs.de/api/health
   - Frontend: https://dev.brain.falklabs.de
   - Logs: `docker compose logs -f`

---

## Additional Resources

**Documentation:**
- `docs/brain_framework.md` - Framework overview
- `docs/BRAIN_SERVER_DATASHEET_FOR_CHATGPT.md` - Server specifications
- `README.dev.md` - Developer quick start
- `CHANGELOG.md` - Version history
- `nginx/README.md` - Nginx configuration guide

**Key Technologies:**
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js Docs](https://nextjs.org/docs)
- [TanStack Query](https://tanstack.com/query/latest)
- [shadcn/ui](https://ui.shadcn.com/)
- [Pydantic](https://docs.pydantic.dev/)

---

## Version History

**0.5.0** (2025-12-20)
- **Phase 5.1:** Generic API Client Framework with enterprise-grade resilience patterns
  - BaseAPIClient abstract class for all external integrations
  - Multi-authentication support (OAuth 2.0, API Key, Bearer, Basic, Custom)
  - Automatic retry with exponential backoff and jitter
  - Circuit breaker pattern for cascading failure prevention
  - Rate limiting with token bucket algorithm
  - Comprehensive examples and documentation
- **Phase 3:** RYR Core Integration - Multi-robot fleet coordination
  - FleetAgent for fleet-level coordination and task distribution
  - SafetyAgent for real-time safety rule enforcement
  - NavigationAgent for path planning and obstacle avoidance
  - Agent blueprints for fleet operations
- **Phase 2:** Foundation modules for governance and safety
  - Policy Engine with rule-based governance (ALLOW/DENY/WARN/AUDIT)
  - Fleet Management module for multi-robot coordination
  - Foundation Layer for safety verification and authorization
  - KARMA Framework for knowledge-aware reasoning
- **Database Migrations:** Alembic integration for version-controlled schema management
- **Mission Control Core:** WebSocket support for real-time mission updates
- **WebDev Agent Cluster:** Full-stack development agent system with 11 specialized sub-agents
- **Control Deck Frontend:** New comprehensive dashboard with 14 pages
- **Module Expansion:** 17+ specialized modules in app/modules/
- **API Expansion:** 60+ new API endpoints across new modules
- **Documentation:** Comprehensive updates with examples for all new features

**0.4.0** (2025-12-12)
- Comprehensive documentation overhaul
- Updated all README files for clarity and completeness
- Enhanced architecture documentation
- Improved developer onboarding documentation
- Synchronized version across all documentation files

**0.3.1** (2025-12-11)
- Added comprehensive Server Deployment section
- Fixed missing sidebar components (SidebarProvider, SidebarInset, SidebarTrigger)
- Created modular nginx configuration structure
- Added deployment troubleshooting guide

**0.3.0** (2025-12-11)
- Supervisor deck integration
- Lifecycle fixes
- UI polishing
- Dark mode foundation

**0.2.0**
- Mission system implementation
- LLM configuration API
- Control UI dashboard

**0.1.0**
- Initial MVP release
- Agent system
- Basic API

---

**This guide is maintained for AI assistants. When making significant architectural changes, update this file accordingly.**
