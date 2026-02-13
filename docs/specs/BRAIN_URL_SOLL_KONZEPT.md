# BRAiN URL-SOLL-Konzept

**Version:** 2.0
**Letzte Aktualisierung:** 2026-01-14
**Status:** ✅ In Umsetzung

---

## 🎯 Zielsetzung

Saubere Trennung aller BRAiN-Services über **Subdomains** mit konsistenter Struktur über alle Environments (Development, Staging, Production).

**Prinzipien:**
- ✅ Ein Service = Eine Subdomain
- ✅ Keine Port-Exposition (außer intern)
- ✅ Automatisches SSL/TLS via Let's Encrypt
- ✅ Traefik-basiertes Routing via Coolify
- ✅ Environment-spezifische Konfiguration via Docker Compose Overrides

---

## 🌐 URL-Struktur pro Environment

### **Development** (`dev.brain.falklabs.de`)

| Service | Subdomain | Interner Port | Zweck |
|---------|-----------|---------------|-------|
| **BRAiN UI** | `dev.brain.falklabs.de` | 3000 | Haupt-UI für Endnutzer (Chat/Avatar/Canvas) |
| **Control Deck** | `control.dev.brain.falklabs.de` | 3000 | Admin/Monitoring Dashboard (14 Seiten) |
| **AXE UI** | `axe.dev.brain.falklabs.de` | 3000 | Auxiliary Execution Widget |
| **Backend API** | `api.dev.brain.falklabs.de` | 8000 | FastAPI Backend (REST API) |
| **API Docs** | `docs.dev.brain.falklabs.de` | - | Nginx-Proxy → `/docs` (Swagger UI) |

**DNS-Konfiguration (Hetzner):**
```
dev.brain.falklabs.de          A    46.224.37.114
control.dev.brain.falklabs.de  A    46.224.37.114
axe.dev.brain.falklabs.de      A    46.224.37.114
api.dev.brain.falklabs.de      A    46.224.37.114
docs.dev.brain.falklabs.de     A    46.224.37.114
```

---

### **Staging** (`stage.brain.falklabs.de`)

| Service | Subdomain | Interner Port | Zweck |
|---------|-----------|---------------|-------|
| **BRAiN UI** | `stage.brain.falklabs.de` | 3000 | Staging Haupt-UI |
| **Control Deck** | `control.stage.brain.falklabs.de` | 3000 | Staging Admin Dashboard |
| **AXE UI** | `axe.stage.brain.falklabs.de` | 3000 | Staging AXE Widget |
| **Backend API** | `api.stage.brain.falklabs.de` | 8000 | Staging API |
| **API Docs** | `docs.stage.brain.falklabs.de` | - | Nginx-Proxy → `/docs` |

---

### **Production** (`brain.falklabs.de`)

| Service | Subdomain | Interner Port | Zweck |
|---------|-----------|---------------|-------|
| **BRAiN UI** | `brain.falklabs.de` | 3000 | Production Haupt-UI |
| **Control Deck** | `control.brain.falklabs.de` | 3000 | Production Admin Dashboard |
| **AXE UI** | `axe.brain.falklabs.de` | 3000 | Production AXE Widget |
| **Backend API** | `api.brain.falklabs.de` | 8000 | Production API |
| **API Docs** | `docs.brain.falklabs.de` | - | Nginx-Proxy → `/docs` |

---

## 📱 Frontend-Applikationen

### **1. BRAiN UI** (`frontend/brain_ui/`)

**Zweck:** Immersive User Interface für Endnutzer

**Features:**
- 🗣️ Conversational Interface (Chat, später Voice/Video)
- 🎭 Avatar/Circle-Präsenz mit emotionalen Zuständen
- 📋 Kontext-Canvas für Dokumente, Tools, Inspector
- 🎨 Emotional Colors, Movement, Graphics/Audio

**URL:**
- Dev: `https://dev.brain.falklabs.de`
- Staging: `https://stage.brain.falklabs.de`
- Prod: `https://brain.falklabs.de`

**Technologie:** Next.js 14 (App Router), Zustand, TailwindCSS

---

### **2. Control Deck** (`frontend/control_deck/`)

**Zweck:** System-Administration & Monitoring (Operator Interface)

**Features:**
- 📊 Dashboard mit System-Metriken
- 🤖 Agent Management (14 Dashboard-Seiten)
- 📋 Mission Control & Queue Management
- 🛡️ Immune System Monitoring
- ⚙️ System Settings & Configuration
- 🎓 Course Factory (Kurs-Erstellung)

**URL:**
- Dev: `https://control.dev.brain.falklabs.de`
- Staging: `https://control.stage.brain.falklabs.de`
- Prod: `https://control.brain.falklabs.de`

**Technologie:** Next.js 14 (App Router), React Query, shadcn/ui

**Zielgruppe:** BRAiN Admins & Developers

---

### **3. AXE UI** (`frontend/axe_ui/`)

**Zweck:** Auxiliary Execution Engine Interface (Floating Widget)

**Features:**
- 🎯 Embedding in externe Projekte möglich
- 💬 Schnell-Zugriff auf AXE-Funktionen
- 🔌 Widget-Architektur

