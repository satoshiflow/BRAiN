# Code Review Checklist - BRAiN Phase 3+4

**Reviewer:** Claude (Senior Developer)
**Reviewee:** Max (Junior Developer)
**Scope:** Cluster System + Worker Pool

---

## 📋 GENERAL CODE QUALITY

### Python Best Practices
- [ ] **PEP 8** compliance (line length ≤ 120 chars)
- [ ] **Type hints** on all function signatures
- [ ] **Docstrings** (Google style) on all public functions
- [ ] **No wildcard imports** (`from x import *`)
- [ ] **No unused imports** or variables
- [ ] **f-strings** statt `.format()` oder `%`
- [ ] **Pathlib** statt `os.path` für File Operations
- [ ] **Constants** in UPPER_CASE
- [ ] **Private functions** mit `_` Prefix

### Code Organization
- [ ] **Single Responsibility** - Eine Funktion, eine Aufgabe
- [ ] **DRY** - Keine Code-Duplikation
- [ ] **Max function length** ≤ 50 Zeilen
- [ ] **Max file length** ≤ 500 Zeilen
- [ ] **Imports** sortiert (stdlib, third-party, local)
- [ ] **Logical grouping** mit Kommentaren

---

## 🗄️ DATABASE (SQLAlchemy Models)

### Model Definition
- [ ] **Base** von `app.core.database.Base` erbt
- [ ] **`__tablename__`** explizit gesetzt
- [ ] **Primary Keys** definiert (`primary_key=True`)
- [ ] **Foreign Keys** mit Constraints
- [ ] **Nullable** explizit: `nullable=False` oder `True`
- [ ] **Default Values** für optionale Felder
- [ ] **Enums** statt Magic Strings
- [ ] **JSON Fields** haben `default=dict` oder `default=list`

### Relationships
- [ ] **back_populates** bidirektional definiert
- [ ] **Cascade** rules korrekt (`all, delete-orphan` für 1:N)
- [ ] **Lazy Loading** strategy bewusst gewählt
- [ ] **Remote side** bei self-referencing relationships

### Indexes & Performance
- [ ] **Indexes** auf häufig gesuchte Felder
- [ ] **Compound indexes** für Multi-Column queries
- [ ] **Unique constraints** wo nötig
- [ ] **Check constraints** für Data Validation

### Migration
```bash
# Prüfe:
- [ ] `alembic revision --autogenerate` läuft ohne Fehler
- [ ] Migration up: `alembic upgrade head`
- [ ] Migration down: `alembic downgrade -1`
- [ ] Keine manuelle Änderung nötig
```

### Example Check
```python
# ❌ BAD
class Cluster(Base):
    id = Column(String)  # Missing primary_key
    name = Column(String)  # Missing nullable
    agents = relationship("ClusterAgent")  # Missing back_populates

# ✅ GOOD
class Cluster(Base):
    __tablename__ = "clusters"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    agents = relationship("ClusterAgent", back_populates="cluster")
```

---

## 📊 SCHEMAS (Pydantic)

### Schema Definition
- [ ] **BaseModel** inheritance
- [ ] **Field** validators für komplexe Validation
- [ ] **Config** class mit `from_attributes = True` (ORM mode)
- [ ] **Separate Schemas** für Create/Update/Response
- [ ] **Sensible Defaults** in Create Schemas
- [ ] **Optional Fields** für Update Schemas

### Field Validation
- [ ] **String length** limits (`min_length`, `max_length`)
- [ ] **Number ranges** (`ge`, `le` für ≥, ≤)
- [ ] **Regex patterns** für Formats (Email, UUID, etc.)
- [ ] **Custom validators** mit `@field_validator`
- [ ] **Enums** für restricted choices

### Example Check
```python
# ❌ BAD
class ClusterCreate(BaseModel):
    name: str
    type: str
    max_workers: int

# ✅ GOOD
from pydantic import Field, field_validator

class ClusterCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    type: ClusterType  # Enum statt String
    max_workers: int = Field(default=10, ge=1, le=100)

    @field_validator('name')
    def name_must_be_alphanumeric(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('name must be alphanumeric')
        return v

    model_config = {"from_attributes": True}
```

