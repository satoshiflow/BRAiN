# ✅ BRAIN DOMAIN-MIGRATION - AUSFÜHRUNGS-CHECKLISTE

**Version:** 1.0
**Erstellt am:** 2026-01-07
**Zweck:** Schritt-für-Schritt Checkliste für sichere Migration

---

## 🎯 VERWENDUNG DIESER CHECKLISTE

**Anleitung:**
1. Kopiere diese Datei für jede Umgebung (dev/stage/prod)
2. Arbeite die Checkboxen **sequenziell** ab
3. Dokumentiere Abweichungen in `NOTES` Sektion
4. Bei Problemen → siehe `TROUBLESHOOTING`

**Notation:**
- ✅ = Erledigt
- ⏳ = In Arbeit
- ❌ = Fehlgeschlagen
- ⚠️ = Mit Warnung erledigt

---

## 📋 PRE-MIGRATION CHECKLIST (24-48h vorher)

### DNS Vorbereitung

- [ ] **DNS TTL reduzieren**
  ```bash
  # Hetzner DNS Console → brain.falklabs.de Zone
  # Alle A/CNAME Records TTL auf 300s setzen
  # Screenshot machen ✅
  ```
  - Datum/Zeit: __________
  - TTL alt: __________
  - TTL neu: 300s
  - Screenshot: `dns_ttl_before.png`

- [ ] **24h warten** (damit alte TTL ausläuft)
  - Start: __________
  - Ende (24h später): __________

- [ ] **DNS-Einträge für neue Subdomains anlegen**

  **DEV:**
  ```
  api.dev.brain.falklabs.de   → A → 46.224.37.114 (oder Ihre IP)
  ```

  **STAGE:**
  ```
  api.stage.brain.falklabs.de → A → 46.224.37.114
  ```

  **PROD:**
  ```
  api.brain.falklabs.de       → A → 46.224.37.114
  ```

  - [ ] DEV DNS-Eintrag erstellt
  - [ ] STAGE DNS-Eintrag erstellt
  - [ ] PROD DNS-Eintrag erstellt
  - Screenshot: `dns_new_records.png`

- [ ] **DNS Propagation prüfen**
  ```bash
  # Warten bis alle auflösen:
  dig api.dev.brain.falklabs.de
  dig api.stage.brain.falklabs.de
  dig api.brain.falklabs.de

  # Online Tools:
  # https://dnschecker.org
  # https://whatsmydns.net
  ```
  - [ ] DEV aufgelöst
  - [ ] STAGE aufgelöst
  - [ ] PROD aufgelöst
  - Datum/Zeit: __________

---

### Scripts & Tools vorbereiten

- [ ] **Scripts auf Server kopieren**
  ```bash
  # Auf Ihrem lokalen Rechner:
  scp coolify_manager.py root@brain.falklabs.de:/root/brain-migration/
  scp migrate_brain_domains.py root@brain.falklabs.de:/root/brain-migration/
  scp validate_brain_deployment.py root@brain.falklabs.de:/root/brain-migration/
  scp rollback_brain_migration.py root@brain.falklabs.de:/root/brain-migration/
  scp MIGRATION_CHECKLIST.md root@brain.falklabs.de:/root/brain-migration/
  ```
  - [ ] Scripts hochgeladen
  - [ ] Executable-Rechte gesetzt (`chmod +x *.py`)

- [ ] **Python Dependencies installieren**
  ```bash
  ssh root@brain.falklabs.de
  pip install requests
  ```
  - [ ] `requests` installiert

- [ ] **Coolify API Token setzen**
  ```bash
  export COOLIFY_TOKEN="1|uSdCef6GSa77y8jU18wEgbwsHqlJRomDofMm33Wgf1aa9227"
  echo $COOLIFY_TOKEN  # Verifizieren
  ```
  - [ ] Token gesetzt
  - [ ] Token verifiziert

- [ ] **Coolify API Zugriff testen**
  ```bash
  python3 coolify_manager.py list | jq .
  ```
  - [ ] API erreichbar
  - [ ] BRAIN Apps gefunden
  - Output gespeichert: `coolify_apps_before.json`

---

### Kommunikation (nur PROD)

