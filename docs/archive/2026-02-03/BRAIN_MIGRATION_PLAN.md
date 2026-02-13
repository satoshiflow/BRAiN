# 🚀 BRAIN DOMAIN-MIGRATION - MASTER PLAN

**Version:** 1.0
**Erstellt am:** 2026-01-07
**Autor:** Claude Code
**Zweck:** Vollständiger Migrations-Plan für BRAIN Subdomain-Architektur

---

## 📋 DOKUMENTATIONS-INDEX

| Dokument | Zweck | Status |
|----------|-------|--------|
| `BRAIN_IST_ZUSTAND.md` | Aktuelle Konfiguration | ✅ Fertig |
| `BRAIN_SOLL_KONZEPT.md` | Ziel-Architektur | ✅ Fertig |
| `BRAIN_RISIKO_ANALYSE.md` | Risiken & Mitigation | ✅ Fertig |
| `BRAIN_MIGRATION_PLAN.md` | Dieser Plan | ✅ Fertig |
| `MIGRATION_CHECKLIST.md` | Schritt-für-Schritt Checkliste | ✅ Fertig |

**Scripts:**
- `coolify_manager.py` - Coolify API Helper
- `migrate_brain_domains.py` - Hauptmigrations-Script
- `validate_brain_deployment.py` - Validierungs-Script
- `rollback_brain_migration.py` - Rollback-Script

---

## 🎯 MIGRATION ZIELE

### **Primärziel:**
Saubere Trennung aller BRAIN Services über dedizierte Subdomains (dev/stage/prod).

### **Sekundärziele:**
1. ✅ Kein Domain-Sharing mehr (Backend + Frontend getrennt)
2. ✅ Konsistente Struktur über alle Umgebungen
3. ✅ Spezifische CORS-Konfiguration
4. ✅ Einfacheres Debugging (klare Routing-Regeln)
5. ✅ Vorbereitung für Skalierung (weitere Services)

---

## 📊 IST → SOLL TRANSFORMATION

### **DEV Environment**

| Service | VORHER | NACHHER |
|---------|--------|---------|
| Backend | `dev.brain.falklabs.de/api/*` (Priority 10) | `api.dev.brain.falklabs.de` |
| Control Deck | `dev.brain.falklabs.de` (Priority 1) | `dev.brain.falklabs.de` |
| AXE UI | `axe.dev.brain.falklabs.de` | `axe.dev.brain.falklabs.de` ✅ |

### **STAGE Environment**

| Service | VORHER | NACHHER |
|---------|--------|---------|
| Backend | ❓ (nicht konfiguriert) | `api.stage.brain.falklabs.de` |
| Control Deck | ❓ (nicht konfiguriert) | `stage.brain.falklabs.de` |
| AXE UI | ❓ (nicht konfiguriert) | `axe.stage.brain.falklabs.de` |

### **PROD Environment**

| Service | VORHER | NACHHER |
|---------|--------|---------|
| Backend | ❓ (vermutlich `brain.falklabs.de/api/*`) | `api.brain.falklabs.de` |
| Control Deck | `brain.falklabs.de` | `brain.falklabs.de` ✅ |
| AXE UI | ❓ (vermutlich `axe.brain.falklabs.de`) | `axe.brain.falklabs.de` ✅ |

---

## 🗓️ MIGRATIONS-PHASEN

### **Phase 0: Vorbereitung (24-48h vorher)**

**Dauer:** 2-4 Stunden
**Risiko:** Niedrig

#### Aufgaben:
1. ✅ **DNS TTL reduzieren**
   ```bash
   # Hetzner DNS: TTL auf 300s setzen (5 Minuten)
   # Für alle brain.falklabs.de Records
   # 24h warten bis alte TTL abgelaufen
   ```

2. ✅ **DNS-Einträge für neue Subdomains anlegen**
   ```
   # DEV:
   api.dev.brain.falklabs.de   → A     → SERVER_IP
   docs.dev.brain.falklabs.de  → CNAME → api.dev.brain.falklabs.de

   # STAGE:
   api.stage.brain.falklabs.de   → A     → SERVER_IP
   docs.stage.brain.falklabs.de  → CNAME → api.stage.brain.falklabs.de

   # PROD:
   api.brain.falklabs.de   → A     → SERVER_IP
   docs.brain.falklabs.de  → CNAME → api.brain.falklabs.de
   ```

3. ✅ **DNS Propagation warten**
   ```bash
   # Prüfen bis bereit:
   dig api.dev.brain.falklabs.de
   dig api.stage.brain.falklabs.de
   dig api.brain.falklabs.de

   # Online Tools:
   # https://dnschecker.org
   ```

