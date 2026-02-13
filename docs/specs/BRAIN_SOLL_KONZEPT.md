# 🎯 BRAIN SOLL-KONZEPT - Subdomain-Architektur

**Version:** 1.0
**Erstellt am:** 2026-01-07
**Zweck:** Saubere Trennung aller Services über Subdomains (dev/stage/prod)

---

## 🌐 SUBDOMAIN-STRUKTUR

### **DEVELOPMENT Environment**

| Service | Subdomain | Zweck | SSL | Port (intern) |
|---------|-----------|-------|-----|---------------|
| **Control Deck** | `dev.brain.falklabs.de` | Frontend - System Admin UI | ✅ Let's Encrypt | 3000 |
| **Backend API** | `api.dev.brain.falklabs.de` | Backend REST API | ✅ Let's Encrypt | 8000 |
| **API Docs** | `docs.dev.brain.falklabs.de` | Swagger/ReDoc | ✅ Let's Encrypt | 8000 |
| **AXE UI** | `axe.dev.brain.falklabs.de` | AXE Conversational UI | ✅ Let's Encrypt | 3000 |

**Rationale:**
- `dev.brain.falklabs.de` - Primäre Entwicklungs-URL (Control Deck)
- `api.dev.brain.falklabs.de` - Klare Trennung für API-Zugriffe
- `docs.dev.brain.falklabs.de` - Separate Docs-URL (oder als Alias zu api)
- `axe.dev.brain.falklabs.de` - Bleibt wie bisher ✅

---

### **STAGING Environment**

| Service | Subdomain | Zweck | SSL | Port (intern) |
|---------|-----------|-------|-----|---------------|
| **Control Deck** | `stage.brain.falklabs.de` | Frontend - System Admin UI | ✅ Let's Encrypt | 3000 |
| **Backend API** | `api.stage.brain.falklabs.de` | Backend REST API | ✅ Let's Encrypt | 8000 |
| **API Docs** | `docs.stage.brain.falklabs.de` | Swagger/ReDoc | ✅ Let's Encrypt | 8000 |
| **AXE UI** | `axe.stage.brain.falklabs.de` | AXE Conversational UI | ✅ Let's Encrypt | 3000 |

**Rationale:**
- Staging als Pre-Production Test-Umgebung
- Identische Struktur wie PROD (für realistische Tests)

---

### **PRODUCTION Environment**

| Service | Subdomain | Zweck | SSL | Port (intern) |
|---------|-----------|-------|-----|---------------|
| **Control Deck** | `brain.falklabs.de` | Frontend - System Admin UI | ✅ Let's Encrypt | 3000 |
| **Backend API** | `api.brain.falklabs.de` | Backend REST API | ✅ Let's Encrypt | 8000 |
| **API Docs** | `docs.brain.falklabs.de` | Swagger/ReDoc | ✅ Let's Encrypt | 8000 |
| **AXE UI** | `axe.brain.falklabs.de` | AXE Conversational UI | ✅ Let's Encrypt | 3000 |

**Rationale:**
- `brain.falklabs.de` - Haupt-Produktions-URL (Control Deck)
- `api.brain.falklabs.de` - Production API
- Klare Trennung, keine Priority-Hacks nötig

---

## 🔧 TRAEFIK KONFIGURATION

### **Backend (alle Umgebungen)**

**DEV:**
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.backend-dev.rule=Host(`api.dev.brain.falklabs.de`)"
  - "traefik.http.routers.backend-dev.entrypoints=https"
  - "traefik.http.routers.backend-dev.tls=true"
  - "traefik.http.routers.backend-dev.tls.certresolver=letsencrypt"
  - "traefik.http.services.backend-dev.loadbalancer.server.port=8000"
```

**STAGE:**
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.backend-stage.rule=Host(`api.stage.brain.falklabs.de`)"
  - "traefik.http.routers.backend-stage.entrypoints=https"
  - "traefik.http.routers.backend-stage.tls=true"
  - "traefik.http.routers.backend-stage.tls.certresolver=letsencrypt"
  - "traefik.http.services.backend-stage.loadbalancer.server.port=8000"
```

