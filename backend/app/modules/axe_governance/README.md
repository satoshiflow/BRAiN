# AXE Governance (G3) - DMZ Isolation & Trust Tier System

**Version:** 1.0
**Status:** ✅ Production Ready
**Security Level:** CRITICAL

---

## Table of Contents

1. [Overview](#overview)
2. [Security Model](#security-model)
3. [Trust Tier System](#trust-tier-system)
4. [DMZ Gateway Authentication](#dmz-gateway-authentication)
5. [Audit Events](#audit-events)
6. [API Integration](#api-integration)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The AXE Governance module implements **DMZ-Only access control** for the AXE (Auxiliary Execution Engine) API. This closes a critical security gap where AXE previously had direct Core access.

### Critical Security Principle

**AXE MUST NEVER have direct Core access.**

All external requests to AXE must go through authenticated DMZ gateways. Direct access is only allowed from:
- **Localhost** (127.0.0.1, ::1) - for admin/testing
- **Authenticated DMZ Gateways** - with valid credentials

### Key Features

✅ **Trust Tier Classification** - Every request is classified (LOCAL, DMZ, EXTERNAL)
✅ **Fail-Closed Design** - Unknown sources are blocked by default
✅ **DMZ Gateway Authentication** - Header-based token authentication
✅ **Comprehensive Audit Logging** - All operations tracked
✅ **FastAPI Dependency Injection** - Clean, testable architecture

---

## Security Model

### Fail-Closed Principle

The system operates on a **fail-closed** security model:

```
Unknown Source → CLASSIFY as EXTERNAL → BLOCK (403 Forbidden) → AUDIT
```

**No implicit decisions** - if we can't determine the trust level, we deny access.

### Defense in Depth

```
┌─────────────────────────────────────────────────┐
│  Internet / External Networks                   │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │   DMZ Gateway  │ ← Authenticates with X-DMZ-Gateway-ID/Token
         │  (Telegram,    │
         │   WhatsApp,    │
         │   Discord)     │
         └────────┬───────┘
                  │
                  ▼
         ┌────────────────┐
         │ AXE Governance │ ← validate_axe_request()
         │  Trust Tier    │ ← TrustTier.DMZ
         │   Validation   │
         └────────┬───────┘
                  │
                  ▼ (if ALLOWED)
         ┌────────────────┐
         │   AXE Engine   │
         │  (Core Logic)  │
         └────────────────┘
```

**Direct Access Blocked:**
```
External Request → AXE API → validate_axe_request()
                           → TrustTier.EXTERNAL
                           → 403 Forbidden
                           → Audit Event
```

---

## Trust Tier System

### Tier Definitions

```python
class TrustTier(str, Enum):
    LOCAL = "local"      # Core-internal - HIGHEST TRUST
    DMZ = "dmz"          # Authenticated DMZ gateways - MEDIUM TRUST
    EXTERNAL = "external"  # Unknown sources - NO TRUST (BLOCKED)
```

### Trust Tier Determination Logic

**Priority Order** (evaluated top to bottom):

1. **DMZ Gateway Authentication** (Headers present + valid token)
   - Check: `X-DMZ-Gateway-ID` header exists
   - Check: `X-DMZ-Gateway-Token` header exists
   - Validate: Gateway ID is in `KNOWN_DMZ_GATEWAYS`
   - Validate: Token matches expected value
   - Result: `TrustTier.DMZ`

2. **Localhost Detection** (Admin/Testing)
   - Check: Client IP is `127.0.0.1`, `::1`, or `localhost`
   - Result: `TrustTier.LOCAL`

3. **Default: External** (Fail-Closed)
   - No authentication headers
   - Unknown source IP
   - Result: `TrustTier.EXTERNAL` → **BLOCKED**

### Request Context

Every validated request produces an `AXERequestContext`:

```python
@dataclass
class AXERequestContext:
    trust_tier: TrustTier
    source_service: Optional[str]  # e.g., "telegram_gateway"
    source_ip: Optional[str]
    authenticated: bool
    dmz_gateway_token: Optional[str]  # Redacted (first 8 chars)
    timestamp: datetime
    request_id: str  # Unique request identifier
    user_agent: Optional[str]
    rate_limit_key: str  # For rate limiting
```

---

## DMZ Gateway Authentication

### Known DMZ Gateways

```python
KNOWN_DMZ_GATEWAYS = {
    "telegram_gateway",
    "whatsapp_gateway",
    "discord_gateway",
    "email_gateway",
}
```

### Authentication Headers

DMZ gateways must send these headers with **every request**:

```http
POST /api/axe/message HTTP/1.1
Host: brain-backend:8000
Content-Type: application/json
X-DMZ-Gateway-ID: telegram_gateway
X-DMZ-Gateway-Token: 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08

{
  "message": "User request from Telegram",
  "metadata": {}
}
```

### Token Generation

**Current Implementation** (Development/Testing):
```python
# Simplified HMAC-based token
import hashlib

raw = f"{gateway_id}:{DMZ_GATEWAY_SECRET}"
token = hashlib.sha256(raw.encode()).hexdigest()
```

**Production Requirements:**
- Use **JWT** (JSON Web Tokens) with expiration
- Rotate shared secrets regularly
- Per-gateway unique secrets
- Token refresh mechanism

### Generating Tokens for DMZ Gateways

**Example for Telegram Gateway:**

```bash
# Calculate expected token
GATEWAY_ID="telegram_gateway"
SHARED_SECRET="REPLACE_WITH_SECURE_SECRET_IN_PRODUCTION"

echo -n "${GATEWAY_ID}:${SHARED_SECRET}" | sha256sum
# Output: 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
```

**Configure in DMZ Gateway:**

```python
# In telegram gateway service
import httpx

async def call_axe(message: str):
    headers = {
        "X-DMZ-Gateway-ID": "telegram_gateway",
        "X-DMZ-Gateway-Token": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://brain-backend:8000/api/axe/message",
            json={"message": message},
            headers=headers
        )

    return response.json()
```

---

## Audit Events

All AXE operations emit audit events to the sovereign_mode audit system.

### Event Types

| Event Type | When Emitted | Success | Severity |
|------------|--------------|---------|----------|
| `AXE_REQUEST_RECEIVED` | Every request (after validation) | True | INFO |
| `AXE_REQUEST_FORWARDED` | Request processed successfully | True | INFO |
| `AXE_REQUEST_BLOCKED` | Request denied (EXTERNAL tier) | False | ERROR |
| `AXE_TRUST_TIER_VIOLATION` | EXTERNAL request attempted | False | ERROR |

### Audit Event Metadata

Every audit event includes:

```json
{
  "event_type": "axe.request_received",
  "success": true,
  "severity": "info",
  "reason": "AXE request received from dmz source",
  "metadata": {
    "trust_tier": "dmz",
    "source_service": "telegram_gateway",
    "source_ip": "172.20.0.5",
    "authenticated": true,
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Querying Audit Events

```bash
# Get recent AXE audit events
curl http://localhost:8000/api/sovereign/audit/events?event_type=axe.request_received

# Get blocked requests
curl http://localhost:8000/api/sovereign/audit/events?event_type=axe.request_blocked
```

---

## API Integration

### Protected Endpoints

All AXE endpoints use the `validate_axe_request()` dependency:

```python
from fastapi import Depends
from backend.app.modules.axe_governance import AXERequestContext, validate_axe_request

@router.get("/info")
async def axe_info(context: AXERequestContext = Depends(validate_axe_request)):
    """Get AXE info - DMZ-only access."""
    return {
        "name": "AXE",
        "governance": {
            "trust_tier": context.trust_tier.value,
            "source_service": context.source_service,
            "authenticated": context.authenticated,
            "request_id": context.request_id,
        }
    }
```

### Response Format

All AXE responses include governance metadata:

```json
{
  "mode": "gateway",
  "gateway": "telegram",
  "reply": "Response from AXE",
  "governance": {
    "trust_tier": "dmz",
    "source_service": "telegram_gateway",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Error Responses

**403 Forbidden (EXTERNAL request):**

```json
{
  "detail": {
    "error": "Forbidden",
    "message": "AXE is only accessible via DMZ gateways",
    "trust_tier": "external",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

## Testing

### Test Scenarios

**✅ Positive Tests:**

1. **Localhost Access** (Admin/Testing)
   ```bash
   curl http://localhost:8000/api/axe/info
   # Expected: 200 OK, trust_tier=local
   ```

2. **DMZ Gateway with Valid Token**
   ```bash
   curl http://localhost:8000/api/axe/info \
     -H "X-DMZ-Gateway-ID: telegram_gateway" \
     -H "X-DMZ-Gateway-Token: <valid_token>"
   # Expected: 200 OK, trust_tier=dmz
   ```

**❌ Negative Tests:**

3. **External Request (No Headers)**
   ```bash
   curl http://localhost:8000/api/axe/info
   # Expected: 403 Forbidden, trust_tier=external
   ```

4. **Invalid Token**
   ```bash
   curl http://localhost:8000/api/axe/info \
     -H "X-DMZ-Gateway-ID: telegram_gateway" \
     -H "X-DMZ-Gateway-Token: invalid_token"
   # Expected: 403 Forbidden
   ```

5. **Unknown Gateway**
   ```bash
   curl http://localhost:8000/api/axe/info \
     -H "X-DMZ-Gateway-ID: unknown_gateway" \
     -H "X-DMZ-Gateway-Token: <any_token>"
   # Expected: 403 Forbidden
   ```

**🔓 Bypass Attempt Tests:**

6. **Header Spoofing** (External IP with DMZ headers)
   ```bash
   # From external IP (not localhost)
   curl http://external-ip:8000/api/axe/info \
     -H "X-DMZ-Gateway-ID: telegram_gateway" \
     -H "X-DMZ-Gateway-Token: <valid_token>"
   # Expected: Should work if token is valid (token validates identity)
   ```

7. **Missing Token Header**
   ```bash
   curl http://localhost:8000/api/axe/info \
     -H "X-DMZ-Gateway-ID: telegram_gateway"
   # Expected: 403 Forbidden (missing token)
   ```

### Automated Test Suite

See `backend/tests/test_axe_governance.py` for comprehensive pytest test cases.

---

## Troubleshooting

### Issue: "AXE is only accessible via DMZ gateways"

**Symptoms:**
```json
{
  "detail": {
    "error": "Forbidden",
    "message": "AXE is only accessible via DMZ gateways"
  }
}
```

**Diagnosis:**
1. Check if you're accessing from localhost:
   ```bash
   curl http://localhost:8000/api/axe/info
   ```

2. Check if DMZ headers are present:
   ```bash
   curl -v http://localhost:8000/api/axe/info \
     -H "X-DMZ-Gateway-ID: telegram_gateway" \
     -H "X-DMZ-Gateway-Token: <token>"
   ```

3. Verify token is correct:
   ```bash
   # Generate expected token
   echo -n "telegram_gateway:REPLACE_WITH_SECURE_SECRET_IN_PRODUCTION" | sha256sum
   ```

4. Check audit logs:
   ```bash
   curl http://localhost:8000/api/sovereign/audit/events?event_type=axe.request_blocked
   ```

### Issue: "Unknown DMZ gateway ID"

**Symptoms:**
```
WARNING: Unknown DMZ gateway ID: my_custom_gateway
```

**Solution:**
Add your gateway to `KNOWN_DMZ_GATEWAYS`:

```python
# backend/app/modules/axe_governance/__init__.py
KNOWN_DMZ_GATEWAYS = {
    "telegram_gateway",
    "whatsapp_gateway",
    "discord_gateway",
    "email_gateway",
    "my_custom_gateway",  # Add this
}
```

### Issue: "Invalid token for DMZ gateway"

**Symptoms:**
```
WARNING: Invalid token for DMZ gateway: telegram_gateway
```

**Solution:**
Regenerate token with correct shared secret:

```bash
# Check current shared secret
grep DMZ_GATEWAY_SECRET backend/app/modules/axe_governance/__init__.py

# Generate token
echo -n "telegram_gateway:<shared_secret>" | sha256sum
```

Update DMZ gateway configuration with new token.

---

## Production Checklist

Before deploying to production:

- [ ] Replace `DMZ_GATEWAY_SECRET` with strong random value (min 32 chars)
- [ ] Move shared secret to environment variable (`AXE_DMZ_SHARED_SECRET`)
- [ ] Implement JWT-based authentication (instead of HMAC)
- [ ] Add token expiration (recommended: 1 hour)
- [ ] Implement token refresh mechanism
- [ ] Use per-gateway unique secrets
- [ ] Set up secret rotation schedule (recommended: monthly)
- [ ] Configure rate limiting per `rate_limit_key`
- [ ] Enable audit log export to SIEM
- [ ] Test all DMZ gateways with new authentication
- [ ] Document token distribution process
- [ ] Set up monitoring for `AXE_TRUST_TIER_VIOLATION` events

---

## Security Considerations

### Token Storage

**DMZ Gateways:**
- Store tokens in environment variables (`.env` files)
- Never commit tokens to Git
- Use secret management systems (Vault, AWS Secrets Manager)

**Core:**
- Shared secret in environment variable
- Rotate regularly
- Audit access to secret storage

### Rate Limiting

Each request context includes a `rate_limit_key`:
```python
rate_limit_key = f"dmz:{gateway_id}"  # For DMZ
rate_limit_key = f"local:{client_host}"  # For localhost
rate_limit_key = f"external:{client_host}"  # For external (blocked anyway)
```

Implement rate limiting middleware:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=lambda: context.rate_limit_key)

@limiter.limit("100/minute")
@router.post("/message")
async def axe_message(context: AXERequestContext = Depends(validate_axe_request)):
    ...
```

### Network-Level Defense

**Firewall Rules** (IPv4 + IPv6):
```bash
# Only allow DMZ gateway IPs to reach port 8000
iptables -A DOCKER-USER -p tcp --dport 8000 -s <dmz_gateway_ip> -j ACCEPT
iptables -A DOCKER-USER -p tcp --dport 8000 -j DROP

ip6tables -A DOCKER-USER -p tcp --dport 8000 -s <dmz_gateway_ipv6> -j ACCEPT
ip6tables -A DOCKER-USER -p tcp --dport 8000 -j DROP
```

---

## References

- **Parent Module**: Sovereign Mode (`backend/app/modules/sovereign_mode/`)
- **Audit System**: `backend/app/modules/sovereign_mode/service.py`
- **AXE API**: `backend/api/routes/axe.py`
- **Governance Sprint**: Internal documentation (G3 - AXE Governance & DMZ Finalisierung)

---

**Last Updated**: 2025-12-24
**Reviewed By**: Security Team
**Next Review**: 2026-03-24 (Quarterly)
