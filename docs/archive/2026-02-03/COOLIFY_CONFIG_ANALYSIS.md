# 🔍 COOLIFY KONFIGURATION - ANALYSE

**Datum:** 2026-01-09
**Analyst:** Claude Code
**Problem:** Traefik Router Rule Parsing Errors

---

## 📊 IST-ZUSTAND

### Traefik Log Errors (aus Original-Prompt)

```
error while parsing rule Host(``) && PathPrefix(`dev.brain.falklabs.de`)
empty args for matcher Host, []
```

**Betroffene Services:**
1. **backend** (Container: `mw0ck04s8go048c0g4so48cc-backend`)
2. **control_deck** (Container: `mw0ck04s8go048c0g4so48cc-control_deck`)
3. **axe_ui** (Container: `mw0ck04s8go048c0g4so48cc-axe_ui`)

**Fehlerhafte Syntax:**
- `Host(``)` - Leerer Host Matcher
- `&& PathPrefix(`dev.brain.falklabs.de`)` - Domain steht fälschlicherweise im PathPrefix

**Korrekte Syntax sollte sein:**
- `Host(`dev.brain.falklabs.de`)`

---

## ✅ DOCKER COMPOSE KONFIGURATION (Repository)

**Datei:** `/home/user/BRAiN/docker-compose.yml`

### Backend Labels (Zeilen 17-24)
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.backend.rule=Host(`dev.brain.falklabs.de`) && (PathPrefix(`/api`) || PathPrefix(`/docs`) || PathPrefix(`/redoc`) || Path(`/openapi.json`))"
  - "traefik.http.routers.backend.entrypoints=https"
  - "traefik.http.routers.backend.tls=true"
  - "traefik.http.routers.backend.tls.certresolver=letsencrypt"
  - "traefik.http.routers.backend.priority=10"
  - "traefik.http.services.backend.loadbalancer.server.port=8000"
```

**✅ Status:** KORREKT - Syntax ist valide!

### Control Deck Labels (Zeilen 40-47)
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.control_deck.rule=Host(`dev.brain.falklabs.de`)"
  - "traefik.http.routers.control_deck.entrypoints=https"
  - "traefik.http.routers.control_deck.tls=true"
  - "traefik.http.routers.control_deck.tls.certresolver=letsencrypt"
  - "traefik.http.services.control_deck.loadbalancer.server.port=3000"
  - "traefik.http.routers.control_deck.priority=1"
```

**✅ Status:** KORREKT - Syntax ist valide!

### AXE UI Labels (Zeilen 63-69)
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.axe_ui.rule=Host(`axe.dev.brain.falklabs.de`)"
  - "traefik.http.routers.axe_ui.entrypoints=https"
  - "traefik.http.routers.axe_ui.tls=true"
  - "traefik.http.routers.axe_ui.tls.certresolver=letsencrypt"
  - "traefik.http.services.axe_ui.loadbalancer.server.port=3000"
