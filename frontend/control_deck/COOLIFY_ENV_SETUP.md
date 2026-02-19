# Coolify Environment Variables Setup

## Required Build Arguments (Build-time)

In Coolify unter **Build Configuration → Build Arguments** hinzufügen:

```bash
NEXT_PUBLIC_BRAIN_API_BASE=https://brain-api.yourdomain.com
```

## Required Environment Variables (Runtime)

In Coolify unter **Environment Variables** hinzufügen:

```bash
# Authentication Secret (CRITICAL - generiere ein sicheres Secret)
AUTH_SECRET=your-super-secret-auth-key-min-32-chars

# API Base URL (für client-side requests)
NEXT_PUBLIC_BRAIN_API_BASE=https://brain-api.yourdomain.com

# Node Environment
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
```

## AUTH_SECRET generieren

```bash
# Generiere ein sicheres Secret (32+ Zeichen):
openssl rand -base64 32
```

## Vollständige Coolify Konfiguration

### Service: Control Deck Frontend

**General:**
- Name: brain-control-deck
- Port: 3000
- Build Pack: Dockerfile
- Dockerfile Location: frontend/control_deck/Dockerfile
- Base Directory: /

**Build Arguments:**
```
NEXT_PUBLIC_BRAIN_API_BASE=https://brain-api.satoshiflow.com
```

**Environment Variables:**
```
AUTH_SECRET=<generiertes-secret-hier-einfügen>
NEXT_PUBLIC_BRAIN_API_BASE=https://brain-api.satoshiflow.com
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
```

**Health Check:**
- Path: /
- Port: 3000
- Interval: 30s

## Troubleshooting

### Build failed - Check Debug Logs

In Coolify:
1. Klicke auf "Show Debug Logs"
2. Suche nach Fehlern mit Pattern:
   - `Error: `
   - `Failed to compile`
   - `Module not found`
   - `Cannot find module`

### Common Build Errors

#### 1. Memory Issues
```
JavaScript heap out of memory
```
**Fix:** Erhöhe Build Memory in Coolify Resource Limits

#### 2. Missing Dependencies
```
Cannot find module 'react-markdown'
```
**Fix:** Verify package-lock.json ist committed

#### 3. TypeScript Errors
```
Type error: ...
```
**Fix:** Bereits deaktiviert via `ignoreBuildErrors: true` in next.config.mjs

#### 4. Missing ENV Vars
```
ReferenceError: process is not defined
```
**Fix:** Setze alle NEXT_PUBLIC_* variablen als Build Args

### Test Build Locally with Docker

```bash
cd /home/oli/dev/brain-v2/frontend/control_deck

# Build with production settings
docker build \
  --build-arg NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8000 \
  -t control-deck:test \
  .

# Run container
docker run -p 3000:3000 \
  -e AUTH_SECRET=test-secret-min-32-characters-long \
  control-deck:test
```

### Memory Limits für Coolify Build

Falls "JavaScript heap out of memory" Fehler:

In Coolify Service Settings:
- Memory Limit: 4GB (während Build)
- Memory Reservation: 2GB

Oder in Dockerfile NODE_OPTIONS setzen:
```dockerfile
ENV NODE_OPTIONS="--max-old-space-size=4096"
```

## Post-Deployment Verification

Nach erfolgreichem Deployment:

```bash
# Health Check
curl https://control-deck.yourdomain.com

# Test API Connection
curl https://control-deck.yourdomain.com/api/health

# Test AXE Identity Pages
# Browser: https://control-deck.yourdomain.com/axe/identity
```
