# Better Auth Service - Technische Dokumentation

**Service:** Identity (Better Auth)  
**UUID:** qcks8kwws80cw0s4sscw00wg  
**Status:** Running  
**Letztes Update:** 2026-02-21

---

## Basis Informationen

| Attribut | Wert |
|----------|------|
| **Name** | Identity |
| **Beschreibung** | IdP - Identitätsanbieter (betterAuth) |
| **Build Pack** | Docker Compose |
| **Base Directory** | / |
| **Domain** | identity.falklabs.de |
| **Status** | running |

---

## Container Konfiguration

### MSSQL Container (Haupt-Endpoint)

| Attribut | Wert |
|----------|------|
| **Image** | mcr.microsoft.com/mssql/server:latest |
| **Container Name** | mssql-qcks8kwws80cw0s4sscw00wg-142905229216 |
| **Port (Extern)** | 1433:1433 |
| **SA Password** | Password123! |
| **Accept EULA** | Y |

### PostgreSQL Container

| Attribut | Wert |
|----------|------|
| **Image** | postgres:latest |
| **Container Name** | postgres-qcks8kwws80cw0s4sscw00wg-142905206243 |
| **Port (Extern)** | 5432:5432 |
| **User** | user |
| **Password** | password |
| **Database** | better_auth |

### MySQL Container

| Attribut | Wert |
|----------|------|
| **Image** | mysql:latest |
| **Container Name** | mysql-qcks8kwws80cw0s4sscw00wg-142905219576 |
| **Port (Extern)** | 3306:3306 |
| **Root Password** | root_password |
| **User** | user |
| **Password** | password |
| **Database** | better_auth |

### MongoDB Container

| Attribut | Wert |
|----------|------|
| **Image** | mongo:latest |
| **Container Name** | mongodb-qcks8kwws80cw0s4sscw00wg-142905196104 |
| **Port (Extern)** | 27017:27017 |

---

## Netzwerk Konfiguration

| Attribut | Wert |
|----------|------|
| **Netzwerk** | qcks8kwws80cw0s4sscw00wg |
| **Netzwerk Typ** | Extern |
| **Destination** | coolify (localhost) |
| **Server IP** | host.docker.internal |

---

## SSL / Traefik Konfiguration

```yaml
traefik.enable: true
traefik.http.middlewares.gzip.compress: true
traefik.http.middlewares.redirect-to-https.redirectscheme.scheme: https
traefik.http.routers.http-0-qcks8kwws80cw0s4sscw00wg-mssql.entryPoints: http
traefik.http.routers.http-0-qcks8kwws80cw0s4sscw00wg-mssql.middlewares: redirect-to-https
traefik.http.routers.http-0-qcks8kwws80cw0s4sscw00wg-mssql.rule: Host(`identity.falklabs.de`) && PathPrefix(`/`)
traefik.http.routers.https-0-qcks8kwws80cw0s4sscw00wg-mssql.entryPoints: https
traefik.http.routers.https-0-qcks8kwws80cw0s4sscw00wg-mssql.middlewares: gzip
traefik.http.routers.https-0-qcks8kwws80cw0s4sscw00wg-mssql.rule: Host(`identity.falklabs.de`) && PathPrefix(`/`)
traefik.http.routers.https-0-qcks8kwws80cw0s4sscw00wg-mssql.tls.certresolver: letsencrypt
traefik.http.routers.https-0-qcks8kwws80cw0s4sscw00wg-mssql.tls: true
```

---

## Volumes

| Volume Name | Pfad im Container |
|-------------|-------------------|
| qcks8kwws80cw0s4sscw00wg_mssql-data | /var/opt/mssql |
| qcks8kwws80cw0s4sscw00wg_postgres-data | /var/lib/postgresql |
| qcks8kwws80cw0s4sscw00wg_mysql-data | /var/lib/mysql |
| qcks8kwws80cw0s4sscw00wg_mongodb-data | /data/db |

---

## Environment Variables (Auszug)

```bash
COOLIFY_BRANCH="main"
COOLIFY_RESOURCE_UUID=qcks8kwws80cw0s4sscw00wg
SERVICE_URL_MSSQL=https://identity.falklabs.de
SERVICE_FQDN_MSSQL=identity.falklabs.de
SERVICE_NAME_MONGODB=mongodb
SERVICE_NAME_POSTGRES=postgres
SERVICE_NAME_MYSQL=mysql
SERVICE_NAME_MSSQL=mssql
```

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

## Git Repository

| Attribut | Wert |
|----------|------|
| **Repository** | better-auth/better-auth |
| **Branch** | main |
| **Commit SHA** | HEAD |
| **Source Type** | GitHub App |

---

## Deployment Info

| Attribut | Wert |
|----------|------|
| **Erstellt am** | 2026-02-21T13:12:51.000000Z |
| **Letztes Update** | 2026-02-21T15:17:05.000000Z |
| **Restart Count** | 0 |
| **Concurrent Builds** | 2 |
| **Deployment Queue Limit** | 25 |

---

## Docker Compose Raw (Auszug)

```yaml
version: '3.8'
services:
  mssql:
    image: 'mcr.microsoft.com/mssql/server:latest'
    container_name: mssql
    environment:
      SA_PASSWORD: Password123!
      ACCEPT_EULA: 'Y'
    ports:
      - '1433:1433'
    volumes:
      - 'mssql_data:/var/opt/mssql'
  
  postgres:
    image: 'postgres:latest'
    container_name: postgres
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: better_auth
    ports:
      - '5432:5432'
    volumes:
      - 'postgres_data:/var/lib/postgresql'
  
  mysql:
    image: 'mysql:latest'
    container_name: mysql
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_DATABASE: better_auth
      MYSQL_USER: user
      MYSQL_PASSWORD: password
    ports:
      - '3306:3306'
    volumes:
      - 'mysql_data:/var/lib/mysql'
  
  mongodb:
    image: 'mongo:latest'
    container_name: mongodb
    ports:
      - '27017:27017'
    volumes:
      - 'mongodb_data:/data/db'

volumes:
  mssql_data: null
  postgres_data: null
  mysql_data: null
  mongodb_data: null
```

---

## Wichtige Notizen

1. **Aktueller Status:** Service läuft, aber Better Auth Endpoints noch nicht implementiert
2. **MSSQL ist der Haupt-Endpoint** über identity.falklabs.de erreichbar
3. **PostgreSQL** läuft auf Port 5432 (kann für Better Auth genutzt werden)
4. **SSL/TLS** aktiv via Traefik mit Let's Encrypt
5. **Kein Health Check** aktiviert - sollte für Production aktiviert werden

---

## Nächste Schritte (TODO)

- [ ] Better Auth Node.js Service hinzufügen
- [ ] Environment Variables für Better Auth konfigurieren
- [ ] Health Check aktivieren
- [ ] API Endpoints definieren (siehe betterauth_plan.md)
- [ ] BRAiN Backend Integration
