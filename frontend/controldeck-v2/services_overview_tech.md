# BRAiN Services - Technische Übersicht

**Datum:** 2026-02-21  
**Server:** 46.224.37.114 (Hetzner)  
**Coolify:** http://46.224.37.114:8000

---

## 1. AXE UI (brain-axe-ui)

**UUID:** uc08ssg8444kk00ws8s0osss  
**Beschreibung:** BRAiN AXE-UI - Kommunikator & Chat  
**Domain:** https://axe.brain.falklabs.de  
**Port:** 3002  
**Status:** running:unknown

### Konfiguration
- **Build Pack:** Dockerfile
- **Base Directory:** /frontend/axe_ui
- **Git Repository:** satoshiflow/BRAiN
- **Branch:** main
- **Proxy:** TRAEFIK (v3.6.8)
- **SSL:** Let's Encrypt

### Ressourcen
- CPU Shares: 1024
- Memory: 0 (unlimited)
- Restart Count: 0

---

## 2. ControlDeck (brain-controldeck)

**UUID:** msso0o88oc0wskkwwg4cks40  
**Beschreibung:** BRAiN Frontend - Control Deck  
**Domain:** https://control.brain.falklabs.de  
**Port:** 3001  
**Status:** exited:unhealthy ⚠️

### Konfiguration
- **Build Pack:** Dockerfile
- **Base Directory:** /frontend/control_deck
- **Git Repository:** /satoshiflow/BRAiN
- **Branch:** main
- **Proxy:** TRAEFIK (v3.6.8)
- **SSL:** Let's Encrypt

### Problem
- Status: **exited:unhealthy**
- Letztes Online: 2026-02-20 05:19:31
- Aktion: Neu starten oder v2 deployen

### Ressourcen
- CPU Shares: 1024
- Memory: 0 (unlimited)
- Restart Count: 0

---

## 3. Qdrant Vector DB

**UUID:** dgscsswg4g8gksgw40csgw4c  
**Beschreibung:** Qdrant Vector DB  
**Domain:** http://dgscsswg4g8gksgw40csgw4c.46.224.37.114.sslip.io  
**Port:** 80 (intern 6333)  
**Status:** running:unknown

### Konfiguration
- **Build Pack:** Docker Image
- **Image:** qdrant/qdrant:latest
- **Proxy:** TRAEFIK

### Ressourcen
- CPU Shares: 1024
- Memory: 0 (unlimited)
- Restart Count: 0

---

## 4. Ollama Container

**UUID:** xkg0gc00sgcg0sc0g8wowskw  
**Beschreibung:** Ollama Container  
**Domain:** http://xkg0gc00sgcg0sc0g8wowskw.46.224.37.114.sslip.io  
**Port:** 80 (intern 11434)  
**Status:** running:unknown

### Konfiguration
- **Build Pack:** Docker Image
- **Image:** ollama/ollama:latest
- **Proxy:** TRAEFIK

### Ressourcen
- CPU Shares: 1024
- Memory: 0 (unlimited)
- Restart Count: 0

---

## Zusammenfassung aller Services

| Service | Domain | Port | Status | Build Pack |
|---------|--------|------|--------|------------|
| **Identity** (Better Auth) | identity.falklabs.de | 1433 | ✅ running | Docker Compose |
| **BRAiN Backend** | api.brain.falklabs.de | 8000 | ✅ running | Dockerfile |
| **AXE UI** | axe.brain.falklabs.de | 3002 | ✅ running | Dockerfile |
| **ControlDeck** | control.brain.falklabs.de | 3001 | ⚠️ exited | Dockerfile |
| **Qdrant** | sslip.io | 80 | ✅ running | Docker Image |
| **Ollama** | sslip.io | 80 | ✅ running | Docker Image |

---

## Netzwerk Übersicht

| Netzwerk | Services |
|----------|----------|
| **coolify** (Standard) | Alle Services |
| **qcks8kwws80cw0s4sscw00wg** | Identity (Better Auth) |

---

## Offene Punkte

1. **ControlDeck** - Status: exited, muss neu gestartet oder v2 deployt werden
2. **Better Auth** - Node.js Service fehlt noch (nur Datenbanken laufen)
3. **OpenClaw Worker** - Muss noch als Service angelegt werden

---

## Nächste Schritte

1. [ ] ControlDeck neu starten oder v2 deployen
2. [ ] Better Auth Node.js Service hinzufügen
3. [ ] OpenClaw Worker Service anlegen
4. [ ] Alle Services dokumentieren
