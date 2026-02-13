# 🎯 COOLIFY UI FIX GUIDE - Phase 0

**Ziel:** Traefik Router Rules korrigieren durch Coolify UI Domain-Konfiguration

**Zeitaufwand:** 5-10 Minuten

**Voraussetzung:** Login zu https://coolify.falklabs.de

---

## 🔐 SCHRITT 1: Login

1. Öffne Browser: https://coolify.falklabs.de
2. Login mit Admin-Credentials
3. Wechsle zum richtigen **Project** (wahrscheinlich "BRAIN" oder "Default")

---

## 🔍 SCHRITT 2: Services finden

**Suche nach:**
- `backend` oder `brain-backend` oder `mw0ck04s8go048c0g4so48cc-backend`
- `control_deck` oder `brain-control-deck`
- `axe_ui` oder `brain-axe-ui`

**Tipp:** Nutze die Suche oder gehe zu **Applications** → Filter nach "brain"

---

## 🛠️ SCHRITT 3: Backend Domain Fix

### A) Backend Service öffnen
1. Klicke auf **backend** Service
2. Gehe zum Tab **"Domains"** oder **"Configuration"** → **"Domains"**

### B) Aktuelle Domains prüfen
**Suche nach fehlerhaften Einträgen wie:**
- Leere Domain + PathPrefix
- Falsch konfigurierte Rules
- `dev.brain.falklabs.de` im falschen Feld

### C) Domains korrigieren

**❌ LÖSCHE fehlerhafte Einträge**

**✅ SETZE korrekte Domain:**

| Feld | Wert |
|------|------|
| **Domain** | `dev.brain.falklabs.de` |
| **Path** (optional) | `/api` |
| **Port** | `8000` |
| **HTTPS/TLS** | ✅ Enabled |
| **Certificate Resolver** | `letsencrypt` |

**Optional:** Zusätzliche Paths hinzufügen:
- `/docs`
- `/redoc`
- `/openapi.json`

**Tipp in Coolify:**
- Manche UIs nutzen "Path Prefix" statt "Path"
- Stelle sicher, dass Domain im **Domain-Feld** steht, NICHT im Path!

### D) Speichern & Redeploy
1. Klicke **"Save"**
2. Klicke **"Redeploy"** oder **"Restart"**
3. Warte ca. 30 Sekunden

---

## 🎨 SCHRITT 4: Control Deck Domain Fix

### A) Control Deck Service öffnen
1. Klicke auf **control_deck** Service
2. Gehe zum Tab **"Domains"**

### B) Domains korrigieren

**❌ LÖSCHE fehlerhafte Einträge**

**✅ SETZE korrekte Domain:**

| Feld | Wert |
|------|------|
| **Domain** | `dev.brain.falklabs.de` |
| **Path** | `/` (root, catch-all) oder LEER lassen |
| **Port** | `3000` |
| **HTTPS/TLS** | ✅ Enabled |
| **Certificate Resolver** | `letsencrypt` |

**WICHTIG:**
- Control Deck ist der **Fallback** (catch-all)
- Muss **niedrigere Priority** als Backend haben
- Wenn Coolify "Priority" anzeigt: Setze z.B. `1` (Backend hat `10`)

### C) Speichern & Redeploy
1. **"Save"**
2. **"Redeploy"**
3. Warte 30 Sekunden

---

## 🎯 SCHRITT 5: AXE UI Domain Fix

### A) AXE UI Service öffnen
1. Klicke auf **axe_ui** Service
2. Gehe zum Tab **"Domains"**

### B) Domains korrigieren

**❌ LÖSCHE fehlerhafte Einträge**

**✅ SETZE korrekte Domain:**

| Feld | Wert |
|------|------|
| **Domain** | `axe.dev.brain.falklabs.de` |
| **Path** | `/` oder LEER |
| **Port** | `3000` |
| **HTTPS/TLS** | ✅ Enabled |
| **Certificate Resolver** | `letsencrypt` |

**WICHTIG:** AXE UI hat eine **separate Subdomain**!

### C) Speichern & Redeploy
1. **"Save"**
2. **"Redeploy"**
3. Warte 30 Sekunden

---

## ✅ SCHRITT 6: VALIDATION

### A) Traefik Logs prüfen

**In Coolify:**
1. Gehe zu **Proxy** (Traefik Container)
2. Öffne **Logs**
3. Suche nach Errors

**Erwartung:**
```
✅ Keine Errors mehr: "empty args for matcher Host"
✅ Registrierte Router: backend, control_deck, axe_ui
✅ SSL Certificates requested/obtained
```

**❌ Falls immer noch Errors:**
- Warte 2 Minuten (Traefik reload)
- Force-Restart Traefik Proxy
- Check Domain-Syntax nochmal

---

### B) SSL Certificates prüfen

