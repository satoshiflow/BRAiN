# ControlDeck v2 - Neu-Konzeptionierung Plan

**Datum:** 29.03.2026
**Status:** Vorschlag zur Diskussion

---

## 1. Aktuelle Probleme

### 1.1 Technische Probleme (Sofort)
- [ ] Build-Fehler: Doppelte Next.js Routes
- [ ] Dependency-Konflikte: better-auth Version
- [ ] Fehlende Auth-Integration

### 1.2 Architektur-Probleme
- [ ] Keine klare Trennung zwischen Operations und Chat
- [ ] Mock-Daten statt echte API-Integration
- [ ] Überladene Feature-Liste ohne Priorisierung

---

## 2. Neue Konzeptionierung

### 2.1 Klare Mission
**ControlDeck** = **Operations & Monitoring Dashboard**
- Überwachung aller BRAiN-Komponenten
- Konfiguration und Administration
- Event- und Incident-Management
- **NICHT**: Chat-Interface (das ist AXE UI)

### 2.2 Kern-Features (MVP)

| Feature | Priorität | Beschreibung |
|---------|-----------|--------------|
| **Dashboard** | P0 | KPIs, System-Status, Alerts |
| **Health** | P0 | Component Health, Uptime |
| **Events** | P0 | Real-time Event Stream |
| **Missions** | P1 | Mission Queue & Status |
| **Settings** | P1 | Provider, Security, Config |
| **Audit** | P2 | Audit Logs |
| **Agents** | P2 | Agent Registry |

### 2.3 NICHT in ControlDeck
- ❌ Chat-Funktionalität (→ AXE UI)
- ❌ Neural Core Dashboard (→ AXE UI)
- ❌ Odoo Settings (→ AXE UI Settings)

---

## 3. Technische Anforderungen

### 3.1 Architektur
```
ControlDeck v2 (neu)
├── UI-Core (shared)
│   ├── Design System
│   └── Common Components
├── Pages
│   ├── /dashboard    → KPIs + Alerts
│   ├── /health       → Component Monitoring
│   ├── /events      → Real-time Stream
│   ├── /missions    → Queue Management
│   ├── /settings    → Configuration
│   └── /audit       → Audit Logs
└── API Client
    └── /api/v1/*
```

### 3.2 Auth-Anforderungen
- JWT-basierte Auth (wie AXE UI)
- Role-based Access Control (Admin, Operator, Viewer)
- Session-Management über Backend

### 3.3 API-Integration

| Endpoint | Verwendung |
|----------|------------|
| `GET /api/health` | Health Check |
| `GET /api/events` | Event Stream |
| `GET /api/missions/*` | Mission Management |
| `GET /api/system/*` | System Status |
| `GET /api/audit/*` | Audit Logs |

---

## 4. Implementierungs-Phasen

### Phase 1: Grundgerüst (1 Woche)
- [ ] Build-Fixes (Routes, Dependencies)
- [ ] Auth-Integration
- [ ] UI-Core aufsetzen

### Phase 2: Core Features (2 Wochen)
- [ ] Dashboard mit echten KPIs
- [ ] Health Monitoring
- [ ] Event Stream

### Phase 3: Operations (2 Wochen)
- [ ] Mission Management
- [ ] Settings Page
- [ ] Audit Logs

### Phase 4: Erweiterungen (1 Woche)
- [ ] Agent Registry
- [ ] Security Panel
- [ ] Intelligence

---

## 5. Design-Prinzipien

1. **Information Density**: Mehr Info pro Pixel, aber lesbar
2. **Real-time First**: WebSocket für Events, nicht Polling
3. **Operational Clarity**: Klare Status-Farben, keine Ambiguität
4. **Security by Default**: RBAC, Audit-Log, kein Frontend-Bypass

---

## 6. Offene Fragen

1. **Separate Domain oder Sub-Path?**
   - Option A: `control.brain.local` (separate Domain)
   - Option B: `brain.local/control` (Sub-Path)

2. **Shared Auth oder Eigenes System?**
   - Empfehlung: Shared JWT, unterschiedliche Rollen

3. **Monorepo oder Getrennt?**
   - Empfehlung: Getrennte Repos für Unabhängigkeit

---

## 7. Ressourcen

### Benötigt für Umsetzung:
- 1x Frontend-Entwickler (React/Next.js)
- 1x Designer (Dashboard-UX)
- 1x Backend-API-Unterstützung

### Geschätzte Zeit:
- MVP: 3-4 Wochen
- V1.0: 6-8 Wochen
