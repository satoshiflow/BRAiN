# AXE + ControlDeck Help Docs Seed Runbook

This runbook describes how to reseed canonical help documents used by:

- AXE help pages (`/help/[topic]`)
- ControlDeck v3 help pages (`/help/[topic]`)
- Knowledge Engine help endpoints (`/api/knowledge-engine/help*`)

## Scope

The seeding source is:

- `backend/app/modules/knowledge_engine/help_docs_seed.py`

It creates or updates `knowledge_items` rows with:

- `type = help_doc`
- `metadata.help_key`
- `metadata.surface`

## Startup behavior

On backend startup, seeding runs automatically when:

- `ENABLE_KNOWLEDGE_HELP_SEED=true` (default)

Hook location:

- `backend/main.py`

## Manual reseed (running Docker stack)

From repo root:

```bash
docker exec brain-backend python -c "import asyncio; from app.core.database import AsyncSessionLocal; from app.modules.knowledge_engine.help_docs_seed import seed_help_documents; exec('async def _run():\n    async with AsyncSessionLocal() as db:\n        await seed_help_documents(db)'); asyncio.run(_run())"
```

Expected log snippet:

```text
Knowledge help docs seeding complete: created=<n> updated=<m> total=7
```

## Verification

1) Get access token:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"admin123"}'
```

2) List help docs by surface:

```bash
curl "http://localhost:8000/api/knowledge-engine/help?surface=axe-ui&limit=50" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

curl "http://localhost:8000/api/knowledge-engine/help?surface=controldeck-v3&limit=50" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

3) Fetch one detail doc:

```bash
curl "http://localhost:8000/api/knowledge-engine/help/axe.chat.intent?surface=axe-ui" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

## Current canonical topic keys

- AXE: `axe.chat.intent`, `axe.health.indicator`, `axe.navigation`
- ControlDeck v3: `skills.catalog`, `knowledge.explorer`, `healing.actions`, `settings.appearance`

## Troubleshooting

- `ModuleNotFoundError ... help_docs_seed`: backend container is stale. Rebuild backend image.
- `401` on help endpoint: missing/expired bearer token.
- `TimeoutError` while seeding locally: DB not reachable from host shell; run seeding inside backend container.
