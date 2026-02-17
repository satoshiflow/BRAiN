# BRAiN Integrations Module

**Generic API Client Framework for External Integrations**

Version: 1.0.0
Status: Production-Ready

---

## Overview

The Integrations module provides a robust, production-ready foundation for ALL external API integrations in BRAiN. It implements enterprise-grade patterns including:

- **Automatic Retry** with exponential backoff and jitter
- **Circuit Breaker** for resilience against cascading failures
- **Rate Limiting** with token bucket algorithm and burst support
- **Multi-Auth Support** (API Key, OAuth 2.0, Basic, Bearer, Custom)
- **Request/Response Logging** with configurable detail levels
- **Metrics Collection** for monitoring and debugging
- **Connection Pooling** for optimal performance
- **Timeout Management** with separate connect/read timeouts

---

## Quick Start

### Installation

The module is already integrated into BRAiN. No additional installation needed.

### Basic Usage

```python
from backend.app.modules.integrations import (
    BaseAPIClient,
    APIClientConfig,
    AuthConfig,
    AuthType,
)

# 1. Define your API client
class MyAPIClient(BaseAPIClient):
    async def _build_base_url(self) -> str:
        return "https://api.example.com"

    async def get_users(self):
        response = await self.get("/users")
        return response.body

# 2. Configure the client
config = APIClientConfig(
    name="my_api",
    base_url="https://api.example.com",
    auth=AuthConfig(
        type=AuthType.API_KEY,
        token="sk-your-api-key",
        token_key="X-API-Key",
    ),
)

# 3. Use the client
async with MyAPIClient(config).session():
    users = await client.get_users()
```

---

## Core Components

### 1. BaseAPIClient

Abstract base class for all API integrations.

**Features:**
- HTTP methods: `get()`, `post()`, `put()`, `patch()`, `delete()`
- Automatic auth injection
- Built-in retry, rate limiting, circuit breaker
- Response parsing (JSON/text)
- Metrics tracking

**Subclass Requirements:**
```python
class MyClient(BaseAPIClient):
    async def _build_base_url(self) -> str:
        """REQUIRED: Return base URL for API."""
        return self.config.base_url
```

**Optional Overrides:**
```python
async def _prepare_request(self, method, path, **kwargs):
    """Customize request preparation."""
    # Add custom headers, modify params, etc.
    return await super()._prepare_request(method, path, **kwargs)

async def _handle_response(self, response, start_time):
    """Customize response handling."""
    # Parse custom formats, extract metadata, etc.
    return await super()._handle_response(response, start_time)

async def health_check(self) -> bool:
    """Custom health check."""
    # Ping specific endpoint, check status, etc.
    return await super().health_check()
```

---

### 2. Authentication Manager

Supports multiple authentication types with automatic token refresh (OAuth 2.0).

#### API Key Authentication

```python
from backend.app.modules.integrations import create_api_key_auth

auth = create_api_key_auth(
    api_key="sk-abc123",
    header_name="X-API-Key",  # or "Authorization"
    prefix=None,  # or "Bearer", "ApiKey", etc.
)
```

#### Bearer Token

```python
from backend.app.modules.integrations import create_bearer_auth

auth = create_bearer_auth("my-token-123")
# Sends: Authorization: Bearer my-token-123
```

#### Basic Authentication

```python
from backend.app.modules.integrations import create_basic_auth

auth = create_basic_auth("username", "password")
# Sends: Authorization: Basic <base64>
```

#### OAuth 2.0 (Client Credentials)

```python
from backend.app.modules.integrations import create_oauth2_auth

auth = create_oauth2_auth(
    client_id="client-123",
    client_secret="secret-456",
    token_url="https://auth.example.com/token",
    scopes=["read", "write"],
)

# Auth manager automatically:
# - Gets initial token
# - Refreshes when expired
# - Handles token storage
```

#### Custom Authentication

```python
config = AuthConfig(
    type=AuthType.CUSTOM,
    custom_headers={
        "X-Custom-Auth": "value",
        "X-Tenant-ID": "tenant-123",
    },
    custom_params={
        "api_key": "key-value",
    },
)
```

---