**URL:**
- Dev: `https://axe.dev.brain.falklabs.de`
- Staging: `https://axe.stage.brain.falklabs.de`
- Prod: `https://axe.brain.falklabs.de`

**Technologie:** Next.js 14 (App Router)

---

## 🔧 Technische Implementierung

### **1. Docker Compose** (`docker-compose.yml`)

Alle Services haben `expose:` Ports für Traefik-Discovery:

```yaml
services:
  backend:
    build:
      context: ./backend
    expose:
      - "8000"  # Required for Traefik to discover backend port
    networks:
      - brain_internal
      - mw0ck04s8go048c0g4so48cc  # Coolify Traefik network

  control_deck:
    build:
      context: ./frontend/control_deck
    expose:
      - "3000"  # Required for Traefik to discover frontend port
    environment:
      - NEXT_PUBLIC_BRAIN_API_BASE=http://backend:8000
    networks:
      - brain_internal
      - mw0ck04s8go048c0g4so48cc

  axe_ui:
    build:
      context: ./frontend/axe_ui
    expose:
      - "3000"
    environment:
      - NEXT_PUBLIC_BRAIN_API_BASE=http://backend:8000
    networks:
      - brain_internal
      - mw0ck04s8go048c0g4so48cc

  brain_ui:
    build:
      context: ./frontend/brain_ui
    expose:
      - "3000"
    environment:
      - NEXT_PUBLIC_BRAIN_API_BASE=http://backend:8000
    networks:
      - brain_internal
      - mw0ck04s8go048c0g4so48cc

networks:
  brain_internal:
    driver: bridge
  mw0ck04s8go048c0g4so48cc:
    external: true  # Coolify Traefik network
```

**Wichtig:**
- ❌ **KEINE** manuellen Traefik-Labels im Compose-File
- ✅ Coolify injiziert Labels automatisch basierend auf Domain-Konfiguration
- ✅ `expose:` reicht für Port-Discovery

---

### **2. Coolify Domain-Konfiguration**

**Pro Service in Coolify UI konfigurieren:**

**Backend:**
```
Domain: api.dev.brain.falklabs.de
Port: 8000
Generate Certificate: ✅ Let's Encrypt
```

**Control Deck:**
```
Domain: control.dev.brain.falklabs.de
Port: 3000
Generate Certificate: ✅ Let's Encrypt
```

**AXE UI:**
```
Domain: axe.dev.brain.falklabs.de
Port: 3000
Generate Certificate: ✅ Let's Encrypt
```

**BRAiN UI:**
```
Domain: dev.brain.falklabs.de
Port: 3000
Generate Certificate: ✅ Let's Encrypt
```

---

### **3. Environment Variables**

**Alle Frontend-Services:**

```bash
# Development
NEXT_PUBLIC_BRAIN_API_BASE=https://api.dev.brain.falklabs.de

# Staging
NEXT_PUBLIC_BRAIN_API_BASE=https://api.stage.brain.falklabs.de

# Production
NEXT_PUBLIC_BRAIN_API_BASE=https://api.brain.falklabs.de
```

**Backend (CORS):**

```bash
# Development
CORS_ORIGINS=["https://dev.brain.falklabs.de","https://control.dev.brain.falklabs.de","https://axe.dev.brain.falklabs.de","https://api.dev.brain.falklabs.de"]

# Staging
CORS_ORIGINS=["https://stage.brain.falklabs.de","https://control.stage.brain.falklabs.de","https://axe.stage.brain.falklabs.de","https://api.stage.brain.falklabs.de"]

# Production
CORS_ORIGINS=["https://brain.falklabs.de","https://control.brain.falklabs.de","https://axe.brain.falklabs.de","https://api.brain.falklabs.de"]
```

---

### **4. Nginx-Proxy für API Docs** (Optional)

Für `docs.dev.brain.falklabs.de` → `/docs` Weiterleitung:

**Nginx-Konfiguration** (`/etc/nginx/sites-available/brain-docs`):

```nginx
server {
    listen 80;
    server_name docs.dev.brain.falklabs.de;

    # Let's Encrypt Challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name docs.dev.brain.falklabs.de;

    # SSL Certificates
    ssl_certificate /etc/letsencrypt/live/docs.dev.brain.falklabs.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/docs.dev.brain.falklabs.de/privkey.pem;

    # Redirect to API Docs
    location / {
        return 301 https://api.dev.brain.falklabs.de/docs$request_uri;
    }
}
```

**Aktivieren:**
```bash
sudo ln -s /etc/nginx/sites-available/brain-docs /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d docs.dev.brain.falklabs.de
```

---

## 🚀 Deployment-Prozess

### **1. Code-Änderungen**

```bash
# Lokale Entwicklung
cd /home/user/BRAiN
git checkout -b feature/mein-feature
# ... Code-Änderungen ...
git add .
git commit -m "feat: Beschreibung"
git push -u origin feature/mein-feature
```

### **2. Pull Request & Merge**

```bash
# GitHub UI: Pull Request erstellen
# Merge zu v2 Branch
```

### **3. Coolify Deployment**

