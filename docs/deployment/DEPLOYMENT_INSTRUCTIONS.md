# 🚀 Deployment Anweisungen - Backend Import Fix

**Branch:** `claude/check-project-status-y4koZ`
**Commit:** `96cb90b`
**Datum:** 2026-01-11

---

## 📋 Deployment Schritte

### 1. SSH zum Server verbinden

```bash
ssh root@brain.falklabs.de
# oder
ssh root@46.224.37.114
```

### 2. Zum Development Workspace navigieren

```bash
cd /root/BRAiN
# oder falls in /srv/dev deployed:
cd /srv/dev
```

### 3. Änderungen pullen

```bash
# Aktuellen Branch prüfen
git branch

# Auf den Fix-Branch wechseln
git checkout claude/check-project-status-y4koZ

# Oder Änderungen in aktuellen Branch mergen
git pull origin claude/check-project-status-y4koZ
```

### 4. Backend Container neu bauen

```bash
# Standard Deployment
docker compose build backend

# ODER für Development mit Override
docker compose -f docker-compose.yml -f docker-compose.dev.yml build backend

# ODER für Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml build backend --no-cache
```

### 5. Services neu starten

```bash
# Backend neu starten
docker compose up -d backend

# ODER mit Override
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d backend

# Warten auf Startup (10 Sekunden)
sleep 10
```

### 6. Health Check durchführen

```bash
# Backend Health Endpoint
curl http://localhost:8000/api/health

# Erwartete Antwort: {"status":"healthy","version":"0.3.0",...}
```

### 7. Logs prüfen

```bash
# Letzte 100 Zeilen
docker compose logs backend --tail=100

# Live Logs (Ctrl+C zum Beenden)
docker compose logs -f backend

# Nach Import-Fehlern suchen
docker compose logs backend | grep -i "import\|error\|exception"
```

### 8. Erwartete Log-Ausgabe (NACH Fix)

**✅ Sollte erscheinen:**
```
✅ Redis connection established
✅ Event Stream started
✅ Mission worker started
✅ All systems operational
Application startup complete.
Uvicorn running on http://0.0.0.0:8000
```

**❌ Sollte NICHT mehr erscheinen:**
```
⚠️ Could not import backend.api.routes: No module named 'backend.mission_control_core'
⚠️ Could not import app.api.routes: No module named 'backend.brain'
ModuleNotFoundError: No module named 'backend.brain'
(trapped) error reading bcrypt version
```

---

## 🔍 Detaillierte Verifikation

### A. Import-Fehler Check

```bash
# Prüfe auf Import-Fehler in Logs
docker compose logs backend 2>&1 | grep -i "ModuleNotFoundError\|ImportError"

# Sollte KEINE Ergebnisse zurückgeben
```

### B. bcrypt Warnung Check

```bash
# Prüfe auf bcrypt Warnung
docker compose logs backend 2>&1 | grep -i "bcrypt\|__about__"

# Sollte KEINE AttributeError Warnung zeigen
```

### C. Routes Auto-Discovery Check

```bash
# Prüfe ob alle Routes entdeckt wurden
curl -s http://localhost:8000/debug/routes | jq '.routes[] | select(.path | contains("neurorail"))' | head -5
curl -s http://localhost:8000/debug/routes | jq '.routes[] | select(.path | contains("governor"))' | head -5

# Sollte NeuroRail und Governor Endpoints zeigen
```

### D. Kritische Endpoints Test

```bash
# Agents
curl -s http://localhost:8000/api/agents/info | jq .

# Missions
curl -s http://localhost:8000/api/missions/info | jq .

# NeuroRail Identity
curl -s http://localhost:8000/api/neurorail/v1/identity/health | jq .

# Governor Stats
curl -s http://localhost:8000/api/governor/v1/stats | jq .

# Alle sollten 200 OK zurückgeben
```

### E. Frontend Test

```bash
# Control Deck (Port 3000 oder 3001)
curl -I http://localhost:3000
curl -I http://localhost:3001

# Sollte 200 OK oder 304 Not Modified zurückgeben
# NICHT mehr: 504 Gateway Timeout
```

---

## 🐛 Troubleshooting

### Problem 1: Immer noch Import-Fehler

**Symptom:**
```
ModuleNotFoundError: No module named 'backend.brain'
```