---

## 🔧 SERVICES (Business Logic)

### Async/Await
- [ ] **Alle DB Operations** sind async (`async def`)
- [ ] **await** bei allen async calls
- [ ] **Keine blocking I/O**: `time.sleep` → `asyncio.sleep`
- [ ] **File I/O** via `aiofiles`
- [ ] **HTTP Requests** via `httpx` (async)

### Database Session
- [ ] **AsyncSession** als Parameter
- [ ] **Keine globalen sessions**
- [ ] **Transaction Handling** mit `async with session.begin()`
- [ ] **Commit** nach Änderungen
- [ ] **Rollback** im Error Case

### Error Handling
- [ ] **try/except** bei externen Calls
- [ ] **Specific exceptions** statt `except Exception`
- [ ] **Logging** mit loguru (`logger.error()`)
- [ ] **HTTPException** für API Errors
- [ ] **Custom exceptions** für Domain Errors
- [ ] **Keine silent failures**

### Example Check
```python
# ❌ BAD
def create_cluster(db, data):  # Nicht async!
    cluster = Cluster(**data)
    db.add(cluster)
    db.commit()  # Sollte async sein
    return cluster

# ✅ GOOD
async def create_cluster(
    db: AsyncSession,
    data: ClusterCreate
) -> Cluster:
    try:
        async with db.begin():  # Transaction
            cluster = Cluster(**data.model_dump())
            db.add(cluster)
            await db.flush()  # Get ID before commit

            logger.info(f"Created cluster: {cluster.id}")
            return cluster

    except IntegrityError as e:
        logger.error(f"Cluster creation failed: {e}")
        raise HTTPException(
            status_code=400,
            detail="Cluster with this name already exists"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
```

---

## 🚀 ROUTERS (FastAPI Endpoints)

### Endpoint Definition
- [ ] **Correct HTTP methods** (GET/POST/PUT/DELETE)
- [ ] **Path parameters** typed: `{id: str}`
- [ ] **Response model** definiert
- [ ] **Status codes** explicit: `status_code=201`
- [ ] **Tags** für OpenAPI Grouping
- [ ] **Summary & Description** für Docs

### Authentication & Authorization
- [ ] **`Depends(get_current_principal)`** auf protected routes
- [ ] **Role-based** mit `require_role(UserRole.ADMIN)`
- [ ] **Rate limiting** via `@limiter.limit()`
- [ ] **CORS** headers korrekt

### Input Validation
- [ ] **Pydantic Schemas** für Request Body
- [ ] **Query Parameters** mit Defaults
- [ ] **Path Parameters** validiert
- [ ] **File Uploads** size limits

### Response Handling
- [ ] **Consistent response format**
- [ ] **Pagination** für Lists (offset/limit)
- [ ] **HTTP 404** wenn Resource nicht gefunden
- [ ] **HTTP 403** bei Authorization failures
- [ ] **HTTP 422** bei Validation Errors
- [ ] **No sensitive data** in Error Responses

### Example Check
```python
# ❌ BAD
@router.post("/clusters")  # No auth, no response model
def create_cluster(data: dict):  # Dict statt Schema
    return service.create_cluster(data)

# ✅ GOOD
@router.post(
    "/clusters",
    response_model=ClusterResponse,
    status_code=201,
    tags=["Clusters"],
    summary="Create new cluster from blueprint"
)
@limiter.limit("10/minute")
async def create_cluster(
    data: ClusterCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal)
):
    """
    Create a new cluster from a blueprint.

    Requires ADMIN or OPERATOR role.
    """
    service = ClusterService(db)
    cluster = await service.create_from_blueprint(
        blueprint_id=data.blueprint_id,
        name=data.name,
        config=data.config
    )
    return cluster
```

---

## 🏃 WORKERS

