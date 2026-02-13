# LLM Router Module

**Version:** 0.1.0
**Status:** Active
**Backend:** litellm

## Overview

The LLM Router module provides unified LLM access with intelligent provider routing and abstraction. It enables BRAiN to use multiple LLM providers simultaneously while maintaining clean separation between local and API-based models.

### Key Features

- 🔄 **Multi-Provider Support** - Ollama, OpenRouter, OpenAI, Anthropic
- 🏠 **Local + API Separation** - AXE uses local, Constitutional Agents use API
- 🌐 **OpenWebUI Compatible** - Full OpenWebUI integration endpoints
- 🔁 **Automatic Fallback** - Graceful degradation to backup providers
- 🎯 **Agent-Specific Routing** - Different providers for different agents
- 📊 **Health Monitoring** - Real-time provider status checks
- ⚡ **litellm Powered** - Industry-standard LLM abstraction

## Architecture

```
┌──────────────────────────────────────────────────────┐
│              LLM Router Service                       │
├───────────────────────────┬──────────────────────────┤
│   LOCAL PROVIDER          │   API PROVIDERS          │
│   ┌─────────────┐         │   ┌────────────────┐   │
│   │   Ollama    │         │   │  OpenRouter    │   │
│   │ (llama3.2)  │         │   │ (Claude, GPT)  │   │
│   └──────┬──────┘         │   └────────┬───────┘   │
│          │                │            │            │
│          ▼                │            ▼            │
│   ┌─────────────┐         │   ┌────────────────┐   │
│   │  AXE Agent  │         │   │ Constitutional │   │
│   │             │         │   │    Agents      │   │
│   │  - Local    │         │   │  - SupervisorAgent  │
│   │  - Fast     │         │   │  - CoderAgent │   │
│   │  - Private  │         │   │  - ArchitectAgent  │
│   └─────────────┘         │   │  - KnowledgeGraph │
│                           │   └────────────────┘   │
└───────────────────────────┴──────────────────────────┘
```

## Supported Providers

### 1. Ollama (Local)

**Use Case**: AXE Agent, development, private data

**Configuration**:
```bash
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest
```

**Features**:
- ✅ No API costs
- ✅ Complete privacy
- ✅ Fast local inference
- ✅ No rate limits
- ❌ Requires local GPU/CPU
- ❌ Limited to installed models

### 2. OpenRouter (Recommended)

**Use Case**: Constitutional Agents, production, best-in-class models

**Configuration**:
```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_SITE_URL=https://brain.falklabs.de
OPENROUTER_SITE_NAME=BRAiN
```

**Features**:
- ✅ Access to 100+ models (Claude, GPT-4, Llama, etc.)
- ✅ Single API key for all providers
- ✅ Pay-per-use pricing
- ✅ No separate API keys needed
- ✅ Automatic best-price routing
- ❌ Requires internet
- ❌ Costs per token

**Available Models**:
- `anthropic/claude-3.5-sonnet` (Recommended)
- `anthropic/claude-3-opus`
- `openai/gpt-4-turbo`
- `openai/gpt-4`
- `google/gemini-pro`
- `meta-llama/llama-3-70b-instruct`

### 3. OpenAI (Direct)

**Use Case**: When you need pure OpenAI models

**Configuration**:
```bash
OPENAI_API_KEY=sk-xxxxx
OPENAI_MODEL=gpt-4-turbo-preview
```

### 4. Anthropic (Direct)

**Use Case**: When you need pure Claude models

**Configuration**:
```bash
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

## Quick Start

### 1. Configure Environment

Create `.env` file:

```bash
# Local LLM (Ollama) - for AXE Agent
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest

# API LLM (OpenRouter) - for Constitutional Agents
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_SITE_URL=https://your-site.com
OPENROUTER_SITE_NAME=BRAiN

# Router Settings
LLM_DEFAULT_PROVIDER=ollama
LLM_ENABLE_FALLBACK=true
```

### 2. Test API

```bash
# Health check
curl http://localhost:8000/api/llm-router/health

