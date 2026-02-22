# 🚀 Deployment Anleitung - Better Auth & ControlDeck v2

**Datum:** 2026-02-21  
**GitHub Branch:** `better-auth-controldeck-v2`  
**URL:** https://github.com/satoshiflow/BRAiN/tree/better-auth-controldeck-v2

---

## Teil 1: Better Auth Service (Port 3030)

### Schritt 1: Coolify UI öffnen
```
http://46.224.37.114:8000
```

### Schritt 2: Projekt auswählen
```
Projekt: BRAiN
```

### Schritt 3: Service anlegen
```
1. Klicke: "+ Add Service"
2. Wähle: "Public Repository"
3. Repository: https://github.com/satoshiflow/BRAiN
4. Branch: better-auth-controldeck-v2
5. Base Directory: better-auth-node
6. Build Pack: Docker Compose
```

### Schritt 4: Konfiguration
```yaml
Name: better-auth-node
Description: Better Auth Node.js Service
Domain: auth.falklabs.de
Port: 3030 (extern) → 3000 (intern)
```

### Schritt 5: Environment Variables
```bash
DATABASE_URL=postgresql://user:password@postgres-qcks8kwws80cw0s4sscw00wg:5432/better_auth
BETTER_AUTH_SECRET=xwt9wydiCHA9RwxU5h+sLSZJl71gQeWPVDEHcyD0MVs=
BETTER_AUTH_URL=https://auth.falklabs.de
TRUSTED_ORIGINS=https://control.brain.falklabs.de,https://axe.brain.falklabs.de,https://api.brain.falklabs.de
PORT=3000
NODE_ENV=production
```

### Schritt 6: Deploy
```
Klicke: "Deploy"
Warte: 5-10 Minuten (Build + Start)
```

---

## Teil 2: ControlDeck v2 (Port 3001)

### Schritt 1: Service anlegen
```
1. Klicke: "+ Add Service"
2. Wähle: "Public Repository"
3. Repository: https://github.com/satoshiflow/BRAiN
4. Branch: better-auth-controldeck-v2
5. Base Directory: frontend/controldeck-v2
6. Build Pack: Dockerfile
```

### Schritt 2: Konfiguration
```yaml
Name: controldeck-v2
Description: BRAiN ControlDeck v2 Dashboard
Domain: control.brain.falklabs.de
Port: 3001 (extern) → 3000 (intern)
```

### Schritt 3: Build Arguments
```yaml
NEXT_PUBLIC_BRAIN_API_BASE: http://backend:8000
```

### Schritt 4: Environment Variables
```bash
PORT=3000
NODE_ENV=production
NEXT_PUBLIC_BRAIN_API_BASE=http://backend:8000
```

### Schritt 5: Deploy
```
Klicke: "Deploy"
Warte: 10-15 Minuten (npm install + Build)
```

---

## Teil 3: Verifikation

### Better Auth testen
```bash
# Health Check
curl https://auth.falklabs.de:3030/health

# Sign Up
curl -X POST https://auth.falklabs.de:3030/api/auth/sign-up/email \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","name":"Test"}'

# Sign In
curl -X POST https://auth.falklabs.de:3030/api/auth/sign-in/email \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

### ControlDeck v2 testen
```bash
# Öffne im Browser
https://control.brain.falklabs.de

# Sollte anzeigen:
# - Dashboard mit KPIs
# - Sidebar Navigation
# - Mission Control
```

---

## Fehlerbehebung

### Build dauert zu lange
- **Normal:** Erster Build 10-15 Minuten
- **Abbruch:** Nur wenn >30 Minuten

### Port bereits belegt
```bash
# Prüfen:
sudo lsof -i :3030
sudo lsof -i :3001

# Falls belegt:
sudo kill -9 <PID>
```

### Database Connection failed
```bash
# Prüfe PostgreSQL Container:
docker ps | grep postgres

# Prüfe Netzwerk:
docker network inspect qcks8kwws80cw0s4sscw00wg
```

### CORS Errors
```bash
# Prüfe TRUSTED_ORIGINS:
# Muss alle Domains enthalten
```

---

## Status Übersicht

| Service | Port | Status | URL |
|---------|------|--------|-----|
| OpenWebUI | 3000 | ✅ Läuft | - |
| **Better Auth** | **3030** | ⏳ **Deploy** | auth.falklabs.de |
| **ControlDeck v2** | **3001** | ⏳ **Deploy** | control.brain.falklabs.de |
| AXE-UI | 3002 | ✅ Läuft | axe.brain.falklabs.de |
| BRAiN API | 8000 | ✅ Läuft | api.brain.falklabs.de |

---

## Support

Bei Problemen:
1. Coolify Logs prüfen
2. Container Status: `docker ps`
3. Network: `docker network ls`
4. GitHub Branch: `better-auth-controldeck-v2`

**Beginne mit Teil 1 (Better Auth) jetzt!**
