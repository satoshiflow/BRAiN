# AXE UI Login Fix - 28.03.2026

## Problem

AXE UI Login funktionierte nicht. Browser zeigte CORS-Fehler:
```
Cross-Origin Request Blocked: Die Gleiche-Quelle-Regel verbietet das Lesen der externen Ressource auf http://backend:8000/auth/login
```

## Was NICHT funktionierte

### 1. Proxy-Konfiguration (next.config.js)
Der Next.js Proxy leitete Anfragen an `http://brain-backend:8000` statt `http://127.0.0.1:8000` weiter.
- **Fix**: Proxy so konfiguriert, dass `NEXT_PUBLIC_BRAIN_API_BASE` ENV-Variable verwendet wird

### 2. Auth-Pfade in auth.ts
Die API-Aufrufe in `lib/auth.ts` verwendeten Pfade ohne `/api` Prefix (z.B. `/auth/login` statt `/api/auth/login`).
- **Fix**: Alle Pfade auf `/api/auth/...` umgestellt

### 3. Absolute vs. relative URLs
`auth.ts` verwendete absolute URLs (`${getApiBase()}${path}`), die der Browser direkt an die externe API sendet statt über den Next.js Proxy.
- **Fix**: Relative Pfade verwenden, damit Next.js Proxy greift

### 4. Docker Cache
Der Docker-Build-Cache enthielt alte Versionen der Dateien. Alle Änderungen an `auth.ts` und `next.config.js` wurden nicht in den Container übernommen.
- **Fix**: Docker-Image mit `--no-cache` neu bauen

### 5. Passwort-Hash Problem
Die bcrypt-Passwort-Hashes in der Datenbank waren fehlerhaft. Direkte SQL-Updates mit vorgefertigten Hashes funktionierten nicht (vermutlich Escape-Probleme).
- **Fix**: Python bcrypt verwenden um Hash zu generieren und direkt in DB schreiben

## Warum es SO LANGE dauerte

1. **Docker Build-Cache**: Der wichtigste Faktor. Jeder Build verwendete gecachte Schichten mit alten Dateien. Selbst nach Änderungen wurde die alte Version gestartet.

2. **Keine sichtbare Fehlermeldung**: Der Browser zeigte nur "NetworkError" ohne Details. Das echte Problem (falsches Passwort) war im Backend-Log versteckt.

3. **Mehrere Probleme gleichzeitig**: 
   - Proxy-Konfiguration falsch
   - Auth-Pfade falsch
   - Passwort-Hash kaputt
   
   Alle drei mussten gleichzeitig gefixt werden.

4. **Fehlende Transparenz**: Ich wusste nicht, dass der Container die alte Version nutzte, bis ich das BUILD_ID verglichen habe.

## Finale Lösung

1. **auth.ts** - Relative Pfade verwenden:
```typescript
async function authRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const useProxy = true; 
  const url = useProxy ? path : `${getApiBase()}${path}`;
  // ...
}

export async function login(credentials: LoginCredentials): Promise<TokenPair> {
  return authRequest<TokenPair>("/api/auth/login", { ... });
}
```

2. **next.config.js** - Proxy mit ENV-Variable:
```javascript
async rewrites() {
  const apiBase = process.env.NEXT_PUBLIC_BRAIN_API_BASE || 'http://127.0.0.1:8000';
  return [
    {
      source: '/api/:path*',
      destination: `${apiBase}/api/:path*`,
    },
  ];
},
```

3. **Passwort zurücksetzen**:
```bash
# Mit Python bcrypt einen korrekten Hash generieren
NEW_HASH=$(python3 -c "import bcrypt; print(bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode())")

# In DB schreiben
docker exec brain-postgres psql -U brain -d brain -c "UPDATE users SET password_hash = '$NEW_HASH' WHERE email = 'admin@test.com';"
```

4. **Docker Image neu bauen** (ohne Cache):
```bash
docker rmi brain-local-axe_ui:latest
docker compose -f docker-compose.local.yml build axe_ui
```

## Funktionsweisende Credentials

- **Email**: `admin@test.com`
- **Passwort**: `admin123`

## Lessons Learned

1. Bei Docker-Problemen IMMER BUILD_ID vergleichen
2. Backend-Logs prüfen (zeigen 401 bei falschem Passwort)
3. CORS-Problem war Täuschung - echtes Problem war Authentifizierung
4. Passwort-Hashes NIE manuell in SQL schreiben - Python bcrypt verwenden