# Get provider status
curl http://localhost:8000/api/llm-router/providers

# Send chat request (uses default provider)
curl -X POST http://localhost:8000/api/llm-router/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'

# Send chat request with specific provider
curl -X POST http://localhost:8000/api/llm-router/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Write a Python function"}
    ],
    "provider": "openrouter",
    "model": "anthropic/claude-3.5-sonnet",
    "temperature": 0.7
  }'
```

### 3. Python Usage

```python
from backend.app.modules.llm_router.service import get_llm_router
from backend.app.modules.llm_router.schemas import LLMRequest, ChatMessage, MessageRole, LLMProvider

# Get router instance
router = get_llm_router()

# Create request
request = LLMRequest(
    messages=[
        ChatMessage(
            role=MessageRole.USER,
            content="Explain async/await in Python"
        )
    ],
    provider=LLMProvider.OPENROUTER,
    model="anthropic/claude-3.5-sonnet",
    temperature=0.7,
    max_tokens=1000
)

# Send request
response = await router.chat(request, agent_id="supervisor_agent")

print(f"Response: {response.content}")
print(f"Provider: {response.provider}")
print(f"Tokens used: {response.usage}")
```

## Agent-Specific Routing

### AXE Agent (Local Only)

```python
# AXE Agent automatically uses Ollama
request = LLMRequest(
    messages=[ChatMessage(role=MessageRole.USER, content="Hello")],
    provider=LLMProvider.AUTO  # Will be forced to OLLAMA
)

response = await router.chat(request, agent_id="axe_agent")
# Always uses Ollama regardless of provider setting
```

### Constitutional Agents (API)

```python
# Supervisor Agent uses OpenRouter
request = LLMRequest(
    messages=[ChatMessage(role=MessageRole.USER, content="Review this code")],
    provider=LLMProvider.OPENROUTER,
    model="anthropic/claude-3.5-sonnet"
)

response = await router.chat(request, agent_id="supervisor_agent")
# Uses OpenRouter with Claude 3.5 Sonnet
```

## OpenWebUI Integration

### Setup OpenWebUI

1. **Configure OpenWebUI to use BRAiN as backend**:

```bash
# OpenWebUI environment
OPENAI_API_BASE=http://localhost:8000/api/llm-router/openwebui
OPENAI_API_KEY=not-needed
```

2. **Verify compatibility**:

```bash
curl http://localhost:8000/api/llm-router/openwebui/compatibility
```

3. **Test models endpoint**:

```bash
curl http://localhost:8000/api/llm-router/openwebui/models
```

### OpenWebUI Features Supported

- ✅ Chat completions
- ✅ Model selection
- ✅ Streaming responses
- ✅ Temperature control
- ✅ Max tokens configuration
- ✅ Multi-provider routing

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/llm-router/info` | Router information |
| POST | `/api/llm-router/chat` | Send chat request |
| GET | `/api/llm-router/providers` | Provider health status |
| GET | `/api/llm-router/providers/{provider}/models` | List models |
| GET | `/api/llm-router/health` | Health check |

### OpenWebUI Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/llm-router/openwebui/compatibility` | Compatibility info |
| POST | `/api/llm-router/openwebui/chat/completions` | Chat (OpenAI format) |
| GET | `/api/llm-router/openwebui/models` | Models list (OpenAI format) |

### Chat Request Format

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Your message here"
    }
  ],
  "provider": "openrouter",
  "model": "anthropic/claude-3.5-sonnet",
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false
}
```

### Chat Response Format

```json
{
  "content": "AI response here",
  "provider": "openrouter",
  "model": "openrouter/anthropic/claude-3.5-sonnet",
  "finish_reason": "stop",
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 50,
    "total_tokens": 60
  },
  "metadata": {
    "latency_ms": 1234.56,
    "agent_id": "supervisor_agent"
  }
}
```

## Configuration

### Environment Variables

```bash
# === Ollama (Local) ===
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest

# === OpenRouter (Recommended) ===
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_SITE_URL=https://your-site.com
OPENROUTER_SITE_NAME=BRAiN

