# BRAiN Context & Session Readiness Plan (2026-04-01)

Status: In implementation (Slices 1-6 baseline delivered on 2026-04-01)

Audience:
- Dev Agent (autonomous planning + implementation)
- Runtime/Governance owners
- AXE/ControlDeck product operators

## 1) Zielsetzung

BRAiN soll in produktiver Nutzung lange AXE-Sessions stabil, kosteneffizient und governance-konform verarbeiten,
ohne dass Kontextgröße zu unvorhersehbaren Fehlern, Kostenexplosionen oder Qualitätsabfall führt.

Kernziel:
- von "message-count based replay" zu "token-aware, retrieval-backed, governed context management"

Erwartetes Ergebnis:
- reproduzierbare Antwortqualität auch bei langen Threads
- kontrollierte Latenz und Kosten
- klare, auditierbare Regeln für Kontextaufbau

## 2) Warum das notwendig ist

### 2.1 Kontextgröße ist für BRAiN relevant

Im aktuellen Stand sind AXE-Requests auf Zeichen-/Nachrichtenebene begrenzt:
- `MAX_MESSAGE_LENGTH = 10000`
- `MAX_MESSAGES_PER_REQUEST = 100`

Quelle:
- `backend/app/modules/axe_fusion/router.py`

Das ist kein "1M Token Kontextfenster"-Modell, sondern ein Request-Limit.

Praktische Konsequenz:
- lange Sessions bleiben möglich, aber Kontextqualität und Kosten werden ohne zusätzliche Steuerung unzuverlässig.
- Voll- oder Fast-Voll-Replay alter Nachrichten skaliert schlecht.

### 2.2 1M-Token-Frage (Einordnung)

Frage: "Brauchen wir wie Claude 1 Mio Token?"

Antwort für BRAiN:
- nicht als primäre Produktanforderung.
- wichtiger ist kontrollierte Kontextselektion, Kompression und Retrieval.

Warum:
- große rohe Kontexte erhöhen Kosten und Latenz massiv
- erhöhen Drift-/Halluzinationsrisiko durch irrelevante Altinhalte
- reduzieren Vorhersagbarkeit über Provider mit unterschiedlichen effektiven Limits

Damit ist für BRAiN entscheidend:
- token-aware Budgeting pro Turn
- strukturierte Session-Kompression
- relevance-first Retrieval statt blindem Verlauf-Replay

## 3) Architekturprinzipien (BRAiN-spezifisch)

Diese Regeln folgen den bestehenden Design- und Contract-Linien:
- `SkillRun` bleibt kanonischer Ausführungsanker (`DESIGN.md`)
- kein zweites Runtime-/Governance-System
- AXE bleibt Menschenschnittstelle, nicht Kontextwahrheit
- Domain/Routing entscheidet Ausführungspfad, nicht UI-Historie
- Lernpfad bleibt: `experience -> insight -> pattern -> evolution`

## 4) Sollbild: Context Management Layer für AXE/BRAiN

### 4.1 Context Envelope pro Turn

Jeder LLM-Request soll aus klaren Segmenten gebaut werden:
- `system/governance segment`
- `active turn segment` (aktuelle Benutzerintention)
- `short-term session segment` (letzte relevante Turns)
- `retrieved memory/knowledge segment` (selektiv)
- `worker/runtime evidence segment` (falls nötig)

Für jedes Segment werden erfasst:
- geschätzte Tokens
- Priorität
- truncation policy

### 4.2 Budget-Entscheidung vor Provider-Call

Vor jedem Call:
1. Kontext zusammensetzen
2. Token schätzen
3. gegen Modell-/Policy-Budget prüfen
4. bei Überschreitung: geordnet komprimieren oder selektieren

Keine unkontrollierte Oversize-Anfrage.

### 4.3 Session-Kompression als Standard

Wenn Sessiongröße Schwellwerte erreicht:
- ältere Turns in strukturierten Summary-Artefakt überführen
- Summary mit Provenance speichern
- Originalturns nicht als primärer Promptkontext verwenden

## 5) Konkrete Empfehlungen (direkt umsetzbar)

## Empfehlung A - Token-aware Guardrail einführen

Erweitere AXE-Chat-Flow um:
- `estimated_prompt_tokens`
- `max_allowed_prompt_tokens` (modell-/policyabhängig)
- `context_trim_reason`

Muss in Response/Telemetry sichtbar sein.

## Empfehlung B - Session-Tiering

Definiere Session-Kontext-Tiers:
- Tier 1: letzte N Turns (z. B. 6-12)
- Tier 2: komprimierte Session-Summary
- Tier 3: selektive Retrieval-Fakten

Promptaufbau priorisiert Tier 1, nutzt Tier 2/3 nur bei Relevanz.

