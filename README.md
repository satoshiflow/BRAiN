# 🧠 BRAiN - Base Repository for AI Networks

[![Version](https://img.shields.io/badge/version-0.4.0-blue.svg)](https://github.com/satoshiflow/BRAiN)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-yellow.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/next.js-14.2-black.svg)](https://nextjs.org/)

**BRAiN** is a production-ready AI agent framework designed for building, orchestrating, and managing autonomous AI systems. It provides a complete infrastructure for multi-agent collaboration, mission-based task execution, and real-time monitoring through an intuitive control interface.

---

## 🌟 Features

### Core Capabilities

- **🤖 Multi-Agent System** - Deploy and orchestrate specialized AI agents with distinct roles and capabilities
- **📋 Mission Queue** - Priority-based task scheduling with Redis-backed persistence and automatic retry logic
- **👁️ Real-Time Monitoring** - Comprehensive control deck with live system status, agent health, and mission tracking
- **🔌 Extensible Architecture** - Plugin-based design for easy integration of new agents, tools, and connectors
- **🚀 Production Ready** - Docker-based deployment, health checks, graceful shutdown, and comprehensive error handling
- **🔄 Supervisor Orchestration** - Intelligent agent lifecycle management with heartbeat monitoring
- **💬 LLM Integration** - Runtime-configurable LLM providers (Ollama, OpenAI, and more via LiteLLM)
- **📊 Analytics & Insights** - Event history, statistics, and performance metrics

### Technical Highlights

- **Async-First Design** - Built on FastAPI and asyncio for maximum concurrency
- **Type-Safe** - End-to-end type safety with Pydantic (backend) and TypeScript (frontend)
- **Event-Driven** - Redis-based pub/sub for real-time updates and inter-agent communication
- **Modular** - Clean separation of concerns with auto-discovered routes and components
- **Observable** - Comprehensive logging, health checks, and monitoring endpoints

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     BRAiN Control Deck                      │
│            (Next.js 14 - Real-time Dashboard)              │
└────────────────────┬───────────────────────────────────────┘
                     │ HTTP/WebSocket
┌────────────────────▼───────────────────────────────────────┐
│                   FastAPI Backend                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Mission    │  │  Supervisor  │  │   Agents     │    │
│  │   System     │  │   Service    │  │   Manager    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└────────────────────┬───────────────────────────────────────┘
                     │
      ┌──────────────┼──────────────┐
      │              │              │
┌─────▼─────┐  ┌────▼────┐  ┌─────▼─────┐
│ PostgreSQL│  │  Redis  │  │  Qdrant   │
│ (Storage) │  │ (Queue) │  │ (Vectors) │
└───────────┘  └─────────┘  └───────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose** (recommended)
- **Python 3.11+** (for local development)
- **Node.js 18+** (for frontend development)
- **PostgreSQL 15+** (if not using Docker)
- **Redis 7+** (if not using Docker)

### Option 1: Docker (Recommended)

Start all services with a single command:

```bash
# Clone the repository
git clone https://github.com/satoshiflow/BRAiN.git
cd BRAiN

# Start all services (backend, databases, frontends)
docker compose up -d --build

# View logs
docker compose logs -f backend

# Access the services
# - Backend API: http://localhost:8000
# - Control Deck: http://localhost:3000
# - Chat Interface: http://localhost:3002
# - API Documentation: http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# 1. Start backend
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your database URLs
uvicorn main:app --reload

# 2. Start Control Deck (new terminal)
cd frontend/brain_control_ui
npm install
npm run dev

# 3. Start Chat Interface (new terminal)
cd frontend/brain_ui
npm install
npm run dev
```

### Verify Installation

```bash
# Check backend health
curl http://localhost:8000/api/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "0.4.0",
#   "services": {
#     "postgres": "connected",
#     "redis": "connected",
#     "llm": "available"
#   }
# }
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [**CLAUDE.md**](CLAUDE.md) | 📖 Comprehensive guide for AI assistants working with BRAiN |
| [**README.dev.md**](README.dev.md) | 💻 Developer setup and contribution guide |
| [**ARCHITECTURE.md**](docs/ARCHITECTURE.md) | 🏛️ System architecture and design decisions |
| [**CHANGELOG.md**](CHANGELOG.md) | 📝 Version history and release notes |
| [**API Docs**](http://localhost:8000/docs) | 🔌 Interactive API documentation (when running) |

### Additional Resources

- [Mission System](docs/mission_system/README.md) - Mission queue architecture and usage
- [Supervisor Guide](docs/README_SUPERVISOR.md) - Agent supervision and lifecycle management
- [Deployment Guide](DEPLOYMENT.md) - Production deployment instructions
- [Workflows Guide](docs/WORKFLOWS-GUIDE.md) - Common workflows and examples

---

## 🎯 Usage Examples

### Enqueue a Mission

```bash
curl -X POST http://localhost:8000/api/missions/enqueue \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Code Review Task",
    "description": "Review the new authentication module",
    "priority": "HIGH",
    "payload": {
      "repository": "myapp",
      "branch": "feature/auth",
      "files": ["src/auth/*.py"]
    }
  }'
```

### Chat with an Agent

```bash
curl -X POST http://localhost:8000/api/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "coder_agent",
    "message": "Help me refactor this function to be more efficient",
    "context": {
      "code": "def process_items(items): ..."
    }
  }'