### Worker Lifecycle
- [ ] **Graceful Shutdown** mit Signal Handling
- [ ] **Heartbeat** regelmäßig an Redis
- [ ] **Health Check** Endpoint/Command
- [ ] **Metrics Publishing** (Tasks processed, errors, etc.)
- [ ] **Reconnect Logic** bei Redis/DB disconnect

### Task Processing
- [ ] **Task Dequeue** atomic (Redis BLPOP)
- [ ] **Concurrency Limiting** (Semaphore)
- [ ] **Timeout** pro Task
- [ ] **Retry Logic** mit Backoff
- [ ] **Dead Letter Queue** für failed tasks
- [ ] **Task Acknowledgement** nach Success

### Error Handling
- [ ] **try/except** um Task Processing
- [ ] **Logging** mit Task Context
- [ ] **Keine Crashes** bei Task Errors
- [ ] **Error Metrics** publishen

### Example Check
```python
# ❌ BAD
while True:
    task = redis.lpop("queue")  # Blocking!
    process(task)  # No error handling

# ✅ GOOD
async def run_worker(self):
    while not self.shutdown_event.is_set():
        try:
            # Atomic dequeue with timeout
            task_data = await self.redis.blpop(
                self.queue_name,
                timeout=5
            )

            if not task_data:
                continue

            task = Task.parse_raw(task_data[1])

            # Concurrency limit
            async with self.semaphore:
                await self._process_task(task)

        except asyncio.CancelledError:
            logger.info("Worker cancelled, exiting...")
            break
        except Exception as e:
            logger.error(f"Task processing error: {e}", exc_info=True)
            await self._publish_error_metric(e)
            await asyncio.sleep(1)  # Backoff
```

---

## 🐳 DOCKER

### Dockerfile
- [ ] **Multi-stage build** (builder + runner)
- [ ] **Non-root user** (`USER nobody`)
- [ ] **Minimal base image** (slim/alpine)
- [ ] **.dockerignore** vorhanden
- [ ] **HEALTHCHECK** definiert
- [ ] **No secrets** in Image
- [ ] **Cache-freundlich** (COPY requirements erst)

### docker-compose.yml
- [ ] **Service names** lowercase
- [ ] **Networks** explizit definiert
- [ ] **Volumes** für Persistence
- [ ] **Environment** aus `.env` File
- [ ] **Depends_on** korrekt
- [ ] **Health checks** definiert
- [ ] **Resource limits** gesetzt
- [ ] **Restart policy** configured

### Example Check
```dockerfile
# ❌ BAD
FROM python:3.11
COPY . .
RUN pip install -r requirements.txt
CMD python worker.py

# ✅ GOOD
# Build stage
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app

# Non-root user
RUN useradd -m -u 1000 worker
USER worker

# Copy dependencies
COPY --from=builder /root/.local /home/worker/.local
ENV PATH=/home/worker/.local/bin:$PATH

# Copy app
COPY --chown=worker:worker worker.py .
COPY --chown=worker:worker app/ ./app/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import redis; r=redis.Redis(host='redis'); r.ping()"

CMD ["python", "worker.py"]
```

---

## 📝 DOCUMENTATION

### Code Comments
- [ ] **Why, not what** - Code zeigt "was", Comment erklärt "warum"
- [ ] **Complex logic** kommentiert
- [ ] **TODOs** mit Ticket-Nummer
- [ ] **Keine commented-out code** (Git History nutzen)

### Docstrings
```python
# ✅ GOOD
async def create_cluster(
    self,
    db: AsyncSession,
    blueprint_id: str,
    name: str
) -> Cluster:
    """
    Create a new cluster from a blueprint.

    Args:
        db: Database session
        blueprint_id: ID of the blueprint to use
        name: Human-readable cluster name

    Returns:
        Cluster: The created cluster instance

    Raises:
        ValueError: If blueprint not found
        IntegrityError: If cluster name already exists

    Example:
        >>> cluster = await service.create_cluster(
        ...     db,
        ...     "marketing-v1",
        ...     "Marketing Q1 2024"
        ... )
    """
```

