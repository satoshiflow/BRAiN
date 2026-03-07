# BRAIN Local Micro Manifest

## Zweck

Dieses Dokument definiert das lokale Minimalprofil von BRAiN für einen kleinen Entwicklungsrechner mit 8 GB RAM.

Ziel ist nicht die vollständige Produktionsausführung, sondern ein tragfähiges, ressourcenschonendes Entwicklungsprofil, das die spätere Produktionsarchitektur vorbereitet.

---

## Leitidee

BRAiN ist das souveräne System.

OpenCode ist nicht das Herz von BRAiN, sondern ein eingebettetes Entwicklungs-, Reparatur- und Heilungsorgan innerhalb des BRAiN-Ökosystems.

OpenCode entwickelt BRAiN, wartet BRAiN, unterstützt Selbstheilung und arbeitet mit Immunsystem und Healthcare zusammen.

---

## Kernprinzipien

1. **BRAiN Core ist die höchste Instanz.**
2. **Agent != LLM != Worker**
3. **OpenCode ist Dev-/Repair-Worker, nicht Systemherrscher**
4. **Lokale Entwicklung darf pragmatisch sein**
5. **Produktionsarchitektur bleibt strikt getrennt**
6. **Entwicklung gegen API-Verträge, nicht gegen konkrete Engines**
7. **LLM-Inferenz ist im Local-Micro-Profil austauschbar und optional**
8. **Self-Healing und Self-Development sind Teil der Zielarchitektur**

---

## Lokales Minimalprofil (Local Micro)

### Lokal aktiv
- PostgreSQL
- Redis
- Qdrant
- BRAiN Core / API
- OpenCode Runtime
- Mock-LLM-Service
- minimales Interface / AXE light

### Lokal nicht verpflichtend
- Ollama
- vLLM lokal
- große Modellserver
- schwere Worker-Farmen
- produktionsnahe Cluster-Topologie

### Später extern
- dedizierter GPU-LLM-Server
- vLLM oder vergleichbarer OpenAI-kompatibler Inference-Server
- externe Worker und zusätzliche Laufzeitumgebungen

---

## Rollenmodell

### DU
Vision, Priorität, Richtung, Freigabe.

### GOTT
Meta-Supervisor für Entwicklung, Heilung und strukturelle Weiterentwicklung von BRAiN.

GOTT arbeitet über OpenCode und koordiniert Dev-/Repair-Arbeit.

### BRAiN Supervisor
System-Supervisor für das eigentliche laufende BRAiN-System.

Er koordiniert Runtime-Aufgaben, Missionen, Ressourcen und Agenten.

### OpenCode
Interne Entwicklungs- und Reparaturruntime von BRAiN.

OpenCode:
- schreibt Code
- refaktoriert
- repariert
- erstellt Patches
- unterstützt Selbstheilung
- arbeitet mit Immunsystem und Healthcare zusammen

### Immunsystem / Healthcare
Erkennen Fehler, bewerten Risiken, stoßen Prüfungen, Isolation oder Recovery an und können OpenCode für Reparaturaufgaben beauftragen.

---

## Architekturregel

Die korrekte Hierarchie lautet:

DU  
↓  
AXE / Interface  
↓  
BRAiN Supervisor  
↓  
Mission / Governance / Memory / Runtime  
↓  
OpenCode Dev- & Repair-Layer

Für Entwicklungsarbeit lokal darf vereinfacht auch gelten:

DU  
↓  
GOTT  
↓  
OpenCode  
↓  
Dev-/Repair-Agenten

Aber diese Vereinfachung ist nur für die lokale Aufbauphase zulässig.

---

## Zielbild

OpenCode verschmilzt funktional mit BRAiN als internes Entwicklungs- und Heilungsorgan.

BRAiN behält jedoch dauerhaft die Hoheit über:
- Identität
- Mission
- Governance
- Memory
- Ressourcensteuerung
- Produktionsfreigaben

---

## Local-Micro-Startziel

Ein lauffähiges lokales BRAiN-Kernsystem mit:

- PostgreSQL
- Redis
- Qdrant
- leichtem Mock-LLM
- OpenCode als Dev-/Repair-Modul
- späterer Umschaltbarkeit auf externen LLM-Server per API

---

## Striktes No-Go

Folgendes darf langfristig nicht passieren:

- OpenCode als oberste Instanz behandeln
- Agentenidentität in OpenCode verlagern
- Modelllogik hart an Ollama oder lokale Sonderwege koppeln
- Produktionsarchitektur vom Dev-Modus ableiten
- ungeprüfte Selbständerung ohne Governance, Ledger und Gesundheitslogik

---

## Arbeitsregel für OpenCode

Wenn OpenCode für BRAiN arbeitet, gilt immer:

- BRAiN Core ist die höchste Instanz
- OpenCode ist Entwickler, Arzt und Reparaturorgan
- Agentenidentität bleibt in BRAiN
- LLM bleibt austauschbar
- Entwicklung erfolgt modular, ressourcenschonend und production-aware

######
