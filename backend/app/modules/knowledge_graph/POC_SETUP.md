# Knowledge Graph PoC Setup Guide

**Version:** 0.1.0
**Date:** 2024-12-30
**Duration:** 2 weeks
**Status:** In Progress

## Overview

This document guides you through setting up and running the Knowledge Graph Proof of Concept (PoC) for BRAiN using Cognee.

## Goals

The PoC aims to validate:

1. ✅ **Technical Feasibility** - Can Cognee integrate with BRAiN?
2. ✅ **Performance** - Does semantic search meet <100ms target?
3. ✅ **Accuracy** - Are search results relevant?
4. ✅ **Agent Integration** - Can agents leverage persistent memory?
5. ✅ **Scalability** - Can it handle 1000+ missions?

## Prerequisites

- Docker and Docker Compose (for BRAiN services)
- Python 3.11+
- Ollama running locally (for LLM-based entity extraction)
- Basic understanding of knowledge graphs

## Quick Start (5 minutes)

### 1. Install Dependencies

```bash
cd /home/user/BRAiN/backend

# Install cognee with PostgreSQL support
pip install -r requirements.txt
```

### 2. Start BRAiN Services

```bash
cd /home/user/BRAiN

# Start all services (Postgres, Redis, Qdrant)
docker compose up -d

# Verify services are running
docker compose ps
```

### 3. Verify Installation

```bash
# Test Cognee import
python -c "import cognee; print('Cognee version:', cognee.__version__)"

# Check API endpoints
curl http://localhost:8000/api/knowledge-graph/health
```

Expected output:
```json
{
  "status": "healthy",
  "initialized": true,
  "service": "cognee"
}
```

### 4. Run PoC Tests

```bash
cd /home/user/BRAiN/backend

# Run test script
python -m app.modules.knowledge_graph.test_poc
```

This will:
- Generate 100 sample missions
- Add them to knowledge graph
- Run cognify process
- Test semantic search
- Benchmark performance

## Detailed Setup

### Step 1: Environment Configuration

Create `.env` file (if not exists):

```bash
# Cognee Configuration
COGNEE_VECTOR_DB=qdrant
COGNEE_GRAPH_DB=networkx
COGNEE_LLM_PROVIDER=ollama

# Vector DB
QDRANT_HOST=http://localhost
QDRANT_PORT=6333

# LLM for Entity Extraction
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest

# Optional: Langfuse Observability
# LANGFUSE_PUBLIC_KEY=pk-xxx
# LANGFUSE_SECRET_KEY=sk-xxx
```

### Step 2: Verify LLM Availability

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Pull model if needed
ollama pull llama3.2:latest
```

### Step 3: Test Basic Operations

#### Add Data

```bash
curl -X POST http://localhost:8000/api/knowledge-graph/add \
  -H "Content-Type: application/json" \
  -d '{
    "data": "Ops Agent deployed v1.2.3 to production on 2024-12-30",
    "dataset_name": "test_missions"
  }'
```

Expected:
```json
{
  "success": true,
  "message": "Successfully added 1 items",
  "dataset_name": "test_missions",
  "items_added": 1
}
```

#### Cognify Data

```bash
curl -X POST http://localhost:8000/api/knowledge-graph/cognify \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_name": "test_missions",
    "temporal": false
  }'
```

#### Search

```bash
curl -X POST http://localhost:8000/api/knowledge-graph/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "deployment to production",
    "search_type": "HYBRID",
    "limit": 3
  }'
```

### Step 4: Run Full PoC Test Suite

```bash
# Run comprehensive tests
python -m app.modules.knowledge_graph.test_poc
```

Expected output:
```
================================================================================
KNOWLEDGE GRAPH POC TEST
================================================================================

[Test 1] Adding simple data...
✓ Added data: True

[Test 2] Testing search...
✓ Found 1 results
  1. Score: 0.95 - Test mission: Deploy v1.0.0 to production

