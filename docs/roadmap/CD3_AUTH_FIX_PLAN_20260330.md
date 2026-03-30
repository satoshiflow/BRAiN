# ControlDeck v3 Auth Fix Plan
Stand: 2026-03-30

## Zielsetzung

ControlDeck v3 soll lokal und spaeter remote denselben verlaesslichen Login-Grundmechanismus wie AXE UI nutzen, damit sich ein Benutzer erfolgreich anmelden, auf geschuetzten Seiten bleiben und nach Reload weiterhin eingeloggt bleiben kann.

Kurzfristig gilt:
- CD3 nutzt dieselben BRAiN-Backend-Endpunkte wie AXE UI
- keine halbe oder implizite Better-Auth-Nutzung im lokalen Betrieb
- kein fehlerhaftes Routing auf `127.0.0.1:8000` aus dem Container heraus
- Session-Persistenz muss funktionieren

Langfristig gilt:
- Better Auth wird sauber eingefuehrt
- dafuer werden passende Backend-Endpunkte und Contracts bereitgestellt
- lokaler und Hetzner-Betrieb muessen architektonisch deckungsgleich oder bewusst unterschiedlich dokumentiert sein

## Aktueller Befund

### Was funktioniert
- Das BRAiN-Backend laeuft lokal und beantwortet `POST /api/auth/login` erfolgreich.
- Die Zugangsdaten sind nicht das Problem.
- AXE UI funktioniert bereits mit dem aktuellen Auth-Grundansatz.

### Was nicht funktioniert
- ControlDeck v3 scheitert beim Login.
- CD3 versucht Requests auf `http://127.0.0.1:8000` zu routen.
- Innerhalb des Docker-Containers zeigt `127.0.0.1` nicht auf den Backend-Container, sondern auf den Container selbst.
- In den CD3-Build-Artefakten tauchen weiterhin Rewrite-/Proxy-Ziele mit `127.0.0.1:8000` auf.

### Wahrscheinliche Hauptursache
- In CD3 ist die API-Basisaufloesung nicht sauber mit dem Docker-Betrieb abgestimmt.
- Zusaetzlich existieren stale Build-Artefakte oder eine Rewrite-Konfiguration, die weiterhin falsche Ziele einbrennt.
- Es gibt aktuell keine einzige, eindeutige Wahrheit fuer die Auth-Zieladresse.

## Gewuenschter Zielzustand

### Kurzfristiger Zielzustand
ControlDeck v3 verhaelt sich auth-seitig wie AXE UI:
- Login ueber BRAiN-Backend `/api/auth/login`
- User-Aufloesung ueber `/api/auth/me`
- Token-Refresh ueber `/api/auth/refresh`
- Logout ueber `/api/auth/logout`
- Session bleibt nach Reload bestehen
- Protected Routes funktionieren stabil

### Langfristiger Zielzustand
Better Auth wird als eigene Migrationsstufe eingefuehrt:
- dedizierte Better-Auth-Endpunkte im Backend
- definierte Cookie-/Session-Strategie
- optional lokaler Better-Auth-Container, falls fuer Paritaet mit Hetzner noetig
- keine Mischphase mit zwei konkurrierenden Auth-Systemen im laufenden UI

## Leitprinzipien fuer die Umsetzung

- AXE UI ist die Referenz fuer den kurzfristigen Fix.
- Eine Auth-Methode gleichzeitig.
- Eine Quelle der Wahrheit fuer die API-Basis.
- Docker-intern niemals unbewusst `127.0.0.1` fuer Backend-Kommunikation verwenden.
- Rewrites nur dann verwenden, wenn sie nachweislich robuster als direkte Aufrufe sind.
- Build-Artefakte muessen nach jeder Aenderung gegen den Quellstand verifiziert werden.

## Detaillierte Todo

### Phase 1 - Referenz und Ist-Zustand absichern
- AXE UI Auth-Fluss vollstaendig dokumentieren:
  - Login
  - Current User
  - Refresh
  - Logout
  - Token Storage
  - Route Protection
- CD3 Auth-Fluss vollstaendig dokumentieren.
- Beide Fluesse 1:1 vergleichen.
- Alle Abweichungen markieren:
  - API-Basisaufloesung
  - Browser vs. Server-Verhalten
  - Proxy/Rewrites
  - Session-Speicherung
  - Redirect-Logik

### Phase 2 - Zielarchitektur fuer den kurzfristigen Fix festlegen
- Verbindlich festlegen, dass CD3 kurzfristig denselben Auth-Mechanismus wie AXE UI nutzt.
- Better Auth fuer den akuten lokalen Login-Fix explizit ausklammern.
- Festlegen, ob CD3:
  - direkt gegen das Backend spricht
  - oder ueber einen stabilen Next-Proxy spricht
- Bevorzugte Entscheidung:
  - den robusteren AXE-UI-Weg uebernehmen
  - keine Mischform zulassen

### Phase 3 - API-Basis in CD3 bereinigen
- `getApiBase()` pruefen und korrigieren.
- Reihenfolge der Aufloesung verbindlich machen:
  1. explizite Env-Werte
  2. optional origin-relative Pfade
  3. klar definierte Fallbacks
- Fallback `127.0.0.1:8000` nur fuer echten Browser-Lokalbetrieb verwenden.
- Server-/Container-Kontext von Browser-Kontext trennen, falls noetig.
- Sicherstellen, dass `http://backend:8000` im Docker-Netz korrekt genutzt wird.