- [ ] **Wartungsfenster kommunizieren**
  - [ ] Slack: #general Channel
  - [ ] Email: Stakeholder
  - [ ] Status-Page: brain-status.falklabs.de (falls vorhanden)

  **Nachricht Template:**
  ```
  📢 Geplante Wartung: BRAIN API Migration

  Zeitpunkt: [DATUM] um [UHRZEIT]
  Dauer: ca. 30-60 Minuten
  Betroffene Services: BRAIN Backend API, Control Deck

  Was passiert:
  - Migration auf neue Subdomain-Architektur
  - Kurze Unterbrechungen möglich (~5 Min)
  - Neue URLs: api.brain.falklabs.de

  Bei Fragen: [KONTAKT]
  ```

  - Datum/Zeit gesendet: __________

---

## 🚀 DEV MIGRATION CHECKLIST

**Environment:** DEV
**Datum:** __________
**Start Zeit:** __________

### Phase 1: Dry-Run

- [ ] **Dry-Run ausführen**
  ```bash
  cd /root/brain-migration
  python3 migrate_brain_domains.py --env dev --dry-run | tee dev_dryrun.log
  ```
  - [ ] Script läuft durch ohne Errors
  - [ ] Richtige UUIDs gefunden (Backend, Control Deck, AXE UI)
  - [ ] Domains korrekt (api.dev.brain.falklabs.de)
  - [ ] ENV-Vars korrekt (CORS_ORIGINS, NEXT_PUBLIC_BRAIN_API_BASE)
  - Log gespeichert: `dev_dryrun.log`

- [ ] **Dry-Run Output reviewen**
  - Backend UUID: __________
  - Control Deck UUID: __________
  - AXE UI UUID: __________
  - Alles korrekt? Ja / Nein

---

### Phase 2: Backup

- [ ] **Automatisches Backup**
  ```bash
  # Wird von migrate_brain_domains.py erstellt
  # Prüfen:
  ls -lh brain_backup_dev_*.json
  ```
  - Backup Datei: __________
  - Datum/Zeit: __________

- [ ] **Backup verifizieren**
  ```bash
  cat brain_backup_dev_*.json | jq . > dev_backup_readable.json
  cat dev_backup_readable.json | grep -i "uuid\|domain\|environment"
  ```
  - [ ] Backup lesbar
  - [ ] Enthält UUIDs
  - [ ] Enthält Domains
  - [ ] Enthält ENV-Vars

---

### Phase 3: Migration Ausführung

- [ ] **Migration starten**
  ```bash
  python3 migrate_brain_domains.py --env dev --execute | tee dev_migration.log
  ```
  - Start Zeit: __________
  - [ ] Backend Domain update → OK
  - [ ] Backend ENV update → OK
  - [ ] Backend Restart → OK
  - [ ] Control Deck Domain update → OK
  - [ ] Control Deck ENV update → OK
  - [ ] Control Deck Redeploy → OK (mit neuen Build Args!)
  - [ ] AXE UI Domain update → OK
  - [ ] AXE UI ENV update → OK
  - [ ] AXE UI Redeploy → OK
  - Ende Zeit: __________
  - Dauer: __________ Minuten
  - Log gespeichert: `dev_migration.log`

---

### Phase 4: Traefik SSL-Zertifikate

- [ ] **Traefik Logs überwachen**
  ```bash
  docker logs traefik -f | grep -i "dev.brain.falklabs.de\|certificate\|acme"
  ```
  - [ ] SSL-Zertifikat für `api.dev.brain.falklabs.de` beantragt
  - [ ] SSL-Zertifikat für `api.dev.brain.falklabs.de` erhalten
  - [ ] SSL-Zertifikat für `dev.brain.falklabs.de` OK
  - [ ] SSL-Zertifikat für `axe.dev.brain.falklabs.de` OK
  - [ ] Keine Errors in Traefik Logs
  - Screenshot: `traefik_ssl_success.png`

---

### Phase 5: Automatische Validierung

