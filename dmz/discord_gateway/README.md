# BRAiN Discord Gateway (Transport-Only)

## Purpose

Minimal Discord bot gateway that ONLY forwards messages between Discord and BRAiN Core API.

**Security Constraints:**
- ❌ NO business logic
- ❌ NO state storage
- ❌ NO database access
- ✅ ONLY message forwarding

## Architecture

```
Discord User ↔ Discord Gateway ↔ Core API (host.docker.internal:8000)
```

## Environment Variables

```bash
DISCORD_BOT_TOKEN=your_bot_token_here    # Required: Discord bot token
DISCORD_COMMAND_PREFIX=!                  # Command prefix (default: !)
BRAIN_API_URL=http://host.docker.internal:8000  # Core API URL
LOG_LEVEL=INFO                            # Logging level
```

## Usage

### Docker Compose

The gateway is part of the DMZ compose stack:

```bash
docker compose -f docker-compose.dmz.yml up -d discord_gateway
```

### Standalone

```bash
cd dmz/discord_gateway
export DISCORD_BOT_TOKEN="your_token_here"
export DISCORD_COMMAND_PREFIX="!"
export BRAIN_API_URL="http://localhost:8000"
python gateway.py
```

## Health Check

```bash
curl http://localhost:8003/health
# {"status": "healthy", "service": "discord", "bot_user": "BRAiN#1234"}
```

## Message Flow

1. User sends Discord message with command prefix (e.g., `!hello`)
2. Gateway receives message (sanitized logging - no content)
3. Gateway forwards to Core API: `POST /api/axe/message`
4. Core processes and returns reply
5. Gateway sends reply back to Discord channel

## Security

- Does NOT log message content (privacy)
- Only logs metadata (user ID, channel ID, message ID)
- Minimal error information exposed
- No state persistence
- Only processes messages with command prefix

## Bot Setup

1. Create Discord application at https://discord.com/developers/applications
2. Create bot user and get token
3. Enable "Message Content Intent" in bot settings
4. Invite bot to server with appropriate permissions:
   - Read Messages
   - Send Messages
   - Read Message History