**PROD:**
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.backend-prod.rule=Host(`api.brain.falklabs.de`)"
  - "traefik.http.routers.backend-prod.entrypoints=https"
  - "traefik.http.routers.backend-prod.tls=true"
  - "traefik.http.routers.backend-prod.tls.certresolver=letsencrypt"
  - "traefik.http.services.backend-prod.loadbalancer.server.port=8000"
```

---

### **Control Deck (alle Umgebungen)**

**DEV:**
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.control-deck-dev.rule=Host(`dev.brain.falklabs.de`)"
  - "traefik.http.routers.control-deck-dev.entrypoints=https"
  - "traefik.http.routers.control-deck-dev.tls=true"
  - "traefik.http.routers.control-deck-dev.tls.certresolver=letsencrypt"
  - "traefik.http.services.control-deck-dev.loadbalancer.server.port=3000"
```

**STAGE:**
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.control-deck-stage.rule=Host(`stage.brain.falklabs.de`)"
  - "traefik.http.routers.control-deck-stage.entrypoints=https"
  - "traefik.http.routers.control-deck-stage.tls=true"
  - "traefik.http.routers.control-deck-stage.tls.certresolver=letsencrypt"
  - "traefik.http.services.control-deck-stage.loadbalancer.server.port=3000"
```

**PROD:**
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.control-deck-prod.rule=Host(`brain.falklabs.de`)"
  - "traefik.http.routers.control-deck-prod.entrypoints=https"
  - "traefik.http.routers.control-deck-prod.tls=true"
  - "traefik.http.routers.control-deck-prod.tls.certresolver=letsencrypt"
  - "traefik.http.services.control-deck-prod.loadbalancer.server.port=3000"
```

---

### **API Docs (Optional - Alias zu Backend)**

**Option A: Separate Traefik Rule (empfohlen)**
```yaml
labels:
  # Backend-Regel (wie oben)
  - "traefik.http.routers.backend-dev.rule=Host(`api.dev.brain.falklabs.de`)"

  # Docs-Alias (zusätzlich)
  - "traefik.http.routers.docs-dev.rule=Host(`docs.dev.brain.falklabs.de`)"
  - "traefik.http.routers.docs-dev.entrypoints=https"
  - "traefik.http.routers.docs-dev.tls=true"
  - "traefik.http.routers.docs-dev.tls.certresolver=letsencrypt"
  - "traefik.http.routers.docs-dev.service=backend-dev"  # Nutzt gleichen Service
```

**Option B: Redirect (einfacher)**
- `docs.dev.brain.falklabs.de` redirected zu `api.dev.brain.falklabs.de/docs`

---

## 📝 ENVIRONMENT VARIABLEN

### **Backend (.env Änderungen)**

**DEV:**
```bash
# CORS Origins - spezifisch für dev
CORS_ORIGINS=["https://dev.brain.falklabs.de","https://axe.dev.brain.falklabs.de","https://docs.dev.brain.falklabs.de"]

# OpenRouter Site URL
OPENROUTER_SITE_URL=https://dev.brain.falklabs.de
OPENROUTER_SITE_NAME=BRAiN DEV
```

**STAGE:**
```bash
CORS_ORIGINS=["https://stage.brain.falklabs.de","https://axe.stage.brain.falklabs.de","https://docs.stage.brain.falklabs.de"]

OPENROUTER_SITE_URL=https://stage.brain.falklabs.de
OPENROUTER_SITE_NAME=BRAiN STAGING
```

**PROD:**
```bash
CORS_ORIGINS=["https://brain.falklabs.de","https://axe.brain.falklabs.de","https://docs.brain.falklabs.de"]

OPENROUTER_SITE_URL=https://brain.falklabs.de
OPENROUTER_SITE_NAME=BRAiN
```

---

### **Frontend Control Deck (.env.local / Build Args)**

**DEV:**
```bash
NEXT_PUBLIC_BRAIN_API_BASE=https://api.dev.brain.falklabs.de
```

**STAGE:**
```bash
NEXT_PUBLIC_BRAIN_API_BASE=https://api.stage.brain.falklabs.de
```