- [ ] **Validierungs-Script ausführen**
  ```bash
  python3 validate_brain_deployment.py --env dev --full | tee dev_validation.log
  ```
  - [ ] Backend HTTP: ✅ Pass
  - [ ] Backend SSL: ✅ Pass
  - [ ] Backend CORS: ✅ Pass (oder ⚠️ Warning)
  - [ ] Backend Endpoints: ✅ Pass (/health, /docs, /api/health)
  - [ ] Control Deck HTTP: ✅ Pass
  - [ ] Control Deck SSL: ✅ Pass
  - [ ] AXE UI HTTP: ✅ Pass
  - [ ] AXE UI SSL: ✅ Pass
  - **Summary: ___ / ___ Passed**
  - Log gespeichert: `dev_validation.log`

- [ ] **Validierungs-Fehler beheben (falls vorhanden)**
  - Fehler 1: __________
    - Lösung: __________
  - Fehler 2: __________
    - Lösung: __________

---

### Phase 6: Manuelle Tests

- [ ] **Frontend öffnen**
  ```
  https://dev.brain.falklabs.de
  ```
  - [ ] Seite lädt ohne Errors
  - [ ] SSL-Zertifikat gültig (grünes Schloss)
  - [ ] Keine Console Errors (F12 → Console)
  - [ ] Keine Network Errors (F12 → Network)
  - Screenshot: `dev_frontend_loaded.png`

- [ ] **API Requests prüfen (Browser Console)**
  ```javascript
  // Im Browser Console:
  fetch('https://api.dev.brain.falklabs.de/health')
    .then(r => r.json())
    .then(console.log)
  ```
  - [ ] Request erfolgreich (200 OK)
  - [ ] Response korrekt
  - Screenshot: `dev_api_request.png`

- [ ] **Backend Docs öffnen**
  ```
  https://api.dev.brain.falklabs.de/docs
  ```
  - [ ] Swagger UI lädt
  - [ ] Endpoints sichtbar
  - [ ] SSL-Zertifikat gültig
  - Screenshot: `dev_docs_loaded.png`

- [ ] **CORS Test (curl)**
  ```bash
  curl -H "Origin: https://dev.brain.falklabs.de" \
       -H "Access-Control-Request-Method: GET" \
       -X OPTIONS \
       https://api.dev.brain.falklabs.de/api/health \
       -v 2>&1 | grep -i "access-control"

  # Erwartete Output:
  # < access-control-allow-origin: https://dev.brain.falklabs.de
  ```
  - [ ] CORS Header vorhanden
  - [ ] CORS Header korrekt
  - Output: __________

---

### Phase 7: Service Logs

- [ ] **Backend Logs prüfen**
  ```bash
  docker logs dev-backend --tail 50 | grep -i error
  ```
  - [ ] Keine kritischen Errors
  - Errors (falls vorhanden): __________

- [ ] **Frontend Logs prüfen**
  ```bash
  docker logs dev-control-deck --tail 50 | grep -i error
  ```
  - [ ] Keine kritischen Errors
  - Errors (falls vorhanden): __________

- [ ] **AXE UI Logs prüfen**
  ```bash
  docker logs dev-axe-ui --tail 50 | grep -i error
  ```
  - [ ] Keine kritischen Errors
  - Errors (falls vorhanden): __________

---

### Phase 8: 15-Minuten Beobachtung

- [ ] **Monitoring (15 Min)**
  - Start Zeit: __________
  - Ende Zeit: __________

  **Überwachen:**
  - [ ] Traefik Logs: Keine Errors
  - [ ] Backend Logs: Keine Errors
  - [ ] Frontend Logs: Keine Errors
  - [ ] CPU/Memory normal (docker stats)

  **Notes:**
  - __________

---

### Phase 9: DEV SUCCESS / ROLLBACK Decision

**DECISION:** ✅ SUCCESS / ❌ ROLLBACK

**Wenn SUCCESS:**
- [ ] Alle Checks passed
- [ ] Migration als erfolgreich markiert
- [ ] 24h Monitoring geplant
- Nächster Schritt: STAGE Migration (nach 24h)

**Wenn ROLLBACK:**
- [ ] **Rollback ausführen**
  ```bash
  python3 rollback_brain_migration.py \
    --backup brain_backup_dev_TIMESTAMP.json \
    --execute | tee dev_rollback.log
  ```
- [ ] Validierung nach Rollback
- [ ] Incident dokumentieren
- [ ] Post-Mortem planen

---

## 🟡 STAGE MIGRATION CHECKLIST

