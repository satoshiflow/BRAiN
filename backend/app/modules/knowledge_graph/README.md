# Knowledge Graph Module

**Version:** 0.1.0 (PoC)
**Status:** Proof of Concept
**Backend:** Cognee

## Overview

The Knowledge Graph module provides semantic memory and knowledge graph capabilities for BRAiN using [Cognee](https://github.com/satoshiflow/cognee). This enables:

- **Persistent Agent Memory** - Agents remember decisions across sessions
- **Semantic Search** - Find similar missions and contexts using natural language
- **Knowledge Graph Reasoning** - Connect facts through entity-relationship triplets
- **Audit Trail** - Structured decision history for compliance (DSGVO, EU AI Act)

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  BRAiN Application                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │ Supervisor │  │   Coder    │  │    Ops     │   │
│  │   Agent    │  │   Agent    │  │   Agent    │   │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘   │
│        │                │                │          │
│        └────────────────┼────────────────┘          │
│                         ▼                           │
│           ┌──────────────────────────┐              │
│           │  AgentMemoryService      │              │
│           │  - record_mission()      │              │
│           │  - find_similar()        │              │
│           │  - get_expertise()       │              │
│           └────────────┬─────────────┘              │
│                        │                            │
│                        ▼                            │
│           ┌──────────────────────────┐              │
│           │    CogneeService         │              │
│           │  - add_data()            │              │
│           │  - cognify()             │              │
│           │  - search()              │              │
│           └────────────┬─────────────┘              │
└────────────────────────┼──────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │         Cognee Backend         │
        │  ┌──────────┐  ┌─────────────┐ │
        │  │  Vector  │  │    Graph    │ │
        │  │   DB     │  │     DB      │ │
        │  │ (Qdrant) │  │ (NetworkX)  │ │
        │  └──────────┘  └─────────────┘ │
        └────────────────────────────────┘
```

## Core Concepts

### 1. ECL Pipeline (Extract-Cognify-Load)

Cognee uses a three-phase process:

```
Extract → Cognify → Load
   ↓         ↓        ↓
Raw Data → Knowledge → Memory
          Graph + Vector
```

**Extract**: Ingest data from missions, logs, conversations
**Cognify**: Extract entities and relationships as triplets
**Load**: Persist to vector DB + graph DB

### 2. Knowledge Triplets

Data is structured as **subject-predicate-object** triplets:

```
Mission_123 → assigned_to → Ops_Agent
Ops_Agent → role → "Operations Specialist"
Mission_123 → requires_policy → DataProtectionPolicy
```

### 3. Hybrid Search

Combines vector similarity (breadth) with graph relationships (precision):

- **Vector Search**: "Find missions with similar descriptions"
- **Graph Traversal**: "Show policy chain for this decision"
- **Hybrid**: Best of both worlds

## Quick Start

### 1. Installation

Cognee is already added to `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 2. Configuration

Set environment variables (optional, defaults work):

```bash
# Vector database (Qdrant is default)
VECTOR_DB_URL=http://qdrant:6333

# Graph database (NetworkX is default for PoC)
GRAPH_DB_TYPE=networkx

# LLM for entity extraction
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest
```

### 3. Basic Usage

#### Add Data

```bash
curl -X POST http://localhost:8000/api/knowledge-graph/add \
  -H "Content-Type: application/json" \
  -d '{
    "data": "Mission Deploy_v1.2.3 was completed by Ops Agent on 2024-12-30",
    "dataset_name": "missions"
  }'
```

#### Cognify (Process Data)

```bash
curl -X POST http://localhost:8000/api/knowledge-graph/cognify \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_name": "missions",
    "temporal": false
  }'
```

#### Search

```bash
curl -X POST http://localhost:8000/api/knowledge-graph/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "deployment missions by Ops Agent",
    "search_type": "HYBRID",
    "limit": 5
  }'
```

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/knowledge-graph/info` | System information |
| POST | `/api/knowledge-graph/add` | Add data to knowledge graph |
| POST | `/api/knowledge-graph/cognify` | Process data (extract entities) |
| POST | `/api/knowledge-graph/search` | Semantic search |
| GET | `/api/knowledge-graph/datasets` | List all datasets |
| DELETE | `/api/knowledge-graph/reset` | Reset all data (CAUTION) |

### Agent Memory Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/knowledge-graph/missions/record` | Record mission context |
| POST | `/api/knowledge-graph/missions/similar` | Find similar missions |
| GET | `/api/knowledge-graph/agents/{agent_id}/expertise` | Get agent expertise |

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/knowledge-graph/health` | Service health status |

## Integration Examples

### 1. Record Mission Context (Python)

```python
from backend.app.modules.knowledge_graph.service import AgentMemoryService
from backend.app.modules.knowledge_graph.schemas import MissionContextRequest

memory_service = AgentMemoryService()

# Record mission after completion
mission = MissionContextRequest(
    mission_id="mission_123",
    name="Deploy Application",
    description="Deploy v1.2.3 to production",
    status="completed",
    priority="HIGH",
    assigned_agent="ops_agent",
    mission_type="deployment",
    result={"success": True, "deployed_version": "1.2.3"}
)

response = await memory_service.record_mission_context(mission)
print(f"Recorded: {response.success}")
```

### 2. Find Similar Missions

```python
# When planning new mission, find similar past missions
new_mission = MissionContextRequest(
    mission_id="mission_456",
    name="Deploy New Feature",
    description="Deploy feature X to production",
    priority="HIGH",
    mission_type="deployment",
)

similar = await memory_service.find_similar_missions(
    query_mission=new_mission,
    limit=5
)

for m in similar.similar_missions:
    print(f"{m.name}: {m.similarity_score:.2f}")
    # Use for risk assessment, learning from past failures
```

### 3. Supervisor Agent with Memory

```python
from backend.brain.agents.supervisor_agent import SupervisorAgent
from backend.app.modules.knowledge_graph.service import AgentMemoryService

supervisor = SupervisorAgent()
memory = AgentMemoryService()

async def supervise_with_memory(request: SupervisionRequest):
    # Find precedent decisions
    similar = await memory.find_similar_missions(
        query_mission=request_to_mission(request),
        limit=3
    )

    # Inform decision with historical context
    response = await supervisor.supervise_action(
        request,
        precedents=similar.similar_missions
    )

    # Record decision for future reference
    await memory.record_mission_context(
        decision_to_mission(response)
    )

    return response
```

## Use Cases

### 1. Constitutional Agent Decision Support

**Problem**: Supervisor needs to decide if CoderAgent can process personal data.

**Solution**: Query knowledge graph for similar past decisions:

```python
query = "previous decisions about processing personal data in production"
results = await cognee_service.search(query, dataset_name="supervision_decisions")

# Use results to inform current decision
if results.total_results > 0:
    # Learn from past patterns
    risk_level = infer_risk_from_precedents(results)
```

### 2. Policy Compliance Audit

**Problem**: Generate compliance report for DSGVO Article 22.

**Solution**: Extract all automated decisions from knowledge graph:

```python
query = "all automated decisions involving personal data in last 90 days"
audit_data = await cognee_service.search(
    query,
    dataset_name="supervision_decisions",
    limit=100
)

# Generate structured audit report
report = generate_compliance_report(audit_data)
```

### 3. Mission Success Prediction

**Problem**: Predict if new mission will succeed.

**Solution**: Find similar historical missions and analyze outcomes:

```python
similar = await memory_service.find_similar_missions(new_mission, limit=10)

success_rate = sum(
    1 for m in similar.similar_missions
    if m.status == "completed"
) / len(similar.similar_missions)

if success_rate < 0.7:
    # High risk - require human oversight
    mission.requires_oversight = True
```

## PoC Testing Plan

### Phase 1: Basic Functionality (Week 1)

1. **Setup & Validation**
   - Install cognee
   - Verify service initialization
   - Test basic add/search operations

2. **Sample Data Ingestion**
   - Create 100 sample missions
   - Add to knowledge graph
   - Run cognify process

3. **Search Validation**
   - Test semantic search
   - Validate result relevance
   - Measure search latency

### Phase 2: Integration Testing (Week 2)

1. **Mission Integration**
   - Record real mission data
   - Test similar mission retrieval
   - Validate accuracy

2. **Agent Memory**
   - Test agent expertise extraction
   - Validate decision history
   - Measure performance

3. **Performance Benchmarks**
   - Query latency: Target <100ms
   - Cognify speed: 100 missions in <60s
   - Search relevance: Manual validation

## Configuration

### Environment Variables

```bash
# Cognee Configuration
COGNEE_VECTOR_DB=qdrant          # Vector database backend
COGNEE_GRAPH_DB=networkx         # Graph database backend
COGNEE_LLM_PROVIDER=ollama       # LLM for entity extraction

# Vector DB (Qdrant)
QDRANT_HOST=http://qdrant
QDRANT_PORT=6333

# LLM (Ollama)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest

# Optional: Langfuse Observability
LANGFUSE_PUBLIC_KEY=pk-xxx
LANGFUSE_SECRET_KEY=sk-xxx
```

### Database Options

**Vector Storage**:
- `qdrant` - Production-ready (already in BRAiN)
- `pgvector` - PostgreSQL extension (no new service)
- `lancedb` - File-based (development)

**Graph Storage**:
- `networkx` - In-memory (PoC, fast)
- `falkordb` - Redis-based (leverage existing Redis)
- `kuzu` - Embedded (zero-ops)
- `neo4j` - Production-grade (enterprise)

## Limitations (PoC)

1. **Graph DB**: Using NetworkX (in-memory) - data not persisted
2. **Entity Extraction**: Depends on LLM quality
3. **Scale**: Not tested beyond 1000 missions
4. **Search Accuracy**: Requires tuning and validation

## Next Steps (Post-PoC)

1. **Production Graph DB**: Migrate to FalkorDB or Kuzu
2. **Persistent Storage**: Configure proper data persistence
3. **Performance Tuning**: Optimize cognify and search
4. **Integration**: Connect with all Constitutional Agents
5. **Observability**: Add Langfuse for LLM tracking
6. **Testing**: Comprehensive integration tests

## Troubleshooting

### Cognee not initializing

```bash
# Check installation
pip list | grep cognee

# Reinstall with postgres support
pip install --upgrade cognee[postgres]
```

### Search returns no results

```bash
# Verify data was cognified
curl http://localhost:8000/api/knowledge-graph/datasets

# Re-run cognify
curl -X POST http://localhost:8000/api/knowledge-graph/cognify \
  -d '{"dataset_name": "missions"}'
```

### LLM errors during cognify

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Verify model is available
ollama list
```

## Resources

- [Cognee GitHub](https://github.com/satoshiflow/cognee)
- [Cognee Documentation](https://docs.cognee.ai)
- [BRAiN CLAUDE.md](../../../CLAUDE.md) - Full system documentation
- [Knowledge Graph Analysis Report](../../../../docs/cognee_analysis.md)

## Support

For issues with this module:
1. Check logs: `docker compose logs backend | grep "knowledge_graph"`
2. Verify health: `GET /api/knowledge-graph/health`
3. Review configuration in `.env`

---

**Maintained by**: BRAiN Development Team
**Last Updated**: 2024-12-30
**Phase**: PoC (Proof of Concept)
