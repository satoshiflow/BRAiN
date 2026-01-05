# 🚀 BRAiN v2 Migration Instructions

**Ziel:** Migration von `/opt/brain-v2/` zu sauberer `/srv/*` Struktur (Option B)

---

## ⚠️ WICHTIG: Vor der Migration

**Diese Anweisungen gelten für den Remote Server:** `brain.falklabs.de` (46.224.37.114)

**Was wird gemacht:**
- ✅ Backup der alten Installation erstellen
- ✅ Alte Container stoppen
- ✅ Symlinks entfernen
- ✅ Saubere `/srv/*` Struktur erstellen
- ✅ Code nach `/srv/dev` deployen
- ✅ Alte Installation löschen

**Was wird NICHT gelöscht:**
- ❌ Docker Volumes (Datenbanken, Models) - bleiben erhalten
- ❌ `/root/BRAiN` Development Workspace - bleibt erhalten

---

## 📋 Schritt-für-Schritt Anleitung

### 1️⃣ Auf Server einloggen

```bash
ssh root@brain.falklabs.de
```

### 2️⃣ Zum Development Workspace wechseln

```bash
cd /root/BRAiN
```

### 3️⃣ Git auf neuesten Stand bringen

```bash
git fetch origin
git checkout claude/update-claude-md-Q9jY6
git pull origin claude/update-claude-md-Q9jY6
```

### 4️⃣ CLAUDE.md Updates überprüfen (Optional)

```bash
# Zeige aktuelle Version
head -20 CLAUDE.md

# Sollte zeigen:
# Version: 0.6.1
# Last Updated: 2026-01-05
```

### 5️⃣ Migration Script überprüfen

```bash
# Script anschauen (Optional)
cat migrate-to-srv-structure.sh

# Script ist ausführbar?
ls -l migrate-to-srv-structure.sh
# Sollte zeigen: -rwxr-xr-x
```

### 6️⃣ Migration durchführen

```bash
# Script ausführen
sudo bash migrate-to-srv-structure.sh
```

**Das Script wird:**
1. Dich nach Bestätigung fragen (mehrfach für Sicherheit)
2. Backup in `/root/backups/` erstellen
3. Alte Container stoppen
4. Symlinks finden und entfernen
5. `/srv/dev/`, `/srv/stage/`, `/srv/prod/` erstellen
6. Code nach `/srv/dev/` kopieren
7. `.env.dev` mit sicheren Passwörtern erstellen
8. Alte Installation `/opt/brain-v2/` löschen

### 7️⃣ Development Environment starten

```bash
# Zu /srv/dev wechseln
cd /srv/dev

# Container starten
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 8️⃣ Status überprüfen

```bash
# Container Status
docker ps

# Sollte zeigen:
# dev-backend
# dev-control-deck
# dev-axe-ui
# dev-postgres
# dev-redis
# dev-qdrant
# dev-ollama
# dev-openwebui

# Logs anschauen
docker compose logs -f backend

# Oder spezifische Services
docker compose logs -f control_deck
docker compose logs -f axe_ui
```

### 9️⃣ Services testen

```bash
# Backend Health Check
curl http://localhost:8001/health

# Sollte zeigen: {"status":"healthy"}

# Control Deck (im Browser oder curl)
curl -I http://localhost:3001

# AXE UI
curl -I http://localhost:3002
```

### 🔟 Docker Volumes überprüfen (Optional)

```bash
# Alle BRAiN Volumes anzeigen
docker volume ls | grep brain

# Wenn alte Volumes existieren und nicht mehr benötigt:
docker volume rm <volume_name>

# ACHTUNG: Nur löschen wenn sicher keine Daten mehr benötigt werden!
```

---

## 🎯 Nach der Migration

### Neue Verzeichnisstruktur:

```
/root/BRAiN/          → Development Workspace (git, code editing)
├── .git/
├── backend/
├── frontend/
├── migrate-to-srv-structure.sh  ← Migration Script
└── CLAUDE.md         → Aktualisiert auf v0.6.1

/srv/dev/             → Development Deployment (Docker Container)
├── backend/
├── frontend/
├── docker-compose.yml
├── docker-compose.dev.yml
└── .env.dev          → Mit sicheren Passwörtern

/srv/stage/           → Staging (Geplant)
/srv/prod/            → Production (Geplant)

/root/backups/        → Backups
└── brain-v2-backup-YYYYMMDD_HHMMSS.tar.gz
```

### Workflow ab jetzt:

**Entwicklung (Code editieren):**
```bash
cd /root/BRAiN
# Git operations, code editing
git pull
nano backend/main.py
git commit -m "..."
git push
```

**Deployment (Services starten):**
```bash
cd /srv/dev
# Docker operations
ENV_FILE=.env.dev docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
docker compose logs -f
```

---

## 🔧 Troubleshooting

### Problem: Script stoppt mit "Old installation not found"

**Lösung:** Das ist OK! Bedeutet `/opt/brain-v2/` existiert nicht. Script macht trotzdem weiter.

### Problem: "Low disk space" Warnung

**Lösung:**
```bash
# Disk space checken
df -h /

# Alte Docker Images löschen
docker system prune -a

# Alte Volumes löschen (NUR wenn sicher!)
docker volume prune
```

### Problem: Port bereits in Verwendung

**Lösung:**
```bash
# Prüfen was Ports nutzt
netstat -tulpn | grep -E ":(8001|3001|3002)"

# Alte Container stoppen
docker stop $(docker ps -aq --filter "name=brain")
docker rm $(docker ps -aq --filter "name=brain")
```

### Problem: Container starten nicht

**Lösung:**
```bash
cd /srv/dev

# Logs checken
docker compose logs backend

# Neu bauen
docker compose build --no-cache
docker compose up -d
```

### Problem: .env.dev fehlt

**Lösung:**
```bash
cd /srv/dev
cp .env.example .env.dev

# Passwörter manuell generieren
echo "POSTGRES_PASSWORD=$(openssl rand -base64 25 | tr -d '=+/')"
echo "JWT_SECRET_KEY=$(openssl rand -base64 64 | tr -d '=+/')"

# In .env.dev eintragen
nano .env.dev
```

---

## 🔄 Rollback (Falls nötig)

Falls etwas schief geht, kannst du das Backup wiederherstellen:

```bash
# Backup finden
ls -lh /root/backups/

# Neue Installation stoppen
cd /srv/dev
docker compose down

# Backup wiederherstellen
cd /opt
tar -xzf /root/backups/brain-v2-backup-YYYYMMDD_HHMMSS.tar.gz

# Alte Installation starten
cd /opt/brain-v2
docker compose up -d
```

---

## ✅ Erfolgskriterien

Migration ist erfolgreich wenn:

- ✅ `/srv/dev/` existiert und enthält alle Files
- ✅ `.env.dev` existiert mit sicheren Passwörtern
- ✅ Container laufen: `docker ps` zeigt 8 Container
- ✅ Backend erreichbar: `curl http://localhost:8001/health`
- ✅ Control Deck erreichbar: `curl -I http://localhost:3001`
- ✅ AXE UI erreichbar: `curl -I http://localhost:3002`
- ✅ `/opt/brain-v2/` ist gelöscht
- ✅ Backup existiert in `/root/backups/`

---

## 📞 Support

Bei Problemen:

1. Logs checken: `docker compose logs -f`
2. CLAUDE.md konsultieren (v0.6.1)
3. Backup wiederherstellen (siehe Rollback)

---

**Viel Erfolg! 🚀**