**Bedingung:** ✅ DEV läuft 24h stabil

**Environment:** STAGE
**Datum:** __________
**Start Zeit:** __________

### Schritte:
- [ ] Gleiche Schritte wie DEV (siehe oben)
- [ ] Dry-Run: `--env stage`
- [ ] Migration: `--env stage --execute`
- [ ] Validierung: `--env stage --full`

**DEV vs STAGE Unterschiede:**
- Domains: `stage.brain.falklabs.de` statt `dev.brain.falklabs.de`
- UUIDs: Andere App-UUIDs in Coolify

**STAGE SUCCESS:** ✅ / ❌
- Wenn ✅: Warten 72h vor PROD

---

## 🔴 PROD MIGRATION CHECKLIST

**Bedingung:** ✅ DEV + STAGE laufen stabil (7 + 3 Tage)

**Environment:** PROD
**Datum:** __________
**Wartungsfenster:** __________ bis __________

### Extra Steps (nur PROD):

- [ ] **Wartungsfenster Start - Status-Page Update**
  ```
  🔧 Wartung läuft: BRAIN API Migration
  Status: In Progress
  ETA: 30-60 Minuten
  ```
  - Update Zeit: __________

- [ ] **Extra Backup (Database)**
  ```bash
  docker exec prod-postgres pg_dump -U brain brain_prod > prod_db_backup_$(date +%Y%m%d_%H%M%S).sql
  gzip prod_db_backup_*.sql
  ```
  - [ ] Database Dump erstellt
  - Datei: __________
  - Größe: __________

- [ ] **Extra Backup (Docker Volumes)**
  ```bash
  docker run --rm -v brain_pg_data:/data -v $(pwd):/backup \
    alpine tar czf /backup/prod_volumes_backup_$(date +%Y%m%d_%H%M%S).tar.gz /data
  ```
  - [ ] Volume Backup erstellt
  - Datei: __________
  - Größe: __________

### Migration (Gleiche Schritte wie DEV):

- [ ] Dry-Run: `--env prod --dry-run`
- [ ] Backup via Script
- [ ] Migration: `--env prod --execute`
  - **Extra Confirmation:** "Type 'MIGRATE PRODUCTION' to confirm:"
- [ ] Traefik SSL überwachen
- [ ] Validierung: `--env prod --full`
- [ ] Manuelle Tests
- [ ] Smoke Tests (kritische User Flows)

### Extra Tests (nur PROD):

- [ ] **Kritische User Flows testen**
  - [ ] User Login
  - [ ] Mission Enqueue
  - [ ] Agent Chat
  - [ ] API Docs erreichbar
  - [ ] OpenWebUI funktioniert

- [ ] **Verschiedene Browser testen**
  - [ ] Chrome
  - [ ] Firefox
  - [ ] Safari (falls verfügbar)

- [ ] **Monitoring Dashboard prüfen**
  - [ ] Error Rate normal
  - [ ] Response Time normal
  - [ ] Request Count normal

### Wartungsfenster Ende:

- [ ] **Status-Page Update**
  ```
  ✅ Wartung abgeschlossen
  Status: Operational
  Alle Services wieder verfügbar.
  ```
  - Update Zeit: __________

- [ ] **Slack Nachricht**
  ```
  ✅ BRAIN API Migration erfolgreich abgeschlossen.
  Neue URLs:
  - API: https://api.brain.falklabs.de
  - Docs: https://api.brain.falklabs.de/docs

  Bei Problemen bitte melden!
  ```
  - Nachricht gesendet: __________

**PROD SUCCESS:** ✅ / ❌

---

## 📊 POST-MIGRATION (24h nach PROD)

- [ ] **Monitoring Review**
  - [ ] Error Rate: Normal / Erhöht
  - [ ] Response Times: Normal / Langsamer
  - [ ] SSL-Zertifikate: Alle gültig
  - [ ] User Complaints: Anzahl: __________

- [ ] **Logs Review**
  ```bash
  # Error Count (vergleichen mit vor Migration):
  docker logs prod-backend --since 24h | grep -i error | wc -l
  docker logs prod-control-deck --since 24h | grep -i error | wc -l
  ```
  - Backend Errors: __________ (vorher: __________)
  - Frontend Errors: __________ (vorher: __________)
  - Anstieg akzeptabel? Ja / Nein

