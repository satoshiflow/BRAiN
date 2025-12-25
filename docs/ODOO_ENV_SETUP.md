# Odoo Environment Configuration Guide

**Sprint IV: AXE × Odoo Integration**
**Date:** 2025-12-25
**Version:** 1.0.0

---

## Overview

This guide explains how to configure environment variables for BRAiN's Odoo integration layer. All configuration is done via environment variables for security and flexibility.

**Prerequisites:**
- Odoo 19 instance running and accessible
- Admin user credentials with module management permissions
- Shared filesystem or Docker volume for module deployment

---

## Required Environment Variables

### 1. ODOO_BASE_URL

**Description:** Base URL of your Odoo instance

**Format:** `http(s)://hostname:port` (no trailing slash)

**Examples:**
```bash
# Local development
ODOO_BASE_URL=http://localhost:8069

# Docker Compose
ODOO_BASE_URL=http://odoo:8069

# Remote/Production
ODOO_BASE_URL=https://erp.example.com
```

**Security Notes:**
- Use HTTPS in production
- Do not include paths (e.g., `/web`)
- Ensure URL is reachable from BRAiN container/host

---

### 2. ODOO_DB_NAME

**Description:** Name of the Odoo database to connect to

**Format:** Alphanumeric string (database name)

**Examples:**
```bash
# Production database
ODOO_DB_NAME=production

# Staging database
ODOO_DB_NAME=staging_erp

# Development database
ODOO_DB_NAME=odoo_dev
```

