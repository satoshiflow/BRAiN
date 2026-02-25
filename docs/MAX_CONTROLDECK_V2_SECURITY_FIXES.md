# MAX Execution Prompt — controldeck-v2 Security Fixes

**Datum:** 2026-02-25
**Branch:** `claude/auth-governance-engine-vZR1n`
**Basis:** Security Review controldeck-v2 (Score: 6.5/10)

Claude hat soeben Fix #2 (SSRF Proxy) und Fix #5 (Deprecated Routes) implementiert.
Du übernimmst die verbleibenden Issues.

---

## Dein Auftrag: 5 Security Fixes in controldeck-v2

**Arbeitsverzeichnis:** `/home/user/BRAiN/frontend/controldeck-v2`

---

## Fix A — HARDCODED SECRET (CRITICAL, ~15 min)

**Datei:** `src/lib/auth.ts` Zeile 8

**Problem:**
```typescript
secret: process.env.BETTER_AUTH_SECRET || process.env.JWT_SECRET_KEY || "change-me-in-production",
```
Wenn die Env-Var fehlt, läuft die App mit einem bekannten Default-Secret → Session-Tokens können gefälscht werden.

**Fix:**
```typescript
const secret = process.env.BETTER_AUTH_SECRET;
if (!secret) {
  throw new Error(
    "BETTER_AUTH_SECRET environment variable is required. " +
    "Set it to a random 32+ character string."
  );
}

export const auth = betterAuth({
  secret,
  // ... rest
  session: {
    expiresIn: 60 * 60 * 2, // 2h statt 7 Tage (Security Best Practice)
    // ...
  }
});
```

---

## Fix B — RBAC MIDDLEWARE (CRITICAL, ~3h)

**Problem:** `src/app/(protected)/layout.tsx` prüft nur ob Session vorhanden ist, nicht welche Rolle der User hat. Jeder Auth-User sieht alle Seiten.

**Prisma Schema hat bereits `role` Feld auf User-Modell.**

**Schritt 1: `src/lib/rbac.ts` erstellen**
```typescript
export type UserRole = 'admin' | 'operator' | 'agent' | 'user';

export function hasRole(sessionRole: string | undefined | null, required: UserRole): boolean {
  const hierarchy: Record<UserRole, number> = {
    admin: 100,
    operator: 50,
    agent: 25,
    user: 10,
  };
  const userLevel = hierarchy[sessionRole as UserRole] ?? 0;
  const requiredLevel = hierarchy[required] ?? 0;
  return userLevel >= requiredLevel;
}
```

**Schritt 2: Admin-only Pages schützen**

Dateien die `require_admin` brauchen (analog zum Backend):
- `src/app/(protected)/settings/page.tsx`
- `src/app/(protected)/api-keys/page.tsx`

Pattern:
```typescript
import { hasRole } from '@/lib/rbac';
// in layout/page:
if (!hasRole(session.user.role, 'admin')) {
  redirect('/dashboard?error=unauthorized');
}
```

**Schritt 3: Operator-only Pages**
- `src/app/(protected)/intelligence/skills/creator/page.tsx`

---

## Fix C — AUTH PROVIDER ENDPOINT (HIGH, ~30 min)

**Datei:** `src/components/auth/auth-provider.tsx` Zeile 44

**Problem:**
```typescript
const res = await fetch("/api/auth", { credentials: "include", cache: "no-store" })
```
Dieser GET-Request an `/api/auth` existiert nicht als Endpoint — Better Auth nutzt `/api/auth/[action]`.

**Fix:** Better Auth Client verwenden statt raw fetch:
```typescript
// In auth-provider.tsx
import { createAuthClient } from 'better-auth/react';

const authClient = createAuthClient({
  baseURL: typeof window !== 'undefined' ? window.location.origin : '',
});

// Session abrufen:
const { data: session } = await authClient.useSession();
```

Oder server-side:
```typescript
// Statt fetch("/api/auth"):
const res = await fetch("/api/auth/get-session", { credentials: "include", cache: "no-store" });
```

---