**PROD:**
```bash
NEXT_PUBLIC_BRAIN_API_BASE=https://api.brain.falklabs.de
```

---

### **Frontend AXE UI (.env.local / Build Args)**

Gleiche Struktur wie Control Deck (siehe oben).

---

## 🔒 COOKIE & SESSION HANDLING

**Domain Setting für Cookies:**
```python
# Für alle Subdomains gültig
COOKIE_DOMAIN=".brain.falklabs.de"

# Oder spezifisch pro Subdomain:
COOKIE_DOMAIN="dev.brain.falklabs.de"  # DEV
COOKIE_DOMAIN="stage.brain.falklabs.de"  # STAGE
COOKIE_DOMAIN="brain.falklabs.de"  # PROD
```

**Empfehlung:** Spezifisch pro Subdomain (höhere Sicherheit).

---

## 🗂️ DOCKER COMPOSE ÄNDERUNGEN

### **docker-compose.yml (Base) - WIRD NICHT MEHR GENUTZT FÜR DOMAINS**

Die Base-Datei sollte **keine** Traefik Labels mehr enthalten, da diese environment-spezifisch sind.

**Nur diese Labels bleiben:**
```yaml
labels:
  - "traefik.enable=false"  # Default: deaktiviert
```

---

### **docker-compose.dev.yml (DEV Overrides)**

```yaml
services:
  backend:
    container_name: dev-backend
    environment:
      - APP_ENV=development
      - CORS_ORIGINS=["https://dev.brain.falklabs.de","https://axe.dev.brain.falklabs.de"]
    networks:
      - brain_internal
      - mw0ck04s8go048c0g4so48cc  # Coolify Traefik
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend-dev.rule=Host(`api.dev.brain.falklabs.de`)"
      - "traefik.http.routers.backend-dev.entrypoints=https"
      - "traefik.http.routers.backend-dev.tls=true"
      - "traefik.http.routers.backend-dev.tls.certresolver=letsencrypt"
      - "traefik.http.services.backend-dev.loadbalancer.server.port=8000"

  control_deck:
    container_name: dev-control-deck
    build:
      args:
        NEXT_PUBLIC_BRAIN_API_BASE: https://api.dev.brain.falklabs.de
    environment:
      - NEXT_PUBLIC_BRAIN_API_BASE=https://api.dev.brain.falklabs.de
    networks:
      - brain_internal
      - mw0ck04s8go048c0g4so48cc
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.control-deck-dev.rule=Host(`dev.brain.falklabs.de`)"
      - "traefik.http.routers.control-deck-dev.entrypoints=https"
      - "traefik.http.routers.control-deck-dev.tls=true"
      - "traefik.http.routers.control-deck-dev.tls.certresolver=letsencrypt"
      - "traefik.http.services.control-deck-dev.loadbalancer.server.port=3000"

  axe_ui:
    container_name: dev-axe-ui
    build:
      args:
        NEXT_PUBLIC_BRAIN_API_BASE: https://api.dev.brain.falklabs.de
    environment:
      - NEXT_PUBLIC_BRAIN_API_BASE=https://api.dev.brain.falklabs.de
    networks:
      - brain_internal
      - mw0ck04s8go048c0g4so48cc
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.axe-ui-dev.rule=Host(`axe.dev.brain.falklabs.de`)"
      - "traefik.http.routers.axe-ui-dev.entrypoints=https"
      - "traefik.http.routers.axe-ui-dev.tls=true"
      - "traefik.http.routers.axe-ui-dev.tls.certresolver=letsencrypt"
      - "traefik.http.services.axe-ui-dev.loadbalancer.server.port=3000"
```

---

### **docker-compose.stage.yml (STAGE Overrides)**

Gleiche Struktur wie DEV, aber mit `stage.*` Domains.

---

### **docker-compose.prod.yml (PROD Overrides)**

Gleiche Struktur wie DEV, aber mit Production Domains (`brain.falklabs.de`, `api.brain.falklabs.de`, etc.).

---

## 🚀 COOLIFY KONFIGURATION