# === OpenAI (Optional) ===
OPENAI_API_KEY=sk-xxxxx
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_ORGANIZATION=org-xxxxx

# === Anthropic (Optional) ===
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# === Router Settings ===
LLM_DEFAULT_PROVIDER=ollama
LLM_ENABLE_FALLBACK=true
LLM_CACHE_ENABLED=true
LLM_CACHE_TTL=3600
```

### Provider Priority

```python
# Configure in code
from backend.app.modules.llm_router.schemas import LLMRouterConfig, OllamaConfig, OpenRouterConfig

config = LLMRouterConfig(
    default_provider=LLMProvider.OLLAMA,
    enable_fallback=True,

    ollama=OllamaConfig(
        enabled=True,
        priority=100,  # Highest priority
        restrict_to_agents=["axe_agent"]
    ),

    openrouter=OpenRouterConfig(
        enabled=True,
        priority=90,
        fallback_providers=[LLMProvider.OLLAMA]
    )
)

router = get_llm_router(config)
```

## Routing Logic

### Provider Selection Flow

```
1. Check agent_id
   ├─ If "axe" in agent_id → Force OLLAMA
   └─ Continue

2. Check requested provider
   ├─ If provider != AUTO → Use requested provider
   └─ Continue

3. Use default provider
   └─ Return config.default_provider
```

### Fallback Logic

```
1. Send request to primary provider
   ├─ Success → Return response
   └─ Failure → Continue

2. If fallback enabled
   ├─ Try fallback provider(s)
   │  ├─ Success → Return response
   │  └─ Failure → Continue
   └─ Raise exception
```

## Cost Management

### OpenRouter Pricing

- **Claude 3.5 Sonnet**: ~$3/M input tokens, ~$15/M output tokens
- **GPT-4**: ~$10/M input tokens, ~$30/M output tokens
- **Llama 3 70B**: ~$0.60/M input tokens, ~$0.80/M output tokens

### Cost Optimization Strategies

1. **Use Ollama for development**:
   ```python
   # Development: Free local inference
   provider = LLMProvider.OLLAMA if os.getenv("ENV") == "dev" else LLMProvider.OPENROUTER
   ```

2. **Set max token limits**:
   ```python
   request = LLMRequest(
       messages=messages,
       max_tokens=500,  # Limit response length
   )
   ```

3. **Use cheaper models for simple tasks**:
   ```python
   # Simple task → Llama 3
   model = "meta-llama/llama-3-70b-instruct"

   # Complex task → Claude 3.5
   model = "anthropic/claude-3.5-sonnet"
   ```

4. **Enable caching**:
   ```python
   config = LLMRouterConfig(
       enable_caching=True,
       cache_ttl=3600  # Cache for 1 hour
   )
   ```

## Troubleshooting

### Issue: "litellm not available"

**Solution**:
```bash
pip install litellm>=1.76.0
```

### Issue: "OpenRouter API key not found"

**Solution**:
```bash
export OPENROUTER_API_KEY=sk-or-v1-your-key
# or add to .env file
```

### Issue: "Ollama connection refused"

**Solution**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
systemctl start ollama
# or
ollama serve
```

### Issue: "Provider health check failed"

**Check logs**:
```bash
docker compose logs backend | grep "llm_router"
```

