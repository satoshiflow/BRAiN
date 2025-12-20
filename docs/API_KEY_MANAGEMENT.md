# API Key Management for BRAiN Core

**Version:** 1.0.0
**Phase:** 4 - Security & Compliance
**Status:** ✅ Production Ready

---

## Overview

BRAiN Core provides a secure API key management system for programmatic access:

- **Cryptographically secure** key generation (32 bytes, 256 bits)
- **SHA-256 hashing** for storage (plaintext keys never stored)
- **Scope-based permissions** (granular access control)
- **Key rotation** and expiration
- **Usage tracking** and audit trail
- **IP whitelisting** support

---

## Quick Start

### Generate API Key

```bash
# Create API key with scopes
curl -X POST http://localhost:8000/api/keys/ \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API",
    "scopes": ["missions:read", "agents:read"],
    "expires_in_days": 90
  }'

# Response (SAVE THE KEY - it's only shown once!):
{
  "id": "abc123def456",
  "name": "Production API",
  "key": "brain_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0",
  "prefix": "a1b2c3d4",
  "scopes": ["missions:read", "agents:read"],
  "created_at": "2025-12-20T10:30:00Z",
  "expires_at": "2026-03-20T10:30:00Z",
  "is_active": true,
  "usage_count": 0
}
```

### Use API Key

```bash
# Method 1: X-API-Key header (recommended)
curl http://localhost:8000/api/missions/info \
  -H "X-API-Key: brain_a1b2c3d4e5f6..."

# Method 2: Bearer token (also works)
curl http://localhost:8000/api/missions/info \
  -H "Authorization: Bearer brain_a1b2c3d4e5f6..."
```

---

## Architecture

### Key Format

```
brain_<64_hex_characters>

Example:
brain_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0
│     │
│     └─ 32 bytes (256 bits) of cryptographic randomness
└─ Prefix identifier
```

### Storage

```
Plaintext Key (generated once):
  brain_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0

          ↓ SHA-256 Hash

Stored Hash:
  b5e7d9f3a1c4e8f2d6b0a5c9e3d7f1b4a8c2e6f0d4b8a2c6e0d4b8a2c6e0d4
  │
  └─ Only hash stored in database (plaintext never persisted)
```

**Security Benefits:**
- Plaintext key never stored
- Database breach doesn't expose keys
- Hash verification during authentication

---

## API Reference

### Create API Key

```http
POST /api/keys/
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "name": "Production API",
  "scopes": ["missions:read", "agents:read"],
  "expires_in_days": 90,
  "ip_whitelist": ["203.0.113.1", "198.51.100.1"],
  "metadata": {"project": "frontend-v2"}
}

Response:
{
  "id": "abc123",
  "name": "Production API",
  "key": "brain_...",  # ⚠️ ONLY RETURNED ONCE!
  "prefix": "a1b2c3d4",
  "scopes": ["missions:read", "agents:read"],
  "created_at": "2025-12-20T10:30:00Z",
  "expires_at": "2026-03-20T10:30:00Z",
  "is_active": true,
  "usage_count": 0
}
```

**⚠️ IMPORTANT:** The plaintext key is only returned in the creation response. Store it securely - it cannot be retrieved again.

### List API Keys

```http
GET /api/keys/?include_inactive=false
Authorization: Bearer <JWT_TOKEN>

Response:
[
  {
    "id": "abc123",
    "name": "Production API",
    "prefix": "a1b2c3d4",
    "scopes": ["missions:read", "agents:read"],
    "created_at": "2025-12-20T10:30:00Z",
    "expires_at": "2026-03-20T10:30:00Z",
    "last_used_at": "2025-12-20T15:45:00Z",
    "is_active": true,
    "usage_count": 1234
  }
]
```

### Get API Key

```http
GET /api/keys/{key_id}
Authorization: Bearer <JWT_TOKEN>

Response:
{
  "id": "abc123",
  "name": "Production API",
  "prefix": "a1b2c3d4",
  "scopes": ["missions:read", "agents:read"],
  "created_at": "2025-12-20T10:30:00Z",
  "expires_at": "2026-03-20T10:30:00Z",
  "last_used_at": "2025-12-20T15:45:00Z",
  "is_active": true,
  "usage_count": 1234
}
```

### Revoke API Key

```http
POST /api/keys/{key_id}/revoke
Authorization: Bearer <JWT_TOKEN>

Response:
{
  "success": true,
  "message": "API key revoked: abc123"
}
```

### Rotate API Key

