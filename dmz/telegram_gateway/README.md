# BRAiN DMZ Telegram Gateway

**Transport-only** Telegram bot gateway for BRAiN DMZ zone.

## Security Constraints

- ✅ NO business logic
- ✅ NO state storage
- ✅ NO database access
- ✅ ONLY message forwarding (Telegram ↔ Core API)

## Features

- Telegram Bot API integration (python-telegram-bot 20.7)
- Two modes: Polling (dev) or Webhook (prod)
- Health check endpoint (`/health`)
- Automatic message forwarding to Core API
- No payload logging (security)

## Configuration

Environment variables (set in `docker-compose.dmz.yml` or `.env`):

```bash
# Required
TELEGRAM_BOT_TOKEN=<your_bot_token>

# Optional
BRAIN_API_URL=http://host.docker.internal:8000  # Core API endpoint
TELEGRAM_MODE=polling                           # polling or webhook
TELEGRAM_WEBHOOK_URL=https://your.domain/webhook  # if webhook mode
LOG_LEVEL=INFO
```

## Usage

### Development (Polling Mode)

```bash
cd /path/to/BRAiN
docker compose -f docker-compose.dmz.yml up telegram_gateway
```

### Production (Webhook Mode)

1. Set environment variables:
   ```bash
   TELEGRAM_MODE=webhook
   TELEGRAM_WEBHOOK_URL=https://your.domain/webhook
   ```

2. Start:
   ```bash
   docker compose -f docker-compose.dmz.yml up -d telegram_gateway
   ```

## API Endpoint

Messages are forwarded to:
```
POST http://<BRAIN_API_URL>/api/axe/message
```

Payload:
```json
{
  "message": "user message text",
  "metadata": {
    "source": "telegram",
    "user_id": "123456789",
    "username": "johndoe",
    "chat_id": "123456789",
    "message_id": 42
  }
}
```

Expected response:
```json
{
  "reply": "response text to send back to user"
}
```

## Health Check

```bash
curl http://localhost:8001/health
```

Response:
```json
{"status": "healthy", "mode": "polling"}
```

## Logs

Logs DO NOT contain message payloads for security reasons.

Example:
```
2025-12-24 12:00:00 | INFO     | Message from user 123456789
2025-12-24 12:00:01 | INFO     | Response sent to user 123456789
```

## Isolated from Core

This gateway:
- ❌ Cannot access Postgres
- ❌ Cannot access Redis
- ❌ Cannot access Qdrant
- ✅ Can only call Core HTTP API via `host.docker.internal`

## Stopped by Sovereign Mode

When BRAiN enters Sovereign Mode, this gateway is **automatically stopped** by the DMZ Control Service.

## License

Part of BRAiN (Base Repository for AI Networks)
