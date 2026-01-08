# ⚠️ BRAIN DOMAIN-MIGRATION - RISIKO-ANALYSE

**Version:** 1.0
**Erstellt am:** 2026-01-07
**Zweck:** Identifikation und Mitigation von Risiken bei der Domain-Migration

---

## 🎯 ÜBERBLICK

Diese Migration ändert die Domain-Struktur für BRAIN Services über DEV, STAGE und PROD Umgebungen. Die Hauptänderung ist die Trennung von Backend und Frontend auf separate Subdomains.

**Primäres Risiko:** Downtime und Zugriffsprobleme während der Migration.

---

## 🔴 KRITISCHE RISIKEN

### 1. **SSL-Zertifikat Generierung schlägt fehl**

**Beschreibung:**
Let's Encrypt / Traefik kann möglicherweise nicht sofort SSL-Zertifikate für neue Subdomains generieren.

**Wahrscheinlichkeit:** Mittel
**Impact:** Hoch (Service nicht erreichbar über HTTPS)

**Symptome:**
- `ERR_SSL_PROTOCOL_ERROR` im Browser
- Traefik Logs zeigen Let's Encrypt Fehler
- 502 Bad Gateway

**Ursachen:**
- DNS noch nicht propagiert (bis zu 48h)
- Let's Encrypt Rate Limits erreicht
- Traefik Konfiguration fehlerhaft
- Firewall blockiert Port 80/443

**Mitigation:**
```bash
# VORHER: DNS-Einträge prüfen
dig api.dev.brain.falklabs.de
nslookup api.dev.brain.falklabs.de

# Warten bis DNS propagiert ist (kann Stunden dauern)
# Erst dann Migration starten

# Traefik Logs überwachen
docker logs -f traefik

# Manuelle Let's Encrypt Challenge falls nötig
# (via Coolify UI oder Traefik Dashboard)
```

**Rollback:**
Backup-Konfiguration wiederherstellen, alte Domains funktionieren sofort wieder (SSL bereits vorhanden).

---

### 2. **CORS-Konfiguration blockiert Frontend-Zugriffe**

**Beschreibung:**
Backend CORS_ORIGINS nicht korrekt aktualisiert → Frontend kann API nicht erreichen.

**Wahrscheinlichkeit:** Mittel
**Impact:** Hoch (Frontend funktional tot)

**Symptome:**
```
Access to XMLHttpRequest at 'https://api.dev.brain.falklabs.de/api/health'
from origin 'https://dev.brain.falklabs.de' has been blocked by CORS policy
```

**Ursachen:**
- ENV-Variable `CORS_ORIGINS` nicht aktualisiert
- Format falsch (JSON String vs. Array)
- Tippfehler in Domain-Namen

**Mitigation:**
```bash
# VORHER: Korrekte CORS-Origins vorbereiten
# Backend .env (DEV):
CORS_ORIGINS=["https://dev.brain.falklabs.de","https://axe.dev.brain.falklabs.de"]

# Nach Migration: Sofort testen
curl -H "Origin: https://dev.brain.falklabs.de" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     https://api.dev.brain.falklabs.de/api/health \
     -v

# Erwartete Response Header:
# Access-Control-Allow-Origin: https://dev.brain.falklabs.de
```

**Rollback:**
CORS_ORIGINS auf `["*"]` setzen (temporär, bis Rollback komplett).

---

### 3. **Next.js Build-Time API URL nicht aktualisiert**

**Beschreibung:**
Frontend (control_deck, axe_ui) hat API-URL hart-coded im Build → zeigt auf alte URL.

**Wahrscheinlichkeit:** Hoch
**Impact:** Hoch (Frontend kann Backend nicht erreichen)

**Symptome:**
- Netzwerk-Requests gehen an alte URL
- Console Error: `Failed to fetch`
- Backend erreichbar, aber Frontend sendet Requests an falsche Domain

**Ursachen:**
- Build-Args nicht korrekt gesetzt
- Frontend nicht rebuildet nach ENV-Änderung
- Next.js Cache

**Mitigation:**
```bash
# KRITISCH: Redeploy mit neuen Build Args
# Nicht nur ENV-Variable ändern, sondern REBUILD!

# In docker-compose.dev.yml:
control_deck:
  build:
    args:
      NEXT_PUBLIC_BRAIN_API_BASE: https://api.dev.brain.falklabs.de
  environment:
    - NEXT_PUBLIC_BRAIN_API_BASE=https://api.dev.brain.falklabs.de

# Via Coolify: Full Redeploy (nicht nur Restart)
```

**Validierung:**
```bash
# Im Frontend Container prüfen:
docker exec -it dev-control-deck env | grep API_BASE

# Im Browser Console:
console.log(process.env.NEXT_PUBLIC_BRAIN_API_BASE)
```

**Rollback:**
Redeploy mit alten Build Args.

