# 🚀 BRAiN Coolify Quick Start - SOFORT HEUTE

**Status:** Bereit für sofortige Ausführung
**Dauer:** ~1 Stunde (inkl. DNS-Propagierung)
**Ziel:** Coolify installiert, dev-Environment läuft

---

## ✅ Voraussetzungen Check

Basierend auf Server-Check vom 2026-01-05:

- ✅ Server: brain.falklabs.de (46.224.37.114)
- ✅ /srv/dev/ läuft bereits (8 Container)
- ✅ Port 9000 frei für Coolify
- ✅ Docker installiert und läuft
- ✅ User 'claude' hat GitHub SSH-Zugriff

---

## 🎯 Plan für HEUTE (3 Phasen)

### Phase 1: DNS Records (5 Minuten + Wartezeit)
**Wo:** do.de Control Panel (vorerst, Hetzner-Migration später diese Woche)

### Phase 2: Coolify Installation (15 Minuten)
**Wo:** Server brain.falklabs.de

### Phase 3: BRAiN Dev-Environment (20 Minuten)
**Wo:** Coolify UI (coolify.falklabs.de:9000)

---

## 📋 PHASE 1: DNS Records erstellen (JETZT)

### Bei do.de Control Panel:

1. **Login:** https://www.do.de/
2. **Domain Management** → falklabs.de → **DNS-Einträge**
3. **Folgende 3 A-Records hinzufügen:**

```
Type  | Name     | Wert            | TTL
------|----------|-----------------|-----
A     | dev      | 46.224.37.114   | 300
A     | stage    | 46.224.37.114   | 300
A     | coolify  | 46.224.37.114   | 300
```

**Hinweis:** `brain` existiert wahrscheinlich schon (prüfen!), die anderen 3 sind neu.

### DNS-Propagierung testen:

```bash
# Lokal auf deinem Windows-PC:
nslookup dev.brain.falklabs.de
nslookup stage.brain.falklabs.de
nslookup coolify.falklabs.de

# Sollte jeweils 46.224.37.114 zurückgeben
```

**Wartezeit:** 5-30 Minuten (do.de ist meist schnell)

---

## ⏸️ WARTEN bis DNS aktiv ist

Während du wartest, lies die beiden Hauptdokumente:

1. **DNS_MIGRATION_PLAN.md** - Für spätere Hetzner-Migration
2. **COOLIFY_DEPLOYMENT_PLAN.md** - Vollständige Coolify-Anleitung

---

## 🚀 PHASE 2: Coolify Installation

**Voraussetzung:** DNS Records aktiv (siehe oben)

### Auf dem Server (als root):

```bash
ssh root@brain.falklabs.de

# 1. Coolify installieren (Port 9000)
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash -s -- --port 9000

# Das Script wird automatisch:
# - Docker/Docker Compose prüfen (bereits installiert ✅)
# - PostgreSQL-Container starten (Coolify-Metadaten)
# - Redis-Container starten (Queue)
# - Traefik/Caddy-Proxy starten
# - Coolify UI auf Port 9000 starten

# 2. Installation verifizieren
docker ps | grep coolify

# Erwartete Container:
# - coolify
# - coolify-db (PostgreSQL)
# - coolify-redis
# - coolify-proxy (Traefik)

# 3. Logs checken
docker logs coolify -f
```

**Dauer:** ~5-10 Minuten (Download + Container-Start)

### Erste Anmeldung:

1. **Browser öffnen:** http://coolify.falklabs.de:9000
   - Falls DNS noch nicht propagiert: http://46.224.37.114:9000

2. **Setup-Wizard:**
   - Admin-Email: (deine Email)
   - Admin-Passwort: (sicheres Passwort generieren)
   - Server-Name: `brain-hetzner-01`
   - Server-IP: `46.224.37.114`

3. **SSL-Zertifikat (später):**
   - Coolify kann automatisch Let's Encrypt für coolify.falklabs.de konfigurieren
   - Wird nach erstem Login angeboten

---

## 🎯 PHASE 3: BRAiN Dev-Environment einrichten

**Voraussetzung:** Coolify UI erreichbar

### In Coolify UI:

#### 1. Neues Projekt erstellen

- **Name:** `BRAiN`
- **Description:** `BRAiN v2.0 - Multi-Environment Deployment`
- **Click:** "Create Project"

#### 2. Server hinzufügen (falls nicht automatisch)

- **Server-Typ:** Localhost
- **Name:** `brain-hetzner-01`
- **IP:** `46.224.37.114`
- **Private Key:** (Coolify generiert automatisch)

#### 3. Erste Resource: BRAiN Dev-Environment

**Klick:** "New Resource" → "Application" → "Public Repository"

**Repository-Einstellungen:**
```
Git Repository: https://github.com/satoshiflow/BRAiN.git
Branch:         dev      # WICHTIG: Du musst v2 → dev umbenennen!
Build Pack:     Docker Compose
```

**Docker Compose Einstellungen:**
```
Compose File:        docker-compose.yml
Additional Files:    docker-compose.dev.yml

Command Override:    docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**Environment-Einstellungen:**
```
Environment Name:    dev
Domain:              dev.brain.falklabs.de
Port Mappings:
  - Backend:         8001 → 8000
  - Control Deck:    3001 → 3000
  - AXE UI:          3002 → 3000
```

**Environment Variables:**
(Aus bestehender .env.dev übernehmen)

```bash
# Auf Server: Aktuelle .env.dev anzeigen
cat /srv/dev/.env.dev