- [ ] **User Feedback**
  - Slack: __________ Mentions
  - Support Tickets: __________ neue Tickets
  - Allgemeine Stimmung: 😊 / 😐 / 😞

---

## 🔧 POST-MIGRATION CLEANUP (1 Woche nach PROD)

- [ ] **DNS TTL wieder erhöhen**
  ```bash
  # Hetzner DNS: TTL zurück auf 3600s (1h)
  ```
  - Datum: __________
  - Screenshot: `dns_ttl_after.png`

- [ ] **Post-Mortem Meeting**
  - Datum: __________
  - Teilnehmer: __________
  - Lessons Learned dokumentiert: Ja / Nein
  - Dokument: `BRAIN_MIGRATION_POSTMORTEM.md`

- [ ] **Dokumentation aktualisiert**
  - [ ] README.md
  - [ ] CLAUDE.md
  - [ ] docker-compose.yml Kommentare
  - [ ] API Dokumentation

- [ ] **Alte Backups archivieren**
  ```bash
  mkdir -p /backup/brain_migration_2026
  mv brain_backup_*.json /backup/brain_migration_2026/
  mv prod_db_backup_*.sql.gz /backup/brain_migration_2026/
  ```
  - [ ] Backups archiviert
  - Location: __________

---

## 🚨 TROUBLESHOOTING

### Problem: SSL-Zertifikat nicht generiert

**Symptome:**
- Browser: `ERR_SSL_PROTOCOL_ERROR`
- Traefik Logs: Let's Encrypt Fehler

**Lösung:**
```bash
# 1. DNS nochmal prüfen
dig api.dev.brain.falklabs.de

# 2. Traefik neu starten
docker restart traefik

# 3. Warten (bis zu 5 Min)

# 4. Falls weiterhin Problem → Coolify UI:
#    Applications → Backend DEV → Domains → SSL → Force Regenerate
```

---

### Problem: CORS-Fehler

**Symptome:**
- Browser Console: `blocked by CORS policy`

**Lösung:**
```bash
# 1. Backend ENV prüfen
docker exec dev-backend env | grep CORS

# 2. Falls falsch → Coolify UI:
#    Backend DEV → Environment → CORS_ORIGINS → Edit
#    Setze: ["https://dev.brain.falklabs.de","https://axe.dev.brain.falklabs.de"]

# 3. Backend neu starten
docker restart dev-backend

# 4. Test
curl -H "Origin: https://dev.brain.falklabs.de" \
     -X OPTIONS https://api.dev.brain.falklabs.de/api/health -v
```

---

### Problem: Frontend zeigt alte API URL

**Symptome:**
- Network Tab: Requests gehen an falsche URL

**Lösung:**
```bash
# Frontend MUSS rebuildet werden (nicht nur Restart!)

# Via Coolify UI:
# Control Deck DEV → Deploy → Full Redeploy

# Oder via API:
# python3 -c "from coolify_manager import CoolifyClient; ..."
```

---

### Problem: Rollback nötig

**Schritte:**
```bash
# 1. Ruhe bewahren
# 2. Rollback-Script ausführen
python3 rollback_brain_migration.py \
  --backup brain_backup_{env}_TIMESTAMP.json \
  --execute

# 3. Validierung
python3 validate_brain_deployment.py --env {env}

# 4. Incident dokumentieren
# 5. Post-Mortem planen
```

---

## 📝 NOTES & DEVIATIONS

**Abweichungen vom Plan:**
- __________
- __________

**Unerwartete Probleme:**
- __________
- __________

**Lessons Learned:**
- __________
- __________

---

## ✅ FINAL SIGN-OFF

**DEV Migration:**
- [ ] Completed
- Datum: __________
- Signed by: __________

**STAGE Migration:**
- [ ] Completed
- Datum: __________
- Signed by: __________

**PROD Migration:**
- [ ] Completed
- Datum: __________
- Signed by: __________

**Post-Migration:**
- [ ] Completed
- Datum: __________
- Signed by: __________

---

**🎉 MIGRATION ABGESCHLOSSEN!**

**Version:** 1.0
**Erstellt:** 2026-01-07
**Erstellt von:** Claude Code
