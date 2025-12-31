# 🧠 BRAiN - Business Reasoning and Intelligence Network

[![Version](https://img.shields.io/badge/version-0.3.0-blue.svg)](https://github.com/satoshiflow/BRAiN)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-yellow.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/next.js-14.2-black.svg)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

**BRAiN** is an enterprise-grade AI orchestration platform designed for building, deploying, and managing autonomous AI systems at scale. It provides a complete infrastructure for multi-agent collaboration, mission execution, security governance, and real-time monitoring.

---

## 🌟 Key Features

### Core Platform
- **🤖 39+ Specialized Modules** - From AI agents to business automation, security, and robotics
- **🎯 Mission Queue System** - Redis-backed priority scheduling with automatic retry and EventStream integration
- **👁️ Real-Time Monitoring** - 4 dedicated frontend applications for different use cases
- **🔒 Enterprise Security** - Sovereign mode, DMZ control, policy engine, and threat detection
- **🏭 Business Automation** - Course factory, monetization, distribution, and payment processing
- **🤖 Robotics Integration** - ROS2 bridge, SLAM, fleet management, and computer vision
- **💰 Payment Processing** - PayCore module with Stripe integration and payment workflows
- **🧬 Self-Optimization** - DNA system for genetic algorithm-based optimization
- **🛡️ Immune System** - Automated threat detection and response

### Technical Excellence
- **⚡ Async-First** - Built on FastAPI and asyncio for maximum concurrency
- **🔐 Type-Safe** - End-to-end type safety with Pydantic and TypeScript
- **📡 Event-Driven** - EventStream architecture with Redis pub/sub
- **🔧 Modular** - Auto-discovered routes and plug-and-play modules
- **📊 Observable** - Comprehensive logging, metrics, and health monitoring
- **🐳 Production Ready** - Docker-based deployment with graceful shutdown

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend Applications                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Control  │  │  Brain   │  │  Brain   │  │   AXE    │       │
│  │   Deck   │  │ Control  │  │    UI    │  │    UI    │       │
│  │  :3000   │  │UI :3000  │  │  :3002   │  │  :3001   │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼─────────────┼─────────────┼─────────────┼──────────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                      │ HTTP/WS
        ┌─────────────▼────────────────────────────────────┐
        │         BRAiN Core Backend (FastAPI)             │
        │                  Port: 8000                      │
        │                                                   │
        │  ┌──────────────┬──────────────┬──────────────┐ │
        │  │   Business   │   Security   │   Robotics   │ │
        │  │   Modules    │   Modules    │   Modules    │ │
        │  ├──────────────┼──────────────┼──────────────┤ │
        │  │ CourseFactory│ Sovereign    │ Fleet Mgmt   │ │
        │  │ PayCore      │ Policy       │ ROS2 Bridge  │ │
        │  │ Distribution │ Immune       │ SLAM         │ │
        │  │ Monetization │ Threats      │ Vision       │ │
        │  └──────────────┴──────────────┴──────────────┘ │
        │                                                   │
        │  ┌──────────────────────────────────────────┐   │
        │  │         Core Infrastructure              │   │
        │  ├──────────────────────────────────────────┤   │
        │  │ Missions │ Supervisor │ DNA │ Karma      │   │
        │  │ Credits  │ Telemetry  │ Metrics │ Health │   │
        │  └──────────────────────────────────────────┘   │
        └───────────────────┬──────────────────────────────┘
                           │
        ┌──────────────────┼────────────────┐
        │                  │                │
   ┌────▼────┐      ┌─────▼─────┐    ┌────▼────┐
   │PostgreSQL│      │   Redis   │    │  Qdrant │
   │  :5432  │      │   :6379   │    │  :6333  │
   └─────────┘      └───────────┘    └─────────┘
        │                  │                │
   ┌────▼────┐      ┌─────▼─────┐    ┌────▼────┐
   │ Ollama  │      │ OpenWebUI │    │  LiteLLM│
   │ :11434  │      │   :8080   │    │ (opt)   │
   └─────────┘      └───────────┘    └─────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Docker** and **Docker Compose** (recommended)
- **Python 3.11+** (for local development)
- **Node.js 18+** (for frontend development)

### 1. Clone and Configure

```bash
# Clone repository
git clone https://github.com/satoshiflow/BRAiN.git
cd BRAiN

# Create environment file
cp .env.example .env

# Review and update .env file
# Important: Change default passwords and secrets!
nano .env
```

### 2. Start All Services

```bash
# Build and start all containers
docker compose up -d --build

# View logs
docker compose logs -f backend

# Check service status
docker compose ps
```

### 3. Verify Installation

```bash
# Check backend health
curl http://localhost:8000/api/health

# Expected response:
# {"status":"ok","message":"BRAiN Core Backend is running","version":"0.3.0"}

# View all available routes
curl http://localhost:8000/debug/routes
```

### 4. Access Applications

| Service | URL | Description |
|---------|-----|-------------|
| **API Documentation** | http://localhost:8000/docs | Interactive Swagger UI |
| **Backend API** | http://localhost:8000 | REST API endpoints |
| **Control Deck** | http://localhost:3000 | Main admin dashboard |
| **Brain Control UI** | http://localhost:3000 | Alternative control interface |
| **Chat Interface** | http://localhost:3002 | Conversational AI interface |
| **AXE UI** | http://localhost:3001 | AXE agent interface |
| **OpenWebUI** | http://localhost:8080 | LLM chat interface |
| **PostgreSQL** | localhost:5432 | Database (user: brain, db: brain) |
| **Redis** | localhost:6379 | Cache and queue |
| **Qdrant** | http://localhost:6333 | Vector database |
| **Ollama** | http://localhost:11434 | Local LLM server |

---

## 📊 Module Overview

### Business & Automation (8 modules)
- **course_factory** - AI-powered course creation and management
- **course_distribution** - Multi-platform course distribution
- **business_factory** - Business process automation
- **paycore** - Payment processing with Stripe integration
- **factory** - Generic factory pattern implementation
- **factory_executor** - Factory execution engine
- **autonomous_pipeline** - Automated workflow pipelines
- **template_registry** - Template management system

### Security & Governance (9 modules)
- **sovereign_mode** - Sovereign mode egress control
- **safe_mode** - Safe mode operations
- **policy** - Rule-based policy engine
- **immune** - Threat detection and immune system
- **threats** - Threat analysis and response
- **dmz_control** - DMZ gateway management
- **foundation** - Core security primitives
- **ir_governance** - Intelligent reasoning governance
- **axe_governance** - AXE agent governance
- **governance** - HITL approval workflows

### Core Infrastructure (10 modules)
- **missions** - Priority-based mission queue system
- **supervisor** - Agent lifecycle and orchestration
- **credits** - Resource credit management
- **hardware** - Hardware resource tracking
- **telemetry** - System telemetry and monitoring
- **metrics** - Performance metrics collection
- **system_health** - System health monitoring
- **runtime_auditor** - Runtime audit and compliance
- **monitoring** - Infrastructure monitoring
- **karma** - Knowledge-aware reasoning

### AI & Optimization (2 modules)
- **dna** - Genetic algorithm optimization
- **integrations** - External API integration framework

### Robotics (4 modules)
- **fleet** - Multi-robot fleet management
- **ros2_bridge** - ROS2 integration bridge
- **slam** - Simultaneous localization and mapping
- **vision** - Computer vision processing

### Platform Extensions (6 modules)
- **genesis** - WebGenesis AI system
- **aro** - Autonomous reasoning orchestrator
- **physical_gateway** - Physical device integration

---

## 🎯 Common Use Cases

### 1. Enqueue a Mission

```bash
curl -X POST http://localhost:8000/api/missions/enqueue \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Process Customer Data",
    "description": "Analyze customer behavior patterns",
    "priority": "HIGH",
    "payload": {
      "dataset": "customers_2024",
      "analysis_type": "behavioral"
    }
  }'
```

### 2. Check Mission Queue

```bash
# Get queue overview
curl http://localhost:8000/api/missions/info

# Get mission statistics
curl http://localhost:8000/api/missions/events/stats

# View queue preview
curl http://localhost:8000/api/missions/queue
```

### 3. Monitor System Health

```bash
# Overall health
curl http://localhost:8000/api/health

# Supervisor status
curl http://localhost:8000/api/supervisor/status

# System metrics
curl http://localhost:8000/api/metrics/system
```

### 4. Manage Payments (PayCore)

```bash
# Create payment
curl -X POST http://localhost:8000/api/paycore/payments \
  -H "Content-Type: application/json" \
  -d '{
    "amount_cents": 2999,
    "currency": "EUR",
    "customer_email": "customer@example.com",
    "description": "Course purchase"
  }'
```

### 5. Course Factory Operations

```bash
# Create course
curl -X POST http://localhost:8000/api/course-factory/courses \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Introduction to AI",
    "description": "Learn AI fundamentals",
    "target_audience": "beginners"
  }'
```

---

## 🛠️ Technology Stack

### Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | **FastAPI** | Async web framework |
| Language | **Python 3.11+** | Backend logic |
| Database | **PostgreSQL 16** | Persistent storage |
| Cache/Queue | **Redis 7** | Mission queue & pub/sub |
| Vector DB | **Qdrant** | Semantic search |
| LLM | **Ollama** | Local AI inference |
| Validation | **Pydantic 2.0** | Type-safe models |
| Logging | **loguru** | Structured logging |
| Migrations | **Alembic** | Database versioning |

### Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | **Next.js 14.2** | React framework |
| Language | **TypeScript 5.4** | Type safety |
| Server State | **TanStack Query** | API data management |
| Client State | **Zustand** | UI state |
| UI Library | **shadcn/ui** | Component primitives |
| Styling | **Tailwind CSS** | Utility-first CSS |
| Icons | **lucide-react** | Icon library |

### Infrastructure
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Container | **Docker** | Containerization |
| Orchestration | **Docker Compose** | Multi-service setup |
| Web Server | **Nginx** | Reverse proxy |
| SSL | **Let's Encrypt** | Free certificates |

---

## 📁 Project Structure

```
BRAiN/
├── backend/                    # Python FastAPI backend
│   ├── main.py                # Unified entry point (v0.3.0)
│   ├── app/                   # Modern app structure
│   │   ├── core/              # Core infrastructure
│   │   │   ├── config.py      # Settings management
│   │   │   ├── logging.py     # Logging setup
│   │   │   └── redis_client.py # Redis client
│   │   └── modules/           # 39+ specialized modules
│   │       ├── missions/      # Mission system
│   │       ├── supervisor/    # Agent orchestration
│   │       ├── course_factory/# Course creation
│   │       ├── paycore/       # Payment processing
│   │       ├── policy/        # Policy engine
│   │       ├── immune/        # Security system
│   │       └── ...            # 30+ more modules
│   ├── alembic/               # Database migrations
│   ├── tests/                 # Test suite
│   └── requirements.txt       # Python dependencies
│
├── frontend/                  # Frontend applications
│   ├── control_deck/         # Main admin dashboard
│   ├── brain_control_ui/     # Alternative control UI
│   ├── brain_ui/             # Chat interface
│   └── axe_ui/               # AXE agent UI
│
├── docs/                     # Documentation
├── nginx/                    # Nginx configuration
├── scripts/                  # Utility scripts
├── reports/                  # Generated reports
│   └── archive/             # Archived documentation
│
├── docker-compose.yml        # Main compose file
├── docker-compose.monitoring.yml  # Monitoring stack
├── docker-compose.dmz.yml    # DMZ services
├── .env.example              # Environment template
├── CLAUDE.md                 # AI assistant guide
├── README.md                 # This file
├── README.dev.md             # Developer guide
├── DEPLOYMENT.md             # Deployment guide
└── CHANGELOG.md              # Version history
```

---

## 🔧 Development

### Local Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run migrations
alembic upgrade head

# Start development server
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Local Frontend Development

```bash
# Control Deck
cd frontend/control_deck
npm install
npm run dev  # Runs on port 3000

# Brain UI
cd frontend/brain_ui
npm install
npm run dev  # Runs on port 3002

# AXE UI
cd frontend/axe_ui
npm install
npm run dev  # Runs on port 3001
```

### Running Tests

```bash
# Backend tests
docker compose exec backend pytest

# With coverage
docker compose exec backend pytest --cov=backend

# Specific test file
docker compose exec backend pytest tests/test_missions.py
```

### Database Migrations

```bash
# Create new migration
cd backend
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

---

## 🌐 Deployment

### Environment Setup

1. **Copy environment file**
   ```bash
   cp .env.example .env
   ```

2. **Update critical settings**
   - `POSTGRES_PASSWORD` - Strong database password
   - `JWT_SECRET_KEY` - Random secret key for JWT
   - `STRIPE_SECRET_KEY` - Stripe API key (for PayCore)
   - `OLLAMA_MODEL` - LLM model to use

3. **Configure external services** (optional)
   - Email/SMTP settings
   - Telegram/WhatsApp/Discord (DMZ)
   - PayPal credentials

### Production Deployment

```bash
# Build and start all services
docker compose up -d --build

# Check logs
docker compose logs -f

# Scale services (if needed)
docker compose up -d --scale backend=3

# Stop all services
docker compose down

# Stop and remove volumes (⚠️ data loss)
docker compose down -v
```

### Multi-Environment Setup

The system supports three environments:
- **Development** (`:8001`, `:3001`)
- **Staging** (`:8002`, `:3003`)
- **Production** (`:8000`, `:3000`)

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed multi-environment setup.

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[CLAUDE.md](CLAUDE.md)** | Comprehensive AI assistant guide (96KB) |
| **[README.dev.md](README.dev.md)** | Developer setup and workflows |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Production deployment guide |
| **[DEVELOPMENT.md](DEVELOPMENT.md)** | Development best practices |
| **[CHANGELOG.md](CHANGELOG.md)** | Version history |
| **[CLUSTER_ARCHITECTURE.md](CLUSTER_ARCHITECTURE.md)** | Cluster deployment |
| **[API Docs](http://localhost:8000/docs)** | Interactive API documentation |

---

## 🔐 Security Features

- **Sovereign Mode** - Network egress control and isolation
- **Policy Engine** - Rule-based access control
- **Immune System** - Automated threat detection
- **DMZ Gateway** - Secure external communication
- **Safe Mode** - Fail-safe operations
- **Runtime Auditor** - Real-time compliance monitoring
- **IR Governance** - Intelligent reasoning governance
- **HITL Approvals** - Human-in-the-loop workflows

---

## 💡 Key Capabilities

### Mission System
- Priority-based queue (Redis ZSET)
- Automatic retry with exponential backoff
- Event sourcing and replay
- Real-time status updates
- Mission snapshots for fast replay

### Agent Orchestration
- Multi-agent coordination
- Lifecycle management
- Heartbeat monitoring
- Graceful degradation

### Business Automation
- AI course generation
- Payment processing (Stripe)
- Multi-platform distribution
- Monetization workflows
- Template-based generation

### Robotics
- Fleet management
- ROS2 integration
- SLAM capabilities
- Computer vision
- Multi-robot coordination

---

## 📈 Monitoring & Observability

### Health Checks
```bash
# Global health
curl http://localhost:8000/api/health

# Mission system
curl http://localhost:8000/api/missions/health

# Supervisor
curl http://localhost:8000/api/supervisor/status

# System metrics
curl http://localhost:8000/api/metrics/system
```

### Logs
```bash
# View all logs
docker compose logs -f

# Backend only
docker compose logs -f backend

# With timestamps
docker compose logs -f -t backend
```

### Metrics (Grafana/Prometheus)
```bash
# Start monitoring stack
docker compose -f docker-compose.monitoring.yml up -d

# Access Grafana
open http://localhost:3001
```

---

## 🤝 Contributing

We welcome contributions! See [README.dev.md](README.dev.md) for:
- Setting up development environment
- Code style and conventions
- Running tests
- Submitting pull requests

### Quick Contribution Guide

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and add tests
4. Run tests: `docker compose exec backend pytest`
5. Commit: `git commit -m 'feat: Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastAPI** - Modern async web framework
- **Next.js** - React production framework
- **shadcn/ui** - Beautiful component primitives
- **Ollama** - Local LLM inference
- **Stripe** - Payment processing
- **Redis** - High-performance data structures
- **PostgreSQL** - Reliable database

---

## 📞 Support

- **Documentation**: See [CLAUDE.md](CLAUDE.md)
- **Issues**: [GitHub Issues](https://github.com/satoshiflow/BRAiN/issues)
- **Discussions**: [GitHub Discussions](https://github.com/satoshiflow/BRAiN/discussions)
- **Email**: support@falklabs.de

---

## 🎯 Roadmap

### Current Version: 0.3.0 (December 2024)

**✅ Completed**
- Core mission system with EventStream
- 39+ specialized modules
- 4 frontend applications
- Payment processing (PayCore)
- Course factory and distribution
- Security and governance systems
- Robotics integration
- Database migrations

**🚧 In Progress**
- Advanced monitoring and alerting
- Horizontal scaling
- Multi-tenancy support
- Advanced analytics

**📅 Planned**
- Kubernetes deployment
- Plugin marketplace
- Advanced AI capabilities
- Enhanced robotics features

---

**Built with ❤️ by the BRAiN Team**

_Empowering the next generation of autonomous AI systems and business automation_