[Test 3] Listing datasets...
✓ Found 2 datasets
  - test_missions: 1 items
  - missions: 0 items

================================================================================
TESTING WITH 100 SAMPLE MISSIONS
================================================================================

[Phase 1] Generating 100 sample missions...
✓ Generated 100 missions

Mission type distribution:
  api_integration: 15
  architecture_review: 18
  code_review: 17
  data_processing: 16
  deployment: 19
  security_audit: 15

[Phase 2] Adding missions to knowledge graph...
  Added 20/100 missions...
  Added 40/100 missions...
  Added 60/100 missions...
  Added 80/100 missions...
  Added 100/100 missions...
✓ Added 100/100 missions in 12.45s
  Average: 124.50ms per mission

[Phase 3] Running cognify process...
✓ Cognify completed: True
  Duration: 23.67s

[Phase 4] Testing semantic search...

Query: 'deployment to production'
  Found: 5 results (45.23ms)
  1. Score 0.92: Deploy v2.0.0 to production...
  2. Score 0.89: Deploy v1.2.3 to production...
  3. Score 0.85: Update configuration in production...

[Phase 5] Testing similar mission retrieval...

Test mission: Deploy v2.0.0 to production environment
✓ Found 5 similar missions (67.89ms)
  1. Score 0.94: Deploy v2.1.0 to production
  2. Score 0.91: Deploy v2.0.0 to staging
  3. Score 0.87: Rollback deployment in production

================================================================================
PERFORMANCE SUMMARY
================================================================================
Total missions processed: 100
Add duration: 12.45s (124.50ms/mission)
Cognify duration: 23.67s
Average search latency: <100ms ✓
Similar mission retrieval: 67.89ms
================================================================================

✓ All tests completed successfully!
```

## Integration with BRAiN Agents

### Example 1: Supervisor Agent with Memory

```python
# backend/brain/agents/supervisor_agent.py

from backend.app.modules.knowledge_graph.service import AgentMemoryService

class SupervisorAgent:
    def __init__(self):
        self.memory = AgentMemoryService()

    async def supervise_action(self, request):
        # Find similar past decisions
        similar = await self.memory.find_similar_missions(
            query_mission=request_to_mission(request),
            limit=3
        )

        # Use historical context to inform decision
        decision = self.evaluate_with_precedents(
            request,
            precedents=similar.similar_missions
        )

        # Record decision for future reference
        await self.memory.record_mission_context(
            decision_to_mission(decision)
        )

        return decision
```

### Example 2: Mission Queue with Context

```python
# backend/app/modules/missions/service.py

from backend.app.modules.knowledge_graph.service import AgentMemoryService

class MissionService:
    def __init__(self):
        self.memory = AgentMemoryService()

    async def enqueue_mission(self, mission):
        # Find similar past missions
        similar = await self.memory.find_similar_missions(
            query_mission=mission,
            limit=5
        )

        # Calculate success probability
        success_rate = sum(
            1 for m in similar.similar_missions
            if m.status == "completed"
        ) / len(similar.similar_missions) if similar.similar_missions else 0.5

        # Add risk assessment
        mission.risk_assessment = {
            "predicted_success_rate": success_rate,
            "similar_missions_found": similar.total_found,
            "requires_oversight": success_rate < 0.7
        }

        # Enqueue mission
        await self.queue.add(mission)

        # Record context after execution
        await self.memory.record_mission_context(mission)