### 3. Rate Limiter

Token bucket algorithm with burst support and API header respect.

```python
from backend.app.modules.integrations import RateLimitConfig

rate_limit = RateLimitConfig(
    max_requests=100,        # 100 requests
    window_seconds=60.0,     # per 60 seconds
    burst_size=120,          # Allow bursts up to 120
    respect_retry_after=True, # Respect server headers
)
```

**How It Works:**

1. **Token Bucket:** Requests consume tokens. Tokens refill at constant rate.
2. **Burst Support:** Allow short bursts above average rate.
3. **Server Headers:** Automatically respects `Retry-After`, `X-RateLimit-*` headers.
4. **Wait Strategy:** If no tokens available, waits until tokens refill.

**Example:**
```python
# 10 requests/second with burst of 15
RateLimitConfig(
    max_requests=10,
    window_seconds=1.0,
    burst_size=15,  # Can send 15 requests instantly, then 10/sec
)
```

---

### 4. Circuit Breaker

Three-state circuit breaker (CLOSED → OPEN → HALF_OPEN) for resilience.

```python
from backend.app.modules.integrations import CircuitBreakerConfig

circuit_breaker = CircuitBreakerConfig(
    failure_threshold=5,        # Open after 5 failures
    recovery_timeout=60.0,      # Try recovery after 60s
    success_threshold=2,        # Need 2 successes to close
    failure_status_codes=[500, 502, 503, 504],
    count_timeouts_as_failures=True,
)
```

**States:**

1. **CLOSED (Normal):** Requests pass through. Failures are counted.
2. **OPEN (Blocking):** Failure threshold exceeded. All requests blocked.
3. **HALF_OPEN (Testing):** After recovery timeout. Testing if service recovered.

**State Transitions:**

```
CLOSED --[failures >= threshold]--> OPEN
OPEN --[recovery_timeout elapsed]--> HALF_OPEN
HALF_OPEN --[success_threshold met]--> CLOSED
HALF_OPEN --[any failure]--> OPEN
```

---

### 5. Retry Handler

Exponential backoff with jitter to prevent thundering herd.

```python
from backend.app.modules.integrations import RetryConfig, RetryStrategy

retry = RetryConfig(
    max_retries=3,              # Try up to 3 times
    strategy=RetryStrategy.EXPONENTIAL,
    initial_delay=1.0,          # Start with 1s delay
    max_delay=60.0,             # Cap at 60s
    backoff_multiplier=2.0,     # Double each time
    jitter=True,                # Add random ±25% jitter
    retry_status_codes=[408, 429, 500, 502, 503, 504],
    retry_on_timeout=True,
)
```

**Backoff Strategies:**

1. **Exponential:** `delay = initial * (multiplier ^ attempt)`
   - Attempt 0: 1s
   - Attempt 1: 2s
   - Attempt 2: 4s
   - Attempt 3: 8s

2. **Linear:** `delay = initial * (attempt + 1) * multiplier`
   - Attempt 0: 2s
   - Attempt 1: 4s
   - Attempt 2: 6s

3. **Fixed:** `delay = initial` (constant)

**Jitter:** Adds random ±25% to prevent synchronized retries across clients.

---

## Complete Example

### Production-Ready API Client

