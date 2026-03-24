# AXE Local Chat Pipeline Runbook

Purpose: provide one reproducible local path for validating AXE UI -> BRAiN backend -> mock OpenAI-compatible LLM without relying on Hetzner production.

## Scope

- AXE UI at `frontend/axe_ui`
- BRAiN backend AXE chat route
- mock LLM server at `scripts/mock_llm_server.py`
- manual Playwright coverage at `frontend/axe_ui/e2e/manual/backend-chat-pipeline.spec.ts`

## Local prerequisites

1. Infrastructure available for backend local mode.
2. Backend env allows local AXE ingress:
   - `AXE_FUSION_ALLOW_LOCAL_REQUESTS=true`
   - `AXE_FUSION_ALLOW_LOCAL_FALLBACK=true`
3. AXE runtime points to the local backend:
   - `NEXT_PUBLIC_APP_ENV=local`
   - `NEXT_PUBLIC_BRAIN_API_BASE=http://127.0.0.1:8000`

## Mock LLM setup

Start the local OpenAI-compatible mock:

```bash
python3 scripts/mock_llm_server.py
```

Expected behavior:

- `GET /models` returns `mock-model`
- `POST /chat/completions` replies with `MOCK-LLM ACK: <last user message>`

## Backend runtime setup

Run the backend with an explicit OpenAI-compatible provider target:

```bash
cd backend
export BRAIN_RUNTIME_MODE=local
export AXE_FUSION_ALLOW_LOCAL_REQUESTS=true
export AXE_FUSION_ALLOW_LOCAL_FALLBACK=true
export LOCAL_LLM_MODE=openai
export OPENAI_BASE_URL=http://127.0.0.1:8099
export OPENAI_API_KEY=dummy-local-key
export OPENAI_MODEL=mock-model
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Verification target:

- `POST /api/axe/chat` should resolve through the OpenAI-compatible mock, not production services.

## AXE UI setup

```bash
cd frontend/axe_ui
NEXT_PUBLIC_APP_ENV=local NEXT_PUBLIC_BRAIN_API_BASE=http://127.0.0.1:8000 npm run dev
```

Open:

- `http://127.0.0.1:3002/widget-test`

## Manual validation flow

1. Open the widget test page.
2. Click `Open AXE chat`.
3. Send: `Hallo AXE, bitte pruefe die Backend-Verbindung.`
4. Confirm the widget shows:
   - the original user message
   - `MOCK-LLM ACK: Hallo AXE, bitte pruefe die Backend-Verbindung.`
5. Confirm backend logs show an AXE chat request without fallback to production endpoints.

## Optional Playwright execution

The manual spec captures request/response traces but is intentionally outside the default CI smoke set.

Recommended execution pattern:

```bash
cd frontend/axe_ui
npx playwright test e2e/manual/backend-chat-pipeline.spec.ts --project=chromium
```

## Expected success signals

- AXE UI loads from `127.0.0.1:3002`
- Network calls target `127.0.0.1:8000/api/axe/chat`
- backend reaches `http://127.0.0.1:8099/v1/chat/completions`
- response text contains `MOCK-LLM ACK:`

## Fail-closed rules

- Do not point local dev verification at production API endpoints.
- If `OPENAI_BASE_URL` is unset, stop and re-check env instead of assuming remote OpenAI access.
- Keep the manual pipeline spec out of automatic CI until the local stack is deterministic enough for unattended runs.