```

### Monitor System Health

```bash
# Get mission system status
curl http://localhost:8000/api/missions/health

# Get supervisor status
curl http://localhost:8000/api/supervisor/status

# Get LLM configuration
curl http://localhost:8000/api/llm/config
```

---

## 🧩 Core Components

### Backend (FastAPI)

- **Mission System** - Priority queue with Redis backend
  - Automatic retry with exponential backoff
  - Mission lifecycle: `PENDING → QUEUED → RUNNING → COMPLETED/FAILED`
  - Event history and statistics

- **Agent System** - Multi-agent orchestration
  - Supervisor agent for coordination
  - Specialized agents: Coder, Ops, Architect, Data Analyst
  - Agent lifecycle management (register, heartbeat, deregister)

- **LLM Integration** - Flexible LLM backend
  - Ollama support (default)
  - LiteLLM for multi-provider support (OpenAI, Anthropic, etc.)
  - Runtime configuration updates

### Frontend (Next.js)

- **Control Deck** - Admin and monitoring interface
  - Real-time dashboard with system metrics
  - Mission queue visualization
  - Agent health monitoring
  - LLM configuration management

- **Chat Interface** - Conversational UI
  - Direct agent interaction
  - Context-aware conversations
  - File and code sharing

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (async Python web framework)
- **Database**: PostgreSQL 15+ with pgvector extension
- **Cache/Queue**: Redis 7+ (ZSET for priority queue)
- **Vector Store**: Qdrant (semantic search and memory)
- **Validation**: Pydantic 2.0+ (type-safe data models)
- **HTTP Client**: httpx (async requests)
- **Logging**: loguru (structured logging)

### Frontend
- **Framework**: Next.js 14.2 (App Router)
- **Language**: TypeScript 5.4+
- **State Management**:
  - TanStack React Query (server state)
  - Zustand (client state)
- **UI Components**: shadcn/ui (Radix UI primitives)
- **Styling**: Tailwind CSS 3.4+
- **Icons**: lucide-react

### Infrastructure
- **Containers**: Docker & Docker Compose
- **Web Server**: Nginx (reverse proxy, SSL termination)
- **SSL**: Let's Encrypt (automated certificates)

---

## 📊 Project Status

### Current Version: 0.4.0 (December 2025)

**Status**: ✅ Production Ready

**Recent Milestones**:
- ✅ Core mission system with Redis queue
- ✅ Multi-agent orchestration with supervisor
- ✅ Real-time control deck with live updates
- ✅ LLM integration with runtime configuration
- ✅ Docker-based deployment
- ✅ Comprehensive documentation

**In Progress**:
- 🚧 WebSocket support for real-time updates
- 🚧 Advanced agent tools and capabilities
- 🚧 Cluster mode for horizontal scaling
- 🚧 Authentication and authorization system

**Roadmap**:
- 📅 Q1 2026: Kubernetes deployment templates
- 📅 Q1 2026: Plugin marketplace for agents and tools
- 📅 Q2 2026: Multi-tenant support
- 📅 Q2 2026: Advanced analytics and ML insights

---

## 🤝 Contributing

We welcome contributions! Please see our [Developer Guide](README.dev.md) for:

- Setting up your development environment
- Code style and conventions
- Running tests
- Submitting pull requests
- Reporting issues

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`docker compose exec backend pytest`)
5. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **Next.js** - React framework for production
- **shadcn/ui** - Beautiful UI components
- **Ollama** - Local LLM inference
- **Anthropic** - Claude AI models

---

## 📞 Support

- **Documentation**: [CLAUDE.md](CLAUDE.md)
- **Issues**: [GitHub Issues](https://github.com/satoshiflow/BRAiN/issues)
- **Discussions**: [GitHub Discussions](https://github.com/satoshiflow/BRAiN/discussions)
- **Email**: support@falklabs.de

---

## 🎓 Learn More

- [System Architecture](docs/ARCHITECTURE.md)
- [Mission System Deep Dive](docs/mission_system/README.md)
- [Agent Development Guide](docs/agents/README.md)
- [API Reference](http://localhost:8000/docs)
- [Deployment Best Practices](DEPLOYMENT.md)

---

**Built with ❤️ by the BRAiN Team**

_Empowering the next generation of autonomous AI systems_
