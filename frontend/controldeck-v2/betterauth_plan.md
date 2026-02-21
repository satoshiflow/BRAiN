# Better Auth Integration - Plan & Konzept

**Datum:** 2026-02-21  
**Status:** Konzept Phase  
**Ziel:** Authentifizierung für BRAiN Ökosystem

---

## 1. Aktueller Stand

### Was existiert bereits:
- ✅ Coolify Service "Identity" läuft
- ✅ PostgreSQL, MySQL, MongoDB, MSSQL Container
- ✅ Domain: identity.falklabs.de
- ✅ SSL/TLS via Traefik
- ❌ Better Auth Node.js Service fehlt
- ❌ API Endpoints nicht definiert
- ❌ Integration mit BRAiN Backend fehlt

---

## 2. Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  ControlDeck    │  │    AXE UI       │  │  Mobile App     │ │
│  │  (Next.js)      │  │  (Next.js)      │  │   (optional)    │ │
│  └────────┬────────┘  └────────┬────────┘  └─────────────────┘ │
└───────────┼────────────────────┼────────────────────────────────┘
            │                    │
            └──────────┬─────────┘
                       │ HTTPS
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Better Auth Service                         │
│                     identity.falklabs.de                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Better Auth (Node.js/Express)                              ││
│  │  - Sign Up / Sign In                                        ││
│  │  - Session Management                                       ││
│  │  - OAuth (GitHub, Google)                                   ││
│  │  - 2FA (optional)                                           ││
│  └────────┬────────────────────────────────────────────────────┘│
└───────────┼─────────────────────────────────────────────────────┘
            │
            ▼ HTTPS/Internal
┌─────────────────────────────────────────────────────────────────┐
│                      BRAiN Backend API                           │
│                   api.brain.falklabs.de                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  FastAPI + Auth Middleware                                  ││
│  │  - Token Validation                                         ││
│  │  - Protected Endpoints                                      ││
│  │  - User Context                                             ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Better Auth Service - Node.js

### 3.1 Service Konfiguration

| Attribut | Wert |
|----------|------|
| **Name** | better-auth-node |
| **Image** | node:20-alpine |
| **Port** | 3000 |
| **Domain** | auth.falklabs.de |
| **Datenbank** | PostgreSQL (bestehend) |

### 3.2 Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/better_auth

# Better Auth
BETTER_AUTH_SECRET=<generate-32-char-secret>
BETTER_AUTH_URL=https://auth.falklabs.de
TRUSTED_ORIGINS=https://control.brain.falklabs.de,https://axe.brain.falklabs.de,https://api.brain.falklabs.de

# OAuth (optional)
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx

# Email (für Verifikation)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@falklabs.de
SMTP_PASSWORD=xxx
```

### 3.3 Datei Struktur

```
better-auth-service/
├── src/
│   ├── index.ts              # Express Server
│   ├── auth.ts               # Better Auth Konfiguration
│   └── middleware/
│       └── cors.ts           # CORS Handling
├── package.json
├── tsconfig.json
├── Dockerfile
└── docker-compose.yml
```

### 3.4 Better Auth Config (auth.ts)

```typescript
import { betterAuth } from "better-auth";
import { pg } from "better-auth/adapters";

export const auth = betterAuth({
  database: {
    provider: "pg",
    connectionString: process.env.DATABASE_URL,
  },
  
  // Social Providers
  socialProviders: {
    github: {
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
    },
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    },
  },
  
  // CORS
  trustedOrigins: process.env.TRUSTED_ORIGINS?.split(",") || [],
  
  // Sessions
  advanced: {
    cookiePrefix: "brain_auth",
    useSecureCookies: true,
    sameSite: "lax",
  },
  
  // Email Verification
  emailVerification: {
    sendOnSignUp: true,
    autoSignInAfterVerification: true,
    sendVerificationEmail: async ({ user, url }) => {
      // SMTP Integration
    },
  },
});
```

### 3.5 Express Server (index.ts)

```typescript
import express from "express";
import { toNodeHandler } from "better-auth/node";
import { auth } from "./auth";

const app = express();
const PORT = process.env.PORT || 3000;

// CORS
app.use(cors({
  origin: process.env.TRUSTED_ORIGINS?.split(",") || [],
  credentials: true,
}));

// Better Auth Handler
app.all("/api/auth/*", toNodeHandler(auth));

// Health Check
app.get("/health", (req, res) => {
  res.json({ status: "ok", service: "better-auth" });
});

