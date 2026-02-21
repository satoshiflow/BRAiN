# Better Auth Node.js Service

Better Auth Service für das BRAiN Ökosystem.

## Features

- Email/Password Authentication
- Session Management
- OAuth (GitHub, Google)
- PostgreSQL Database
- CORS enabled for BRAiN domains
- Health Check endpoint

## Schnellstart

### Lokale Entwicklung

```bash
# Dependencies installieren
npm install

# Environment konfigurieren
cp .env.example .env
# .env anpassen

# Development Server starten
npm run dev
```

### Docker Build

```bash
# Image bauen
docker build -t better-auth-service .

# Container starten
docker run -p 3000:3000 --env-file .env better-auth-service
```

## API Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/` | GET | Service Info |
| `/health` | GET | Health Check |
| `/api/auth/sign-up/email` | POST | Registrierung |
| `/api/auth/sign-in/email` | POST | Login |
| `/api/auth/session` | GET | Session abrufen |
| `/api/auth/sign-out` | POST | Logout |

## Coolify Deployment

1. **In Coolify UI:**
   - Projekt: falklabs-core
   - Add Service → Docker Compose
   - Repository: Lokaler Pfad oder Git

2. **Environment Variables:**
   ```bash
   DATABASE_URL=postgresql://user:password@postgres:5432/better_auth
   BETTER_AUTH_SECRET=<generate-32-char-secret>
   BETTER_AUTH_URL=https://auth.falklabs.de
   TRUSTED_ORIGINS=https://control.brain.falklabs.de,https://axe.brain.falklabs.de
   ```

3. **Domain:**
   - auth.falklabs.de
   - Port: 3000

4. **Networks:**
   - coolify (Standard)
   - qcks8kwws80cw0s4sscw00wg (PostgreSQL)

## Umgebungsvariablen

| Variable | Beschreibung | Required |
|----------|--------------|----------|
| `PORT` | Server Port | Nein (Default: 3000) |
| `NODE_ENV` | Environment | Nein (Default: development) |
| `DATABASE_URL` | PostgreSQL URL | Ja |
| `BETTER_AUTH_SECRET` | Secret Key (min 32 chars) | Ja |
| `BETTER_AUTH_URL` | Auth Service URL | Ja |
| `TRUSTED_ORIGINS` | CORS Origins (comma separated) | Ja |
| `GITHUB_CLIENT_ID` | GitHub OAuth ID | Nein |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth Secret | Nein |
| `GOOGLE_CLIENT_ID` | Google OAuth ID | Nein |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Secret | Nein |

## Lizenz

MIT