4. ✅ **Scripts auf Server kopieren**
   ```bash
   # Auf Server (wo Coolify API erreichbar):
   scp coolify_manager.py root@SERVER:/root/brain-migration/
   scp migrate_brain_domains.py root@SERVER:/root/brain-migration/
   scp validate_brain_deployment.py root@SERVER:/root/brain-migration/
   scp rollback_brain_migration.py root@SERVER:/root/brain-migration/

   # Python Dependencies:
   pip install requests
   ```

5. ✅ **Coolify API Token vorbereiten**
   ```bash
   export COOLIFY_TOKEN="1|uSdCef6GSa77y8jU18wEgbwsHqlJRomDofMm33Wgf1aa9227"
   ```

6. ✅ **Wartungsfenster kommunizieren** (PROD)
   - Slack Nachricht
   - Status-Page Update
   - Email an Stakeholder

---

### **Phase 1: DEV Migration (Pilot)**

**Dauer:** 30-60 Minuten
**Risiko:** Niedrig
**Rollback:** Sofort möglich

#### Schritt 1.1: Dry-Run
```bash
cd /root/brain-migration

python3 migrate_brain_domains.py \
  --env dev \
  --dry-run

# Output prüfen:
# - Werden richtige UUIDs gefunden?
# - Sind Domains korrekt?
# - Sind ENV-Vars korrekt?
```

#### Schritt 1.2: Backup erstellen
```bash
python3 migrate_brain_domains.py \
  --env dev \
  --dry-run  # Erstellt Backup auch im Dry-Run

# Backup prüfen:
ls -lh brain_backup_dev_*.json
cat brain_backup_dev_*.json | jq .
```

#### Schritt 1.3: Migration ausführen
```bash
python3 migrate_brain_domains.py \
  --env dev \
  --execute

# Überwachen:
# - Coolify API Responses
# - Traefik Logs (SSL-Zertifikat Generierung)
# - Service Restart/Redeploy Status
```

#### Schritt 1.4: Validierung
```bash
# Sofort nach Migration:
python3 validate_brain_deployment.py --env dev --full

# Erwartetes Ergebnis:
# ✅ ALL CHECKS PASSED
```

#### Schritt 1.5: Manuelle Tests
```bash
# 1. Frontend öffnen
open https://dev.brain.falklabs.de

# 2. Browser Console prüfen (keine Errors)
# 3. API Request testen
curl https://api.dev.brain.falklabs.de/health
curl https://api.dev.brain.falklabs.de/docs

# 4. CORS Test
curl -H "Origin: https://dev.brain.falklabs.de" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     https://api.dev.brain.falklabs.de/api/health \
     -v | grep -i "access-control"
```

#### Schritt 1.6: Beobachtung (15 Minuten)
```bash
# Logs überwachen:
docker logs -f dev-backend
docker logs -f dev-control-deck
docker logs traefik -f | grep dev.brain

# Keine Errors → Success ✅
```

**✅ DEV SUCCESS CRITERIA:**
- [ ] Alle Services erreichbar (HTTPS)
- [ ] SSL-Zertifikate gültig
- [ ] Frontend funktioniert (kann API erreichen)
- [ ] Keine Console Errors
- [ ] Validierungs-Script: 100% Pass

**❌ ROLLBACK (falls Probleme):**
```bash
python3 rollback_brain_migration.py \
  --backup brain_backup_dev_TIMESTAMP.json \
  --execute
```

---

### **Phase 2: STAGE Migration (Pre-Production Test)**

**Dauer:** 30-60 Minuten
**Risiko:** Niedrig
**Warten:** 24h nach DEV (Monitoring)

#### Bedingung:
- ✅ DEV läuft 24h stabil ohne Errors

#### Schritte:
Identisch zu Phase 1, aber mit `--env stage`

```bash
# 1. Dry-Run
python3 migrate_brain_domains.py --env stage --dry-run

# 2. Migration
python3 migrate_brain_domains.py --env stage --execute

# 3. Validierung
python3 validate_brain_deployment.py --env stage --full
```

**✅ STAGE SUCCESS CRITERIA:**
Gleich wie DEV.

---

### **Phase 3: PROD Migration (Production)**

**Dauer:** 60-90 Minuten
**Risiko:** Mittel
**Warten:** 72h nach STAGE (Monitoring)
**Wartungsfenster:** Ja (kommuniziert)

#### Bedingung:
- ✅ DEV läuft stabil (7 Tage)
- ✅ STAGE läuft stabil (3 Tage)
- ✅ Wartungsfenster kommuniziert
- ✅ Rollback-Plan bereit