### Phase 4 - Proxy-/Rewrite-Strategie vereinheitlichen
- `next.config.js` in CD3 pruefen.
- Alte oder falsche Rewrites entfernen.
- Falls Rewrites beibehalten werden:
  - Ziel muss docker-kompatibel sein
  - kein implizites Zurueckfallen auf `127.0.0.1`
- Keine doppelte Logik:
  - nicht gleichzeitig direkte Backend-Calls und unsaubere Rewrites

### Phase 5 - Build-Kette und Artefakte kontrollieren
- Pruefen, warum alte Ziele weiter in `.next` bzw. Standalone-Artefakten landen.
- Sicherstellen, dass env- und rewrite-relevante Werte im finalen Build korrekt sind.
- Verifizieren, dass nach einem sauberen Rebuild keine alten `127.0.0.1:8000`-Verweise mehr in den laufenden Artefakten existieren.
- Docker-Cache- und Container-Reuse als Fehlerquelle ausschliessen.

### Phase 6 - Docker-Lokalbetrieb stabilisieren
- `docker-compose.local.yml` fuer CD3 pruefen:
  - Build Args
  - Runtime Env
  - Netzwerke
  - Service-Namen
- Sicherstellen, dass CD3 und `backend` im selben Netz laufen.
- Sicherstellen, dass CD3 im Container `backend:8000` erreichen kann.
- Sicherstellen, dass kein alter Container oder altes Image weiterverwendet wird.

### Phase 7 - Session-Persistenz und Guards absichern
- Pruefen, wo CD3 Tokens speichert.
- Pruefen, wie Session beim App-Start rekonstruiert wird.
- Pruefen, ob `me` nach Reload korrekt geladen wird.
- Pruefen, ob Refresh-Logik vor Session-Verlust greift.
- Pruefen, ob Protected Routes bei gueltiger Session korrekt offen bleiben.
- Pruefen, ob Logout denselben konsistenten Pfad nutzt.

### Phase 8 - Browser-Validierung
- Login im Browser mit bekannten Credentials testen.
- Direkt danach:
  - Redirect auf geschuetzte Startseite
  - Aufruf weiterer geschuetzter Seiten
  - Reload
  - erneuter Seitenwechsel
- Pruefen, ob irgendwo ein Redirect zurueck auf `/login` faelschlich erfolgt.
- Browser-Netzwerk-Tab gegen erwartete Ziel-URLs gegenpruefen.

### Phase 9 - E2E-Absicherung
- Einen E2E-Test fuer CD3 Login erstellen oder anpassen:
  - Login erfolgreich
  - Dashboard sichtbar
  - Reload behaelt Session
  - Logout funktioniert
  - geschuetzte Seite ohne Login redirectet korrekt
- Test lokal gegen den Docker-Stack ausfuehren.

### Phase 10 - Better-Auth-Migrationsspur vorbereiten
- Dokumentieren, dass Better Auth nicht Teil des kurzfristigen Fixes ist.
- Remote-/Hetzner-Setup analysieren:
  - lief ein separater Better-Auth-Container
  - welche Endpunkte oder Session-Mechaniken wurden genutzt
- Daraus einen separaten Migrationsplan ableiten:
  - Backend-Endpunkte
  - Session-/Cookie-Modell
  - lokaler Better-Auth-Container optional
  - Umstellung ohne Regression in AXE UI und CD3

## Technische Entscheidung fuer jetzt

Kurzfristig verwenden wir im ControlDeck v3 dieselbe Auth-Methode wie im AXE UI und binden CD3 sauber an die bestehenden BRAiN-Backend-Endpunkte an.

Das bedeutet:
- kein erzwungenes Better Auth im lokalen Fix
- keine impliziten Rewrites auf localhost innerhalb des Containers
- stattdessen klare, docker-faehige Zielauflosung

## Definition of Done

Der Fix ist erst fertig, wenn alle folgenden Punkte erfuellt sind:
- Login in CD3 funktioniert lokal im Browser
- Login nutzt die korrekten BRAiN-Backend-Endpunkte
- Nach Reload bleibt der Benutzer eingeloggt
- Geschuetzte Seiten bleiben erreichbar
- Logout funktioniert sauber
- In CD3 laeuft lokal kein Request mehr unbeabsichtigt auf `127.0.0.1:8000`, wenn CD3 im Container laeuft
- Ein E2E-Test deckt den Login-Grundfluss ab
- Better Auth ist als separate Folgearbeit dokumentiert, aber nicht mehr mit dem akuten Fix vermischt

## Reihenfolge der Ausfuehrung

1. AXE UI vs. CD3 Auth-Fluss vergleichen
2. CD3 auf eine einzige Auth-Strategie reduzieren
3. API-Basis-Aufloesung korrigieren
4. Rewrites bereinigen oder entfernen
5. Build-Artefakte und Docker-Rebuild sauber validieren
6. Session-Persistenz pruefen
7. Browser-Test
8. E2E-Test
10. Better-Auth-Folgeplan dokumentieren

## Zusatznotiz

In den letzten Stunden wurde lokal viel gearbeitet, aber es gab keine frischen Commits. Dadurch ist besonders wichtig, Quellcode, Build-Artefakte und laufende Container strikt gegeneinander zu verifizieren, damit keine veralteten Artefakte falsche Rueckschluesse erzeugen.