**Test provider manually**:
```bash
# Test Ollama
curl http://localhost:11434/api/generate \
  -d '{"model": "llama3.2", "prompt": "test"}'

# Test OpenRouter
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

## Performance

### Expected Latencies

| Provider | Type | Latency (p50) | Latency (p95) |
|----------|------|---------------|---------------|
| Ollama | Local | 50-200ms | 500ms |
| OpenRouter | API | 500-2000ms | 5000ms |
| OpenAI | API | 500-1500ms | 4000ms |
| Anthropic | API | 500-2000ms | 5000ms |

### Optimization Tips

1. **Use streaming for long responses**:
   ```python
   request = LLMRequest(messages=messages, stream=True)
   ```

2. **Reduce temperature for consistency**:
   ```python
   request = LLMRequest(messages=messages, temperature=0.3)
   ```

3. **Batch requests when possible**:
   ```python
   # Process multiple requests concurrently
   tasks = [router.chat(req) for req in requests]
   responses = await asyncio.gather(*tasks)
   ```

## Security

### API Key Management

- ✅ **DO**: Store keys in environment variables
- ✅ **DO**: Use `.env` files (add to `.gitignore`)
- ✅ **DO**: Rotate keys regularly
- ❌ **DON'T**: Commit keys to git
- ❌ **DON'T**: Hardcode keys in code
- ❌ **DON'T**: Share keys in logs

### Rate Limiting

```python
# OpenRouter implements rate limiting automatically
# Additional application-level limiting:
from backend.app.modules.integrations.rate_limit import RateLimiter

limiter = RateLimiter(max_calls=100, time_period=60)  # 100 req/min

async with limiter:
    response = await router.chat(request)
```

## Integration Examples

### Example 1: Supervisor Agent with OpenRouter

```python
from backend.brain.agents.supervisor_agent import SupervisorAgent
from backend.app.modules.llm_router.service import get_llm_router
from backend.app.modules.llm_router.schemas import LLMRequest, ChatMessage, MessageRole, LLMProvider

class EnhancedSupervisorAgent(SupervisorAgent):
    def __init__(self):
        super().__init__()
        self.llm_router = get_llm_router()

    async def review_action(self, action_request):
        """Review action using Claude 3.5 via OpenRouter"""

        request = LLMRequest(
            messages=[
                ChatMessage(
                    role=MessageRole.SYSTEM,
                    content="You are a supervisor reviewing agent actions for EU AI Act compliance."
                ),
                ChatMessage(
                    role=MessageRole.USER,
                    content=f"Review this action: {action_request}"
                )
            ],
            provider=LLMProvider.OPENROUTER,
            model="anthropic/claude-3.5-sonnet",
            temperature=0.3,  # Low temp for consistent decisions
            max_tokens=1000
        )

        response = await self.llm_router.chat(request, agent_id="supervisor_agent")

        return {
            "approved": "approved" in response.content.lower(),
            "reasoning": response.content,
            "model_used": response.model,
            "tokens_used": response.usage
        }
```

### Example 2: Knowledge Graph with Fallback

```python
from backend.app.modules.knowledge_graph.service import CogneeService
from backend.app.modules.llm_router.service import get_llm_router
from backend.app.modules.llm_router.schemas import LLMRequest, ChatMessage, LLMProvider

class EnhancedCogneeService(CogneeService):
    def __init__(self):
        super().__init__()
        self.llm_router = get_llm_router()

    async def extract_entities(self, text):
        """Extract entities with automatic fallback"""

        request = LLMRequest(
            messages=[
                ChatMessage(
                    role=MessageRole.USER,
                    content=f"Extract entities from: {text}"
                )
            ],
            provider=LLMProvider.OPENROUTER,  # Try OpenRouter first
            temperature=0.1,  # Very deterministic
        )

        try:
            # Primary: OpenRouter (Claude)
            response = await self.llm_router.chat(request)
        except Exception:
            # Fallback: Ollama (local, free)
            logger.warning("OpenRouter failed, falling back to Ollama")
            request.provider = LLMProvider.OLLAMA
            response = await self.llm_router.chat(request)

        return parse_entities(response.content)
```

## Resources

- **litellm Documentation**: https://docs.litellm.ai
- **OpenRouter**: https://openrouter.ai
- **OpenWebUI**: https://github.com/open-webui/open-webui
- **Ollama**: https://ollama.com

## Support

For issues with this module:
1. Check logs: `docker compose logs backend | grep "llm_router"`
2. Verify configuration: `GET /api/llm-router/info`
3. Test providers: `GET /api/llm-router/providers`
4. Check health: `GET /api/llm-router/health`

---

**Maintained by**: BRAiN Development Team
**Last Updated**: 2024-12-30
**Status**: Active