```

**✅ Status:** KORREKT - Syntax ist valide!

---

## 🔴 ROOT CAUSE IDENTIFIZIERT

### Problem: Coolify überschreibt Docker Compose Labels

**Beweis:**
1. **Container Names:** `mw0ck04s8go048c0g4so48cc-*` zeigt Coolify-Deployment
2. **External Network:** `mw0ck04s8go048c0g4so48cc` ist von Coolify erstellt
3. **Traefik Errors:** Zeigen falsche Syntax, die NICHT aus docker-compose.yml kommt

**Schlussfolgerung:**
- Services werden via Coolify UI deployed
- Coolify **generiert eigene Traefik Labels** basierend auf UI-Konfiguration
- Diese Labels **überschreiben** die korrekten Labels aus docker-compose.yml
- Die fehlerhafte Syntax `Host(``) && PathPrefix(`domain`)` ist ein **Coolify UI Configuration Bug**

---

## 🗺️ DOMAIN MAPPING (Soll-Zustand)

### Development Environment
| Service | Domain | Port | Router Priority |
|---------|--------|------|----------------|
| **Backend** | `dev.brain.falklabs.de` | 8000 | 10 (high) |
| | Path: `/api/*` | | |
| | Path: `/docs`, `/redoc` | | |
| **Control Deck** | `dev.brain.falklabs.de` | 3000 | 1 (low) |
| | Path: `/*` (catch-all) | | |
| **AXE UI** | `axe.dev.brain.falklabs.de` | 3000 | (default) |
| | Path: `/*` | | |

**Routing Logic:**
1. `axe.dev.brain.falklabs.de` → AXE UI (separate subdomain)
2. `dev.brain.falklabs.de/api/*` → Backend (high priority)
3. `dev.brain.falklabs.de/*` → Control Deck (low priority, catch-all)

---

## 🔧 COOLIFY SERVICE DISCOVERY

### Verfügbare Tools
- **Script:** `/home/user/BRAiN/coolify_manager.py`
- **API URL:** `https://coolify.falklabs.de/api/v1`
- **Token:** ❌ Nicht verfügbar in aktueller Umgebung

### Coolify Manager Capabilities
```python
# Funktionen in coolify_manager.py:
- list_applications()           # Liste aller Apps
- get_application(uuid)         # App-Details abrufen
- update_domains(uuid, domains) # Domains korrigieren (!)
- restart_application(uuid)     # App neu starten
- find_brain_apps()            # Alle BRAIN-Apps finden
- export_current_state()       # Backup erstellen
```

**Key Method für Fix:**
```python
manager.update_domains(uuid, ["dev.brain.falklabs.de"])
```

---

## 🎯 IDENTIFIZIERTE FEHLERQUELLEN

### Coolify UI Domain Configuration (Vermutung)

**Wahrscheinliches Szenario in Coolify UI:**

**❌ FALSCH konfiguriert (aktuell):**
```
Service: backend
Domain Field: [leer] oder falsch gesetzt
Path Prefix: dev.brain.falklabs.de
```
→ Resultat: `Host(``) && PathPrefix(`dev.brain.falklabs.de`)`

**✅ RICHTIG wäre:**
```
Service: backend
Domain: dev.brain.falklabs.de
Path: /api,/docs,/redoc
```
→ Resultat: `Host(`dev.brain.falklabs.de`) && (PathPrefix(`/api`) || ...)`

---

## 📋 NÄCHSTE SCHRITTE

### Option A: Coolify UI Fix (EMPFOHLEN) ⭐

**Voraussetzungen:**
- Zugang zu Coolify UI: `https://coolify.falklabs.de`
- Admin-Berechtigung für BRAIN-Services

**Schritte:**
1. Login zu Coolify UI
2. Service "backend" öffnen
3. **Domains Tab:**
   - Löschen: Falsche Domain-Einträge
   - Setzen: `dev.brain.falklabs.de`
   - Path Prefixes: `/api`, `/docs`, `/redoc`
4. **Save & Redeploy**
5. Wiederholen für `control_deck` und `axe_ui`
6. Warten 30s → Check Traefik Logs

**Erwartetes Ergebnis:**
- Traefik Logs zeigen keine `empty args for matcher Host` Errors mehr
- SSL Certificates werden für alle Domains ausgestellt

---

### Option B: Coolify API Fix (wenn UI nicht verfügbar)

**Voraussetzungen:**
- COOLIFY_TOKEN (API Token aus Coolify UI → Settings → API)

**Schritte:**
```bash
# 1. Export aktuellen Zustand (Backup!)
export COOLIFY_TOKEN="your_token_here"
python3 coolify_manager.py export --output brain_backup_before_fix.json

# 2. Liste BRAIN Apps
python3 coolify_manager.py list > brain_apps.json

# 3. UUIDs identifizieren
cat brain_apps.json | jq '.dev'

# 4. Domains korrigieren (manuelle Python-Session)
python3
>>> from coolify_manager import CoolifyManager
>>> manager = CoolifyManager()
>>> apps = manager.find_brain_apps()
>>> backend_uuid = apps['dev']['backend']['uuid']
>>> manager.update_domains(backend_uuid, ["dev.brain.falklabs.de"])
>>> manager.restart_application(backend_uuid)
```

**Erwartetes Ergebnis:**
- Coolify generiert neue, korrekte Traefik Labels
- Services werden mit fixen Labels neu gestartet

---

### Option C: Direct Docker Labels Override (NICHT EMPFOHLEN)

**⚠️ Warnung:** Wird von Coolify beim nächsten Deploy überschrieben!

**Nur nutzen wenn:**
- Coolify UI und API nicht verfügbar
- Sofortiger Hotfix benötigt

**Schritte:** Siehe `DOCKER_LABELS_FIX.sh` (wird bei Bedarf erstellt)

---

## 📊 CONTAINER/SERVICE MAPPING

### Aktuell Deployed (Coolify)
```
Container ID Pattern: mw0ck04s8go048c0g4so48cc-*
Network: mw0ck04s8go048c0g4so48cc (external, von Coolify erstellt)

Services:
├── mw0ck04s8go048c0g4so48cc-backend
│   ├── Image: aus ./backend/Dockerfile gebaut
│   ├── Port: 8000 (intern)
│   └── Domain: dev.brain.falklabs.de (FALSCH konfiguriert)
│
├── mw0ck04s8go048c0g4so48cc-control_deck
│   ├── Image: aus ./frontend/control_deck/Dockerfile gebaut
│   ├── Port: 3000 (intern)
│   └── Domain: dev.brain.falklabs.de (FALSCH konfiguriert)
│
└── mw0ck04s8go048c0g4so48cc-axe_ui
    ├── Image: aus ./frontend/axe_ui/Dockerfile gebaut
    ├── Port: 3000 (intern)
    └── Domain: axe.dev.brain.falklabs.de (FALSCH konfiguriert)
```

---

## ✅ VALIDATION CHECKLIST

Nach Fix-Implementierung:

- [ ] **Traefik Logs:** Keine `empty args for matcher Host` Errors
- [ ] **SSL Certificates:** Let's Encrypt Certs für alle 3 Domains
- [ ] **HTTP Status:**
  - [ ] `https://dev.brain.falklabs.de/health` → 200 OK
  - [ ] `https://dev.brain.falklabs.de/api/health` → 200 OK
  - [ ] `https://dev.brain.falklabs.de/` → 200 OK (Control Deck)
  - [ ] `https://axe.dev.brain.falklabs.de/` → 200 OK
- [ ] **Docker Container Status:** Alle 3 Services `healthy`
- [ ] **Coolify UI:** Domains korrekt angezeigt

---

## 🚨 STOP CONDITIONS

**STOP und konsultiere User wenn:**
- [ ] Coolify API gibt 401/403 (Auth-Fehler)
- [ ] Services starten nicht nach Domain-Update
- [ ] Neue Traefik-Errors erscheinen
- [ ] SSL Certs nicht nach 5 Min ausgestellt
- [ ] Andere Services (nicht-BRAIN) betroffen

---

## 📝 NOTIZEN

### Warum überschreibt Coolify die Labels?

Coolify ist ein Self-Hosting Platform Manager, ähnlich wie Vercel/Netlify. Es:
1. Liest `docker-compose.yml` als **Template**
2. Generiert eigene Labels basierend auf **UI-Konfiguration**
3. Injiziert diese beim Deployment
4. Managed Traefik Routing zentral

**Das bedeutet:**
- `docker-compose.yml` Labels sind nur **Dokumentation/Fallback**
- **Echte Labels** kommen aus Coolify's Datenbank
- Fix MUSS in Coolify UI/API erfolgen

### Coolify API Endpoints (für Referenz)

```
GET  /api/v1/applications                    # Liste Apps
GET  /api/v1/applications/{uuid}             # App Details
PATCH /api/v1/applications/{uuid}            # Update App
POST /api/v1/applications/{uuid}/restart     # Restart
POST /api/v1/applications/{uuid}/envs        # Set Env Var
```

**Domains Update Payload:**
```json
{
  "domains": "dev.brain.falklabs.de,axe.dev.brain.falklabs.de"
}
```

---

## 🎯 EMPFEHLUNG

**Primäre Strategie:** **Option A - Coolify UI Fix**

**Begründung:**
1. ✅ Nachhaltig (überlebt Redeploys)
2. ✅ Keine API-Token notwendig (UI-Zugang reicht)
3. ✅ Visuelles Feedback
4. ✅ Coolify dokumentiert Änderungen

**Backup-Strategie:** **Option B - Coolify API** (wenn UI nicht verfügbar)

**Nicht empfohlen:** Option C - Direct Docker Override (wird überschrieben)

---

## 📤 NÄCHSTER SCHRITT

**WARTE AUF USER-ENTSCHEIDUNG:**
1. Hat User Zugang zu Coolify UI? → Option A
2. Kann User COOLIFY_TOKEN bereitstellen? → Option B
3. Soll ich Coolify UI Screenshot-Guide erstellen? → Ja/Nein

---

**Ende der Analyse**
