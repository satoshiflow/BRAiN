# **BRAiN CLI Tools**

**Version:** 1.0.0
**Created:** 2025-12-20
**Phase:** 5 - Developer Experience & Advanced Features

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Command Reference](#command-reference)
4. [Usage Examples](#usage-examples)
5. [Development Workflows](#development-workflows)

---

## Overview

The BRAiN CLI provides a comprehensive set of command-line tools for development, testing, deployment, and operations.

**Features:**
- **Database Operations** - Migrations, seeding, health checks
- **Code Generation** - API endpoints, models, tasks, modules
- **Development Tools** - Server, shell, formatting, linting
- **Configuration Management** - View, validate, export config
- **Testing Utilities** - Run tests, coverage, watch mode
- **System Information** - Health checks, routes, stats

**Technology:**
- **Typer** - CLI framework with type hints
- **Rich** - Beautiful terminal output with tables and colors

---

## Installation

The CLI is included with BRAiN backend. Ensure you have the required dependencies:

```bash
pip install typer rich
```

**Run CLI:**

```bash
# From backend directory
python -m brain_cli.main --help

# Or if installed as package
brain --help
```

---

## Command Reference

### Database Commands (`brain db`)

**Migrations:**

```bash
# Run all pending migrations
brain db migrate

# Migrate to specific revision
brain db migrate --revision=abc123

# Rollback 1 migration
brain db downgrade --steps=1

# Create new migration
brain db revision "Add users table"

# Create migration with auto-detection
brain db revision "Add users table" --autogenerate
```

**Migration Status:**

```bash
# Show current migration version
brain db current

# Show migration history
brain db history

# Verbose history
brain db history --verbose
```

**Database Maintenance:**

```bash
# Reset database (DESTRUCTIVE!)
brain db reset

# Seed database with test data
brain db seed

# Reset and seed
brain db seed --reset

# Check database connection
brain db check
```

---

### Code Generation (`brain generate`)

**API Endpoints:**

```bash
# Generate CRUD API endpoints
brain generate api users

# Custom prefix
brain generate api posts --prefix=/v1/api
```

Generates:
- `backend/app/api/routes/users.py` with full CRUD operations
- List, Create, Get, Update, Delete endpoints
- Pydantic models
- Permission decorators

**Pydantic Models:**

```bash
# Basic model
brain generate model User

# With fields
brain generate model User --fields "name:str,email:str,age:int"
```

**Celery Tasks:**

```bash
# Generate task
brain generate task send_email --queue=default

# Different queue
brain generate task process_payment --queue=missions
```

**Complete Modules:**

```bash
# Generate module with all files
brain generate module payments
```

Creates:
- `backend/app/modules/payments/`
  - `__init__.py`
  - `router.py` - API routes
  - `schemas.py` - Pydantic models
  - `service.py` - Business logic
  - `README.md` - Documentation
  - `tests/test_payments.py` - Test file

**Database Migrations:**

```bash
# Create migration from model changes
brain generate migration "Add payment status"
```

---

### Development Tools (`brain dev`)

**Development Server:**

```bash
# Start server with auto-reload
brain dev server

# Custom host/port
brain dev server --host=localhost --port=8080

# Disable auto-reload
brain dev server --no-reload
```

**Interactive Shell:**

```bash
# Start Python shell with app context
brain dev shell
```

Pre-imports commonly used modules for quick testing.

**Code Quality:**

```bash
# Format code with Black
brain dev format

# Check formatting without modifying
brain dev format --check

# Lint with Ruff
brain dev lint

# Auto-fix linting issues
brain dev lint --fix

# Type check with mypy
brain dev typecheck
```

**Docker Operations:**

```bash
# Start all services
brain dev docker up

# Stop all services
brain dev docker down

# Restart services
brain dev docker restart

# Build images
brain dev docker build

# View running containers
brain dev docker ps

# Specific service
brain dev docker up --service=backend
```

**Container Logs:**

```bash
# Follow backend logs
brain dev logs backend

# Follow with 50 lines
brain dev logs backend --tail=50

# Don't follow (just show)
brain dev logs backend --no-follow
```

**Clean Artifacts:**

```bash
# Remove __pycache__, .pyc, etc.
brain dev clean
```

**File Watcher:**

```bash
# Watch for changes and restart
brain dev watch
```

---

### Configuration Management (`brain config`)

**View Configuration:**

```bash
# Show all configuration
brain config show

# Show specific section
brain config show --section=DATABASE_URL
```

**Validate Configuration:**

```bash
# Check required values
brain config validate
```

Validates:
- JWT_SECRET_KEY is set
- Database URL is configured
- Redis URL is configured

**Export Configuration:**

```bash
# Export to JSON
brain config export --output=config.json --format=json

# Export to .env format
brain config export --output=.env.backup --format=env
```

---

### Testing Commands (`brain test`)

**Run Tests:**

```bash
# All tests
brain test run

# Specific file
brain test run tests/test_api.py

# Verbose mode
brain test run --verbose

# Filter by marker
brain test run -m unit

# Filter by keyword
brain test run -k "test_create"
```

**Coverage:**

```bash
# Run with coverage
brain test coverage

# Minimum coverage threshold
brain test coverage --min-coverage=90

# Generate HTML report
brain test coverage --html
```

View HTML report: `open htmlcov/index.html`

**Watch Mode:**

```bash
# Re-run tests on file changes
brain test watch

# Watch specific path
brain test watch tests/test_api.py
```

**Test Types:**

```bash
# Unit tests only
brain test unit

# Integration tests only
brain test integration

# Performance benchmarks
brain test benchmark
```

**Clean Test Artifacts:**

```bash
# Remove test cache and coverage data
brain test clean
```

---

### System Information (`brain info`)

**System Details:**

```bash
# Platform and Python info
brain info system
```

**Health Check:**

```bash
# Check all systems
brain info health
```

Checks:
- Redis connectivity
- Database connectivity
- Configuration validity

**Version Information:**

```bash
# Show versions
brain info version
```

Displays:
- BRAiN version
- FastAPI version
- Pydantic version
- SQLAlchemy version
- Redis version
- Celery version

**Dependencies:**

```bash
# List all installed packages
brain info deps
```

**API Routes:**

```bash
# List all registered routes
brain info routes
```

Shows:
- HTTP method
- Path
- Route name

**Modules:**

```bash
# List all registered modules
brain info modules
```

**Statistics:**

```bash
# Code statistics
brain info stats
```

Shows:
- Python file count
- Lines of code
- API route count
- Module count

---

## Usage Examples

### Daily Development Workflow

**1. Start Development:**

```bash
# Start Docker services
brain dev docker up

# Check health
brain info health

# Start development server
brain dev server
```

**2. Code Changes:**

```bash
# Format code
brain dev format

# Lint code
brain dev lint --fix

# Type check
brain dev typecheck
```

**3. Run Tests:**

```bash
# Run tests with coverage
brain test coverage --min-coverage=80

# Watch mode during development
brain test watch
```

**4. View Logs:**

```bash
# Backend logs
brain dev logs backend -f

# Worker logs
brain dev logs celery_worker -f
```

### Database Migration Workflow

**1. Make Model Changes:**

Edit your SQLAlchemy models in `backend/app/models/`

**2. Generate Migration:**

```bash
# Auto-generate from model changes
brain db revision "Add user profile" --autogenerate
```

**3. Review Migration:**

Check generated file in `backend/alembic/versions/`

**4. Apply Migration:**

```bash
# Apply to database
brain db migrate

# Verify
brain db current
```

**5. Rollback if Needed:**

```bash
# Rollback 1 migration
brain db downgrade --steps=1
```

### Creating a New Feature

**1. Generate Module:**

```bash
brain generate module notifications
```

**2. Generate API:**

```bash
brain generate api notifications
```

**3. Implement Business Logic:**

Edit `backend/app/modules/notifications/service.py`

**4. Add Tests:**

```bash
# Generate test file is already created
# Edit tests/test_notifications.py
```

**5. Run Tests:**

```bash
brain test run tests/test_notifications.py
```

**6. Create Migration (if needed):**

```bash
brain generate migration "Add notifications table"
brain db migrate
```

### Production Deployment Checklist

**1. Validate Configuration:**

```bash
brain config validate
```

**2. Run Full Test Suite:**

```bash
brain test coverage --min-coverage=80
```

**3. Check Database Migrations:**

```bash
brain db current
brain db history
```

**4. Verify Health:**

```bash
brain info health
```

**5. Check System Stats:**

```bash
brain info stats
brain info routes
```

### Code Quality Checks

**Pre-commit Checklist:**

```bash
# Format code
brain dev format

# Lint code
brain dev lint --fix

# Type check
brain dev typecheck

# Run tests
brain test run

# Check coverage
brain test coverage --min-coverage=80
```

**Continuous Integration:**

```bash
# CI pipeline commands
brain dev format --check  # Fail if not formatted
brain dev lint            # Fail on lint errors
brain dev typecheck       # Fail on type errors
brain test coverage --min-coverage=80  # Fail if below threshold
```

---

## Development Workflows

### Interactive Development

**IPython Shell:**

```bash
brain dev shell
```

```python
# In shell
from backend.app.core.config import get_settings
settings = get_settings()

from backend.app.core.redis_client import get_redis_client
import asyncio
redis = get_redis_client()
asyncio.run(redis.ping())
```

### Debugging

**View Logs:**

```bash
# Real-time logs
brain dev logs backend -f

# Last 50 lines
brain dev logs backend --tail=50
```

**Check Health:**

```bash
brain info health
```

**Inspect Routes:**

```bash
brain info routes | grep "/api/missions"
```

### Testing Strategies

**Quick Feedback Loop:**

```bash
# Watch mode
brain test watch tests/test_my_feature.py
```

**Full Test Suite:**

```bash
# All tests with coverage
brain test coverage
```

**Specific Test Types:**

```bash
# Fast unit tests
brain test unit

# Slower integration tests
brain test integration
```

### Database Management

**Development Database:**

```bash
# Reset and seed
brain db reset
brain db seed
```

**Production Database:**

```bash
# Check migration status
brain db current

# Apply pending migrations
brain db migrate

# Never run reset in production!
```

---

## Best Practices

### Code Generation

✅ **DO:**
- Use code generation for boilerplate
- Review and customize generated code
- Add generated files to git

❌ **DON'T:**
- Rely solely on generated code
- Skip reviewing generated code
- Modify generator templates directly

### Testing

✅ **DO:**
- Run tests before committing
- Use watch mode during development
- Maintain >80% coverage
- Use markers for test organization

❌ **DON'T:**
- Skip tests
- Commit failing tests
- Disable coverage checks

### Database Migrations

✅ **DO:**
- Review generated migrations
- Test migrations locally
- Use descriptive migration messages
- Keep migrations small and focused

❌ **DON'T:**
- Skip migration review
- Edit old migrations
- Combine unrelated changes

---

## Troubleshooting

### Command Not Found

```bash
# Ensure you're in backend directory
cd backend

# Run with full path
python -m brain_cli.main --help
```

### Import Errors

```bash
# Install dependencies
pip install -r requirements.txt

# Check Python version
python --version  # Should be 3.11+
```

### Database Connection Issues

```bash
# Check Docker services
brain dev docker ps

# Check database health
brain info health

# View logs
brain dev logs postgres
```

### Test Failures

```bash
# Verbose output
brain test run --verbose

# Run single test
brain test run tests/test_file.py::test_function

# Clean test cache
brain test clean
```

---

## References

- [Typer Documentation](https://typer.tiangolo.com/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [BRAiN CLAUDE.md](../CLAUDE.md)

---

**Last Updated:** 2025-12-20
**Maintainer:** BRAiN Development Team
**Phase:** 5 - Developer Experience & Advanced Features