# Werte in Coolify UI kopieren:
ENVIRONMENT=development
DATABASE_URL=postgresql://brain:[password]@postgres:5432/brain_dev
REDIS_URL=redis://redis:6379/0
CORS_ORIGINS=["http://localhost:3001","https://dev.brain.falklabs.de"]
LOG_LEVEL=DEBUG
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:latest
```

**Auto-Deploy:**
```
✅ Enable Auto Deploy on Push
Webhook URL: (Coolify generiert automatisch)
```

#### 4. GitHub Webhook einrichten

**GitHub:**
1. Repository: https://github.com/satoshiflow/BRAiN
2. Settings → Webhooks → "Add webhook"
3. **Payload URL:** (von Coolify kopieren)
4. **Content type:** application/json
5. **Events:** Just the push event
6. **Active:** ✅

#### 5. Erste Deployment starten

**In Coolify UI:**
- **Click:** "Deploy Now"
- **Warten:** Coolify zieht Code, baut Container, startet Services

**Logs beobachten:**
```bash
# Auf Server
docker logs -f coolify

# BRAiN-Container (nach Start)
docker ps | grep brain
docker logs -f [container-name]
```

---

## ✅ Erfolgskriterien

Nach erfolgreicher Installation:

### 1. Coolify UI erreichbar
```bash
curl http://coolify.falklabs.de:9000
# → Sollte Coolify-UI laden
```

### 2. BRAiN Dev-Environment läuft
```bash
curl https://dev.brain.falklabs.de/api/health
# → {"status": "healthy"}

curl https://dev.brain.falklabs.de
# → Control Deck UI lädt
```

### 3. Auto-Deploy funktioniert
```bash
# Test: Push auf dev-Branch
git push origin dev

# Coolify sollte automatisch:
# 1. Webhook erhalten
# 2. Code pullen
# 3. Container neu bauen
# 4. Rolling Update durchführen
# 5. Health Check ausführen
```

---

## 🎯 Nächste Schritte (nach heute)

### Diese Woche:

1. **Hetzner DNS Migration** (siehe DNS_MIGRATION_PLAN.md)
   - Hetzner API Token generieren
   - DNS-Zone erstellen
   - Nameserver umstellen
   - Coolify DNS-Integration aktivieren

2. **Branch-Umbenennung auf GitHub**
   ```bash
   # v2 → dev
   git branch -m v2 dev
   git push origin dev
   git push origin --delete v2

   # stage-Branch erstellen
   git checkout -b stage dev
   git push origin stage
   ```

3. **Stage-Environment in Coolify**
   - Analog zu dev, aber:
   - Branch: `stage`
   - Domain: `stage.brain.falklabs.de`
   - Auto-Deploy: ❌ (manuelles Approval)

4. **Prod-Environment vorbereiten**
   - Branch: `main`
   - Domain: `brain.falklabs.de`
   - Auto-Deploy: ❌ (nur manuelle Deployments)

---

## 🆘 Troubleshooting

### Problem: DNS propagiert nicht

**Lösung:**
```bash
# Temporär mit IP + Port arbeiten:
http://46.224.37.114:9000  # Coolify UI
http://46.224.37.114:8001/api/health  # Backend direkt

# DNS-Check:
dig dev.brain.falklabs.de
nslookup dev.brain.falklabs.de 8.8.8.8
```

### Problem: Coolify-Installation schlägt fehl

**Lösung:**
```bash
# Logs checken
journalctl -u docker -f

# Port 9000 checken
netstat -tuln | grep 9000

# Bereits laufenden dev-backend stoppen (falls Port-Konflikt)
cd /srv/dev
docker compose down backend
```

### Problem: Webhook kommt nicht an

**Lösung:**
```bash
# Firewall-Check
ufw status
ufw allow 9000/tcp

# GitHub Webhook-Logs prüfen:
# GitHub → Settings → Webhooks → Recent Deliveries
```

### Problem: Container bauen nicht

**Lösung:**
```bash
# Manuell testen
cd /srv/dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache

# Disk Space prüfen
df -h
docker system prune -a  # Alte Images löschen
```

---

## 📞 Support

**Coolify Docs:** https://coolify.io/docs
**BRAiN Docs:** COOLIFY_DEPLOYMENT_PLAN.md (vollständige Anleitung)
**DNS Docs:** DNS_MIGRATION_PLAN.md (Hetzner-Migration)

---

## 🎯 Zusammenfassung für HEUTE

**Was du jetzt tun musst:**

1. ✅ **DNS Records bei do.de erstellen** (5 Min)
   - dev.brain.falklabs.de → 46.224.37.114
   - stage.brain.falklabs.de → 46.224.37.114
   - coolify.falklabs.de → 46.224.37.114

2. ⏸️ **Warten** auf DNS-Propagierung (5-30 Min)

3. 🚀 **Coolify installieren** (10 Min)
   ```bash
   curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash -s -- --port 9000
   ```

4. 🎯 **BRAiN Dev-Environment einrichten** (20 Min)
   - Coolify UI öffnen
   - Projekt erstellen
   - GitHub-Repo verknüpfen
   - Webhook einrichten
   - Erste Deployment starten

**Gesamtdauer:** ~1 Stunde (inkl. Wartezeiten)

**Danach hast du:**
- ✅ Coolify läuft auf Port 9000
- ✅ Auto-Deploy für dev-Branch
- ✅ Rollback-Funktion
- ✅ Health Monitoring
- ✅ Zero-Downtime Deployments

**Let's go!** 🚀
