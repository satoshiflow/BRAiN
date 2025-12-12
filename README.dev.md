# 💻 BRAiN Developer Guide

**Version:** 0.4.0
**Last Updated:** 2025-12-12

Welcome to the BRAiN development guide! This document provides everything you need to know to contribute to the BRAiN project, from setting up your development environment to understanding our code conventions and testing practices.

---

## 📋 Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Code Conventions](#code-conventions)
5. [Testing](#testing)
6. [Git Workflow](#git-workflow)
7. [Debugging](#debugging)
8. [Common Tasks](#common-tasks)
9. [Troubleshooting](#troubleshooting)
10. [Resources](#resources)

---

## 🚀 Development Environment Setup

### Prerequisites

- **Git** - Version control
- **Docker** & **Docker Compose** - Containerization (recommended)
- **Python 3.11+** - Backend development
- **Node.js 18+** & **npm** - Frontend development
- **IDE/Editor** - VS Code (recommended), PyCharm, or your favorite editor

### Recommended VS Code Extensions

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "bradlc.vscode-tailwindcss",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "ms-azuretools.vscode-docker",
    "redhat.vscode-yaml"
  ]
}
```

### Initial Setup

#### 1. Clone the Repository

```bash
git clone https://github.com/satoshiflow/BRAiN.git
cd BRAiN
```

#### 2. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your local settings
# The defaults should work for Docker Compose setup
```

Key environment variables:

```bash
# Application
ENVIRONMENT=development
VERSION=0.4.0
DEBUG=true

# Database
DATABASE_URL=postgresql://brain:brain@localhost:5432/brain
REDIS_URL=redis://localhost:6379/0
QDRANT_HOST=http://localhost
QDRANT_PORT=6333

# LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000","http://localhost:3002"]

# Logging
LOG_LEVEL=DEBUG
```

#### 3. Docker Setup (Recommended)

```bash
# Start all services
docker compose up -d --build

# View logs
docker compose logs -f

# Stop all services
docker compose down

# Rebuild specific service
docker compose build backend
docker compose restart backend
```

#### 4. Local Setup (Alternative)

**Backend:**

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend (Control Deck):**

```bash
cd frontend/brain_control_ui

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check

# Linting
npm run lint
```

**Frontend (Chat Interface):**

```bash
cd frontend/brain_ui

# Install dependencies
npm install

# Run development server
npm run dev
```

---

## 📂 Project Structure

```
BRAiN/
├── backend/                    # Python FastAPI backend
│   ├── main.py                # Application entry point
│   ├── api/
│   │   └── routes/            # API endpoints (auto-discovered)
│   │       ├── agent_manager.py
│   │       ├── missions.py
│   │       ├── axe.py
│   │       ├── connectors.py
│   │       ├── debug_llm.py
│   │       └── llm_config.py
│   ├── brain/
│   │   └── agents/            # Agent implementations
│   │       ├── base_agent.py
│   │       ├── supervisor_agent.py
│   │       ├── coder_agent.py
│   │       ├── ops_agent.py
│   │       └── architect_agent.py
│   ├── modules/               # Core modules
│   │   ├── missions/
│   │   │   ├── models.py
│   │   │   ├── queue.py
│   │   │   ├── worker.py
│   │   │   └── schemas.py
│   │   ├── supervisor/
│   │   │   ├── router.py
│   │   │   ├── service.py
│   │   │   └── schemas.py
│   │   ├── llm_client.py
│   │   └── llm_config.py
│   ├── core/
│   │   ├── app.py
│   │   └── module_loader.py
│   ├── tests/                 # Test suite
│   │   ├── test_mission_system.py
│   │   ├── test_agents.py
│   │   └── conftest.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── brain_control_ui/      # Control Deck (Admin UI)
│   │   ├── src/
│   │   │   ├── app/           # Next.js App Router
│   │   │   │   ├── (control-center)/
│   │   │   │   │   ├── page.tsx         # Dashboard
│   │   │   │   │   ├── agents/page.tsx
│   │   │   │   │   ├── missions/page.tsx
│   │   │   │   │   ├── lifecycle/page.tsx
│   │   │   │   │   └── supervisor/page.tsx
│   │   │   │   ├── settings/
│   │   │   │   │   ├── llm/page.tsx
│   │   │   │   │   └── agents/page.tsx
│   │   │   │   ├── layout.tsx
│   │   │   │   └── providers.tsx
│   │   │   ├── components/
│   │   │   │   ├── ui/        # shadcn/ui components
│   │   │   │   └── control-center/
│   │   │   ├── hooks/         # React Query hooks
│   │   │   │   ├── useAgents.ts
│   │   │   │   ├── useMissions.ts
│   │   │   │   └── useSupervisor.ts
│   │   │   └── lib/
│   │   │       ├── api.ts
│   │   │       ├── brainApi.ts
│   │   │       └── utils.ts
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   └── brain_ui/              # Chat Interface
│       ├── app/
│       └── src/
│
├── docs/                      # Documentation
├── nginx/                     # Nginx configuration
├── .env.example
├── docker-compose.yml
├── CLAUDE.md                  # AI assistant guide
├── README.md                  # User-facing readme
└── README.dev.md              # This file
```

---

## 🔄 Development Workflow

### Daily Development Cycle

#### 1. Backend Development

```bash
# Start services
docker compose up -d postgres redis qdrant

# Run backend in dev mode (auto-reload)
cd backend
uvicorn main:app --reload

# Make changes to files
vim backend/api/routes/my_feature.py

# Backend automatically reloads on file changes
```

#### 2. Frontend Development

```bash
# Run frontend in dev mode (auto-reload)
cd frontend/brain_control_ui
npm run dev

# Make changes
vim src/app/(control-center)/page.tsx

# Next.js automatically hot-reloads
```

#### 3. Full Stack Testing

```bash
# Run entire stack
docker compose up -d --build

# Test backend
curl http://localhost:8000/api/health

# Test frontend
open http://localhost:3000
```

### Making Changes

#### Backend Changes

1. **Add new API endpoint:**

```python
# backend/api/routes/my_feature.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/my-feature", tags=["my-feature"])

class FeatureResponse(BaseModel):
    status: str
    data: dict

@router.get("/info")
async def get_info() -> FeatureResponse:
    """Get feature information."""
    return FeatureResponse(
        status="success",
        data={"version": "1.0", "enabled": True}
    )
```

2. **Restart backend:**

```bash
docker compose restart backend
# or if running locally
# uvicorn will auto-reload
```

#### Frontend Changes

1. **Add new component:**

```typescript
// frontend/brain_control_ui/src/components/feature-card.tsx
"use client";

export function FeatureCard() {
  return (
    <div className="brain-card">
      <h3>New Feature</h3>
      <p>Feature content</p>
    </div>
  );
}
```

2. **Changes are auto-reloaded** - just refresh browser

---

## 📝 Code Conventions

### Backend (Python)

#### File Naming

- Python files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`

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

#### Type Hints (Required)

```python
async def get_mission(mission_id: str) -> Optional[Mission]:
    """Retrieve a mission by ID.

    Args:
        mission_id: The unique mission identifier

    Returns:
        Mission object or None if not found
    """
    # Implementation
```

#### Async/Await (Required for I/O)

```python
# ✅ GOOD - Non-blocking
async def fetch_data() -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return response.json()

# ❌ BAD - Blocks event loop
def fetch_data() -> Dict[str, Any]:
    response = requests.get(url)
    return response.json()
```

#### Error Handling

```python
from loguru import logger

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

### Frontend (TypeScript)

#### File Naming

- Components: `PascalCase.tsx` (e.g., `AgentCard.tsx`)
- Utilities: `camelCase.ts` or `kebab-case.ts`
- Hooks: `useCamelCase.ts` (e.g., `useMissions.ts`)

#### Component Structure

```typescript
"use client"; // If using hooks/browser APIs

import { useState } from "react";

interface MyComponentProps {
  title: string;
  onAction?: () => void;
}

export function MyComponent({ title, onAction }: MyComponentProps) {
  const [state, setState] = useState<string>("");

  return (
    <div className="flex flex-col gap-4">
      <h2>{title}</h2>
      {/* Content */}
    </div>
  );
}
```

#### React Query Hooks

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { brainApi } from "@/lib/brainApi";

export function useMissionsInfo() {
  return useQuery({
    queryKey: ["missions", "info"],
    queryFn: () => brainApi.missions.info(),
    refetchInterval: 30_000,
  });
}

export function useMissionEnqueue() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: ["missions", "enqueue"],
    mutationFn: (payload) => brainApi.missions.enqueue(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["missions"] });
    },
  });
}
```

### Styling (Tailwind CSS)

```tsx
// Use utility classes
<div className="flex flex-col gap-4 p-6 rounded-lg bg-card">
  <h2 className="text-2xl font-bold">Title</h2>
  <p className="text-muted-foreground">Description</p>
