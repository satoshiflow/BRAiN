# Frontend Environment Variables Fix

## Problem

Das Frontend-Build verwendete `.env.local` von deinem Windows-System, was zu **3 kritischen Problemen** führte:

1. ❌ **Windows-spezifische Dateien im Linux-Container**
   - `.env.local` wurde ins Docker-Image kopiert
   - Die Datei ist für lokale Windows-Entwicklung, nicht für Container

2. ❌ **Falsche API-URL**
   - `.env.local` hatte: `NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8000`
   - Im Container sollte es sein: `http://backend:8000`
   - `localhost` im Container zeigt auf den Container selbst, nicht auf den Backend-Container

3. ❌ **Build-Zeit vs. Runtime Probleme**
   - Next.js benötigt `NEXT_PUBLIC_*` Variablen zur **Build-Zeit**
   - Die ENV-Variablen in `docker-compose.yml` werden zur **Runtime** gesetzt
   - Das bedeutet: Die Variablen wurden NICHT während `npm run build` berücksichtigt!

## Lösung (Dauerhaft)

### 1. `.dockerignore` hinzugefügt für alle Frontend-Apps

**Erstellt:**
- `frontend/control_deck/.dockerignore`
- `frontend/axe_ui/.dockerignore`
- `frontend/brain_control_ui/.dockerignore`

**Aktualisiert:**
- `frontend/brain_ui/.dockerignore`

**Inhalt:** `.env.local` und `.env*.local` werden NICHT ins Docker-Image kopiert.

### 2. Dockerfiles mit ARG/ENV erweitert

**control_deck/Dockerfile & axe_ui/Dockerfile:**

```dockerfile
FROM node:22-alpine AS builder

WORKDIR /app

# Build-time arguments for Next.js
ARG NEXT_PUBLIC_BRAIN_API_BASE=http://backend:8000
ENV NEXT_PUBLIC_BRAIN_API_BASE=$NEXT_PUBLIC_BRAIN_API_BASE

COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

COPY . .
RUN npm run build  # ✅ ENV ist jetzt während Build verfügbar
```

**Wie es funktioniert:**
- `ARG` definiert einen Build-Zeit-Parameter
- `ENV` setzt die Umgebungsvariable für `npm run build`
- Default-Wert: `http://backend:8000` (für docker-compose)

### 3. docker-compose.dev.yml mit build: args erweitert

**Vorher (FALSCH):**
```yaml
control_deck:
  environment:
    - NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8001  # ❌ Zu spät!
```

**Nachher (RICHTIG):**
```yaml
control_deck:
  build:
    args:
      NEXT_PUBLIC_BRAIN_API_BASE: http://localhost:8001  # ✅ Build-Zeit!
  environment:
    - NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8001   # Runtime (für SSR)
```

**Wichtig:** `build: args:` wird während `docker compose build` verwendet, **BEVOR** `npm run build` ausgeführt wird.

## Warum ist das wichtig?

### Next.js Build-Prozess

```
docker compose build
  ↓
docker build
  ↓
ARG NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8001  ← Build-Zeit
  ↓
npm run build  ← Next.js ersetzt NEXT_PUBLIC_* im Code
  ↓
Docker Image erstellt
  ↓
docker compose up
  ↓
environment: NEXT_PUBLIC_BRAIN_API_BASE=...  ← Runtime (nur für SSR)
```

**Ohne ARG:** Next.js findet die Variable NICHT während `npm run build` → API-Calls gehen ins Leere!

## Verwendung

### Entwicklung (Windows)

```bash
# Lokale Entwicklung (außerhalb Docker)
# .env.local wird verwendet ✅
npm run dev
```

```bash
# Docker-Entwicklung
docker compose -f docker-compose.yml -f docker-compose.dev.yml build
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Server-Deployment

```bash
# Auf Server (Linux)
docker compose -f docker-compose.yml -f docker-compose.dev.yml build
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# ✅ Verwendet ARG aus docker-compose.dev.yml
# ✅ KEINE .env.local im Image
# ✅ Korrekte API-URL: http://localhost:8001
```

### Produktion

```bash
# docker-compose.prod.yml sollte haben:
control_deck:
  build:
    args:
      NEXT_PUBLIC_BRAIN_API_BASE: https://dev.brain.falklabs.de/api
  environment:
    - NEXT_PUBLIC_BRAIN_API_BASE=https://dev.brain.falklabs.de/api
```

## Verifizierung

Nach dem Build kannst du prüfen, ob die Variable korrekt gesetzt wurde:

```bash
# Im Container prüfen
docker compose exec control_deck env | grep NEXT_PUBLIC

# Oder im Browser DevTools:
console.log(process.env.NEXT_PUBLIC_BRAIN_API_BASE)
```

## Best Practices

1. ✅ **NIEMALS** `.env.local` ins Docker-Image kopieren
2. ✅ **IMMER** `.env.local` in `.dockerignore` eintragen
3. ✅ **IMMER** `ARG` für Build-Zeit-Variablen verwenden
4. ✅ **IMMER** `build: args:` in docker-compose.yml setzen
5. ✅ **OPTIONAL** `environment:` für Runtime (SSR) zusätzlich setzen

## Siehe auch

- Next.js Environment Variables: https://nextjs.org/docs/app/building-your-application/configuring/environment-variables
- Docker ARG vs ENV: https://docs.docker.com/engine/reference/builder/#arg
- Docker Compose Build Args: https://docs.docker.com/compose/compose-file/build/#args
