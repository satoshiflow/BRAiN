# BRAiN Local Micro Dev Stack

This stack is the first local BRAiN development profile for small Ubuntu machines (8 GB RAM target).

It is intentionally minimal and resource-aware.

## Architecture intent

- BRAiN Core remains the highest instance.
- OpenCode is a dev/repair layer inside the BRAiN ecosystem.
- Agent, LLM, and worker responsibilities stay separated.
- Local setup is pragmatic, but production architecture is not collapsed into local shortcuts.
- LLM is API-first and swappable (mock now, external OpenAI-compatible server later).

## What this stack includes

- PostgreSQL (separate container)
- Redis (separate container)
- Qdrant (separate container)
- Optional mock LLM placeholder container (profile `mock-llm`)

No Ollama or vLLM dependency is required for this profile.

## Files

- `docker-compose.dev.yml`
- `.env.example`

## Ports (host -> container)

- PostgreSQL: `5432 -> 5432` (configurable via `POSTGRES_PORT_HOST`)
- Redis: `6379 -> 6379` (configurable via `REDIS_PORT_HOST`)
- Qdrant HTTP: `6333 -> 6333` (configurable via `QDRANT_HTTP_PORT_HOST`)
- Qdrant gRPC: `6334 -> 6334` (configurable via `QDRANT_GRPC_PORT_HOST`)
- Mock LLM (optional): `8081 -> 8080` (configurable via `MOCK_LLM_PORT_HOST`)

## Quick start (Ubuntu)

1. Create `.env` from template:

```bash
cp .env.example .env
```

2. Start the core local micro services:

```bash
docker compose -f docker-compose.dev.yml up -d
```

3. (Optional) Start with mock LLM profile:

```bash
docker compose --profile mock-llm -f docker-compose.dev.yml up -d
```

4. Check service health:

```bash
docker compose -f docker-compose.dev.yml ps
```

## Stop and cleanup

Stop containers only:

```bash
docker compose -f docker-compose.dev.yml down
```

Stop and remove volumes (destructive):

```bash
docker compose -f docker-compose.dev.yml down -v
```

## Resource profile notes

- Services have memory and CPU caps tuned for small machines.
- Volumes persist data across restarts.
- Healthchecks are enabled for all services to support predictable startup and diagnostics.

## Next step (not part of this step-1 delivery)

Wire BRAiN Core API and OpenCode runtime to these service contracts, keeping LLM access abstracted behind `LLM_API_BASE`.