</div>

// Common patterns
- Spacing: gap-2, gap-4, gap-6, p-4, px-6, py-3
- Layout: flex, flex-col, grid, grid-cols-2
- Responsive: md:flex-row, lg:grid-cols-3
- Dark mode: dark:bg-gray-800, dark:text-white
```

---

## 🧪 Testing

### Backend Testing (pytest)

#### Running Tests

```bash
# All tests
docker compose exec backend pytest

# Specific test file
docker compose exec backend pytest tests/test_mission_system.py

# With coverage
docker compose exec backend pytest --cov=backend

# Verbose output
docker compose exec backend pytest -v

# Stop on first failure
docker compose exec backend pytest -x
```

#### Writing Tests

```python
# tests/test_my_feature.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_feature_endpoint():
    """Test feature endpoint returns expected data."""
    response = client.get("/api/my-feature/info")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "version" in data["data"]

@pytest.fixture
def sample_payload():
    return {
        "name": "Test",
        "value": 42
    }

def test_feature_create(sample_payload):
    """Test feature creation."""
    response = client.post("/api/my-feature/create", json=sample_payload)

    assert response.status_code == 201
    assert response.json()["success"] is True
```

### Frontend Testing

```bash
# Type checking
npm run type-check

# Linting
npm run lint

# Fix linting issues
npm run lint:fix
```

---

## 🔀 Git Workflow

### Branch Naming

- Features: `feature/feature-name`
- Bugfixes: `bugfix/bug-description`
- Hotfixes: `hotfix/critical-fix`
- Claude sessions: `claude/description-<session-id>`

### Commit Messages

Use conventional commits:

```
<type>: <brief description>