## Empfehlung C - Relevance Scoring für Verlaufsteile

Nicht "latest only" und nicht "all history", sondern:
- score auf Intent-Overlap, Domäne, offene Aufgaben, Referenzartefakte
- nur Top-K Kontexte in aktiven Prompt

## Empfehlung D - Context Contracts als Artefakte

Pro Request ein strukturiertes Artefakt speichern:
- welche Kontextsegmente verwendet wurden
- welche verworfen/komprimiert wurden
- warum

Das macht Entscheidungen auditierbar und debuggbar.

## Empfehlung E - UI-Transparenz in AXE

In AXE-Chat sichtbar machen:
- Kontextmodus: `full | compacted | retrieval-augmented`
- grobe Tokenklasse: `small | medium | large`
- Hinweis bei automatischer Kompression

## Empfehlung F - Harte Sicherheitsgrenzen

Bei Kontextreduktion niemals entfernen:
- Governance-/Policy-Kernhinweise
- aktive Approval-/Risk-Flags
- tenant-/scope-kritische Constraints

## Empfehlung G - Soak-/Lastprofil aufnehmen

Mindestens drei reproduzierbare Lastprofile:
- lange Session mit 100+ Nachrichten
- attachment-lastige Session
- gemischter Worker-Betrieb parallel

Metriken:
- Erfolgsrate
- median/95p Latenz
- Kosten/Tokens pro Turn
- Kompressionsrate

## 6) Nicht-Ziele (um Scope sauber zu halten)

- kein neuer paralleler Runtime-Stack
- keine globale 1M-Token-Abhängigkeit als Pflicht
- kein unkontrolliertes Persistieren von Chain-of-Thought
- kein Vendor-Lock durch hardcoded model windows

## 7) Mindest-Deliverables für "brauchbar in Produktion"

1. Token-aware Context Builder im AXE-Flow
2. Session-Kompression mit strukturierten Summaries
3. Relevance-gestützte Kontextauswahl
4. Sichtbare Telemetrie (Tokens, Kompression, Kontextmodus)
5. Testmatrix für lange Sessions + parallele Workerläufe

## 8) Done-Kriterien

Als "Context/Session ready" gilt BRAiN erst, wenn:
- kein Oversize-Fehler bei langen realistischen Sessions auftritt
- Antwortqualität bei langen Sessions nicht signifikant degradiert
- Kosten/Tokens pro Turn in definierten Grenzen bleiben
- Kontextentscheidungen nachvollziehbar protokolliert sind
- AXE-Operatoren klar sehen, wann komprimiert/retrieved wurde

## 9) Konkreter Arbeitsauftrag für den Dev Agent

Der Dev Agent soll aus dem aktuellen Repo-Stand einen Umsetzungsplan ableiten mit:

1. Ist-Analyse:
- aktuelle Promptzusammenstellung
- aktuelle Session-Speicherung
- aktuelle Memory/Retrieval-Einbindung

2. Gap-Analyse gegen dieses Dokument:
- was fehlt für A-G

3. Implementierungsslices (klein, testbar):
- Slice 1: Token estimation + telemetry
- Slice 2: Context envelope + tiering
- Slice 3: Session compression summaries
- Slice 4: Relevance scoring + retrieval select
- Slice 5: AXE transparency indicators
- Slice 6: soak tests + acceptance evidence

4. Pro Slice liefern:
- Dateien/Module
- API-/Schemaänderungen
- Testfälle
- Risiko + Rollback
- Done-Kriterium

## 10) Referenzen im aktuellen Repo

- AXE Request limits:
  - `backend/app/modules/axe_fusion/router.py`
- AXE session storage:
  - `backend/app/modules/axe_sessions/models.py`
- AXE contracts/UI:
  - `frontend/axe_ui/lib/contracts.ts`
  - `frontend/axe_ui/app/chat/page.tsx`
- Architecture constraints:
  - `DESIGN.md`
  - `docs/specs/domain_agent_contract.md`
  - `docs/specs/mission_deliberation_insight_evolution.md`

## 11) Fortschritt (2026-04-01)

- Slice 1 umgesetzt: token estimation + response telemetry (`context` block in `/api/axe/chat`).
- Slice 2 umgesetzt: segment-basierter Context Envelope (`governance`, `active`, `short-term`, `retrieval`, `summary`).
- Slice 3 umgesetzt: summary-basierte Kompression fuer lange Sessions.
- Slice 4 umgesetzt: relevance-overlap Top-K retrieval selection.
- Slice 5 umgesetzt: AXE UI zeigt `context_mode`, `token_class`, token budget und trim/compression/retrieval Hinweise.
- Slice 6 umgesetzt: synthetische soak-profile + evidence report unter `docs/roadmap/local_ci/`.