```python
from backend.app.modules.integrations import (
    BaseAPIClient,
    APIClientConfig,
    AuthConfig,
    AuthType,
    RateLimitConfig,
    CircuitBreakerConfig,
    RetryConfig,
)


class ProductionAPIClient(BaseAPIClient):
    """Production-grade API client with all protections enabled."""

    async def _build_base_url(self) -> str:
        # Could read from config, environment, etc.
        return self.config.base_url

    # Business logic methods
    async def create_order(self, order_data: dict):
        response = await self.post("/orders", json=order_data)
        return response.body

    async def get_order(self, order_id: str):
        response = await self.get(f"/orders/{order_id}")
        return response.body


# Configuration
config = APIClientConfig(
    name="production_api",
    base_url="https://api.production.com",

    # Authentication: OAuth 2.0
    auth=AuthConfig(
        type=AuthType.OAUTH2,
        client_id=os.getenv("API_CLIENT_ID"),
        client_secret=os.getenv("API_CLIENT_SECRET"),
        token_url="https://auth.production.com/token",
        scopes=["orders:read", "orders:write"],
    ),

    # Rate Limiting: 1000/hour with bursts
    rate_limit=RateLimitConfig(
        max_requests=1000,
        window_seconds=3600.0,
        burst_size=1100,
        respect_retry_after=True,
    ),

    # Circuit Breaker: Protect against cascading failures
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=10,
        recovery_timeout=60.0,
        success_threshold=3,
    ),

    # Retry: Exponential backoff with jitter
    retry=RetryConfig(
        max_retries=3,
        strategy=RetryStrategy.EXPONENTIAL,
        initial_delay=1.0,
        max_delay=30.0,
        jitter=True,
    ),

    # Timeouts
    timeout=30.0,
    connect_timeout=10.0,

    # Connection Pooling
    max_connections=100,
    max_keepalive_connections=20,

    # Logging
    log_requests=True,
    log_responses=True,
    log_response_body=False,  # Don't log sensitive data

    # Default Headers
    default_headers={
        "User-Agent": "BRAiN/1.0",
        "Accept": "application/json",
    },
)


# Usage
async def process_orders():
    async with ProductionAPIClient(config).session() as client:
        # Create order (with all protections)
        order = await client.create_order({
            "items": [{"sku": "ITEM-123", "quantity": 2}],
            "customer_id": "CUST-456",
        })

        print(f"Order created: {order['id']}")

        # Get metrics
        metrics = client.get_metrics()
        print(f"Requests: {metrics.total_requests}")
        print(f"Avg response time: {metrics.average_response_time_ms:.2f}ms")
```

---

## Configuration Reference

### APIClientConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | **required** | Client identifier |
| `base_url` | str | **required** | API base URL |
| `auth` | AuthConfig | None | Authentication config |
| `rate_limit` | RateLimitConfig | None | Rate limiting config |
| `circuit_breaker` | CircuitBreakerConfig | None | Circuit breaker config |
| `retry` | RetryConfig | None | Retry config |
| `timeout` | float | 30.0 | Request timeout (seconds) |
| `connect_timeout` | float | 10.0 | Connection timeout (seconds) |
| `default_headers` | dict | {} | Default headers for all requests |
| `log_requests` | bool | True | Log requests |
| `log_responses` | bool | True | Log responses |
| `log_response_body` | bool | False | Log response bodies (may contain sensitive data) |
| `max_connections` | int | 100 | Max connections in pool |
| `max_keepalive_connections` | int | 20 | Max keepalive connections |

### AuthConfig

| Field | Type | Description |
|-------|------|-------------|
| `type` | AuthType | Auth type (NONE, API_KEY, BEARER, BASIC, OAUTH2, CUSTOM) |
| `token` | str | API key or bearer token |
| `token_location` | AuthLocation | Where to place token (HEADER, QUERY, BODY) |
| `token_key` | str | Header/query param name (default: "Authorization") |
| `token_prefix` | str | Token prefix (e.g., "Bearer") |
| `username` | str | Username for basic auth |
| `password` | str | Password for basic auth |
| `client_id` | str | OAuth client ID |
| `client_secret` | str | OAuth client secret |
| `token_url` | str | OAuth token endpoint |
| `refresh_token` | str | OAuth refresh token |
| `scopes` | list[str] | OAuth scopes |

### RateLimitConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_requests` | int | 60 | Max requests per window |
| `window_seconds` | float | 60.0 | Time window in seconds |
| `burst_size` | int | max_requests | Max burst size |
| `respect_retry_after` | bool | True | Respect Retry-After headers |
| `backoff_factor` | float | 1.5 | Backoff multiplier when rate limited |

### CircuitBreakerConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `failure_threshold` | int | 5 | Failures before opening circuit |
| `recovery_timeout` | float | 60.0 | Seconds before attempting recovery |
| `success_threshold` | int | 2 | Successes needed to close circuit |
| `failure_status_codes` | list[int] | [500, 502, 503, 504] | Status codes that count as failures |
| `count_timeouts_as_failures` | bool | True | Count timeouts as failures |

### RetryConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_retries` | int | 3 | Maximum retry attempts |
| `strategy` | RetryStrategy | EXPONENTIAL | Backoff strategy |
| `initial_delay` | float | 1.0 | Initial delay in seconds |
| `max_delay` | float | 60.0 | Maximum delay in seconds |
| `backoff_multiplier` | float | 2.0 | Multiplier for backoff |
| `jitter` | bool | True | Add random jitter |
| `retry_status_codes` | list[int] | [408, 429, 500, 502, 503, 504] | Status codes to retry |
| `retry_on_timeout` | bool | True | Retry on timeout |

---

## Advanced Usage

### Custom Request Preparation

```python
class CustomClient(BaseAPIClient):
    async def _prepare_request(self, method, path, **kwargs):
        # Get base preparation
        url, headers, params, json, data = await super()._prepare_request(
            method, path, **kwargs
        )

        # Add custom headers
        headers["X-Request-ID"] = str(uuid.uuid4())
        headers["X-Timestamp"] = datetime.now().isoformat()

        # Add custom params
        params["version"] = "v2"

        return url, headers, params, json, data
```

### Custom Response Handling

```python
class CustomClient(BaseAPIClient):
    async def _handle_response(self, response, start_time):
        # Get base handling
        api_response = await super()._handle_response(response, start_time)

        # Extract custom metadata
        if "X-Request-ID" in response.headers:
            api_response.metadata = {
                "request_id": response.headers["X-Request-ID"]
            }

        return api_response
```

### Manual Retry Logic

```python
from backend.app.modules.integrations import create_retry_handler

handler = create_retry_handler(
    max_retries=5,
    strategy=RetryStrategy.EXPONENTIAL,
    initial_delay=2.0,
)

# Use with custom function
result = await handler.call(my_async_function, arg1, arg2)
```

### Manual Circuit Breaker

```python
from backend.app.modules.integrations import CircuitBreaker, CircuitBreakerConfig

breaker = CircuitBreaker(
    CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30.0)
)

# Use as decorator
@breaker
async def risky_operation():
    # ...
    pass

# Or use directly
result = await breaker.call(risky_operation)
```

---

## Examples

See the `examples/` directory for complete, runnable examples:

1. **`simple_rest.py`** - Basic REST API client
2. **`oauth_flow.py`** - OAuth 2.0 authentication
3. **`rate_limited.py`** - Advanced rate limiting scenarios

Run examples:
```bash
python -m backend.app.modules.integrations.examples.simple_rest
python -m backend.app.modules.integrations.examples.rate_limited
```

---

## Testing

Run the comprehensive test suite:

```bash
# All tests
pytest backend/tests/test_integrations.py -v

# Specific test class
pytest backend/tests/test_integrations.py::TestRateLimiter -v

# With coverage
pytest backend/tests/test_integrations.py --cov=backend.app.modules.integrations
```

---

## Metrics & Monitoring

### Client Metrics

```python
metrics = client.get_metrics()

print(f"Total requests: {metrics.total_requests}")
print(f"Successful: {metrics.successful_requests}")
print(f"Failed: {metrics.failed_requests}")
print(f"Total retries: {metrics.total_retries}")
print(f"Rate limit hits: {metrics.rate_limit_hits}")
print(f"Circuit breaker opens: {metrics.circuit_breaker_opens}")
print(f"Avg response time: {metrics.average_response_time_ms:.2f}ms")
print(f"Min response time: {metrics.min_response_time_ms:.2f}ms")
print(f"Max response time: {metrics.max_response_time_ms:.2f}ms")
```

### Reset Metrics

```python
client.reset_metrics()
```

---

## Best Practices

### 1. Always Use Context Manager

```python
# ✅ GOOD: Automatic cleanup
async with MyClient(config).session() as client:
    await client.get("/endpoint")

# ❌ BAD: Manual cleanup required
client = MyClient(config)
await client.get("/endpoint")
await client.close()  # Easy to forget!
```

### 2. Configure Timeouts Appropriately

