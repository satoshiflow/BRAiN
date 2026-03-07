---
name: brain-local-micro
description: Regeln für den lokalen ressourcenschonenden Aufbau von BRAiN auf einem kleinen Entwicklungsrechner mit integriertem OpenCode-Dev-/Repair-Layer.
---


# brain-local-micro


## Zweck


Diese Skill definiert die Architektur- und Arbeitsregeln für den lokalen Aufbau von BRAiN auf einer kleinen Maschine.


## Grundregeln


1. BRAiN Core ist die höchste Instanz.
2. OpenCode ist nur Dev-, Repair- und Heilungsorgan.
3. Agent != LLM != Worker.
4. Lokale Entwicklung darf pragmatisch sein, aber nicht die Produktionsarchitektur verfälschen.
5. Harte Bindungen an konkrete lokale LLM-Engines vermeiden.
6. Alle Strukturen auf spätere externe API-basierte LLM-Nutzung vorbereiten.
7. Ressourcenverbrauch niedrig halten.
8. Bevorzuge modulare, leichtgewichtige und austauschbare Lösungen.


## Lokales Zielprofil


### Aktiv
- PostgreSQL
- Redis
- Qdrant
- BRAiN Core / API
- OpenCode
- Mock-LLM


### Nicht verpflichtend
- Ollama
- vLLM lokal
- GPU-abhängige Inferenz
- komplexe Cluster


## OpenCode-Rolle


OpenCode ist Teil des BRAiN-Projekts und übernimmt lokal die Rolle eines eingebetteten Entwicklungs- und Heilungssystems.


OpenCode darf:
- Code erstellen
- Refactorings durchführen
- Konfigurationen erzeugen
- Reparaturvorschläge machen
- Health- und Recovery-Flows unterstützen


OpenCode darf nicht:
- BRAiN als höchste Instanz ersetzen
- Agentenidentität übernehmen
- Produktions-Governance umgehen


## Stil


Bevorzuge:
- klare Ordnerstruktur
- kurze README-Dateien
- Healthchecks
- austauschbare ENV-Konfiguration
- geringe Komplexität
- kleine, überprüfbare Schritte


## Bei Architekturentscheidungen


Immer bevorzugen:
- API-Verträge statt Engine-Kopplung
- Adapter statt Direktbindung
- Mocking statt schwerer lokaler Laufzeit
- modulare Dienste statt großer Monolithen


## Bei Unsicherheit


Wähle immer die leichteste Lösung, die:
- modular ist
- auf spätere Produktion vorbereitet
- auf 8 GB RAM tragfähig ist
