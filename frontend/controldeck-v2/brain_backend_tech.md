# BRAiN Backend - Technische Dokumentation

**Service:** brain-backend  
**UUID:** vosss8wcg8cs80kcss8cgccc  
**Status:** Running  
**Letztes Update:** 2026-02-21

---

## Basis Informationen

| Attribut | Wert |
|----------|------|
| **Name** | brain-backend |
| **Beschreibung** | BRAiN KI Agent & Business Ökosystem |
| **Build Pack** | Dockerfile |
| **Base Directory** | /backend |
| **Domain** | https://api.brain.falklabs.de |
| **Port** | 8000 |
| **Status** | running:unknown |

---

## Repository

| Attribut | Wert |
|----------|------|
| **Git Repository** | satoshiflow/BRAiN |
| **Branch** | main |
| **Commit SHA** | HEAD |
| **Source Type** | GitHub App |

---

## Netzwerk & Proxy

| Attribut | Wert |
|----------|------|
| **Destination** | coolify (localhost) |
| **Network** | coolify |
| **Proxy Type** | TRAEFIK |
| **Proxy Status** | running |
| **Traefik Version** | 3.6.8 |

---

## SSL / Traefik Konfiguration

```yaml
# Traefik Labels (Base64 decoded)
traefik.enable: true
traefik.http.middlewares.gzip.compress: true
traefik.http.middlewares.redirect-to-https.redirectscheme.scheme: https
traefik.http.routers.http-0-vosss8wcg8cs80kcss8cgccc.entryPoints: http
traefik.http.routers.http-0-vosss8wcg8cs80kcss8cgccc.middlewares: redirect-to-https
traefik.http.routers.http-0-vosss8wcg8cs80kcss8cgccc.rule: Host(`api.brain.falklabs.de`) && PathPrefix(`/`)
traefik.http.routers.https-0-vosss8wcg8cs80kcss8cgccc.entryPoints: https
traefik.http.routers.https-0-vosss8wcg8cs80kcss8cgccc.middlewares: gzip
traefik.http.routers.https-0-vosss8wcg8cs80kcss8cgccc.rule: Host(`api.brain.falklabs.de`) && PathPrefix(`/`)
traefik.http.routers.https-0-vosss8wcg8cs80kcss8cgccc.tls.certresolver: letsencrypt
traefik.http.routers.https-0-vosss8wcg8cs80kcss8cgccc.tls: true
traefik.http.services.http-0-vosss8wcg8cs80kcss8cgccc.loadbalancer.server.port: 8000
traefik.http.services.https-0-vosss8wcg8cs80kcss8cgccc.loadbalancer.server.port: 8000
```

---

## Ressourcen Limits

| Ressource | Wert |
|-----------|------|
| **CPU Shares** | 1024 |
| **CPUs** | 0 (unlimited) |
| **Memory** | 0 (unlimited) |
| **Memory Reservation** | 0 |
| **Memory Swap** | 0 |
| **Swappiness** | 60 |

---

## Deployment Info

| Attribut | Wert |
|----------|------|
| **Erstellt am** | 2026-02-15T20:25:06.000000Z |
| **Letztes Update** | 2026-02-21T15:17:05.000000Z |
| **Letztes Online** | 2026-02-21 15:17:05 |
| **Restart Count** | 0 |
| **Status** | running:unknown |

---

## Health Check

| Attribut | Wert |
|----------|------|
| **Enabled** | false |
| **Methode** | GET |
| **Pfad** | / |
| **Interval** | 5s |
| **Retries** | 10 |
| **Timeout** | 5s |

---

## Verbundene Services

| Service | Beschreibung |
|---------|--------------|
| PostgreSQL | Datenbank (Port 5432) |
| Redis | Cache & Queue (Port 6379) |
| Qdrant | Vector Database |
| n8n | Workflow Automation |

---

## API Endpoints (Bekannte)

```
GET  /api/missions/info
GET  /api/missions/health
POST /api/missions/enqueue
GET  /api/missions/queue
GET  /api/missions/events/history
GET  /api/missions/events/stats
GET  /api/missions/worker/status
GET  /api/missions/agents/info
GET  /api/events
GET  /api/events/stats
GET  /api/system_stream/*
GET  /api/business/*
GET  /api/axe/*
```

---

## Integration mit Better Auth

**Geplant:**
- Middleware für Token-Validierung
- Endpoints schützen mit Auth
- User-Management über Better Auth

**API URL für Auth:**
```
Better Auth: https://identity.falklabs.de
BRAiN Backend: https://api.brain.falklabs.de
```

---

## Nächste Schritte

- [ ] Health Check aktivieren
- [ ] Better Auth Middleware implementieren
- [ ] API Dokumentation erstellen (Swagger/OpenAPI)
- [ ] Monitoring/Alerts einrichten