```python
APIClientConfig(
    # Connection should be fast
    connect_timeout=5.0,

    # Operations can take longer
    timeout=30.0,
)
```

### 3. Use Environment Variables for Secrets

```python
auth=AuthConfig(
    type=AuthType.API_KEY,
    token=os.getenv("API_KEY"),  # ✅ From environment
    # token="sk-hardcoded",  # ❌ Never hardcode!
)
```

### 4. Enable Rate Limiting for External APIs

```python
# Always configure rate limiting for external APIs
rate_limit=RateLimitConfig(
    max_requests=100,
    window_seconds=60.0,
)
```

### 5. Use Circuit Breaker for Unreliable Services

```python
# Protect against cascading failures
circuit_breaker=CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60.0,
)
```

### 6. Monitor Metrics in Production

```python
# Log metrics periodically
metrics = client.get_metrics()
logger.info(
    f"API metrics: requests={metrics.total_requests}, "
    f"success_rate={metrics.successful_requests/metrics.total_requests:.2%}, "
    f"avg_time={metrics.average_response_time_ms:.2f}ms"
)
```

---

## Troubleshooting

### Issue: Requests timing out

**Solution:** Increase timeout values or check network connectivity.

```python
APIClientConfig(
    timeout=60.0,  # Increase from default 30s
    connect_timeout=15.0,
)
```

### Issue: Rate limited by API

**Solution:** Reduce `max_requests` or increase `window_seconds`.

```python
RateLimitConfig(
    max_requests=50,  # Reduce from 100
    window_seconds=60.0,
)
```

### Issue: Circuit breaker keeps opening

**Solution:** Increase `failure_threshold` or fix underlying service issues.

```python
CircuitBreakerConfig(
    failure_threshold=10,  # Increase from 5
    recovery_timeout=120.0,  # Give more time to recover
)
```

### Issue: OAuth token not refreshing

**Solution:** Ensure `token_url` is correct and credentials are valid.

```python
# Check OAuth config
auth = AuthConfig(
    type=AuthType.OAUTH2,
    client_id="...",
    client_secret="...",
    token_url="https://auth.example.com/oauth/token",  # Verify URL
)

# Manually trigger token refresh
if client.auth_manager:
    await client.auth_manager.get_initial_token()
```

---

## Architecture

### Request Flow

```
User Request
    ↓
BaseAPIClient.get/post/etc()
    ↓
_prepare_request() [Auth injection]
    ↓
RateLimiter.acquire() [Wait if needed]
    ↓
CircuitBreaker.call()
    ↓
RetryHandler.call()
        ↓
    HTTP Request (httpx)
        ↓
    _handle_response() [Parse, log]
        ↓
    Update Metrics
        ↓
    Return APIResponse
```

### Component Interaction

```
┌─────────────────────┐
│   BaseAPIClient     │
│                     │
│  ┌───────────────┐  │
│  │ Auth Manager  │  │
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │ Rate Limiter  │  │
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │Circuit Breaker│  │
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │Retry Handler  │  │
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │ HTTP Client   │──┼──> External API
│  │  (httpx)      │  │
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │   Metrics     │  │
│  └───────────────┘  │
└─────────────────────┘
```

---

## Contributing

When adding new features to the integrations module:

1. Follow BRAiN's coding standards (see `/home/user/BRAiN/CLAUDE.md`)
2. Add comprehensive tests
3. Update this documentation
4. Include usage examples

---

## Version History

### 1.0.0 (2025-12-20)
- Initial release
- BaseAPIClient with all core features
- Multi-auth support (API Key, OAuth 2.0, Basic, Bearer, Custom)
- Rate limiting with token bucket algorithm
- Circuit breaker with three states
- Retry handler with exponential backoff
- Comprehensive test coverage
- Complete documentation and examples

---

## License

Part of the BRAiN project. All rights reserved.

---

## Support

For questions or issues:
1. Check the examples in `examples/`
2. Review the tests in `/home/user/BRAiN/backend/tests/test_integrations.py`
3. Consult `/home/user/BRAiN/CLAUDE.md` for BRAiN development patterns
4. Contact the BRAiN development team

---

**Built with ❤️ for robust, production-ready external integrations.**
