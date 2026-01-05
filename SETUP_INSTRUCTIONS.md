# 🚀 BRAiN Workspace Setup - Quick Guide

**Basierend auf Server-Analyse vom 2026-01-05**

---

## ⚡ Quick Start

### Auf dem Server ausführen:

```bash
ssh root@brain.falklabs.de
cd /root

# Setup-Script ausführen
bash setup-brain-workspace.sh
```

**Fertig!** 🎉

---

## 📋 Was das Script macht:

### ✅ Phase 1: Workspace Setup
```bash
# Git-Repo clonen (HTTPS, kein SSH nötig)
/root/BRAiN/ → Branch: v2
```

### ✅ Phase 2: Backups
```bash
/root/backups/openwebui/
├── .env
└── docker-compose.yml
```

### ✅ Phase 3: Cleanup
```bash
/opt/containerd/ → Gelöscht (2 leere Verzeichnisse)
```

---

## 🎯 Danach:

### Development Workflow:

```bash
# Code editieren
cd /root/BRAiN
git checkout -b feature/my-feature
nano frontend/control_deck/app/page.tsx
git commit -m "feat: Update dashboard"
git push origin feature/my-feature
```

### Services checken:

```bash
# Container Status
docker ps

# Logs anschauen
cd /srv/dev
docker compose logs -f backend
```

---

## 📁 Finale Struktur:

```
/root/BRAiN/          → Development Workspace (git, code editing)
├── .git/
├── backend/
├── frontend/
├── docker-compose.yml
└── CLAUDE.md (v0.6.1)

/srv/dev/             → Running Deployment (Docker)
├── 8 Container running
├── Port 8001 (backend)
├── Port 3001 (control_deck)
└── Port 3002 (axe_ui)

/srv/main/            → Future main branch
/srv/stage/           → Staging
/srv/prod/            → Production

/root/backups/        → Backups
└── openwebui/
    ├── .env
    └── docker-compose.yml
```

---

## ✅ Erfolgskriterien:

Nach dem Setup sollte Folgendes funktionieren:

```bash
# 1. Git-Repo existiert
cd /root/BRAiN && git status

# 2. Branch v2
git branch

# 3. Backups existieren
ls -lh /root/backups/openwebui/

# 4. Cleanup erfolgreich
ls /opt/containerd/  # Should show: No such file or directory

# 5. Services laufen noch
docker ps | grep dev-
```

---

## 🔧 Troubleshooting:

### Problem: Git clone schlägt fehl

**Lösung:**
```bash
# Internet-Verbindung testen
ping github.com

# HTTPS-Zugriff testen
curl -I https://github.com
```

### Problem: Services laufen nicht mehr

**Lösung:**
```bash
cd /srv/dev
docker compose ps
docker compose logs
```

### Problem: Disk voll

**Lösung:**
```bash
# Space checken
df -h /

# Alte Docker Images löschen
docker system prune -a
```

---

## 🎯 Nächste Schritte:

1. ✅ Setup ausführen
2. ✅ Workspace testen (`cd /root/BRAiN && git status`)
3. ✅ CLAUDE.md v0.6.1 lesen
4. 🚀 Frontend-Entwicklung starten (control_deck)

---

**Let's code!** 💻