---

## 🟡 MODERATE RISIKEN

### 4. **Traefik Routing-Konflikte**

**Beschreibung:**
Mehrere Services matchen die gleiche Domain mit unterschiedlichen Priorities.

**Wahrscheinlichkeit:** Niedrig (nach korrekter Konfiguration)
**Impact:** Mittel (Requests landen beim falschen Service)

**Mitigation:**
- Eindeutige Domains pro Service (kein Sharing)
- Traefik Priority NICHT mehr nutzen (war das alte Problem)
- Validierung via Traefik Dashboard

**Check:**
```bash
# Traefik Dashboard öffnen
# → Routers überprüfen
# → Jeder Service sollte eigene Domain haben

# Via API:
curl http://traefik:8080/api/http/routers | jq
```

---

### 5. **Session/Cookie-Domain Probleme**

**Beschreibung:**
Cookies von alter Domain funktionieren nicht auf neuer Domain.

**Wahrscheinlichkeit:** Niedrig (wenn Cookies genutzt werden)
**Impact:** Mittel (User muss neu einloggen)

**Symptome:**
- User wird ausgeloggt
- Session nicht persistent
- Auth-Token ungültig

**Mitigation:**
```python
# Backend Cookie Config:
COOKIE_DOMAIN = "dev.brain.falklabs.de"  # Spezifisch
# NICHT: COOKIE_DOMAIN = ".brain.falklabs.de"  # (würde über Subdomains teilen)

# Nach Migration:
# - Alte Sessions invalidieren
# - User müssen neu einloggen (akzeptabel)
```

---

### 6. **DNS Propagation Delay**

**Beschreibung:**
DNS-Änderungen brauchen Zeit (TTL), User sehen alte IP.

**Wahrscheinlichkeit:** Hoch
**Impact:** Niedrig (temporär, löst sich von selbst)

**Symptome:**
- Einige User erreichen Service, andere nicht
- Geographisch unterschiedliche Ergebnisse
- `nslookup` zeigt verschiedene IPs

**Mitigation:**
```bash
# VORHER: TTL reduzieren (24h vorher)
# DNS Record TTL auf 300s (5 Min) setzen

# WÄHREND Migration:
# DNS-Änderungen durchführen
# Warten bis propagiert (kann 1-48h dauern)

# NACH Migration:
# TTL wieder auf 3600s (1h) erhöhen
```

**Validierung:**
```bash
# DNS Propagation prüfen:
dig @8.8.8.8 api.dev.brain.falklabs.de       # Google DNS
dig @1.1.1.1 api.dev.brain.falklabs.de       # Cloudflare DNS
dig @your-local-dns api.dev.brain.falklabs.de

# Online Tools:
# - https://dnschecker.org
# - https://whatsmydns.net
```

---

### 7. **Hardcoded URLs im Code**

**Beschreibung:**
Alte Domains sind im Code hardcoded (JS, Python, Config-Files).

**Wahrscheinlichkeit:** Niedrig (basierend auf Code-Analyse)
**Impact:** Mittel (einzelne Features brechen)

**Gefunden:**
```bash
# .env.example Zeile 102:
OPENROUTER_SITE_URL=https://brain.falklabs.de

# → Sollte auf https://dev.brain.falklabs.de (DEV) gesetzt werden
```

**Mitigation:**
```bash
# Code-Suche nach hardcoded Domains:
grep -r "dev.brain.falklabs.de" . \
  --include="*.js" \
  --include="*.ts" \
  --include="*.tsx" \
  --include="*.py" \
  --exclude-dir=node_modules \
  --exclude-dir=.next

# Ersetzen durch ENV-Variablen
```

---

## 🟢 NIEDRIGE RISIKEN

### 8. **Downtime während Redeploy**

**Beschreibung:**
Services kurzzeitig offline während Neustart/Rebuild.

**Wahrscheinlichkeit:** Hoch
**Impact:** Niedrig (1-2 Minuten Downtime akzeptabel für DEV/STAGE)

**Mitigation:**
- DEV/STAGE: Akzeptabel
- PROD: Wartungsfenster kommunizieren
- Health Checks vor "done" melden

---

### 9. **Browser Cache zeigt alte Seite**

**Beschreibung:**
User sieht gecachte alte Version des Frontends.

**Wahrscheinlichkeit:** Mittel
**Impact:** Niedrig (User kann Cache clearen)

**Mitigation:**
- HTTP Headers setzen: `Cache-Control: no-cache` während Migration
- User Hinweis: "Hard Refresh" (Ctrl+Shift+R)
- Service Worker invalidieren (falls genutzt)

---

## 📋 RISIKO-MATRIX