### **Option A: Via Coolify UI (Manuell)**

Für jede Application:
1. Settings → Domains
2. Neue Domain eintragen (z.B. `api.dev.brain.falklabs.de`)
3. SSL-Zertifikat wird automatisch von Coolify/Traefik generiert

---

### **Option B: Via Coolify API (Automatisiert - EMPFOHLEN)**

**Beispiel:**
```python
from coolify_manager import CoolifyManager

manager = CoolifyManager(token="YOUR_TOKEN")

# Update Backend DEV Domain
manager.update_domains(
    uuid="backend-dev-uuid",
    domains=["api.dev.brain.falklabs.de"]
)

# Update Control Deck DEV Domain
manager.update_domains(
    uuid="control-deck-dev-uuid",
    domains=["dev.brain.falklabs.de"]
)

# Update ENV Variables
manager.update_env(
    uuid="control-deck-dev-uuid",
    key="NEXT_PUBLIC_BRAIN_API_BASE",
    value="https://api.dev.brain.falklabs.de"
)
```

**Hinweis:** UUIDs müssen aus Coolify abgefragt werden (siehe Migration Script).

---

## 📊 VERGLEICH: VORHER vs. NACHHER

### **VORHER (IST-Zustand)**

| Umgebung | Backend | Control Deck | AXE UI |
|----------|---------|--------------|--------|
| **DEV** | `dev.brain.falklabs.de/api/*` | `dev.brain.falklabs.de` | `axe.dev.brain.falklabs.de` |
| **STAGE** | ❓ | ❓ | ❓ |
| **PROD** | ❓ | `brain.falklabs.de` (vermutlich) | ❓ |

**Probleme:**
- ❌ Backend und Control Deck teilen sich Domain
- ❌ Routing via Traefik Priority (fragil)
- ❌ Inkonsistent mit AXE UI
- ❌ CORS zu permissiv

---

### **NACHHER (SOLL-Zustand)**

| Umgebung | Backend | Control Deck | AXE UI |
|----------|---------|--------------|--------|
| **DEV** | `api.dev.brain.falklabs.de` | `dev.brain.falklabs.de` | `axe.dev.brain.falklabs.de` |
| **STAGE** | `api.stage.brain.falklabs.de` | `stage.brain.falklabs.de` | `axe.stage.brain.falklabs.de` |
| **PROD** | `api.brain.falklabs.de` | `brain.falklabs.de` | `axe.brain.falklabs.de` |

**Vorteile:**
- ✅ Saubere Trennung aller Services
- ✅ Keine Traefik Priority-Hacks nötig
- ✅ Konsistente Struktur über alle Umgebungen
- ✅ Spezifische CORS-Konfiguration
- ✅ Einfach zu debuggen
- ✅ Erweiterbar (z.B. `admin.brain.falklabs.de`)

---

## ✅ VORTEILE DIESER ARCHITEKTUR

1. **Klare Trennung** - Jeder Service hat eigene Subdomain
2. **Skalierbarkeit** - Einfach neue Services hinzufügen
3. **Security** - Spezifische CORS-Regeln pro Service
4. **Debugging** - Keine verwirrenden Priority-Rules
5. **Konsistenz** - Gleiche Struktur für dev/stage/prod
6. **SSL-Zertifikate** - Automatisch via Let's Encrypt
7. **Dokumentation** - Selbsterklärende URLs
8. **Monitoring** - Traefik Dashboard zeigt klare Routing-Regeln

---

## 🔄 MIGRATIONSSTRATEGIE

1. **Phase 1: DEV migrieren**
   - Niedrigstes Risiko
   - Testen der neuen Struktur
   - Rollback möglich ohne Produktionsauswirkung

2. **Phase 2: STAGE migrieren**
   - Pre-Production Test
   - Finale Validierung

3. **Phase 3: PROD migrieren**
   - Nach erfolgreichen DEV + STAGE Tests
   - Mit Rollback-Plan
   - Außerhalb der Hauptnutzungszeiten

---

**Erstellt von:** Claude Code
**Status:** Bereit für Implementation
**Nächster Schritt:** Migration Scripts erstellen