**Lösung:**
```bash
# Prüfe ob __init__.py Dateien existieren im Container
docker compose exec backend ls -la /app/app/__init__.py
docker compose exec backend ls -la /app/brain/__init__.py

# Sollten beide existieren

# Falls nicht, rebuild mit --no-cache
docker compose build backend --no-cache
docker compose up -d backend
```

### Problem 2: bcrypt Warnung bleibt

**Symptom:**
```
(trapped) error reading bcrypt version
AttributeError: module 'bcrypt' has no attribute '__about__'
```

**Lösung:**
```bash
# Prüfe bcrypt Version im Container
docker compose exec backend pip show bcrypt

# Sollte Version 3.2.2 zeigen

# Falls nicht, requirements.txt prüfen
docker compose exec backend cat /app/requirements.txt | grep bcrypt

# Rebuild
docker compose build backend --no-cache
```

### Problem 3: Backend startet nicht

**Symptom:**
```
docker compose logs backend
# Zeigt Container Exit Code 1 oder andere Fehler
```

**Lösung:**
```bash
# Prüfe Python Syntax
docker compose exec backend python3 -m py_compile /app/main.py

# Prüfe Dependencies
docker compose exec backend pip check

# Rebuild komplett
docker compose down backend
docker compose build backend --no-cache
docker compose up -d backend
```

### Problem 4: Gateway Timeout bleibt

**Symptom:**
```
curl http://localhost:3000
# 504 Gateway Timeout
```

**Lösung:**
```bash
# 1. Prüfe Backend Status
docker compose ps backend
# Sollte "Up" sein

# 2. Prüfe Backend Logs
docker compose logs backend --tail=50

# 3. Prüfe ob Backend Port erreichbar ist
curl http://localhost:8000/api/health

# 4. Prüfe Nginx/Traefik Konfiguration
docker compose logs nginx
# oder
docker compose logs traefik
```

---

## 📊 Erfolgsmetriken

Nach erfolgreichem Deployment sollten folgende Metriken erfüllt sein:

- [x] Backend startet ohne Import-Fehler
- [x] Health Endpoint return 200 OK
- [x] Keine bcrypt Warnungen in Logs
- [x] Alle 60+ API Endpoints verfügbar
- [x] NeuroRail Routes auto-discovered
- [x] Governor Routes auto-discovered
- [x] Frontend zeigt KEIN Gateway Timeout
- [x] Logs zeigen "All systems operational"

---

## 🔄 Rollback Plan (falls nötig)

Falls das Deployment fehlschlägt:

```bash
# 1. Zurück zum vorherigen Branch
git checkout v2  # oder main

# 2. Rebuild
docker compose build backend --no-cache

# 3. Restart
docker compose up -d backend

# 4. Verify
curl http://localhost:8000/api/health
```

---

## 📝 Änderungsübersicht

**Was wurde gefixt:**

1. **Package Markers erstellt:**
   - `backend/app/__init__.py`
   - `backend/brain/__init__.py`

2. **Import-Pfade korrigiert (96 Dateien):**
   - `from backend.brain.*` → `from brain.*`
   - `from backend.app.*` → `from app.*`
   - `from backend.modules.*` → `from modules.*`

3. **bcrypt Kompatibilität:**
   - `bcrypt==3.2.2` in requirements.txt gepinnt

4. **Dokumentation:**
   - CLAUDE.md mit Import-Konventionen aktualisiert

**Betroffene Module:**
- Governor (19 Dateien)
- Agents (25 Dateien)
- Tests (45 Dateien)
- Scripts (7 Dateien)

---

## ✅ Post-Deployment Checklist

Nach dem Deployment:

- [ ] Backend Logs prüfen (keine Errors)
- [ ] Health Endpoint funktioniert
- [ ] Frontend erreichbar (kein Gateway Timeout)
- [ ] Alle kritischen Endpoints testen
- [ ] Monitoring Dashboard prüfen
- [ ] Pull Request auf GitHub mergen (optional)

---

**Bei Problemen:**
- Logs speichern: `docker compose logs backend > backend-logs.txt`
- Container Status prüfen: `docker compose ps`
- Docker Events: `docker compose events --tail=50`

**Kontakt:**
- GitHub Issue: https://github.com/satoshiflow/BRAiN/issues
- Branch: claude/check-project-status-y4koZ
- Commit: 96cb90b