**Via Browser:**
1. Öffne https://dev.brain.falklabs.de
2. Klicke auf **Schloss-Symbol** (Adressleiste)
3. Check Certificate

**Erwartung:**
- ✅ Issuer: **Let's Encrypt**
- ✅ Valid für: `dev.brain.falklabs.de`
- ✅ Nicht abgelaufen

**Via CLI (optional):**
```bash
echo | openssl s_client -servername dev.brain.falklabs.de \
  -connect dev.brain.falklabs.de:443 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
```

Wiederhole für:
- https://dev.brain.falklabs.de (Control Deck)
- https://dev.brain.falklabs.de/api/health (Backend)
- https://axe.dev.brain.falklabs.de (AXE UI)

---

### C) HTTP Status prüfen

**Test in Browser oder via curl:**

```bash
# Backend Health
curl -I https://dev.brain.falklabs.de/api/health
# Erwartung: HTTP/2 200 OK

# Backend Docs
curl -I https://dev.brain.falklabs.de/docs
# Erwartung: HTTP/2 200 OK

# Control Deck (Root)
curl -I https://dev.brain.falklabs.de/
# Erwartung: HTTP/2 200 OK

# AXE UI
curl -I https://axe.dev.brain.falklabs.de/
# Erwartung: HTTP/2 200 OK
```

**Mögliche Ergebnisse:**
- ✅ **200 OK** - Perfekt!
- ✅ **301/308 Redirect** - Okay (HTTP → HTTPS)
- ❌ **502 Bad Gateway** - Container nicht erreichbar
- ❌ **404 Not Found** - Routing Problem
- ❌ **SSL Error** - Zertifikat fehlt/falsch

---

## 🐛 TROUBLESHOOTING

### Problem 1: Traefik zeigt immer noch "empty args" Error

**Lösung:**
1. Force-Restart **Traefik Proxy** in Coolify
2. Check ob Domain-Felder wirklich **leer** sind (vor dem Fix)
3. In manchen UIs: Domain muss **MIT** `https://` prefix eingegeben werden

---

### Problem 2: SSL Certificate wird nicht ausgestellt

**Mögliche Ursachen:**
- Let's Encrypt Rate Limit (5 Certs/Woche pro Domain)
- DNS nicht richtig konfiguriert
- Port 80 nicht erreichbar (Let's Encrypt Challenge)

**Lösung:**
```bash
# Check DNS
dig dev.brain.falklabs.de +short
# Sollte 46.224.37.114 zurückgeben

# Check Port 80
curl -I http://dev.brain.falklabs.de
```

---

### Problem 3: 502 Bad Gateway

**Bedeutung:** Traefik kann Container nicht erreichen

**Check:**
1. Container läuft? (Docker Logs)
2. Richtiges Network? (`mw0ck04s8go048c0g4so48cc`)
3. Port korrekt? (8000 für backend, 3000 für frontends)

```bash
# Via SSH auf Server:
docker ps | grep brain
docker logs brain-backend | tail -20
```

---

## 📋 CHECKLIST

Nach Abschluss sollte gelten:

- [ ] **Backend:**
  - [ ] Domain: `dev.brain.falklabs.de`
  - [ ] Paths: `/api`, `/docs`, `/redoc`
  - [ ] Port: 8000
  - [ ] SSL: Let's Encrypt
  - [ ] HTTP Status: 200 OK

- [ ] **Control Deck:**
  - [ ] Domain: `dev.brain.falklabs.de`
  - [ ] Path: `/` (catch-all)
  - [ ] Port: 3000
  - [ ] SSL: Let's Encrypt
  - [ ] HTTP Status: 200 OK

- [ ] **AXE UI:**
  - [ ] Domain: `axe.dev.brain.falklabs.de`
  - [ ] Path: `/`
  - [ ] Port: 3000
  - [ ] SSL: Let's Encrypt
  - [ ] HTTP Status: 200 OK

- [ ] **Traefik Logs:**
  - [ ] Keine "empty args for matcher Host" Errors
  - [ ] Alle 3 Router registriert
  - [ ] SSL Certificates obtained

---

## 📤 NEXT STEPS

**Nach erfolgreichem Fix:**

1. ✅ **Phase 0 DONE**
2. 🔄 **SSH Setup** für Phase 1+ (siehe SSH_SETUP_GUIDE.md)
3. 🚀 **Phase 1:** CORS Testing mit vollem Server-Zugang

---

## 💬 SUPPORT

**Falls Probleme:**
1. Screenshot von Coolify Domain-Konfiguration
2. Traefik Logs (letzte 50 Zeilen)
3. Docker Logs von betroffenen Services

**Zeige mir dann:**
```bash
# Via SSH:
docker logs $(docker ps | grep traefik | awk '{print $1}') 2>&1 | tail -50
docker ps | grep brain
```

---

**Ende des Guides**