#### Schritte:

##### 3.1: Wartungsfenster Start
```bash
# Status-Page Update:
# "BRAIN API wird auf neue Infrastruktur migriert.
#  Kurze Unterbrechungen möglich. ETA: 30 Minuten."
```

##### 3.2: Final Backup
```bash
# Zusätzlich zu automatischem Backup:
# Manueller Database Dump
docker exec prod-postgres pg_dump -U brain brain_prod > prod_db_backup.sql

# Docker Volumes sichern
docker run --rm -v brain_pg_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/prod_volumes_backup.tar.gz /data
```

##### 3.3: Migration
```bash
python3 migrate_brain_domains.py --env prod --execute

# Extra Confirmation:
# "Type 'MIGRATE PRODUCTION' to confirm:"
# MIGRATE PRODUCTION
```

##### 3.4: Validierung (erweitert)
```bash
# Automatisch:
python3 validate_brain_deployment.py --env prod --full

# Manuell:
# 1. Frontend öffnen (verschiedene Browser)
# 2. Kritische User Flows testen
# 3. API Endpoints prüfen
# 4. Monitoring Dashboard checken
```

##### 3.5: Smoke Tests
```bash
# Kritische Funktionen:
# - User Login
# - Mission Enqueue
# - Agent Chat
# - Docs erreichbar
```

##### 3.6: Wartungsfenster Ende
```bash
# Status-Page Update:
# "Migration erfolgreich abgeschlossen.
#  Alle Services wieder verfügbar."
```

**✅ PROD SUCCESS CRITERIA:**
- [ ] Alle Services erreichbar
- [ ] Kritische User Flows funktionieren
- [ ] Keine Error-Spikes in Monitoring
- [ ] Validierungs-Script: 100% Pass
- [ ] 1h Betrieb stabil

**❌ ROLLBACK (falls kritische Probleme):**
```bash
# Sofortiger Rollback:
python3 rollback_brain_migration.py \
  --backup brain_backup_prod_TIMESTAMP.json \
  --execute

# Validierung:
python3 validate_brain_deployment.py --env prod

# Status-Page Update:
# "Migration rückgängig gemacht aufgrund technischer Probleme.
#  Services wieder auf alter Infrastruktur."
```

---

## 🔄 POST-MIGRATION

### **Innerhalb 24h:**
1. ✅ **Monitoring**
   - Fehlerrate normal?
   - Response Times normal?
   - SSL-Zertifikate gültig?

2. ✅ **User Feedback sammeln**
   - Slack: Probleme gemeldet?
   - Support Tickets: Mehr Anfragen?

3. ✅ **Logs prüfen**
   ```bash
   # Error Count (sollte gleich bleiben):
   docker logs prod-backend | grep -i error | wc -l
   docker logs prod-control-deck | grep -i error | wc -l
   ```

### **Innerhalb 1 Woche:**
4. ✅ **DNS TTL wieder erhöhen**
   ```bash
   # Hetzner DNS: TTL zurück auf 3600s (1h)
   ```

5. ✅ **Alte DNS-Einträge bereinigen** (falls vorhanden)
   - Nur wenn 100% sicher, dass nicht mehr genutzt

6. ✅ **Post-Mortem Meeting**
   - Was lief gut?
   - Was lief schlecht?
   - Lessons Learned dokumentieren

7. ✅ **Dokumentation aktualisieren**
   - README.md
   - CLAUDE.md (diese Datei)
   - docker-compose Kommentare

---

## 📊 SUCCESS METRICS

### **Technische Metriken:**
| Metrik | Target | Messung |
|--------|--------|---------|
| Uptime während Migration | >99% | Monitoring Dashboard |
| SSL-Zertifikat Fehlerrate | 0% | Traefik Logs |
| CORS-Fehler | 0 | Browser Console / Backend Logs |
| API Response Time Anstieg | <10% | Monitoring (P95) |
| User-reported Issues | <5 | Support Tickets |

### **Business Metriken:**
| Metrik | Target | Messung |
|--------|--------|---------|
| Downtime (PROD) | <5 Min | Manual Tracking |
| User Complaints | <3 | Slack / Support |
| Rollback Rate | 0% | Hoffnung 😅 |

---

## 🚨 ESKALATIONS-PFAD

### **Level 1: Minor Issues (z.B. CORS-Warnung)**
- **Aktion:** Fix forward (ENV-Variable anpassen)
- **Zeit:** 5-10 Minuten
- **Kommunikation:** Intern (Slack)

### **Level 2: Moderate Issues (z.B. SSL-Zertifikat Delay)**
- **Aktion:** Warten / Manuelle Intervention
- **Zeit:** 15-30 Minuten
- **Kommunikation:** Status-Page Update

