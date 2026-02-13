# 🔍 BRAIN IST-ZUSTAND ANALYSE

**Analysiert am:** 2026-01-07
**Quelle:** Docker Compose Konfigurationen (lokal)
**Coolify API:** Nicht erreichbar von dieser Umgebung (wird auf Server benötigt)

---

## 📊 AKTUELLE KONFIGURATION

### **BASE (docker-compose.yml)**

Genutzt für Coolify/Traefik Deployments mit Let's Encrypt SSL:

| Service | Domain | Traefik Priority | Port (intern) | Besonderheiten |
|---------|--------|------------------|---------------|----------------|
| **backend** | `dev.brain.falklabs.de` | 10 (hoch) | 8000 | Nur für `/api`, `/docs`, `/redoc`, `/openapi.json` |
| **control_deck** | `dev.brain.falklabs.de` | 1 (niedrig) | 3000 | **⚠️ KONFLIKT - gleiche Domain wie backend!** |
| **axe_ui** | `axe.dev.brain.falklabs.de` | - | 3000 | Eigene Subdomain ✅ |

**Netzwerk:**
- `brain_internal` - Interne Kommunikation
- `mw0ck04s8go048c0g4so48cc` - Coolify Traefik Netzwerk

**ENV in Base:**
- Backend: Keine spezifische API URL
- control_deck: `NEXT_PUBLIC_BRAIN_API_BASE=http://backend:8000` (intern)
- axe_ui: `NEXT_PUBLIC_BRAIN_API_BASE=http://backend:8000` (intern)

---

### **DEV (docker-compose.dev.yml)**

Für lokale Entwicklung mit Port-Mapping:

| Service | Container Name | Port Mapping | API Base |
|---------|---------------|--------------|----------|
| **backend** | dev-backend | 8001:8000 | - |
| **control_deck** | dev-control-deck | 3001:3000 | http://localhost:8001 |
| **axe_ui** | dev-axe-ui | 3002:3000 | http://localhost:8001 |
| **postgres** | dev-postgres | (intern) | DB: `brain_dev` |

**ENV:**
- `APP_ENV=development`
- `LOG_LEVEL=DEBUG`
- Build-time arg: `NEXT_PUBLIC_BRAIN_API_BASE: http://localhost:8001`

---

### **PROD (docker-compose.prod.yml)**

Für Production Deployment:

| Service | Container Name | Port Mapping | API Base |
|---------|---------------|--------------|----------|
| **backend** | prod-backend | 8000:8000 | - |
| **control_deck** | prod-control-deck | 3000:3000 | https://brain.falklabs.de |
| **axe_ui** | prod-axe-ui | 3005:3000 | https://brain.falklabs.de |
| **postgres** | prod-postgres | (intern) | DB: `brain_prod` |

**ENV:**
- `APP_ENV=production`
- `LOG_LEVEL=WARNING`
- `ENABLE_API_CACHING=true`
- `NODE_ENV=production`

**Besonderheiten:**
- Redis Persistence aktiviert (`--appendonly yes`)
- Separate Volume für Redis Data

---

### **STAGE (docker-compose.stage.yml)**

⚠️ **Staging-Datei existiert, aber wurde noch nicht analysiert**

---

## ⚠️ IDENTIFIZIERTE PROBLEME

### 1. **Domain-Konflikt (dev.brain.falklabs.de)**

**Problem:**
- Backend UND control_deck nutzen beide `dev.brain.falklabs.de`
- Routing erfolgt über Traefik Priority:
  - Backend (Priority 10) matcht `/api/*`, `/docs/*`, `/redoc/*`, `/openapi.json`
  - control_deck (Priority 1) matcht alle anderen Requests

**Risiko:**
- Verwirrendes Setup
- Fehleranfällig bei Traefik-Änderungen
- Schwer zu debuggen
- Nicht konsistent mit axe_ui (eigene Subdomain)

---

### 2. **Inkonsistente Domain-Struktur**

**Aktuell:**
```
dev.brain.falklabs.de           → Backend API + Control Deck (gemischt)
axe.dev.brain.falklabs.de       → AXE UI (sauber getrennt)
brain.falklabs.de (prod)        → ???
```

**Problem:**
- axe_ui hat eigene Subdomain, control_deck nicht
- Production Domains nicht klar definiert in docker-compose.prod.yml
- Keine staging Domains dokumentiert

---

### 3. **CORS Konfiguration**

**Aktuell (backend/.env):**
```
CORS_ORIGINS=["*"]
```

**Problem:**
- Zu permissiv (erlaubt alle Origins)
- Sollte spezifisch sein für dev/prod/stage

---

### 4. **Hardcoded API URLs**

**Gefunden:**
- `.env.example` Zeile 102: `OPENROUTER_SITE_URL=https://brain.falklabs.de`
- Keine weiteren hardcoded Domains im Code

**Gut:**
- Meiste API URLs sind environment-variable basiert ✅

---

## 📁 RELEVANTE DATEIEN

### **Konfigurationsdateien:**
```
.env.example                              # Template mit Domain-Referenzen
backend/.env                              # Backend ENV (CORS_ORIGINS)
frontend/control_deck/.env.local          # Frontend API Base
docker-compose.yml                        # Base (Traefik Labels)
docker-compose.dev.yml                    # Dev Overrides
docker-compose.prod.yml                   # Prod Overrides
docker-compose.stage.yml                  # Stage Overrides (nicht analysiert)
```

### **Frontend Configs:**
```
frontend/control_deck/next.config.mjs
frontend/axe_ui/next.config.mjs
frontend/brain_control_ui/next.config.mjs
frontend/brain_ui/next.config.js
```

---

## 🎯 HANDLUNGSBEDARF

1. ✅ **Domain-Konflikt auflösen**
   - Backend auf eigene Subdomain: `api.dev.brain.falklabs.de`
   - control_deck behält: `dev.brain.falklabs.de`

2. ✅ **Konsistente Struktur für alle Umgebungen**
   - DEV, STAGE, PROD jeweils mit klaren Subdomains

3. ✅ **CORS richtig konfigurieren**
   - Spezifische Origins pro Umgebung

4. ✅ **ENV-Variablen aktualisieren**
   - `NEXT_PUBLIC_BRAIN_API_BASE` auf neue API Subdomains

5. ✅ **Traefik Labels updaten**
   - Neue Routing Rules ohne Priority-Hacks

---

## 📝 NÄCHSTE SCHRITTE

1. **Coolify API Zugriff herstellen** (auf Server)
   - Script `coolify_manager.py` auf Server kopieren
   - Mit Coolify API Token ausführen
   - Backup erstellen: `python3 coolify_manager.py export`

2. **SOLL-Konzept finalisieren**
   - Subdomain-Struktur definieren
   - ENV-Variablen planen
   - CORS-Konfiguration festlegen

3. **Migration Scripts erstellen**
   - Automatisierte Coolify API Updates
   - Validierung
   - Rollback-Mechanismus

4. **Testing auf DEV**
   - Zuerst DEV migrieren
   - Testen
   - Dann STAGE
   - Dann PROD

---

**Erstellt von:** Claude Code
**Basis:** Docker Compose Analyse
**Status:** Bereit für SOLL-Konzept Phase
