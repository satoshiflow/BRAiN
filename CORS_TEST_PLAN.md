# CORS Test Plan - Option A

**Ziel:** CORS-Konfiguration zwischen Frontend und Backend validieren

**Dauer:** 15-30 Minuten

---

## 🔍 Aktuelle CORS-Konfiguration

### Backend (main.py)
```python
cors_origins = settings.cors_origins if hasattr(settings, 'cors_origins') else [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "*",  # Wildcard als Fallback
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Settings (config.py)
- **Default:** `cors_origins = "*"` (alle Origins erlaubt)
- **Format:** CSV string, JSON array, oder ENV variable
- **ENV Variable:** `CORS_ORIGINS` (optional)

---

## ✅ Test A1: Preflight Check (OPTIONS Request)

### 1. Browser DevTools öffnen

**Chrome/Edge:**
1. Öffne https://dev.brain.falklabs.de
2. Drücke `F12` → Tab "Network"
3. Filter auf "Fetch/XHR"

### 2. API Request auslösen

**Option A: Im Control Deck:**
- Navigiere zu Dashboard
- Warte auf automatische API calls

**Option B: In Browser Console:**
```javascript
fetch('https://dev.brain.falklabs.de/api/health', {
  method: 'GET',
  credentials: 'include'
})
  .then(r => r.json())
  .then(console.log)
  .catch(console.error);
```

### 3. Request inspizieren

**Klicke auf Request → Tab "Headers"**

**Erwartete Request Headers:**
```
Origin: https://dev.brain.falklabs.de
```

**Erwartete Response Headers:**
```
Access-Control-Allow-Origin: https://dev.brain.falklabs.de
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: *
Access-Control-Allow-Headers: *
```

**⚠️ WICHTIG:**
- Wenn `Access-Control-Allow-Origin: *` → CORS ist zu offen (nicht ideal für Cookies)
- Wenn `Access-Control-Allow-Origin: https://dev.brain.falklabs.de` → ✅ KORREKT

### 4. OPTIONS Preflight Check

**Manueller Preflight Test:**
```bash
curl -X OPTIONS https://dev.brain.falklabs.de/api/health \
  -H "Origin: https://dev.brain.falklabs.de" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v
```

**Erwartete Response:**
```
HTTP/2 200
access-control-allow-origin: https://dev.brain.falklabs.de
access-control-allow-credentials: true
access-control-allow-methods: *
access-control-allow-headers: *
```

---

## ❌ Test A2: Negative Test (Evil Origin)

### Ziel
Verifizieren, dass CORS nur erlaubte Origins akzeptiert.

### 1. Test mit falscher Origin

```bash
curl -X GET https://dev.brain.falklabs.de/api/health \
  -H "Origin: https://evil.com" \
  -v
```

**Erwartetes Verhalten:**

**Fall 1: CORS_ORIGINS = "*" (aktuell)**
```
access-control-allow-origin: *
```
→ ⚠️ WARNUNG: Alle Origins erlaubt (nicht sicher für Cookies)

**Fall 2: CORS_ORIGINS = ["https://dev.brain.falklabs.de"]**
```
# Keine CORS-Header ODER
access-control-allow-origin: null
```
→ ✅ KORREKT: Browser blockiert Request

### 2. Browser Test

**In Browser Console von https://evil.com:**
```javascript
fetch('https://dev.brain.falklabs.de/api/health')
  .then(r => r.json())
  .then(console.log)
  .catch(err => {
    console.error('CORS blocked:', err);
    // Erwarteter CORS Error
  });
```

**Erwartete Browser Console Error:**
```
Access to fetch at 'https://dev.brain.falklabs.de/api/health' from origin 'https://evil.com'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present.
```

---

## 🔧 CORS-Konfiguration anpassen (wenn nötig)

### Problem: CORS ist zu offen (wildcard "*")

**Lösung: Spezifische Origins setzen**

**1. In Coolify UI → Environment Variables:**
```bash
CORS_ORIGINS=https://dev.brain.falklabs.de,https://axe.dev.brain.falklabs.de
```

**2. Oder in .env Datei:**
```bash
CORS_ORIGINS="https://dev.brain.falklabs.de,https://axe.dev.brain.falklabs.de"
```

**3. Oder als JSON Array:**
```bash
CORS_ORIGINS='["https://dev.brain.falklabs.de","https://axe.dev.brain.falklabs.de"]'
```

**4. Redeploy Backend:**
```bash
# In Coolify: Redeploy Button
# Oder manuell:
docker restart <backend-container>
```

---

## 📊 Test-Protokoll

### Checklist

- [ ] **A1.1** - Browser DevTools Network Tab geöffnet
- [ ] **A1.2** - API Request ausgelöst (Dashboard oder Console)
- [ ] **A1.3** - Request Headers geprüft (`Origin: https://dev.brain.falklabs.de`)
- [ ] **A1.4** - Response Headers geprüft (`Access-Control-Allow-Origin`)
- [ ] **A1.5** - OPTIONS Preflight Test (curl)
- [ ] **A2.1** - Negative Test mit evil.com Origin (curl)
- [ ] **A2.2** - Browser Console Test mit CORS Error
- [ ] **A2.3** - CORS-Konfiguration dokumentiert

### Ergebnisse

**A1: Preflight Check**
- Request Origin: `___________________________`
- Response CORS Header: `___________________________`
- Allow-Credentials: `___________________________`
- Status: ✅ PASS / ❌ FAIL

**A2: Negative Test**
- Evil Origin Response: `___________________________`
- Browser CORS Error: ✅ JA / ❌ NEIN
- Status: ✅ PASS / ❌ FAIL

---

## 🚨 Troubleshooting

### Problem: Keine CORS-Header in Response

**Ursache:** Backend nicht richtig gestartet oder CORS Middleware fehlt

**Lösung:**
```bash
# Backend Logs prüfen
docker logs <backend-container> | grep CORS

# Backend neu starten
docker restart <backend-container>
```

### Problem: Access-Control-Allow-Origin = "*"

**Ursache:** CORS_ORIGINS ENV variable nicht gesetzt

**Lösung:** ENV variable setzen (siehe oben)

### Problem: Cookies funktionieren nicht

**Ursache:** `allow_credentials=True` benötigt spezifische Origin (nicht "*")

**Lösung:**
```bash
CORS_ORIGINS="https://dev.brain.falklabs.de"
# Nicht "*" verwenden!
```

---

## ✅ Success Criteria

**Test gilt als erfolgreich wenn:**

1. ✅ Response Header `Access-Control-Allow-Origin` enthält korrekte Origin
2. ✅ Response Header `Access-Control-Allow-Credentials: true` vorhanden
3. ✅ OPTIONS Preflight funktioniert (HTTP 200)
4. ✅ Negative Test mit evil.com wird blockiert (CORS Error)
5. ✅ Frontend kann API Calls machen ohne CORS Errors

**Empfehlung für Production:**
```bash
CORS_ORIGINS="https://dev.brain.falklabs.de,https://axe.dev.brain.falklabs.de"
```
Nicht `*` verwenden!

---

**Next Step nach Test:**
→ Phase 1: Mage.ai Service Setup (intern-only, kein Traefik)