### **Level 3: Critical Issues (z.B. Service komplett down)**
- **Aktion:** SOFORTIGER ROLLBACK
- **Zeit:** <5 Minuten
- **Kommunikation:** Status-Page + Slack + Email

**Rollback Decision Criteria:**
- Service >5 Min nicht erreichbar → ROLLBACK
- Kritische User Flows brechen → ROLLBACK
- SSL komplett failed → ROLLBACK
- Mehrere unerwartete Errors → ROLLBACK

**Regel:** Im Zweifel → ROLLBACK (besser safe als sorry)

---

## 🛠️ TOOLS & RESOURCES

### **Scripts:**
```bash
# Migration
python3 migrate_brain_domains.py --env {dev|stage|prod} {--dry-run|--execute}

# Validierung
python3 validate_brain_deployment.py --env {dev|stage|prod} [--full]

# Rollback
python3 rollback_brain_migration.py --backup BACKUP_FILE.json {--dry-run|--execute}

# Quick Check
python3 validate_brain_deployment.py --quick
```

### **Monitoring:**
```bash
# Traefik Dashboard
open http://SERVER_IP:8080/dashboard/

# Coolify Dashboard
open https://coolify.falklabs.de

# Logs
docker logs -f traefik
docker logs -f {dev|stage|prod}-backend
docker logs -f {dev|stage|prod}-control-deck
```

### **DNS Tools:**
```bash
# DNS Check
dig api.dev.brain.falklabs.de
nslookup api.dev.brain.falklabs.de 8.8.8.8

# Online
open https://dnschecker.org
open https://whatsmydns.net
```

---

## 📅 TIMELINE (Empfohlen)

| Datum | Aktion | Verantwortlich | Status |
|-------|--------|----------------|--------|
| **Tag -2** | DNS TTL reduzieren | DevOps | ⏳ |
| **Tag -1** | DNS-Einträge anlegen | DevOps | ⏳ |
| **Tag 0** | DEV Migration | DevOps | ⏳ |
| **Tag +1** | DEV Monitoring (24h) | DevOps | ⏳ |
| **Tag +2** | STAGE Migration | DevOps | ⏳ |
| **Tag +5** | STAGE Monitoring (72h) | DevOps | ⏳ |
| **Tag +8** | PROD Migration | DevOps + Team | ⏳ |
| **Tag +9** | PROD Monitoring (24h) | DevOps | ⏳ |
| **Tag +15** | DNS TTL erhöhen | DevOps | ⏳ |
| **Tag +15** | Post-Mortem Meeting | Team | ⏳ |

**Total Duration:** ~2 Wochen (Safe Rollout)

---

## ✅ FINAL CHECKLIST

Vor Start:
- [ ] Alle Dokumentationen gelesen
- [ ] Scripts getestet (dry-run)
- [ ] Coolify API Zugriff verifiziert
- [ ] DNS-Einträge angelegt & propagiert
- [ ] Backups erstellt
- [ ] Wartungsfenster kommuniziert (PROD)
- [ ] Rollback-Plan bereit
- [ ] Team informiert

Nach Abschluss:
- [ ] Alle Services validiert
- [ ] Monitoring normal
- [ ] User Feedback positiv
- [ ] Dokumentation aktualisiert
- [ ] Post-Mortem durchgeführt
- [ ] Lessons Learned dokumentiert

---

## 📞 KONTAKTE

| Rolle | Name | Kontakt | Erreichbarkeit |
|-------|------|---------|----------------|
| DevOps Lead | TBD | Slack / Phone | 24/7 |
| Backend Dev | TBD | Slack | Business Hours |
| Frontend Dev | TBD | Slack | Business Hours |
| Product Owner | TBD | Email | Business Hours |

---

## 📚 REFERENZEN

1. **IST-Zustand:** `BRAIN_IST_ZUSTAND.md`
2. **SOLL-Konzept:** `BRAIN_SOLL_KONZEPT.md`
3. **Risiko-Analyse:** `BRAIN_RISIKO_ANALYSE.md`
4. **Schritt-für-Schritt:** `MIGRATION_CHECKLIST.md`
5. **Coolify API Docs:** https://coolify.io/docs/api
6. **Traefik Docs:** https://doc.traefik.io/traefik/
7. **Let's Encrypt Docs:** https://letsencrypt.org/docs/

---

**Version:** 1.0
**Erstellt:** 2026-01-07
**Erstellt von:** Claude Code
**Status:** ✅ Ready for Execution
**Nächster Schritt:** MIGRATION_CHECKLIST.md verwenden
