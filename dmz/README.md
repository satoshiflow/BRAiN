# BRAiN DMZ Gateway Services

**Version:** 1.0.0
**Phase:** B - DMZ Gateway & AXE Connector Foundation
**Last Updated:** 2025-12-24

---

## Overview

The DMZ (Demilitarized Zone) layer provides controlled external communication for BRAiN while maintaining core isolation.

**Key Principles:**
- **Separation**: DMZ runs in isolated Docker network (`brain_dmz_net`)
- **Transport-Only**: No business logic in DMZ services
- **Stateless**: No persistent data in DMZ
- **Fail-Closed**: Stopped when Sovereign Mode is active
- **Auditable**: All DMZ actions logged and auditable

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External World                          │
│            (Telegram, Webhooks, External APIs)              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       DMZ Zone                              │
│                  (brain_dmz_net)                            │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         telegram-gateway (Port 8001)                 │  │
│  │  - Telegram Bot webhook receiver                     │  │
│  │  - Transport-only forwarding                         │  │
│  │  - No business logic                                 │  │
│  └─────────────────────┬────────────────────────────────┘  │
│                        │                                    │
└────────────────────────┼────────────────────────────────────┘
                         │ HTTP API only
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Core Zone                              │
│                 (brain_internal)                            │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         BRAiN Backend (Port 8000)                    │  │
│  │  - Business logic                                    │  │
│  │  - Authentication & authorization                    │  │
│  │  - Database access                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Postgres │ Redis │ Qdrant                           │  │
│  │  (NOT accessible from DMZ)                           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Services

### telegram-gateway

**Purpose**: Transport-only gateway for Telegram Bot API

**Location**: `dmz/telegram-gateway/`

**Features**:
- Receives Telegram webhooks
- Forwards to Core API endpoint: `/api/telegram/webhook`
- Health checks
- No state, no business logic

**Environment Variables**:
```bash
TELEGRAM_BOT_TOKEN=<your-bot-token>
TELEGRAM_MODE=webhook  # or polling
BRAIN_CORE_API_URL=http://brain-backend:8000
BRAIN_CORE_API_TOKEN=<secret-token>
```

**Endpoints**:
- `GET /health` - Health check
- `POST /webhook/telegram` - Telegram webhook receiver
- `GET /status` - Gateway status (no secrets)

---

## Network Isolation

### DMZ Network
- **Name**: `brain_dmz_net`
- **Subnet**: `172.21.0.0/16`
- **Internet Access**: ✅ Allowed (for external APIs)
- **Core API Access**: ✅ Allowed (HTTP only)
- **Database Access**: ❌ **Blocked by firewall**

### Firewall Rules (Phase B.5)
```bash
# Allow DMZ → Core API
iptables -A DOCKER-USER -s 172.21.0.0/16 -d 172.20.0.0/16 -p tcp --dport 8000 -j ACCEPT

# Block DMZ → Databases
iptables -A DOCKER-USER -s 172.21.0.0/16 -d 172.20.0.0/16 -p tcp --dport 5432 -j DROP  # Postgres
iptables -A DOCKER-USER -s 172.21.0.0/16 -d 172.20.0.0/16 -p tcp --dport 6379 -j DROP  # Redis
iptables -A DOCKER-USER -s 172.21.0.0/16 -d 172.20.0.0/16 -p tcp --dport 6333 -j DROP  # Qdrant
```

---

## Usage

### Start DMZ Services
```bash
docker compose -f docker-compose.dmz.yml up -d
```

### Stop DMZ Services
```bash
docker compose -f docker-compose.dmz.yml down
```

### Check DMZ Status
```bash
docker compose -f docker-compose.dmz.yml ps
```

### View DMZ Logs
```bash
docker compose -f docker-compose.dmz.yml logs -f telegram-gateway
```

### Test Gateway Health
```bash
curl http://localhost:8001/health
```

---

## Sovereign Mode Enforcement

When Sovereign Mode is activated (`BRAIN_MODE=sovereign`):

1. **DMZ is automatically stopped** via `dmz_control` backend module
2. **Audit events emitted**:
   - `sovereign.dmz_stopped`
   - `sovereign.dmz_blocked`
3. **Firewall rules block DMZ** (if not stopped)
4. **No external communication** possible

**Fail-Closed Design**: If DMZ cannot be stopped, Sovereign Mode activation fails.

---

## Security Considerations

### ✅ Security Features
- Separate Docker network (no direct database access)
- Stateless services (no persistent DMZ data)
- ENV-based secrets (no hardcoded credentials)
- Non-root containers
- Health checks and monitoring
- Audit trail for all DMZ operations

### ⚠️ Security Rules
- **Never** put business logic in DMZ services
- **Never** store state in DMZ
- **Always** authenticate Core API calls
- **Always** validate payloads before forwarding
- **Never** expose internal endpoints externally

---

## Adding New DMZ Services

To add a new gateway service:

1. **Create service directory**: `dmz/my-gateway/`
2. **Implement transport-only logic**: No business logic, only forwarding
3. **Add to docker-compose.dmz.yml**:
   ```yaml
   my-gateway:
     build: ./dmz/my-gateway
     networks:
       - brain_dmz_net
       - brain_internal
     # ... rest of config
   ```
4. **Update firewall rules** in `scripts/sovereign-fw.sh`
5. **Test isolation**: Verify no direct database access
6. **Document in this README**

---

## Troubleshooting

### DMZ service cannot reach Core API
```bash
# Check if brain_internal network exists
docker network ls | grep brain_internal

# Check if DMZ service is on both networks
docker inspect brain-dmz-telegram | grep Networks -A 10
```

### DMZ service can access database (CRITICAL)
```bash
# This should FAIL (blocked by firewall):
docker exec brain-dmz-telegram nc -zv brain-postgres 5432

# If it succeeds, firewall rules are missing!
sudo scripts/sovereign-fw.sh apply sovereign
```

### Sovereign Mode doesn't stop DMZ
```bash
# Check DMZ control module logs
docker logs brain-backend | grep dmz_control

# Manually stop DMZ
docker compose -f docker-compose.dmz.yml down
```

---

## Files

```
dmz/
├── README.md                    # This file
├── telegram-gateway/
│   ├── Dockerfile              # Minimal Python/FastAPI image
│   └── main.py                 # Transport-only gateway
└── (future gateways...)
```

---

## References

- **Phase B Documentation**: `IMPLEMENTATION_TODO.md` (Phase B.1-B.5)
- **Sovereign Mode**: `backend/app/modules/sovereign_mode/`
- **DMZ Control**: `backend/app/modules/dmz_control/` (Phase B.3)
- **Firewall Rules**: `scripts/sovereign-fw.sh` (Phase B.5)

---

**Last Updated**: 2025-12-24
**Version**: 1.0.0 (Phase B - Initial DMZ Implementation)