```http
POST /api/keys/{key_id}/rotate
Authorization: Bearer <JWT_TOKEN>

Response:
{
  "old_key_id": "abc123",
  "new_key": {
    "id": "def456",
    "name": "Production API (rotated)",
    "key": "brain_...",  # ⚠️ New key (save it!)
    "prefix": "x1y2z3w4",
    ...
  }
}
```

**Note:** The old key is automatically revoked.

### Delete API Key

```http
DELETE /api/keys/{key_id}
Authorization: Bearer <JWT_TOKEN>

Response:
{
  "success": true,
  "message": "API key deleted: abc123"
}
```

### List Available Scopes

```http
GET /api/keys/scopes/available
Authorization: Bearer <JWT_TOKEN>

Response:
{
  "scopes": [
    "missions:read",
    "missions:write",
    "missions:delete",
    "missions:*",
    "agents:read",
    "agents:write",
    ...
  ]
}
```

---

## Scopes

### Available Scopes

| Scope | Description |
|-------|-------------|
| `missions:read` | Read missions |
| `missions:write` | Create/update missions |
| `missions:delete` | Delete missions |
| `missions:*` | All mission operations |
| `agents:read` | Read agents |
| `agents:write` | Create/update agents |
| `agents:delete` | Delete agents |
| `agents:*` | All agent operations |
| `policies:read` | Read policies |
| `policies:write` | Create/update policies |
| `policies:delete` | Delete policies |
| `policies:*` | All policy operations |
| `cache:read` | Read cache stats |
| `cache:write` | Set cache values |
| `cache:delete` | Clear cache |
| `cache:*` | All cache operations |
| `db:read` | Read database stats |
| `db:write` | Execute database operations |
| `db:*` | All database operations |
| `admin:*` | Admin operations |
| `*:*` | All operations (superuser) |

### Wildcard Scopes

```python
# Resource wildcard
"missions:*"  # All mission operations (read, write, delete)

# Global wildcard
"*:*"  # All operations on all resources (superuser)
```

### Scope Validation

```python
# API key with "missions:read" scope
Can access:
- GET /api/missions/info ✅
- GET /api/missions/queue ✅

Cannot access:
- POST /api/missions/enqueue ❌ (requires missions:write)
- DELETE /api/missions/{id} ❌ (requires missions:delete)

# API key with "missions:*" scope
Can access:
- GET /api/missions/info ✅
- POST /api/missions/enqueue ✅
- DELETE /api/missions/{id} ✅
```

---

## Authentication

### X-API-Key Header (Recommended)

```bash
curl http://localhost:8000/api/missions/info \
  -H "X-API-Key: brain_a1b2c3d4e5f6..."
```

### Bearer Token (Alternative)

```bash
curl http://localhost:8000/api/missions/info \
  -H "Authorization: Bearer brain_a1b2c3d4e5f6..."
```

### Both Methods Supported

Endpoints accept both JWT tokens and API keys:

```python
@router.get("/missions")
async def list_missions(
    principal: Principal = Depends(get_current_principal_or_api_key)
):
    # Works with:
    # - Authorization: Bearer <JWT_TOKEN>
    # - X-API-Key: brain_...
    # - Authorization: Bearer brain_...
    return {"missions": [...]}
```

---

## Security Features

### 1. Cryptographically Secure Generation

```python
import secrets

# 32 bytes = 256 bits of randomness
random_bytes = secrets.token_bytes(32)
key = f"brain_{random_bytes.hex()}"
```

**Entropy:** 256 bits (same as AES-256 keys)

### 2. SHA-256 Hashing

```python
import hashlib

# Hash key before storage
key_hash = hashlib.sha256(key.encode()).hexdigest()

# Only hash stored in database
# Plaintext key never persisted
```

**Benefits:**
- Database breach doesn't expose keys
- Keys cannot be recovered from hash
- Same security as password hashing

### 3. Automatic Expiration

```python
# Key expires after 90 days
expires_at = datetime.utcnow() + timedelta(days=90)

# Expired keys automatically rejected
if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
    return None  # Unauthorized
```

### 4. IP Whitelisting

```python
# Only allow from specific IPs
ip_whitelist = ["203.0.113.1", "198.51.100.1"]

# Request from 198.51.100.1 → Allowed ✅
# Request from 192.0.2.1 → Denied ❌
```

### 5. Usage Tracking

```python
# Track every API key usage
api_key.last_used_at = datetime.utcnow()
api_key.usage_count += 1

# Monitor for suspicious activity
if usage_count > THRESHOLD:
    alert_admin()
```