<detailed description>

Examples:
feat: Add mission retry logic with exponential backoff
fix: Resolve race condition in mission worker
refactor: Extract LLM client to separate module
docs: Update API documentation for mission endpoints
test: Add tests for mission queue operations
chore: Update dependencies
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

### Pull Request Process

1. **Create feature branch:**
```bash
git checkout -b feature/my-feature
```

2. **Make changes and commit:**
```bash
git add .
git commit -m "feat: Add new feature"
```

3. **Run tests:**
```bash
docker compose exec backend pytest
cd frontend/brain_control_ui && npm run type-check
```

4. **Push to remote:**
```bash
git push origin feature/my-feature
```

5. **Create Pull Request on GitHub**

6. **Address review comments**

7. **Merge when approved**

---

## 🐛 Debugging

### Backend Debugging

#### View Logs

```bash
# Docker logs
docker compose logs -f backend

# Filter for errors
docker compose logs backend | grep ERROR

# View specific number of lines
docker compose logs --tail=100 backend
```

#### Python Debugger

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use built-in breakpoint()
breakpoint()
```

#### VS Code Debugging

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "backend.main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false
    }
  ]
}
```

### Frontend Debugging

#### Browser DevTools

- Network tab: Monitor API calls
- Console: View errors and logs
- React DevTools: Inspect component state

#### VS Code Debugging

Install "Debugger for Chrome" extension, then add to `.vscode/launch.json`:

```json
{
  "type": "chrome",
  "request": "launch",
  "name": "Next.js: debug client-side",
  "url": "http://localhost:3000",
  "webRoot": "${workspaceFolder}/frontend/brain_control_ui"
}
```

---

## 🛠️ Common Tasks

### Add New API Endpoint

See [CLAUDE.md - Task 1](CLAUDE.md#task-1-add-a-new-api-endpoint)

### Create New Agent

See [CLAUDE.md - Task 2](CLAUDE.md#task-2-create-a-new-agent)

### Add shadcn/ui Component

```bash
cd frontend/brain_control_ui
npx shadcn-ui@latest add dialog
```

Then use it:

```typescript
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
```

### Update Dependencies

**Backend:**
```bash
# Update requirements.txt
echo "new-package==1.0.0" >> backend/requirements.txt

# Rebuild container
docker compose build backend
docker compose restart backend
```

**Frontend:**
```bash
cd frontend/brain_control_ui
npm install new-package

# or for dev dependency
npm install --save-dev @types/new-package
```

---

## 🔧 Troubleshooting

### Backend Issues

**Port already in use:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

**Database connection failed:**
```bash
# Check if PostgreSQL is running
docker compose ps postgres

# View PostgreSQL logs
docker compose logs postgres

# Restart PostgreSQL
docker compose restart postgres
```

**Redis connection failed:**
```bash
# Check if Redis is running
docker compose ps redis

# Test Redis connection
docker compose exec redis redis-cli ping
# Should return: PONG
```

### Frontend Issues

**Build errors:**
```bash
# Clear cache and reinstall
rm -rf .next node_modules package-lock.json
npm install
npm run build
```

**TypeScript errors:**
```bash
# Check types
npm run type-check

# View specific errors
npx tsc --noEmit
```

**Port already in use:**
```bash
# Kill process on port 3000
lsof -i :3000
kill -9 <PID>

# Or use different port
npm run dev -- -p 3001
```

### Docker Issues

**Containers won't start:**
```bash
# Remove all containers and volumes
docker compose down -v

# Rebuild from scratch
docker compose up -d --build --force-recreate
```

**Out of disk space:**
```bash
# Clean up Docker
docker system prune -a

# Remove unused volumes
docker volume prune
```

---

## 📚 Resources

### Documentation

- [CLAUDE.md](CLAUDE.md) - Comprehensive AI assistant guide
- [README.md](README.md) - User-facing documentation
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
- [API Docs](http://localhost:8000/docs) - Interactive API documentation

### Technology Documentation

**Backend:**
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [Redis Docs](https://redis.io/docs/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)

**Frontend:**
- [Next.js Docs](https://nextjs.org/docs)
- [React Docs](https://react.dev/)
- [TanStack Query](https://tanstack.com/query/latest)
- [shadcn/ui](https://ui.shadcn.com/)
- [Tailwind CSS](https://tailwindcss.com/docs)

### Tools

- [Docker Docs](https://docs.docker.com/)
- [Git Docs](https://git-scm.com/doc)
- [pytest Docs](https://docs.pytest.org/)

---

## 💡 Tips & Best Practices

1. **Use Docker Compose for development** - Ensures consistent environment
2. **Write tests first** - TDD helps catch bugs early
3. **Use type hints** - Makes code more maintainable
4. **Document complex logic** - Help future developers (including yourself)
5. **Keep commits small** - Easier to review and revert
6. **Run tests before committing** - Prevents broken builds
7. **Use environment variables** - Never hardcode secrets
8. **Read error messages carefully** - They usually tell you exactly what's wrong
9. **Ask for help** - Don't hesitate to ask questions or create issues

---

## 🤝 Getting Help

- **Documentation**: Check [CLAUDE.md](CLAUDE.md) first
- **Issues**: [GitHub Issues](https://github.com/satoshiflow/BRAiN/issues)
- **Discussions**: [GitHub Discussions](https://github.com/satoshiflow/BRAiN/discussions)
- **Team**: Reach out to the development team

---

**Happy Coding! 🚀**

_Remember: Code is read more than it's written. Write code that your future self will thank you for._
