# BRAiN Email Gateway (Transport-Only)

## Purpose

Minimal Email gateway (SMTP/IMAP bridge) that ONLY forwards messages between Email and BRAiN Core API.

**Security Constraints:**
- ❌ NO business logic
- ❌ NO state storage
- ❌ NO database access
- ✅ ONLY message forwarding

## Architecture

```
Email User ↔ IMAP/SMTP ↔ Email Gateway ↔ Core API (host.docker.internal:8000)
```

## Environment Variables

```bash
EMAIL_IMAP_HOST=imap.gmail.com           # Required: IMAP host
EMAIL_IMAP_PORT=993                       # IMAP port (default: 993)
EMAIL_SMTP_HOST=smtp.gmail.com           # Required: SMTP host
EMAIL_SMTP_PORT=587                       # SMTP port (default: 587)
EMAIL_ADDRESS=brain@example.com          # Required: Email address
EMAIL_PASSWORD=your_password             # Required: Email password/app password
EMAIL_POLL_INTERVAL=60                   # Poll interval in seconds (default: 60)
BRAIN_API_URL=http://host.docker.internal:8000  # Core API URL
LOG_LEVEL=INFO                           # Logging level
```

## Usage

### Docker Compose

The gateway is part of the DMZ compose stack:

```bash
docker compose -f docker-compose.dmz.yml up -d email_gateway
```

### Standalone

```bash
cd dmz/email_gateway
export EMAIL_IMAP_HOST="imap.gmail.com"
export EMAIL_SMTP_HOST="smtp.gmail.com"
export EMAIL_ADDRESS="brain@example.com"
export EMAIL_PASSWORD="your_app_password"
export BRAIN_API_URL="http://localhost:8000"
python gateway.py
```

## Health Check

```bash
curl http://localhost:8004/health
# {"status": "healthy", "service": "email", "imap_connected": true}
```

## Message Flow

1. User sends email to configured address
2. Gateway polls IMAP for new messages (every 60s by default)
3. Gateway forwards email body to Core API: `POST /api/axe/message`
4. Core processes and returns reply
5. Gateway sends reply email back to sender
6. Original email marked as read

## Security

- Does NOT log email content (privacy)
- Only logs metadata (sender, subject)
- Minimal error information exposed
- No state persistence
- Polls for new messages (no constant IMAP IDLE)

## Email Provider Setup

### Gmail
1. Enable IMAP in Gmail settings
2. Create App Password (if 2FA enabled): https://myaccount.google.com/apppasswords
3. Use app password instead of regular password

### Other Providers
- Ensure IMAP and SMTP are enabled
- Use correct host and port settings
- Some providers require app-specific passwords