app.listen(PORT, () => {
  console.log(`Better Auth running on port ${PORT}`);
});
```

---

## 4. API Endpoints

### 4.1 Auth Endpoints (Better Auth Standard)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| POST | /api/auth/sign-up/email | Email/Password Registrierung |
| POST | /api/auth/sign-in/email | Email/Password Login |
| POST | /api/auth/sign-in/social | Social Login (GitHub, Google) |
| POST | /api/auth/sign-out | Ausloggen |
| GET | /api/auth/session | Aktuelle Session abrufen |
| POST | /api/auth/forget-password | Passwort vergessen |
| POST | /api/auth/reset-password | Passwort zurücksetzen |
| POST | /api/auth/verify-email | Email verifizieren |
| POST | /api/auth/send-verification-email | Verifikations-Email senden |

### 4.2 User Endpoints

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | /api/user | Aktuellen User abrufen |
| PATCH | /api/user | User-Daten aktualisieren |
| DELETE | /api/user | Account löschen |

---

## 5. BRAiN Backend Integration

### 5.1 Auth Middleware (FastAPI)

```python
# middleware/auth.py
import httpx
from fastapi import Request, HTTPException, Depends

AUTH_SERVICE_URL = "https://auth.falklabs.de"

async def verify_token(request: Request) -> dict:
    """Verify JWT token with Better Auth service"""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    token = auth_header.replace("Bearer ", "")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AUTH_SERVICE_URL}/api/auth/session",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return response.json()

# Dependency für geschützte Endpoints
async def get_current_user(user: dict = Depends(verify_token)):
    return user
```

### 5.2 Geschützte Endpoints

```python
# routes/missions.py
from fastapi import APIRouter, Depends
from middleware.auth import get_current_user

router = APIRouter()

@router.get("/api/missions/queue")
async def get_missions(user: dict = Depends(get_current_user)):
    """Only accessible with valid token"""
    return {
        "missions": [...],
        "user": user["email"]  # User Context verfügbar
    }
```

---

## 6. Frontend Integration (Next.js)

### 6.1 Auth Client

```typescript
// lib/auth.ts
import { createAuthClient } from "better-auth/client";

export const authClient = createAuthClient({
  baseURL: "https://auth.falklabs.de",
});

// hooks/useAuth.ts
export function useAuth() {
  const { data: session, isPending } = authClient.useSession();
  
  return {
    user: session?.user,
    isLoading: isPending,
    signIn: authClient.signIn,
    signOut: authClient.signOut,
    signUp: authClient.signUp,
  };
}
```

### 6.2 API Client mit Auth Header

```typescript
// lib/api.ts
import { authClient } from "./auth";

export async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const session = await authClient.getSession();
  
  const headers = {
    ...options.headers,
    "Authorization": `Bearer ${session?.token}`,
    "Content-Type": "application/json",
  };
  
  return fetch(url, { ...options, headers });
}
```

---

## 7. Implementierungsplan

### Phase 1: Better Auth Service (Week 1)

- [ ] Node.js Service erstellen
- [ ] Docker Konfiguration
- [ ] Environment Variables setzen
- [ ] In Coolify deployen
- [ ] Health Check testen

### Phase 2: Backend Integration (Week 2)

- [ ] Auth Middleware implementieren
- [ ] Geschützte Endpoints markieren
- [ ] User Context in API Responses
- [ ] Testing

### Phase 3: Frontend Integration (Week 3)

- [ ] Auth Client konfigurieren
- [ ] Login/Register Pages
- [ ] Protected Routes
- [ ] Logout Funktionalität

### Phase 4: Testing & Docs (Week 4)

- [ ] End-to-End Testing
- [ ] OAuth Provider testen
- [ ] Dokumentation erstellen
- [ ] Team Training

---

## 8. Security Checklist

- [ ] HTTPS enforced
- [ ] Secure Cookies (SameSite, HttpOnly)
- [ ] CORS configured
- [ ] Rate limiting
- [ ] Input validation
- [ ] SQL Injection protection (via ORM)
- [ ] XSS protection
- [ ] CSRF tokens
- [ ] Secrets in Environment Variables
- [ ] No secrets in Git

---

## 9. Nächste Sofort-Aktionen

1. **Better Auth Node.js Service deployen**
   - Dockerfile erstellen
   - In Coolify als neuen Service anlegen
   - Environment Variables konfigurieren

2. **Backend Auth Middleware implementieren**
   - FastAPI Dependency erstellen
   - Test-Endpoint schützen

3. **Frontend Auth Client einrichten**
   - better-auth/client installieren
   - Login Page erstellen

**Soll ich mit der Implementierung beginnen?**