**Security Notes:**
- Use separate databases for dev/staging/prod
- Database name is NOT a secret (but don't publish publicly)

---

### 3. ODOO_ADMIN_USER

**Description:** Odoo username with module management permissions

**Format:** String (username)

**Examples:**
```bash
# Default admin
ODOO_ADMIN_USER=admin

# Service account
ODOO_ADMIN_USER=brain_integration

# Custom admin
ODOO_ADMIN_USER=erp_admin
```

**Requirements:**
- User must have "Technical Settings" permission
- User must be able to install/upgrade modules
- Recommended: Create dedicated service account for BRAiN

**Security Best Practice:**
```bash
# Create dedicated Odoo user for BRAiN
1. Log into Odoo as admin
2. Go to Settings → Users & Companies → Users
3. Create new user: "brain_service"
4. Grant permissions:
   - Access Rights: "Settings"
   - Technical: ✓ (checked)
5. Set strong password
6. Use this user for BRAiN integration
```

---

### 4. ODOO_ADMIN_PASSWORD

**Description:** Password for the Odoo admin user

**Format:** String (password)

**Security:**
- ⚠️ **NEVER commit this to Git!**
- ⚠️ Use strong passwords (20+ characters)
- ⚠️ Rotate regularly in production
- ⚠️ Store in secrets manager (Vault, AWS Secrets Manager, etc.)

**Examples:**
```bash
# ❌ BAD - Weak password
ODOO_ADMIN_PASSWORD=admin123

# ✅ GOOD - Strong password
ODOO_ADMIN_PASSWORD=Kx9#mP2$vL8@qR5!wN7^tY4&

# ✅ BEST - From secrets manager
ODOO_ADMIN_PASSWORD=$(vault kv get -field=password secret/odoo/brain)
```

**Docker Compose Integration:**
```yaml
# docker-compose.yml
services:
  brain-backend:
    environment:
      - ODOO_ADMIN_PASSWORD=${ODOO_ADMIN_PASSWORD}  # From .env file
    # OR from secrets
    secrets:
      - odoo_password
    environment:
      - ODOO_ADMIN_PASSWORD=/run/secrets/odoo_password
```

---

### 5. ODOO_ADDONS_PATH

**Description:** Filesystem path where BRAiN deploys generated Odoo modules

**Format:** Absolute path (must be accessible to both BRAiN and Odoo)

**Examples:**
```bash
# Docker volume (recommended)
ODOO_ADDONS_PATH=/opt/odoo/addons

# Host path (development)
ODOO_ADDONS_PATH=/var/lib/odoo/addons

# Custom path
ODOO_ADDONS_PATH=/mnt/shared/odoo_modules
```

**Requirements:**
- Path must exist and be writable by BRAiN
- Path must be readable by Odoo
- Recommended: Use Docker volume for sharing

**Docker Compose Setup:**
```yaml
# docker-compose.yml
volumes:
  odoo_addons:

services:
  brain-backend:
    volumes:
      - odoo_addons:/opt/odoo/addons
    environment:
      - ODOO_ADDONS_PATH=/opt/odoo/addons

  odoo:
    image: odoo:19.0
    volumes:
      - odoo_addons:/mnt/extra-addons
    command: --addons-path=/mnt/extra-addons
```

**Permissions:**
```bash
# Ensure correct ownership (Linux/macOS)
sudo chown -R 1000:1000 /var/lib/odoo/addons
sudo chmod -R 755 /var/lib/odoo/addons
```

---

### 6. ODOO_TIMEOUT_SECONDS (Optional)

**Description:** Timeout for XML-RPC calls to Odoo

**Format:** Number (seconds)

**Default:** 30

**Examples:**
```bash
# Default (recommended)
ODOO_TIMEOUT_SECONDS=30

# Slow network
ODOO_TIMEOUT_SECONDS=60

# Fast local network
ODOO_TIMEOUT_SECONDS=15
```

**When to Increase:**
- Slow network connection to Odoo
- Large modules with many dependencies
- Odoo server under heavy load

**When to Decrease:**
- Fast local network (same host/DC)
- Want faster failure detection

---

### 7. ODOO_ENFORCE_TRUST_TIER (Optional)

**Description:** Enable/disable LOCAL trust tier enforcement for Odoo operations

**Format:** Boolean (`true` or `false`)

**Default:** `true` (security enforced)

**Security Impact:**

| Value | Security | Use Case |
|-------|----------|----------|
| `true` | ✅ **HIGH** | Production (recommended) |
| `false` | ⚠️ **NONE** | Development/testing only |

**Examples:**
```bash
# Production (enforced - recommended)
ODOO_ENFORCE_TRUST_TIER=true

# Development (disabled - NOT recommended)
ODOO_ENFORCE_TRUST_TIER=false
```

**⚠️ WARNING:**
Setting to `false` disables ALL security checks. Any user can:
- Generate Odoo modules
- Install/upgrade/rollback modules
- Query Odoo data

**Only use `false` for:**
- Local development
- Automated testing
- Debugging

**NEVER use `false` in production!**

---

## Configuration Scenarios

### Scenario 1: Local Development (Docker Compose)

```bash
# .env
ODOO_BASE_URL=http://odoo:8069
ODOO_DB_NAME=odoo_dev
ODOO_ADMIN_USER=admin
ODOO_ADMIN_PASSWORD=admin  # OK for dev only!
ODOO_ADDONS_PATH=/opt/odoo/addons
ODOO_TIMEOUT_SECONDS=30
ODOO_ENFORCE_TRUST_TIER=false  # Dev convenience
```

```yaml
# docker-compose.yml
version: '3.8'

volumes:
  odoo_addons:
  odoo_data:
  postgres_data:

services:
  brain-backend:
    image: brain-backend:latest
    environment:
      - ODOO_BASE_URL=http://odoo:8069
      - ODOO_DB_NAME=odoo_dev
      - ODOO_ADMIN_USER=admin
      - ODOO_ADMIN_PASSWORD=admin
      - ODOO_ADDONS_PATH=/opt/odoo/addons
    volumes:
      - odoo_addons:/opt/odoo/addons
    depends_on:
      - odoo

  odoo:
    image: odoo:19.0
    ports:
      - "8069:8069"
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_DB=postgres
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
    volumes:
      - odoo_addons:/mnt/extra-addons
      - odoo_data:/var/lib/odoo
    command: --addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

---

### Scenario 2: Production (Secrets Manager)

```bash
# .env (secrets are fetched at runtime)
ODOO_BASE_URL=https://erp.production.com
ODOO_DB_NAME=production
ODOO_ADMIN_USER=brain_service
ODOO_ADMIN_PASSWORD=  # Loaded from Vault
ODOO_ADDONS_PATH=/opt/odoo/addons
ODOO_TIMEOUT_SECONDS=30
ODOO_ENFORCE_TRUST_TIER=true  # ENFORCED
```

```bash
# Startup script (loads secrets)
#!/bin/bash
export ODOO_ADMIN_PASSWORD=$(vault kv get -field=password secret/odoo/brain)
docker compose -f docker-compose.prod.yml up -d
```

---

### Scenario 3: Remote Odoo Instance

```bash
# .env (Odoo on different server)
ODOO_BASE_URL=https://192.168.1.100:8069
ODOO_DB_NAME=company_erp
ODOO_ADMIN_USER=brain_integration
ODOO_ADMIN_PASSWORD=${ODOO_PASSWORD}  # From secrets
ODOO_ADDONS_PATH=/var/lib/odoo/brain_modules
ODOO_TIMEOUT_SECONDS=60  # Increased for network latency
ODOO_ENFORCE_TRUST_TIER=true
```

**Requirements:**
- Network connectivity from BRAiN to Odoo
- Shared filesystem (NFS, SMB, or rsync)
- SSL certificate for HTTPS

---

## Verification

### Step 1: Check Configuration

```bash
# From BRAiN backend container
docker compose exec backend python -c "
import os
print('Odoo Config:')
print(f'  Base URL: {os.getenv(\"ODOO_BASE_URL\")}')
print(f'  Database: {os.getenv(\"ODOO_DB_NAME\")}')
print(f'  User: {os.getenv(\"ODOO_ADMIN_USER\")}')
print(f'  Password: {'***' if os.getenv(\"ODOO_ADMIN_PASSWORD\") else 'NOT SET'}')
print(f'  Addons Path: {os.getenv(\"ODOO_ADDONS_PATH\")}')
print(f'  Timeout: {os.getenv(\"ODOO_TIMEOUT_SECONDS\", \"30\")}s')
print(f'  Enforce Trust: {os.getenv(\"ODOO_ENFORCE_TRUST_TIER\", \"true\")}')
"
```

### Step 2: Test Connection

```bash
# Via BRAiN API
curl http://localhost:8000/api/odoo/status

# Expected response (success):
{
  "connected": true,
  "status": "connected",
  "odoo_version": "19",
  "server_version": "19.0-20251215",
  "database": "production",
  "protocol_version": 1,
  "uid": 2
}

# Expected response (failure):
{
  "connected": false,
  "status": "error",
  "error": "Failed to authenticate: ..."
}
```

### Step 3: Test Module Listing

```bash
# List Odoo modules
curl http://localhost:8000/api/odoo/modules

# Expected: List of installed modules
{
  "modules": [...],
  "total_count": 42,
  "filters_applied": {}
}
```

---

## Troubleshooting

### Problem 1: "Missing required Odoo ENV variables"

**Cause:** One or more required ENV vars not set

**Solution:**
```bash
# Check which are missing
docker compose exec backend env | grep ODOO

# Set in .env file
cat >> .env <<EOF
ODOO_BASE_URL=http://odoo:8069
ODOO_DB_NAME=production
ODOO_ADMIN_USER=admin
ODOO_ADMIN_PASSWORD=secure_password
ODOO_ADDONS_PATH=/opt/odoo/addons
EOF

# Restart
docker compose restart backend
```

---

### Problem 2: "Authentication failed - invalid credentials"

**Cause:** Wrong username or password

**Solution:**
```bash
# Test credentials manually
docker compose exec odoo odoo-bin shell -d ${ODOO_DB_NAME}

# Reset admin password (if needed)
docker compose exec odoo odoo-bin \
  --database=${ODOO_DB_NAME} \
  --reset-password \
  --login=admin
```

---

### Problem 3: "Module not found in Odoo after copy"

**Cause:** ODOO_ADDONS_PATH not mounted correctly

**Solution:**
```bash
# Check if path exists in Odoo container
docker compose exec odoo ls -la /mnt/extra-addons

# Check if BRAiN can write to path
docker compose exec backend touch /opt/odoo/addons/test.txt
docker compose exec odoo ls -la /mnt/extra-addons/test.txt

# Fix: Ensure both containers use same volume
# docker-compose.yml
volumes:
  odoo_addons:

services:
  brain-backend:
    volumes:
      - odoo_addons:/opt/odoo/addons  # ← Same volume
  odoo:
    volumes:
      - odoo_addons:/mnt/extra-addons  # ← Same volume
```

---

### Problem 4: Timeout errors

**Cause:** XML-RPC timeout too short for slow operations

**Solution:**
```bash
# Increase timeout
ODOO_TIMEOUT_SECONDS=60

# Or diagnose slow Odoo
docker compose logs odoo
```

---

### Problem 5: Trust tier blocking legitimate requests

**Cause:** Request not coming from localhost

**Solution:**
```bash
# Option 1: Disable enforcement (dev only!)
ODOO_ENFORCE_TRUST_TIER=false

# Option 2: Access from localhost
curl http://localhost:8000/api/axe/odoo/info  # ✅
curl http://192.168.1.100:8000/api/axe/odoo/info  # ❌

# Option 3: Use SSH tunnel
ssh -L 8000:localhost:8000 user@server
curl http://localhost:8000/api/axe/odoo/info  # ✅
```

---

## Security Checklist

Before deploying to production:

- [ ] Use HTTPS for ODOO_BASE_URL
- [ ] Use strong password (20+ characters)
- [ ] Store password in secrets manager (not .env)
- [ ] Set ODOO_ENFORCE_TRUST_TIER=true
- [ ] Use dedicated service account (not default admin)
- [ ] Rotate passwords regularly
- [ ] Enable firewall between BRAiN and Odoo
- [ ] Monitor failed authentication attempts
- [ ] Audit module installations
- [ ] Test rollback procedure

---

## References

- **Sprint IV Documentation:** `docs/SPRINT4_AXE_ODOO.md`
- **PR Review Report:** `docs/SPRINT4_1_PR_REVIEW.md`
- **Odoo Documentation:** https://www.odoo.com/documentation/19.0/
- **Docker Compose Reference:** https://docs.docker.com/compose/

---

**Configuration Guide Complete**

*Sprint IV: AXE × Odoo Integration*
*Version 1.0.0 | 2025-12-25*