**Automatisch:**
- Coolify überwacht `v2` Branch
- Auto-Deploy bei Push (falls aktiviert)

**Manuell:**
- Coolify UI → BRAiN Project → Service auswählen
- "Deploy" Button klicken
- Logs beobachten

### **4. Verifizierung**

```bash
# Health Checks
curl https://api.dev.brain.falklabs.de/api/health
curl https://dev.brain.falklabs.de
curl https://control.dev.brain.falklabs.de
curl https://axe.dev.brain.falklabs.de

# SSL Check
curl -I https://api.dev.brain.falklabs.de | grep -i ssl

# Traefik Logs
docker logs coolify-proxy | grep -i brain
```

---

## 📋 Checkliste: Neuer Service hinzufügen

- [ ] Service in `docker-compose.yml` definieren mit `expose:` Port
- [ ] DNS A-Record in Hetzner erstellen
- [ ] Service in Coolify hinzufügen
- [ ] Domain in Coolify konfigurieren
- [ ] Environment-Variablen setzen
- [ ] SSL-Zertifikat generieren lassen
- [ ] Deploy ausführen
- [ ] Health Check testen
- [ ] CORS-Origins im Backend aktualisieren (falls Frontend)

---

## 🔐 Sicherheit

**SSL/TLS:**
- ✅ Automatisch via Let's Encrypt (Traefik)
- ✅ HTTP → HTTPS Redirect
- ✅ HSTS Headers

**CORS:**
- ✅ Explizite Origin-Whitelist
- ❌ KEINE Wildcards (`*`)

**Secrets:**
- ✅ Environment-Variablen in Coolify
- ❌ KEINE Secrets in docker-compose.yml committen

---

## 🗂️ Projekt-Struktur

```
BRAiN/
├── backend/                    # FastAPI Backend
│   ├── main.py                # Entry point
│   └── api/routes/            # API Endpoints
│
├── frontend/
│   ├── brain_ui/              # 🎭 Endnutzer-UI (Chat/Avatar)
│   ├── control_deck/          # 📊 Admin Dashboard (14 Seiten)
│   └── axe_ui/                # 🔌 AXE Widget
│
├── docker-compose.yml         # Base configuration
├── docker-compose.dev.yml     # Development overrides
├── docker-compose.stage.yml   # Staging overrides
├── docker-compose.prod.yml    # Production overrides
│
└── BRAIN_URL_SOLL_KONZEPT.md  # Dieses Dokument
```

---

## 📊 Status: Development Environment

| Service | URL | Status | SSL | Traefik |
|---------|-----|--------|-----|---------|
| Backend API | `api.dev.brain.falklabs.de` | ✅ Deployed | ✅ | ✅ |
| AXE UI | `axe.dev.brain.falklabs.de` | ✅ Deployed | ✅ | ✅ |
| Control Deck | `control.dev.brain.falklabs.de` | ⏳ Pending | - | - |
| BRAiN UI | `dev.brain.falklabs.de` | ⏳ Not Deployed | - | - |
| API Docs | `docs.dev.brain.falklabs.de` | ⏳ Not Configured | - | - |

**Letzte Aktualisierung:** 2026-01-14 14:30 UTC

---

## 🛠️ Troubleshooting

### Gateway Timeout

**Ursache:** Fehlendes `expose:` Port-Statement in docker-compose.yml

**Lösung:**
```yaml
services:
  my_service:
    expose:
      - "3000"  # Port hinzufügen
```

### 404 Not Found

**Ursache:** Falsche Domain-Konfiguration in Coolify oder fehlende Traefik-Labels

**Lösung:**
1. Coolify: Domain-Settings prüfen
2. Container inspizieren: `docker inspect <container> | grep traefik`
3. Traefik-Logs checken: `docker logs coolify-proxy`

### SSL Certificate Error

**Ursache:** Let's Encrypt Rate Limit oder DNS nicht propagiert

**Lösung:**
1. DNS propagieren lassen (5-60 Min warten)
2. Coolify: "Regenerate Certificate" ausführen
3. Certbot Logs checken: `journalctl -u certbot`

---

## 🔮 Zukunftsplanung

**Phase 1: Development Environment** (✅ In Umsetzung)
- ✅ Backend API deployed
- ✅ AXE UI deployed
- ⏳ Control Deck deployment
- ⏳ BRAiN UI deployment
- ⏳ Nginx-Proxy für API Docs

**Phase 2: Staging Environment**
- ⏳ Eigener Server (TBD)
- ⏳ Identische Subdomain-Struktur
- ⏳ CI/CD Pipeline (GitHub Actions)

**Phase 3: Production Environment**
- ⏳ Eigener Server (TBD)
- ⏳ Load Balancing (optional)
- ⏳ Monitoring (Prometheus/Grafana)
- ⏳ Backup-Strategie

---

**Version History:**
- **v2.0** (2026-01-14): Überarbeitung mit aktueller Frontend-Struktur, Coolify-Integration
- **v1.0** (2025-12-XX): Initial SOLL-Konzept

**Maintainer:** BRAiN DevOps Team
**Kontakt:** admin@falklabs.de