| Risiko | Wahrscheinlichkeit | Impact | Gesamt | Mitigation vorhanden? |
|--------|-------------------|--------|--------|----------------------|
| SSL-Zertifikat Fehler | Mittel | Hoch | 🔴 **Kritisch** | ✅ Ja |
| CORS-Blockierung | Mittel | Hoch | 🔴 **Kritisch** | ✅ Ja |
| Next.js Build-Args | Hoch | Hoch | 🔴 **Kritisch** | ✅ Ja |
| Traefik Routing | Niedrig | Mittel | 🟡 Moderat | ✅ Ja |
| Cookie-Domain | Niedrig | Mittel | 🟡 Moderat | ✅ Ja |
| DNS Propagation | Hoch | Niedrig | 🟡 Moderat | ✅ Ja |
| Hardcoded URLs | Niedrig | Mittel | 🟡 Moderat | ✅ Ja |
| Downtime | Hoch | Niedrig | 🟢 Niedrig | ✅ Ja |
| Browser Cache | Mittel | Niedrig | 🟢 Niedrig | ✅ Ja |

---

## 🛡️ RISIKO-MITIGATION STRATEGIE

### **Phase 1: Vorbereitung (24h vorher)**
1. ✅ DNS TTL reduzieren (auf 300s)
2. ✅ Backup erstellen (via Script)
3. ✅ DNS-Einträge für neue Subdomains anlegen
4. ✅ Warten bis DNS propagiert ist (prüfen mit `dig`)
5. ✅ Wartungsfenster kommunizieren (PROD)

### **Phase 2: Migration (DEV zuerst)**
1. ✅ Dry-Run ausführen (kein Risiko)
2. ✅ Coolify API Zugriff testen
3. ✅ Migration ausführen (`--execute`)
4. ✅ Sofort CORS testen
5. ✅ SSL-Zertifikate prüfen (Traefik Logs)
6. ✅ Frontend Redeploy überwachen (Build Args)

### **Phase 3: Validierung**
1. ✅ Validierungs-Script ausführen
2. ✅ Manuelle Tests:
   - Frontend öffnen → funktioniert?
   - API Requests im Browser Console prüfen
   - Docs öffnen (`/docs`)
3. ✅ 15 Minuten beobachten
4. ✅ Bei Problemen: Sofort Rollback

### **Phase 4: Rollback-Bereitschaft**
- ✅ Rollback-Script bereit
- ✅ Backup-File verifiziert
- ✅ Rollback innerhalb 5 Minuten möglich

---

## 🚨 NOTFALL-PROZEDUR

### **Wenn etwas schief geht:**

#### Schritt 1: STOP
- Keine weiteren Änderungen
- Fehler dokumentieren (Screenshot, Logs)

#### Schritt 2: DIAGNOSE
```bash
# Quick Checks:
curl -I https://api.dev.brain.falklabs.de
curl -I https://dev.brain.falklabs.de

# Traefik Logs:
docker logs traefik -n 100

# Backend Logs:
docker logs dev-backend -n 50

# Frontend Logs:
docker logs dev-control-deck -n 50
```

#### Schritt 3: ENTSCHEIDUNG
- **Minor Issue** (z.B. CORS): → Fix forward
- **Major Issue** (z.B. SSL failed): → Rollback

#### Schritt 4: ROLLBACK
```bash
# 1. Rollback ausführen
python3 rollback_brain_migration.py \
  --backup brain_backup_dev_TIMESTAMP.json \
  --execute

# 2. Validierung
python3 validate_brain_deployment.py --env dev

# 3. Post-Mortem: Was ging schief?
```

---

## ✅ SUCCESS CRITERIA

Migration gilt als **erfolgreich**, wenn:

1. ✅ Alle Services über neue Domains erreichbar (HTTPS)
2. ✅ SSL-Zertifikate gültig (Let's Encrypt)
3. ✅ Frontend kann Backend erreichen (CORS OK)
4. ✅ API Endpoints antworten (200 OK)
5. ✅ Keine Console Errors im Frontend
6. ✅ Validierungs-Script: 100% Pass
7. ✅ 24h Betrieb stabil (keine Errors in Logs)

---

## 📊 LESSONS LEARNED (Template für Post-Migration)

**Nach Migration ausfüllen:**

### Was lief gut?
- [ ] ...
- [ ] ...

### Was lief schlecht?
- [ ] ...
- [ ] ...

### Verbesserungen für nächstes Mal?
- [ ] ...
- [ ] ...

### Unerwartete Probleme?
- [ ] ...
- [ ] ...

---

## 📞 ESKALATION

**Bei kritischen Problemen:**

1. **Tech Lead kontaktieren** (Slack, Phone)
2. **Rollback initiieren** (nicht warten)
3. **Incident dokumentieren** (Ticket erstellen)
4. **Post-Mortem planen** (48h nach Vorfall)

---

**Erstellt von:** Claude Code
**Status:** Bereit für Review
**Nächster Schritt:** Migration Plan finalisieren
