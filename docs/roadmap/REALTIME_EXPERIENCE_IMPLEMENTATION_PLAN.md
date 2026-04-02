# Realtime Experience Implementation Plan

Status: Working Plan v0.1  
Owner surface: `backend/app/modules/experience_composer/` + `frontend/controldeck-v3/`

## Ziel

BRAiN soll aus Wissen und Kontext kontrolliert mehrere Experience-Typen erzeugen:
- Chat-Antwort
- Landingpage
- Erklaerseite fuer Kunde X
- mobile Ansicht
- Praesentation

Die Implementierung wird absichtlich in kleine, pruefbare Schritte zerlegt.

## Phase 1: Contracts + Preview MVP

Ziel: Ein erster durchgehender Pfad von Request bis sichtbarer Experience in `ControlDeck v3`.

### 1.1 Backend Contracts

- `InputEnvelope` stabilisieren
- `ExperienceRenderRequest` stabilisieren
- `ExperiencePayload` stabilisieren
- `OutputEnvelope` stabilisieren
- API `POST /api/experiences/render` bereitstellen

Done when:
- Endpoint liefert fuer `chat_answer`, `landingpage`, `mobile_view`, `presentation` gueltige Antworten
- Contracts sind versioniert und dokumentiert

### 1.2 Backend Composition MVP

- `experience_composer` an `knowledge_engine` anbinden
- subject `id` und `query` unterstuetzen
- einfache Fallback-Zusammenfassung ohne Treffer liefern
- erste Section-Typen definieren
- Metadaten fuer Audit und Debugging liefern

Done when:
- semantische Suche fuehrt zu sichtbaren Experience-Daten
- Fallback ohne Wissens-Treffer bleibt benutzbar

### 1.3 Frontend Preview Surface

- `ControlDeck v3` bekommt Route `/experiences`
- Formular fuer Intent, Experience-Typ, Subject und Kontext
- Render-Preview fuer `sections[]`
- Anzeige von Quellen, Warnungen und Cache/Metadaten

Done when:
- Nutzer kann aus Query und Kontext eine erste Experience rendern
- UI zeigt dieselbe Antwort als Web-/Mobile-/Presentation-Variante

## Phase 2: Renderer haerten

Ziel: Von Preview zu kontrollierbarem Render-Standard.

### 2.1 Section Library

- feste Section-Komponenten definieren
- unbekannte Section-Typen sicher abfangen
- Data-Ref-Aufloesung zentralisieren
- visuelle Konsistenz fuer Web/Mobile/Presentation herstellen

### 2.2 Safety + Governance

- Experience-Ausgabe gegen Zielgruppe und Sichtbarkeit pruefen
- sensible Daten vor Public-Ausgaben ausblenden
- Warnings/Constraints in Payload und UI sichtbar machen

### 2.3 Response Quality

- Ranking verbessern
- Quellenhinweise erweitern
- bessere CTA-/Next-Step-Logik
- Varianten fuer Kunde/Partner/Internal sauber trennen

## Phase 3: Sources + Media

Ziel: Interne und externe Quellen sauber in Experiences einbinden.

### 3.1 Source Ingestion vereinheitlichen

- URL-, Text-, Dokument- und Datei-Inputs vereinheitlichen
- Herkunft und Versionierung sichtbar machen
- lokale Dateipfade hinter Storage-Abstraktion bringen

### 3.2 Media Support

- Bilder, PDFs und spaeter Video-Referenzen in Experience-Payloads aufnehmen
- Objekt-Storage statt ad-hoc Filesystem-Ablage
- leichte Vorschau- und Download-Komponenten

### 3.3 Kunden-/Zielgruppen-Kontext

- customer-specific variant handling
- audience-scoped filtering
- persistierbare Saved Experiences nur wenn explizit gewollt

## Phase 4: Realtime + Streaming

Ziel: Nicht nur schnell rendern, sondern auch live aktualisieren.

### 4.1 Progressive Rendering

- schnelle Basissektion sofort liefern
- langsamere Sektionen nachladen
- Streaming einzelner Experience-Segmente pruefen

### 4.2 Event-Anbindung

- Experience-Neurender bei laenger laufenden Agentenjobs
- AXE-/SkillRun-Status als Kontext fuer Experience-Updates nutzen
- optionale SSE- oder WebSocket-Updates fuer Preview-Flows

## Phase 5: Publishing Modes

Ziel: Von Preview zu echten auslieferbaren Experience-Modi.

### 5.1 Temporary Experience

- TTL-gesteuerte Experience-Links
- purge-on-close oder kurzer Cache
- keine dauerhafte Content-Vervielfaeltigung

### 5.2 Persistent Experience

- explizites Speichern einer Experience-Konfiguration
- Rehydrate aus Wissen + Contract, nicht aus statischem HTML
- Versionen und Audit fuer spaetere Wiederverwendung

### 5.3 Share Modes

- partner/public/customer views
- lesende externe Zugriffe spaeter kontrolliert freischalten
- zentrale Runtime-Resolver statt hart kodierter Hosts

## Kleine Tasks fuer den aktuellen MVP

1. Plan dokumentieren.
2. `ControlDeck v3` Route fuer Experience Preview anlegen.
3. Frontend API-Client fuer `/api/experiences/render` anlegen.
4. Einfachen Preview-Renderer fuer bestehende Section-Typen bauen.
5. Navigation erweitern.
6. Lint und Build in `frontend/controldeck-v3` laufen lassen.
7. Backend-Tests und RC-Gate sauber halten.

## Fehlervermeidungsregeln

- nur kleine, additive Slices
- keine freie KI-UI, nur kontrollierte Section-Typen
- unbekannte Komponenten fail-soft rendern
- keine neue parallele Runtime neben `SkillRun`
- keine grosse Storage-Migration mitten im UI-MVP
- zuerst sichtbarer Preview-Flow, dann Härtung, dann Streaming, dann Publishing