### README Files
- [ ] **Module README** in jedem Submodule
- [ ] **Purpose** klar beschrieben
- [ ] **Architecture** Diagram (ASCII/Mermaid)
- [ ] **API Examples** mit curl/httpx
- [ ] **Configuration** dokumentiert

---

## 🧪 TESTING

### Unit Tests
- [ ] **Test Coverage** ≥ 80%
- [ ] **Pytest** als Framework
- [ ] **Fixtures** für DB/Redis
- [ ] **Mocking** für externe Services
- [ ] **Async Tests** mit `pytest-asyncio`

### Test Structure
```python
# ✅ GOOD
import pytest
from app.modules.cluster_system.service import ClusterService

@pytest.mark.asyncio
async def test_create_cluster_success(db_session, mock_blueprint):
    """Should create cluster when valid blueprint provided"""
    service = ClusterService(db_session)

    cluster = await service.create_from_blueprint(
        blueprint_id="marketing-v1",
        name="Test Cluster"
    )

    assert cluster.id is not None
    assert cluster.name == "Test Cluster"
    assert cluster.status == ClusterStatus.ACTIVE

@pytest.mark.asyncio
async def test_create_cluster_blueprint_not_found(db_session):
    """Should raise ValueError when blueprint doesn't exist"""
    service = ClusterService(db_session)

    with pytest.raises(ValueError, match="Blueprint not found"):
        await service.create_from_blueprint(
            blueprint_id="nonexistent",
            name="Test"
        )
```

---

## 🔒 SECURITY

### Input Validation
- [ ] **Alle User Inputs** validiert (Pydantic)
- [ ] **SQL Injection** prevention (SQLAlchemy ORM)
- [ ] **Path Traversal** prevention (`..` checks)
- [ ] **Command Injection** prevention (no shell=True)
- [ ] **XSS** prevention (HTML escaping)

### Secrets Management
- [ ] **Keine Secrets** im Code
- [ ] **Environment Variables** für Configs
- [ ] **Keine Secrets** in Logs
- [ ] **Keine Secrets** in Error Messages

### Authentication
- [ ] **JWT Verification** auf protected routes
- [ ] **Role-based Access** (RBAC)
- [ ] **Rate Limiting** gegen Brute Force
- [ ] **CORS** korrekt konfiguriert

---

## 📊 PERFORMANCE

### Database Queries
- [ ] **Keine N+1 Queries** (use `joinedload`/`selectinload`)
- [ ] **Indexes** auf Filter-Felder
- [ ] **Pagination** für große Resultsets
- [ ] **Select only needed columns** (nicht `SELECT *`)

### Async Best Practices
- [ ] **Keine blocking calls** in async functions
- [ ] **asyncio.gather** für parallele Tasks
- [ ] **Connection Pooling** (DB, Redis)
- [ ] **Caching** wo sinnvoll

---

## ✅ FINAL CHECKLIST

### Before Code Review
- [ ] Code läuft lokal ohne Fehler
- [ ] Tests geschrieben und passing
- [ ] Linter clean (`ruff check .`)
- [ ] Type checker clean (`mypy .`)
- [ ] Migration erstellt und getestet
- [ ] Documentation updated

### After Code Review
- [ ] Alle Review-Comments addressed
- [ ] Tests für Bug-Fixes hinzugefügt
- [ ] Performance Issues behoben
- [ ] Security Issues behoben
- [ ] Code formatted (`ruff format .`)

---

## 🚦 REVIEW OUTCOME

**Status:** [ ] APPROVED / [ ] CHANGES REQUESTED / [ ] REJECTED

**Summary:**
```
[Claude's Review Summary hier]
- Positive Punkte
- Verbesserungsbedarf
- Kritische Issues
- Nice-to-haves
```

**Next Steps:**
```
1. ...
2. ...
3. ...
```

---

**Reviewer:** Claude
**Date:** [Auto-generated]
**Review Duration:** [X] minutes
