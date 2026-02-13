# Security Fix: Hardcoded Secrets Removal

**Date:** 2026-02-12  
**Severity:** CRITICAL  
**Status:** FIXED

## Summary

Removed all hardcoded secrets from the BRAiN codebase. Secrets are now loaded from environment variables with validation at startup.

## Changes Made

### 1. Physical Gateway Security (`backend/app/modules/physical_gateway/security.py`)

**Before:**
```python
def __init__(
    self,
    master_key: str = "brain-physical-gateway-master-key",
    ...
):
```

**After:**
```python
def __init__(
    self,
    master_key: Optional[str] = None,
    ...
):
    if master_key is None:
        master_key = os.environ.get("BRAIN_PHYSICAL_GATEWAY_MASTER_KEY")
        if not master_key:
            raise ValueError(
                "BRAIN_PHYSICAL_GATEWAY_MASTER_KEY environment variable must be set"
            )
```

### 2. AXE Governance (`backend/app/modules/axe_governance/__init__.py`)

**Before:**
```python
DMZ_GATEWAY_SECRET = "REPLACE_WITH_SECURE_SECRET_IN_PRODUCTION"
```

**After:**
```python
DMZ_GATEWAY_SECRET: str = ""

def __init__(self):
    self.DMZ_GATEWAY_SECRET = os.environ.get("BRAIN_DMZ_GATEWAY_SECRET", "")
    if not self.DMZ_GATEWAY_SECRET:
        raise ValueError(
            "BRAIN_DMZ_GATEWAY_SECRET environment variable must be set"
        )
```

### 3. Environment Template (`.env.template`)

Created template with all required secrets:
- `BRAIN_PHYSICAL_GATEWAY_MASTER_KEY`
- `BRAIN_DMZ_GATEWAY_SECRET`
- `JWT_SECRET`
- `DATABASE_URL`

### 4. Sandbox Copies

Applied same fixes to:
- `sandbox/backend/app/modules/physical_gateway/security.py`
- `sandbox/backend/app/modules/axe_governance/__init__.py`

## Docker Compose Configuration

The `docker-compose.yml` already correctly loads environment variables via:

```yaml
services:
  backend:
    env_file:
      - .env
```

## Deployment Instructions

1. Copy `.env.template` to `.env`:
   ```bash
   cp .env.template .env
   ```

2. Generate secure secrets:
   ```bash
   export BRAIN_PHYSICAL_GATEWAY_MASTER_KEY=$(openssl rand -hex 32)
   export BRAIN_DMZ_GATEWAY_SECRET=$(openssl rand -hex 32)
   export JWT_SECRET=$(openssl rand -hex 32)
   ```

3. Add to your `.env` file

4. Ensure `.env` is in `.gitignore` (DO NOT commit secrets!)

5. Restart the application

## Verification

The application will now **fail to start** if required environment variables are not set, preventing accidental deployment with missing secrets.

## Files Modified

1. `/backend/app/modules/physical_gateway/security.py`
2. `/backend/app/modules/axe_governance/__init__.py`
3. `/sandbox/backend/app/modules/physical_gateway/security.py`
4. `/sandbox/backend/app/modules/axe_governance/__init__.py`
5. Created: `/.env.template`
