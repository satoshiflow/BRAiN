# 🎯 COOLIFY UI FIX - Exakte Schritte

**Problem:** Coolify generiert fehlerhaften HTTP Router mit `Host('') && PathPrefix('domain')`

**Lösung:** Domain-Felder in Coolify UI korrekt setzen

---

## 📸 WAS DU IM SCREENSHOT SIEHST:

Im Screenshot sehe ich:
- ✅ `backend` (Domain: `dev.brain.falklabs.de`)
- ✅ `control_deck` (Domain: `dev.brain.falklabs.de`)
- ✅ `axe_ui` (Domain: `axe.dev.brain.falklabs.de`)

**Aber:** Das sind nur die angezeigten Domains. Die **FQDN-Felder** müssen korrekt sein!

---

## 🎯 SCHRITT 1: Backend Service öffnen

1. In Coolify: **Projects** → **brain** → **production**
2. Klicke auf **"satoshiflow-b-r-ai-nmain-..."** (der Backend Service)
3. Gehe zum Tab **"Configuration"**

---

## 🎯 SCHRITT 2: Domains Section finden

Im Configuration Tab:
1. Scrolle nach unten zur **"Domains"** Section
2. Du siehst dort **mehrere Domain-Felder**:
   - **"Domains for backend"** oder
   - **"FQDN"** (Fully Qualified Domain Name)

---

## 🎯 SCHRITT 3: Domain-Felder LEEREN

**WICHTIG:** Coolify hat manchmal **versteckte/zusätzliche Domain-Felder**!

### Mögliche Szenarien:

**Szenario A: Ein Domain-Feld**
```
[dev.brain.falklabs.de]
```
✅ Das ist korrekt - KEINE Änderung nötig (aber dann sollte es funktionieren!)

**Szenario B: Mehrere Domain-Felder**
```
Domain 1: [dev.brain.falklabs.de]
Domain 2: [                      ]  ← LEER, aber existiert!
```
❌ Leere Felder LÖSCHEN (X-Button)

**Szenario C: Path Prefix Feld**
```
Domain: [                      ]  ← LEER!
Path:   [dev.brain.falklabs.de]  ← FALSCH!
```
❌ Domain IN Path Prefix ist FALSCH!

---

## 🎯 SCHRITT 4: Domains KORREKT setzen

**Für Backend:**

| Feld | Wert | Notizen |
|------|------|---------|
| **Domain** / **FQDN** | `dev.brain.falklabs.de` | Hauptdomain |
| **Path** / **Path Prefix** | LEER oder `/api` | Nur Pfad, KEINE Domain! |
| **Port** | `8000` | Internal Container Port |
| **Generate Domain** | ❌ AUS | Keine Auto-Generation |

**Wichtig:**
- Domain darf NICHT in "Path Prefix" stehen!
- Wenn mehrere Domain-Felder: Nur EINES ausfüllen
- Leere Felder mit X-Button löschen

---

## 🎯 SCHRITT 5: Save & Force Redeploy

1. **Save** (Button unten)
2. Warte 5 Sekunden
3. Gehe zum Tab **"Deployments"**
4. Klicke **"Redeploy"** oder **"Force Redeploy"**
5. Warte bis Status: **"Healthy"** / **"Running"**

---

## 🎯 SCHRITT 6: Validation

**Nach Redeploy (warte 30-60 Sekunden):**

### Check A: Traefik Logs in Coolify
1. Gehe zu **Proxy** (Traefik Container)
2. Tab **"Logs"**
3. Suche nach: `empty args for matcher Host`

**Erwartung:** ✅ KEINE Errors mehr (oder alte Errors von vor 2 Min)

### Check B: Backend Health (Browser oder CLI)
```bash
curl -I https://dev.brain.falklabs.de/api/health
# Erwartung: HTTP/2 200 OK
```

---

## 🐛 TROUBLESHOOTING

### Problem: Immer noch "empty args" Errors

**Ursache:** Coolify hat die Domain-Config noch nicht übernommen

**Lösung:**
1. In Backend Service: **"Configuration"** → **"Advanced"**
2. Suche nach **"Custom Labels"** oder **"Docker Labels"**
3. Check ob dort ein Label mit `http-0-...backend.rule` existiert
4. Falls JA: **LÖSCHE** das Label
5. **Save** → **Redeploy**

---

### Problem: Domain-Feld akzeptiert keine Änderung

**Ursache:** Coolify UI Bug oder Permissions

**Lösung:**
1. **Delete Domain** (X-Button bei Domain)
2. **Save**
3. Warte 10 Sekunden
4. **Add Domain** (+ Button)
5. Gib Domain ein: `dev.brain.falklabs.de`
6. **Save** → **Redeploy**

---

### Problem: Kein Domain-Feld sichtbar

**Ursache:** Falscher Tab oder Build Pack

**Lösung:**
1. Check ob du im richtigen Service bist (Backend, nicht Control Deck!)
2. Tab **"Configuration"** → Scrolle ganz nach unten
3. Oder Tab **"Domains"** (falls separat)

---

## 📸 BITTE ZEIG MIR:

**Wenn es nicht funktioniert, mach Screenshots von:**

1. **Backend Service Configuration Tab**
   - Gesamte "Domains" Section
   - Alle sichtbaren Felder

2. **Traefik Logs** (letzte 20 Zeilen)

3. **Backend Container Labels** (via CLI):
   ```bash
   docker inspect backend-mw0ck04s8go048c0g4so48cc-* | grep -A 5 "http-0.*backend.rule"
   ```

---

## ✅ ERFOLG wenn:

- ✅ Traefik Logs: Keine "empty args" Errors mehr
- ✅ Backend: `curl https://dev.brain.falklabs.de/api/health` → 200 OK
- ✅ Container Labels: `Host('dev.brain.falklabs.de')` (kein leerer Host!)

---

**Ende der Anleitung**