## Fix D — .env.example ERSTELLEN (HIGH, ~30 min)

**Datei:** `frontend/controldeck-v2/.env.example` neu anlegen:
```env
# Better Auth - REQUIRED (min 32 Zeichen, zufällig generiert)
# Generieren: openssl rand -base64 32
BETTER_AUTH_SECRET=

# PostgreSQL - REQUIRED
DATABASE_URL=postgresql://user:password@localhost:5432/brain_controldeck

# Backend API URLs - REQUIRED
# Intern (Docker-to-Docker):
BRAIN_API_BASE_INTERNAL=http://backend:8000
# Öffentlich (Browser):
NEXT_PUBLIC_BRAIN_API_BASE=https://api.brain.example.com

# WebSocket - OPTIONAL (fällt auf PUBLIC_API_BASE zurück)
BRAIN_WS_BASE_INTERNAL=ws://backend:8000/ws
NEXT_PUBLIC_BRAIN_WS_BASE=wss://api.brain.example.com/ws

# Next.js
NODE_ENV=production
NEXTAUTH_URL=https://brain.example.com
```

---

## Fix E — WEBSOCKET SECURITY (MEDIUM, ~15 min)

**Datei:** `src/lib/api.ts` Zeile 42

**Problem:** Server-seitiger WS-Fallback nutzt `ws://` (unverschlüsselt):
```typescript
return process.env.BRAIN_WS_BASE_INTERNAL || 'ws://backend:8000/ws';
```

**Fix:**
```typescript
export function getWsBaseUrl(): string {
  if (isServer) {
    const url = process.env.BRAIN_WS_BASE_INTERNAL;
    if (!url) {
      console.warn('[WS] BRAIN_WS_BASE_INTERNAL not set');
      return 'ws://backend:8000/ws'; // OK intern (Docker-Netz, kein TLS nötig)
    }
    return url;
  } else {
    const url = process.env.NEXT_PUBLIC_BRAIN_WS_BASE;
    if (!url) {
      // Im Browser: wss:// für HTTPS-Seiten, ws:// für HTTP (dev)
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
      return `${proto}://${window.location.host}/ws`;
    }
    // Env-Var muss wss:// sein wenn auf Production
    if (process.env.NODE_ENV === 'production' && url.startsWith('ws://')) {
      throw new Error('NEXT_PUBLIC_BRAIN_WS_BASE must use wss:// in production');
    }
    return url;
  }
}
```

---

## Medium Issues (falls Zeit bleibt)

### Error Messages nicht exposieren (Proxy)
`src/app/api/proxy/[...path]/route.ts` — in der catch-block:
```typescript
// STATT:
message: error instanceof Error ? error.message : 'Unknown error',
// SO:
// (kein message field)
```

### Session Timeout reduzieren
`src/lib/auth.ts`:
```typescript
session: {
  expiresIn: 60 * 60 * 2, // 2h statt 7 Tage
}
```

### User Context aus HTML entfernen
`src/app/(protected)/layout.tsx` — das `<script id="__USER_CONTEXT__">` Tag entfernen.
Client-Komponenten sollen User-Daten per `authClient.useSession()` holen.

---

## Git Commit am Ende

```bash
git add -A
git commit -m "fix(security): controldeck-v2 - RBAC, secrets, auth fixes

- Remove hardcoded BETTER_AUTH_SECRET fallback (throw on missing)
- Implement RBAC middleware with role hierarchy
- Fix auth-provider.tsx to use Better Auth client correctly
- Add .env.example with all required variables
- Fix WebSocket security: wss:// validation in production
- Reduce session timeout from 7d to 2h
- Remove user context from HTML script tag"

git push -u origin claude/auth-governance-engine-vZR1n
```

---

## Was Claude bereits gefixt hat (NICHT nochmal ändern)

- ✅ **Fix #2:** SSRF in Proxy — Whitelist + Path-Traversal-Schutz implementiert
- ✅ **Fix #5:** Deprecated Routes — login/logout/signup auf Better Auth API umgestellt

---

*Erstellt: 2026-02-25 | Für: Max Agent*