---

## Best Practices

### 1. Use Scopes, Not Global Access

```python
# ❌ BAD - too permissive
scopes = ["*:*"]

# ✅ GOOD - least privilege
scopes = ["missions:read", "agents:read"]
```

### 2. Set Expiration

```python
# ✅ Always set expiration
expires_in_days = 90

# ❌ Never expire = security risk
expires_in_days = None
```

### 3. Rotate Keys Regularly

```bash
# Rotate every 90 days
curl -X POST http://localhost:8000/api/keys/abc123/rotate

# Update applications with new key
# Revoke old key after transition period
```

### 4. Use IP Whitelisting

```python
# ✅ Restrict to known IPs
ip_whitelist = ["203.0.113.1", "198.51.100.1"]

# ❌ Allow from anywhere
ip_whitelist = None
```

### 5. Monitor Usage

```bash
# Check usage stats
curl http://localhost:8000/api/keys/abc123

# Alert on anomalies
if usage_count > 10000/day:
    send_alert()
```

### 6. Revoke Immediately on Compromise

```bash
# If key leaked, revoke ASAP
curl -X POST http://localhost:8000/api/keys/abc123/revoke

# Generate new key
curl -X POST http://localhost:8000/api/keys/abc123/rotate
```

---

## Integration Examples

### Python

```python
import requests

API_KEY = "brain_a1b2c3d4e5f6..."
BASE_URL = "http://localhost:8000"

# Using X-API-Key header
response = requests.get(
    f"{BASE_URL}/api/missions/info",
    headers={"X-API-Key": API_KEY}
)

# Using Bearer token
response = requests.get(
    f"{BASE_URL}/api/missions/info",
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

### JavaScript

```javascript
const API_KEY = "brain_a1b2c3d4e5f6...";
const BASE_URL = "http://localhost:8000";

// Using X-API-Key header
const response = await fetch(`${BASE_URL}/api/missions/info`, {
  headers: {
    "X-API-Key": API_KEY
  }
});

// Using Bearer token
const response = await fetch(`${BASE_URL}/api/missions/info`, {
  headers: {
    "Authorization": `Bearer ${API_KEY}`
  }
});
```

### cURL

```bash
API_KEY="brain_a1b2c3d4e5f6..."

# X-API-Key header
curl http://localhost:8000/api/missions/info \
  -H "X-API-Key: $API_KEY"

# Bearer token
curl http://localhost:8000/api/missions/info \
  -H "Authorization: Bearer $API_KEY"
```

---

## Troubleshooting

### Issue: 401 Unauthorized

**Cause:** Invalid or expired key

**Debug:**
```bash
# Check if key exists
curl http://localhost:8000/api/keys/ \
  -H "Authorization: Bearer $JWT_TOKEN"

# Verify key format
echo $API_KEY | grep "^brain_"

# Check expiration
curl http://localhost:8000/api/keys/abc123 \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### Issue: 403 Forbidden

**Cause:** Insufficient scopes

**Debug:**
```bash
# Check key scopes
curl http://localhost:8000/api/keys/abc123 \
  -H "Authorization: Bearer $JWT_TOKEN"

# Required scope for endpoint
# missions:write for POST /api/missions/enqueue
```

**Fix:**
```bash
# Create new key with correct scopes
curl -X POST http://localhost:8000/api/keys/ \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"name": "New Key", "scopes": ["missions:write"]}'
```

### Issue: IP Whitelist Blocking

**Cause:** Request from non-whitelisted IP

**Debug:**
```bash
# Check client IP
curl ifconfig.me

# Check key whitelist
curl http://localhost:8000/api/keys/abc123 \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Fix:**
```bash
# Update IP whitelist or remove it
# (requires creating new key - cannot update whitelist on existing keys)
```

---

## Production Checklist

- [ ] All API keys have expiration dates
- [ ] No keys with `*:*` scope (except admin keys)
- [ ] IP whitelisting enabled for production keys
- [ ] Key rotation schedule established (90 days)
- [ ] Usage monitoring and alerts configured
- [ ] Revocation process documented
- [ ] Key storage secure (encrypted, access-controlled)
- [ ] Audit logging enabled

---

## References

- [CLAUDE.md](../CLAUDE.md#phase-4-security--compliance) - Development guide
- [Security Best Practices](https://cheatsheetseries.owasp.org/cheatsheets/API_Security_Cheat_Sheet.html)

---

**Last Updated:** 2025-12-20
**Author:** BRAiN Development Team
**Version:** 1.0.0
