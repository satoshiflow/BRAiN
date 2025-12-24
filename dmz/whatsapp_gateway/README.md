# BRAiN WhatsApp Gateway (Transport-Only)

## Purpose

Minimal WhatsApp gateway that ONLY forwards messages between WhatsApp and BRAiN Core API.

**Security Constraints:**
- ❌ NO business logic
- ❌ NO state storage
- ❌ NO database access
- ✅ ONLY message forwarding

## Architecture

```
WhatsApp User ↔ WhatsApp Gateway ↔ Core API (host.docker.internal:8000)
```

## Environment Variables

```bash
WHATSAPP_PHONE_NUMBER=+1234567890    # Required: WhatsApp phone number
BRAIN_API_URL=http://host.docker.internal:8000  # Core API URL
LOG_LEVEL=INFO                        # Logging level
```

## Usage

### Docker Compose

The gateway is part of the DMZ compose stack:

```bash
docker compose -f docker-compose.dmz.yml up -d whatsapp_gateway
```

### Standalone

```bash
cd dmz/whatsapp_gateway
export WHATSAPP_PHONE_NUMBER="+1234567890"
export BRAIN_API_URL="http://localhost:8000"
python gateway.py
```

## Health Check

```bash
curl http://localhost:8002/health
# {"status": "healthy", "service": "whatsapp"}
```

## Message Flow

1. User sends WhatsApp message
2. Gateway receives message (sanitized logging - no content)
3. Gateway forwards to Core API: `POST /api/axe/message`
4. Core processes and returns reply
5. Gateway sends reply back to WhatsApp user

## Security

- Does NOT log message content (privacy)
- Only logs metadata (sender ID, message ID)
- Minimal error information exposed
- No state persistence

## Limitations

- Requires WhatsApp Business API or whatsapp-web.py setup
- Phone number must be verified
- No multimedia support (text only)