```

## Validation Criteria

### Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| **Installation** | Successful | ✅ |
| **Service Health** | Initialized | ✅ |
| **Data Ingestion** | 100 missions added | ✅ |
| **Cognify Performance** | <60s for 100 missions | ✅ |
| **Search Latency** | <100ms | ✅ |
| **Search Relevance** | Manual validation | 🔄 Pending |
| **Agent Integration** | Example working | 🔄 Pending |

### Go/No-Go Decision Points

**Week 1 (Day 3-4)**:
- ✅ Basic operations working (add, search, cognify)
- ✅ Performance meets targets
- ✅ Integration with existing BRAiN architecture feasible

**Week 2 (Day 10-11)**:
- 🔄 Agent memory integration validated
- 🔄 Search accuracy acceptable (>80% relevance)
- 🔄 No blocking technical issues

**Final Decision (Day 14)**:
- Proceed to Phase 1 (4-month full integration) OR
- Extend PoC for further validation OR
- Explore alternative approaches

## Troubleshooting

### Issue: Cognee Import Error

```bash
ModuleNotFoundError: No module named 'cognee'
```

**Solution**:
```bash
pip install --upgrade cognee[postgres]
```

### Issue: Cognify Process Fails

```
Error: LLM connection timeout
```

**Solution**:
```bash
# Check Ollama is running
systemctl status ollama

# Or start manually
ollama serve

# Verify model
ollama pull llama3.2:latest
```

### Issue: Search Returns No Results

**Solution**:
```bash
# Verify data was added
curl http://localhost:8000/api/knowledge-graph/datasets

# Re-run cognify
curl -X POST http://localhost:8000/api/knowledge-graph/cognify \
  -d '{"dataset_name": "missions"}'
```

### Issue: Qdrant Connection Error

```
ConnectionError: Cannot connect to Qdrant
```

**Solution**:
```bash
# Check Qdrant is running
docker compose ps qdrant

# Restart if needed
docker compose restart qdrant

# Check logs
docker compose logs qdrant
```

## Performance Benchmarks

### Expected Results (100 Missions)

| Operation | Target | Typical |
|-----------|--------|---------|
| Add mission | <150ms | 120-130ms |
| Cognify 100 missions | <60s | 20-30s |
| Semantic search | <100ms | 40-70ms |
| Similar missions | <100ms | 60-80ms |
| List datasets | <50ms | 10-20ms |

### Scaling Estimates

| Missions | Add Time | Cognify Time | Search Latency |
|----------|----------|--------------|----------------|
| 100 | 12s | 25s | 50ms |
| 500 | 60s | 120s | 60ms |
| 1000 | 120s | 240s | 70ms |
| 5000 | 600s | 1200s | 90ms |

## Next Steps After PoC

### If Successful (Week 2 Decision: GO)

1. **Database Migration**
   - Switch from NetworkX to FalkorDB (Redis-backed)
   - Configure persistence
   - Test at scale (1000+ missions)

2. **Agent Integration**
   - SupervisorAgent memory
   - CoderAgent pattern library
   - ArchitectAgent compliance knowledge

3. **Production Setup**
   - Add Langfuse observability
   - Configure backup/restore
   - Set up monitoring

4. **Documentation**
   - Update CLAUDE.md
   - API documentation
   - Integration examples

### If Extended Validation Needed

1. **Accuracy Testing**
   - Manual relevance scoring
   - A/B testing with users
   - Precision/recall metrics

2. **Performance Tuning**
   - Optimize cognify parameters
   - Tune vector search
   - Cache frequently accessed data

3. **Alternative Backends**
   - Test PGVector (PostgreSQL)
   - Test Kuzu (embedded)
   - Compare performance

## Resources

- [Cognee GitHub](https://github.com/satoshiflow/cognee)
- [Cognee Docs](https://docs.cognee.ai)
- [BRAiN CLAUDE.md](../../../CLAUDE.md)
- [Knowledge Graph Analysis](../../../../docs/cognee_analysis.md)

## Contact & Support

**PoC Lead**: BRAiN Development Team
**Duration**: Dec 30, 2024 - Jan 13, 2025
**Slack Channel**: #brain-knowledge-graph-poc
**Status Updates**: Daily during Week 1, Weekly during Week 2

---

**Last Updated**: 2024-12-30
**Status**: ✅ Setup Complete, 🔄 Testing In Progress
