# AXEllm - OpenAI Compatible API for Ollama

AXEllm is a lightweight FastAPI service that provides an OpenAI-compatible chat completions API, routing requests to a local Ollama instance.

> **Version:** 1.0.0  
> **Image:** `ghcr.io/satoshiflow/brain/axellm:latest`

## Features

- OpenAI-compatible `/v1/chat/completions` endpoint
- Supports system, user, and assistant roles
- Configurable model and temperature
- Built-in guardrails (max 20k characters, role validation)
- Health check endpoint
- CORS enabled for browser clients

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://ollama-qwen:11434` | Ollama API URL |
| `DEFAULT_MODEL` | `qwen:0.5b` | Default LLM model |
| `REQUEST_TIMEOUT_SECONDS` | `60` | Request timeout |

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Chat Completion
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen:0.5b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.7
  }'
```

### With System Message
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen:0.5b",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What can you do?"}
    ],
    "temperature": 0.7
  }'
```

## Running Locally

```bash
cd services/axellm
pip install -r requirements.txt
python main.py
```

## Docker

```bash
docker build -t axellm .
docker run -p 8000:8000 -e OLLAMA_BASE_URL=http://host.docker.internal:11434 axellm
```
