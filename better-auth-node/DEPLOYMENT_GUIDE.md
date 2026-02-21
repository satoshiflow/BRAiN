# Better Auth Node.js - Deployment Guide

**Datum:** 2026-02-21  
**Service:** better-auth-node  
**Domain:** auth.falklabs.de  
**Port:** 3000

---

## Voraussetzungen

- [ ] Coolify läuft auf http://46.224.37.114:8000
- [ ] Identity Service läuft (PostgreSQL verfügbar)
- [ ] Domain auth.falklabs.de verfügbar

---

## Schnell-Deployment (Manuell)

### Schritt 1: Coolify UI öffnen

```
URL: http://46.224.37.114:8000
Login: Mit deinen Credentials
```

### Schritt 2: Projekt auswählen

```
Projekt: BRAiN
```

### Schritt 3: Neuen Service anlegen

```
1. Klicke auf: "+ Add Service"
2. Wähle: "Docker Compose"
3. Warte auf das Formular
```

### Schritt 4: Service konfigurieren

```yaml
Name: better-auth-node
Description: Better Auth Node.js Service
```

### Schritt 5: Docker Compose einfügen

```yaml
# Kopiere den Inhalt aus:
# /home/oli/projects/BRAiN/BRAiN/better-auth-node/docker-compose.yml

version: '3.8'

services:
  better-auth:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: better-auth-node
    ports:
      - '3000:3000'
    environment:
      - PORT=3000
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - BETTER_AUTH_SECRET=${BETTER_AUTH_SECRET}
      - BETTER_AUTH_URL=${BETTER_AUTH_URL}
      - TRUSTED_ORIGINS=${TRUSTED_ORIGINS}
    networks:
      - coolify
      - qcks8kwws80cw0s4sscw00wg
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  coolify:
    external: true
  qcks8kwws80cw0s4sscw00wg:
    external: true
```

### Schritt 6: Domain konfigurieren

```
Domain: auth.falklabs.de
Port: 3030 (extern) → 3000 (intern)
```

### Schritt 7: Environment Variables setzen

```bash
# Database (PostgreSQL aus Identity Service)
DATABASE_URL=postgresql://user:password@postgres-qcks8kwws80cw0s4sscw00wg:5432/better_auth

# Better Auth Configuration
BETTER_AUTH_SECRET=qXVke1W21lkFGaxrB24BFmypI/IP4uC4V1me4MpjtsA=
BETTER_AUTH_URL=https://auth.falklabs.de
TRUSTED_ORIGINS=https://control.brain.falklabs.de,https://axe.brain.falklabs.de,https://api.brain.falklabs.de

# Server Configuration
PORT=3000
NODE_ENV=production
```

**Hinweis:** Generiere einen neuen Secret mit:
```bash
openssl rand -base64 32
```

### Schritt 8: Source Code auswählen

```
1. Wähle: "Local Directory" oder "Git Repository"
2. Pfad: /home/oli/projects/BRAiN/BRAiN/better-auth-node
3. Oder lade die Dateien als ZIP hoch
```

### Schritt 9: Deploy

```
1. Klicke: "Deploy"
2. Warte auf den Build (2-5 Minuten)
3. Prüfe Logs bei Fehlern
```

---

## Verifikation

### 1. Health Check testen

```bash
curl https://auth.falklabs.de/health
```

**Erwartete Antwort:**
```json
{
  "status": "ok",
  "service": "better-auth",
  "timestamp": "2026-02-21T..."
}
```

### 2. Auth Endpoints testen

```bash
# Sign Up
curl -X POST https://auth.falklabs.de/api/auth/sign-up/email \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","name":"Test User"}'

# Sign In
curl -X POST https://auth.falklabs.de/api/auth/sign-in/email \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

### 3. Session abrufen

```bash
curl https://auth.falklabs.de/api/auth/session \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## Fehlerbehebung

### Problem: Service startet nicht

**Lösung:**
```bash
# Logs prüfen in Coolify UI
# Meist: Environment Variables fehlen oder sind falsch
```

### Problem: Datenbank-Verbindung fehlgeschlagen

**Lösung:**
```bash
# Prüfe ob PostgreSQL läuft:
docker ps | grep postgres

# Prüfe Netzwerk-Verbindung:
docker network inspect qcks8kwws80cw0s4sscw00wg
```

### Problem: CORS Fehler

**Lösung:**
```bash
# TRUSTED_ORIGINS prüfen:
# Muss alle Domains enthalten:
# - https://control.brain.falklabs.de
# - https://axe.brain.falklabs.de
# - https://api.brain.falklabs.de
```

---

## Nächste Schritte nach Deployment

1. [ ] BRAiN Backend Auth Middleware implementieren
2. [ ] Frontend Auth Client einrichten
3. [ ] Login/Register Pages erstellen
4. [ ] Protected Routes implementieren

---

## Support

Bei Problemen:
- Coolify Logs prüfen
- Docker Container Logs: `docker logs better-auth-node`
- Network prüfen: `docker network ls`
