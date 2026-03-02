# BRAiN Frontend Deployment Analysis

## Problem Statement
- Next.js Dev-Server startet korrekt auf `0.0.0.0:3001`
- Stirbt nach ~30 Sekunden mit SIGKILL
- Ursache vermutlich: Ressourcen-Limit oder Session-Management

## Sicherheitsanalyse: 0.0.0.0 vs 127.0.0.1

### 0.0.0.0 (Alle Interfaces)
```
Bindet an: 127.0.0.1 + alle Netzwerk-Interfaces (eth0, wlan0, etc.)
Erreichbar von: localhost + LAN + WAN (falls Firewall offen)
```
**Risiko:**
- Für lokale Entwicklung: Niedrig (bei aktiver Firewall)
- Im Unternehmensnetzwerk: Mittel (LAN-Rechner können zugreifen)
- Öffentlich: Hoch (falls Port freigegeben)

### 127.0.0.1 (Loopback only)
```
Bindet an: Nur lokale Loopback-Schnittstelle
Erreichbar von: Nur localhost (gleicher Rechner)
```
**Risiko:**
- Minimal - nur lokale Prozesse können verbinden
- **EMPFOHLEN für lokale Entwicklung**

## Optionen-Vergleich

| Option | Sicherheit | Stabilität | Komplexität | Empfehlung |
|--------|-----------|------------|-------------|------------|
| A. `127.0.0.1` | ⭐⭐⭐⭐⭐ | ⚠️ Unbekannt | Niedrig | Testen |
| B. `next build + start` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Niedrig | **GUT** |
| C. Docker | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Mittel | **BEST** |
| D. Systemd/PM2 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Mittel | GUT |

## Empfehlung

### Primary: Option B (Production Build)
**Warum:**
- `next dev` ist für Entwicklung (langsam, Ressourcen-intensiv)
- `next build + next start` ist für Produktion (schnell, stabil)
- Keine externen Abhängigkeiten
- Einfach zu starten

**Implementation:**
```bash
cd /home/oli/dev/brain-v2/frontend/control_deck
npm run build
npm start -- -p 3001 -H 127.0.0.1
```

### Secondary: Option C (Docker)
**Warum:**
- Maximale Stabilität
- Isolation
- Einfaches Management
- Reproduzierbar

**Aber:**
- Höherer Overhead
- Mehr Komplexität
- Wir hatten uns anfangs dagegen entschieden

## Entscheidung

**Empfohlene Vorgehensweise:**

1. **SOFORT:** Option A testen - `127.0.0.1` statt `0.0.0.0`
   - Sicherer
   - Evtl. stabiler (weniger Netzwerk-Overhead)

2. **WENN DAS NICHT GEHT:** Option B (Production Build)
   - Schneller
   - Stabiler
   - Ressourcen-effizienter

3. **FÜR PRODUKTION:** Option C (Docker)
   - Wenn stabile Langzeit-Operation nötig
   - Team-Deployment
   - CI/CD Integration

## Nächste Schritte

Soll ich:
1. Option A testen (`127.0.0.1`)?
2. Option B einrichten (Production Build)?
3. Docker Compose erstellen (Option C)?

---
*Analysis by Fred | 2026-02-12*
