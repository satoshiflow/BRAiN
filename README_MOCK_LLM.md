# BRAiN Mock LLM Service

This is a lightweight OpenAI-compatible placeholder service for local BRAiN development.

It does not load any real model and exists only to satisfy API contracts in Local Micro mode.

## Why this exists

- Keep local RAM/CPU usage low on small Ubuntu machines.
- Preserve clean OpenAI-style API contracts.
- Avoid hard coupling to Ollama, local vLLM, or any heavy inference runtime.
- Enable later switch to external OpenAI-compatible endpoints via ENV only.

## Implemented endpoint

- `POST /v1/chat/completions`

Also exposed:

- `GET /healthz`

## Behavior

- Returns fixed/rule-based assistant text.
- Simulates model name and usage token counts.
- Simulates latency.
- Supports optional controlled failures (random rate or keyword trigger).

## Files

- `services/mock-llm/server.py`
- `services/mock-llm/Dockerfile`

## Start options

Using docker compose profile:

```bash
docker compose --profile mock-llm -f docker-compose.dev.yml up -d --build
```

Run service only (without compose):

```bash
cd services/mock-llm
python server.py
```

## ENV reference

- `MOCK_LLM_HOST` default `0.0.0.0`
- `MOCK_LLM_PORT` default `8080`
- `MOCK_LLM_MODEL` default `brain-mock-1`
- `MOCK_LLM_MODE` default `rules` (`rules` or `echo`)
- `MOCK_LLM_LATENCY_MIN_MS` default `40`
- `MOCK_LLM_LATENCY_MAX_MS` default `140`
- `MOCK_LLM_ERROR_RATE` default `0.0` (0.0 - 1.0)
- `MOCK_LLM_ERROR_STATUS` default `503`
- `MOCK_LLM_ERROR_TRIGGER` default `trigger_error`
- `MOCK_LLM_ALLOW_STREAM` default `false`

## Quick test

```bash
curl -s http://localhost:8081/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "mock-local",
    "messages": [
      {"role": "system", "content": "You are BRAiN."},
      {"role": "user", "content": "Give me a short health status"}
    ]
  }' | jq
```

## Swap to real remote LLM later (ENV-only)

When external OpenAI-compatible service is ready, BRAiN can switch without code rewrite:

1. Set:
   - `LLM_MODE=external`
   - `LLM_API_BASE=https://your-gateway.example.com/v1`
   - `LLM_API_KEY=<real-key>`
   - `LLM_DEFAULT_MODEL=<target-model>`
2. Stop using mock profile or keep it off.

Because BRAiN talks via OpenAI-compatible contract, the runtime target changes through ENV only.
