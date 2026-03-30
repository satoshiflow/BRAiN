# ControlDeck v3 - Konzept, Umsetzung und Zukunftsaussichten

**Version:** 1.0  
**Status:** Genehmigt zur Umsetzung  
**Datum:** 29. März 2026  
**Autor:** BRAiN Architecture Team

---

## Inhaltsverzeichnis

1. [Zusammenfassung](#1-zusammenfassung)
2. [Konzept](#2-konzept)
   - 2.1 Vision und Zweck
   - 2.2 Architekturprinzipien
   - 2.3 Klare Abgrenzung zu Business-Anwendungen
   - 2.4 Control Units Übersicht
3. [Technische Grundlagen](#3-technische-grundlagen)
   - 3.1 Technologie-Stack
   - 3.2 Backend-Integration
   - 3.3 Authentifizierung
4. [Umsetzungsplan](#4-umsetzungsplan)
   - 4.1 Phase 0: Fundament (Woche 1)
   - 4.2 Phase 1: Health Monitor (Woche 2)
   - 4.3 Phase 2: Immune Orchestrator (Woche 2-3)
   - 4.4 Phase 3: Neural Core (Woche 3-4)
   - 4.5 Phase 4: Skill Management (Woche 4)
   - 4.6 Phase 5: Desktop-Politur (Woche 5)
5. [Zukunftsaussichten](#5-zukunftsaussichten)
6. [Entscheidungsrahmen](#6-entscheidungsrahmen)
7. [Risiken und Mitigations](#7-risiken-und-mitigations)

---

## 1. Zusammenfassung

**ControlDeck v3** ist die zentrale Governance-Konsole für das BRAiN Operating System. Es ist **ausschließlich** für die Überwachung, Steuerung und Konfiguration von BRAiN-internen Systemen konzipiert und dient als "Human Interface" für operative Entscheidungen am Gehirn selbst.

### Kernprinzipien
- **BRAiN OS Governance Only**: ControlDeck v3 zeigt und steuert NUR BRAiN-interne Systeme
- **Desktop-First**: Optimiert für Desktop-Erfahrung mit Tastatur-Navigation
- **Modular**: Jede Control Unit entspricht einem Backend-Modul
- **Security**: Authentifizierung via JWT (wie AXE UI)
- **Skalierbar**: Einfache Erweiterung um neue Control Units

### Was NICHT in ControlDeck v3 gehört
- Odoo-Daten (Rechnungen, Lagerbestände)
- RenaSecurity Patrouillen-Protokolle
- FeWoHeros Buchungsstatistiken
- Myzelia Produktionsdaten
- SatoshiFlow Transaktionen
- **Diese gehören in separate Business-Anwendungs-UI**

---

## 2. Konzept

### 2.1 Vision und Zweck

ControlDeck v3 ist das "Cockpit" für BRAiN - die zentrale Konsole von der aus:
- Das operative Wohlbefinden von BRAiN überwacht wird (Health)
- Selbstheilungsprozesse beobachtet und gesteuert werden (Immune)
- Die kognitiven Parameter zur Laufzeit justiert werden (Neural Core)
- Skill-Ausführungen überwacht und manuell getriggert werden (Skills)
- Routing-Policies und Autonomie-Einstellungen konfiguriert werden (Governance)

> **Metapher**: BRAiN ist das Gehirn. ControlDeck v3 ist das Diagnose-Cockpit, das仪表brett (Instrumententafel) - nicht die Fernbedienung für die Arme und Beine (Business-Anwendungen).

### 2.2 Architekturprinzipien

Aus AGENTS.md Sections 6 und 6.1 abgeleitet:

| Prinzip | Beschreibung |
|---------|--------------|
| **Modularität** | Jede Control Unit ist unabhängig und spiegelt ein Backend-Modul |
| **Event-getrieben** | Echtzeit-Updates via SSE/WebSocket |
| **Autonomie-respektierend** | Keine Umgehung von BRAiNs Autonomie-Modus |
| **Secure by Design** | JWT-Auth, Role-based Access, Audit-Logging |
| **Desktop-first** | Optimiert für große Bildschirme, Tastatur-Navigation |

### 2.3 Klare Abgrenzung zu Business-Anwendungen

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────┐        ┌──────────────────────────┐ │
│   │   ControlDeck v3    │        │   Business App Insights   │ │
│   │   (BRAiN OS ONLY)   │        │   (Recommendations)       │ │
│   │                     │        │                          │ │
│   │ • Health Monitor   │        │ • Odoo Analytics         │ │
│   │ • Immune Orchestr. │        │ • RenaSecurity Patterns   │ │
│   │ • Neural Core      │        │ • FeWoHeros Optimization │ │
│   │ • Skills           │        │ • Myzelia Predictions    │ │
│   │ • Routing          │        │ • SatoshiFlow Insights   │ │
│   └──────────┬──────────┘        └────────────┬─────────────┘ │
│              │                                  │              │
│              │         ┌────────────────────────┴───────┐      │
│              │         │      BRAiN INTELLIGENCE       │      │
│              │         │   (Neural Core + Skills +     │      │
│              │         │    Mission Deliberation)      │      │
│              │         └────────────────────────┬───────┘      │
│              │                                  │              │
│              │         ┌────────────────────────┴───────┐      │
│              │         │      BACKEND LAYER            │      │
│              │         ├───────────────────────────────┤      │
│              │         │  app/modules/                  │      │
│              │         │  • health_monitor/            │      │
│              │         │  • immune_orchestrator/       │      │
│              │         │  • neural/                    │      │
│              │         │  • skill_engine/              │      │
│              │         │  • domain_agents/             │      │
│              │         │  • odoo_adapter/              │      │
│              └─────────┴───────────────────────────────┘      │
│                                                                 │
│         ┌──────────────────────────────────────────────┐        │
│         │         BUSINESS APPLICATION LAYER          │        │
│         ├──────────────────────────────────────────────┤        │
│         │  Odoo (RenaSecurity, FeWoHeros, Myzelia...)  │        │
│         │  - Transaction Data                          │        │
│         │  - Business Processes                        │        │
│         │  - Native UIs                                │        │
│         └──────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 Control Units Übersicht

| Control Unit | Backend-Modul | Endpunkte | Zweck |
|--------------|---------------|-----------|-------|
| **Health Monitor** | `health_monitor` | `/api/health/*` | Systemüberwachung, Metriken, Trend-Analysen |
| **Immune Orchestrator** | `immune_orchestrator` | `/api/immune/*` | Self-Healing-Events, manuelle Heilungsaktionen |
| **Neural Core** | `neural` | `/api/neural/*` | Laufzeitparameter (Kreativität, Vorsicht, Geschwindigkeit) |
| **Skill Management** | `skill_engine` | `/api/skills/*`, `/api/skill_runs/*` | Skill-Katalog, Ausführungsmonitoring |
| **Routing Governance** | `domain_agents` | `/api/routing/*` | Purpose-Routing, Autonomie-Policies |

---

## 3. Technische Grundlagen

### 3.1 Technologie-Stack

| Komponente | Technologie | Begründung |
|------------|-------------|------------|
| Framework | Next.js 15 (App Router) | Konsistent mit AXE UI |
| Sprache | TypeScript (strict) | Type-Sicherheit |
| UI-Komponenten | shadcn-ui (radix-ui + tailwind) | Konsistent, accessible |
| State Management | TanStack React Query | Server-State, Caching |
| Styling | Tailwind CSS | Schnelle Entwicklung |
| Icons | Lucide React | Konsistent mit AXE UI |
| Testing | Vitest + React Testing Library | Unit-Tests |
| E2E | Playwright | Integration-Tests |

### 3.2 Backend-Integration

Alle API-Aufrufe erfolgen über einen typisierten API-Client:

```typescript
// lib/api/health.ts (Beispielstruktur)
import { api } from '@/lib/api-client';

export interface HealthStatus {
  overall: 'healthy' | 'degraded' | 'critical';
  uptime: number;
  modules: ModuleHealth[];
}

export interface ModuleHealth {
  name: string;
  status: 'up' | 'down' | 'degraded';
  lastCheck: string;
  metrics: Record<string, number>;
}

export const healthApi = {
  getStatus: () => api.get<HealthStatus>('/health'),
  getModules: () => api.get<ModuleHealth[]>('/health/modules'),
  subscribe: () => new EventSource('/api/health/stream'),
};
```

### 3.3 Authentifizierung

JWT-basierte Authentifizierung, identisch mit AXE UI Mustern:

- **Login**: `POST /api/auth/login` → JWT Token
- **Session**: Token gespeichert in httpOnly Cookie
- **Refresh**: Automatisch via Next.js Middleware
- **Logout**: `POST /api/auth/logout` → Cookie gelöscht

---

## 4. Umsetzungsplan

### 4.1 Phase 0: Fundament (Woche 1)

**Ziel**: Laufende Basis-App mit funktionierendem Routing und Auth

| Aufgabe | Beschreibung | geschätzte Zeit |
|---------|--------------|-----------------|
| Projekt-Setup | Next.js 15 + TypeScript + Tailwind + shadcn-ui Initialisierung | 2h |
| Auth-System | JWT-Auth von AXE UI adaptiert | 4h |
| Basis-Layout | Header + Sidebar (shadcn-basiert) | 4h |
| Route-Wrapper | `(protected)` Route Protection | 2h |
| API-Proxy | Backend-API-Proxy einrichten | 4h |
| Docker-Integration | Dockerfile + docker-compose | 2h |

**Deliverables:**
- `frontend/controldeck-v3/` Verzeichnisstruktur
- Funktionsfähiger Login/Logout
- Basis-Layout mit Navigation
- Health-Proxy funktioniert (`curl localhost:3003/api/health` → Backend)

**Definition of Done:**
- `npm run dev` zeigt Dashboard mit Login
- Health-Endpoint zeigt Backend-Daten
- Keine TypeScript-Fehler

### 4.2 Phase 1: Health Monitor (Woche 2)

**Ziel**: Vollständiges Gesundheitsmonitoring

| Aufgabe | Beschreibung |
|---------|--------------|
| Dashboard-Übersicht | Hauptseite mit Systemstatus-Widget |
| Modul-Status-Grid | Alle Backend-Module als Status-Karten |
| Metriken-Diagramme | Reaktionszeit, Fehlerrate, Durchsatz |
| Echtzeit-Updates | SSE-Verbindung für Live-Daten |
| Detailansicht | Klick auf Modul zeigt detaillierte Metriken |

**Deliverables:**
- `/app/(protected)/dashboard/page.tsx`
- `/components/widgets/health/`
- `/lib/api/health.ts`

**Definition of Done:**
- Aktuelle Systemgesicht kann abgelesen werden
- Modul-Ausfälle werden visuell hervorgehoben
- Updates kommen in Echtzeit

### 4.3 Phase 2: Immune Orchestrator (Woche 2-3)

**Ziel**: Self-Healing sichtbar und steuerbar

| Aufgabe | Beschreibung |
|---------|--------------|
| Events-Timeline | Chronologische Liste aller Heilungs-Events |
| Schweregrad-Filter | CRITICAL/WARNING/INFO Toggle |
| Detailansicht | Event-Details: Auslöser, Aktion, Ergebnis |
| Statistik-Panel | Erfolgsrate, MTTR, häufigste Auslöser |
| Manuelle Aktionen | Buttons für Heilungs-Wiederholung/-Überspringen |

**Deliverables:**
- `/app/(protected)/healing/page.tsx`
- `/components/widgets/immune/`
- `/lib/api/immune.ts`

**Definition of Done:**
- Alle Immune-Events sind einsehbar
- Events können nach Schweregrad gefiltert werden
- Statistiken sind korrekt

### 4.4 Phase 3: Neural Core (Woche 3-4)

**Ziel**: Laufzeit-Parametersteuerung

| Aufgabe | Beschreibung |
|---------|--------------|
| Parameter-Editor | Slider für Kreativität, Vorsicht, Geschwindigkeit |
| Zustands-Presets | Buttons für Default, Creative, Fast, Safe |
| Ausführungs-Historie | Letzte Neural-Ausführungen |
| Änderungs-Log | Wer hat wann was geändert |

**Deliverables:**
- `/app/(protected)/neural/page.tsx`
- `/components/widgets/neural/`
- `/lib/api/neural.ts`

**Definition of Done:**
- Parameter können geändert werden
- Änderungen werden im Backend gespeichert
- Presets funktionieren korrekt

### 4.5 Phase 4: Skill Management (Woche 4)

**Ziel**: Skill-Überwachung und -Steuerung

| Aufgabe | Beschreibung |
|---------|--------------|
| Skill-Katalog | Durchsuchbare Skill-Liste mit Beschreibungen |
| Aktive Ausführungen | Laufende SkillRuns mit Fortschritt |
| Ausführungs-Details | Input/Output/Logs pro Run |
| Manuelle Trigger | Formular für Skill-Start |

**Deliverables:**
- `/app/(protected)/skills/page.tsx`
- `/components/widgets/skills/`
- `/lib/api/skills.ts`

**Definition of Done:**
- Alle verfügbaren Skills werden angezeigt
- Laufende Ausführungen sind sichtbar
- Skill kann manuell gestartet werden

### 4.6 Phase 5: Desktop-Politur (Woche 5)

**Ziel**: Produktionsreife Anwendung

| Aufgabe | Beschreibung |
|---------|--------------|
| Tastatur-Navigation | Cmd/Ctrl+K für Quick Actions |
| Dark/Light Mode | System-Präferenz + Toggle |
| Export-Funktionen | Berichte als PDF/CSV |
| Performance | React.memo, useMemo Optimierungen |
| Testing | Unit + E2E Tests |
| Build-Validierung | Docker-Build + Lint + TypeScript |

**Deliverables:**
- `Dockerfile` für Production
- E2E-Tests für kritische Flows
- Dokumentation (README)

**Definition of Done:**
- Anwendung läuft stabil im Docker-Stack
- Lint/Type-Check ohne Fehler
- E2E-Tests bestehen

---

## 5. Zukunftsaussichten

### 5.1 Routing Governance (Phase 6)

- Purpose-Routing Policies anzeigen und editieren
- Autonomie-Modus-Konfiguration (brain_first, human_approval, etc.)
- Domain-Agent-Status-Übersicht

### 5.2 Erweiterte Control Units

Basierend auf neuen Backend-Modulen:
- **Memory/Insight**: Wissensgraph-Visualisierung
- **Mission Control**: Missions-Überwachung und -Steuerung
- **Audit**: Vollständiges Audit-Log aller BRAiN-Aktivitäten

### 5.3 Business App Insights (Separates Projekt)

**NICHT Teil von ControlDeck v3**, sondern eigenständige Anwendung:

| Anwendung | Datenquelle | Insights |
|-----------|-------------|----------|
| RenaSecurity | Odoo Connector | Patrouillen-Optimierung, Incident-Muster |
| FeWoHeros | Odoo Connector | Buchungs-Prognosen, Preis-Optimierung |
| Myzelia | Odoo Connector | Produktions-Empfehlungen, Lager-Optimierung |
| SatoshiFlow | Custom Adapter | Transaktions-Analysen |

Diese werden über BRAiN's Insight-Publikationssystem versorgt und in den jeweiligen Business-Anwendungs-UI angezeigt.

---

## 6. Entscheidungsrahmen

Für zukünftige Feature-Entscheidungen:

### Frage 1: "Governed, überwacht oder konfiguriert dieses Feature ein BRAiN-internes System?"
- **JA** → Kandidaten für ControlDeck v3
- **NEIN** → Siehe Frage 2

### Frage 2: "Wäre dieses Feature sinnvoll, wenn BRAiN von allen Business-Anwendungen getrennt wäre?"
- **JA** → Eventuell ControlDeck v3 (mit Begründung)
- **NEIN** → Business App Insights oder Business-UI

### Frage 3: "Zugriff auf Daten außerhalb von `backend/app/modules/*` erforderlich?"
- **JA** → STOP - Business-Daten, nicht ControlDeck v3
- **NEIN** → Weiter mit Implementierung

---

## 7. Risiken und Mitigations

| Risiko | Wahrscheinlichkeit | Auswirkung | Mitigation |
|--------|-------------------|-------------|------------|
| Scope Creep nach Business-Daten | Hoch | Mittel | Strikte Dokumentation, Entscheidungsrahmen |
| Backend-API-Änderungen | Mittel | Hoch | API-Abstraktionsschicht, Feature-Flags |
| Auth-Komplexität | Niedrig | Hoch | AXE UI Pattern übernehmen, testen |
| UI-Inkonsistenz | Mittel | Mittel | shadcn-ui konsequent nutzen |
| Performance-Probleme | Niedrig | Mittel | Von Anfang an optimieren, React.memo |

---

## Anhang: Dateistruktur (Ziel)

```
frontend/controldeck-v3/
├── src/
│   ├── app/
│   │   ├── (protected)/
│   │   │   ├── dashboard/       # Health Monitor
│   │   │   ├── healing/         # Immune Orchestrator
│   │   │   ├── neural/          # Neural Core
│   │   │   ├── skills/          # Skill Management
│   │   │   └── layout.tsx       # Protected Layout
│   │   ├── api/                 # API Proxy Routes
│   │   │   ├── health/
│   │   │   ├── immune/
│   │   │   ├── neural/
│   │   │   └── skills/
│   │   ├── login/
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── ui/                  # shadcn-Komponenten
│   │   ├── layout/              # Header, Sidebar
│   │   └── widgets/             # Control Unit Widgets
│   │       ├── health/
│   │       ├── immune/
│   │       ├── neural/
│   │       └── skills/
│   ├── lib/
│   │   ├── api/                 # Typisierte API-Clients
│   │   │   ├── client.ts
│   │   │   ├── health.ts
│   │   │   ├── immune.ts
│   │   │   ├── neural.ts
│   │   │   └── skills.ts
│   │   ├── auth/                # Auth-Hilfen
│   │   └── utils.ts
│   └── styles/
│       └── globals.css
├── public/
├── tests/
│   ├── unit/
│   └── e2e/
├── Dockerfile
├── docker-compose.yml
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── README.md
```

---

**Dokument genehmigt für Umsetzung.**  
*Nächste Schritte: Phase 0 - Fundament beginnen*
