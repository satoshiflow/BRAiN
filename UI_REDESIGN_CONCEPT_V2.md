# BRAiN v2.0 UI Redesign - Complete Architecture (4 UIs)

**Version:** 2.0.0
**Date:** 2026-01-10
**Status:** Design Phase

---

## Executive Summary

BRAiN v2.0 umfasst **4 separate Frontend-Anwendungen** mit unterschiedlichen Zielgruppen und Funktionen:

| UI | Zweck | Zielgruppe | Priorität | Domain |
|----|-------|------------|-----------|--------|
| **Control Deck** | BRAiN Admin & Monitoring | BRAiN-Admins & Entwickler | 🔴 HIGHEST | dev.brain.falklabs.de |
| **AXE UI** | Code-Erstellung & Chat | Alle BRAiN-Nutzer | 🟠 HIGH | dev.brain.falklabs.de/axe |
| **brain_control_ui** | Business Dashboard | Projekt-Nutzer (FeWoHeroes, SatoshiFlow) | 🟡 MEDIUM | projects.brain.falklabs.de |
| **OpenWebUI** | Multi-LLM Chat | Externe/bezahlte Nutzer | 🟢 LOW | chat.falklabs.de |

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Design System (Shared)](#2-design-system-shared)
3. [Control Deck - Admin Panel](#3-control-deck---admin-panel)
4. [AXE UI - Code Creation + CANVAS](#4-axe-ui---code-creation--canvas)
5. [brain_control_ui - Business Dashboard](#5-brain_control_ui---business-dashboard)
6. [OpenWebUI - Multi-LLM Chat](#6-openwebui---multi-llm-chat)
7. [Implementation Roadmap](#7-implementation-roadmap)

---

## 1. Architecture Overview

### 1.1 UI Differenzierung

```
┌────────────────────────────────────────────────────────────────┐
│                        BRAiN v2.0 Ecosystem                     │
└────────────────────────────────────────────────────────────────┘

┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   Control Deck      │  │      AXE UI         │  │  brain_control_ui   │
│                     │  │                     │  │                     │
│ Zielgruppe:         │  │ Zielgruppe:         │  │ Zielgruppe:         │
│ • BRAiN Admins      │  │ • Alle BRAiN Nutzer │  │ • Business User     │
│ • Entwickler        │  │ • Entwickler        │  │ • Projekt-Manager   │
│                     │  │ • Support           │  │ • Kunden            │
│                     │  │                     │  │                     │
│ Zweck:              │  │ Zweck:              │  │ Zweck:              │
│ • System Monitoring │  │ • Code erstellen    │  │ • FeWoHeroes Mgmt   │
│ • Agent Management  │  │ • Chat mit BRAiN    │  │ • SatoshiFlow Mgmt  │
│ • NeuroRail         │  │ • Context-aware     │  │ • Kurs-Verwaltung   │
│ • Settings          │  │   Assistance        │  │ • Business Metrics  │
│ • Telemetry         │  │ • Widget-Integration│  │ • Vorlagen-System   │
│                     │  │                     │  │                     │
│ Port: 3001          │  │ Port: 3002          │  │ Port: 3003          │
│ Path: /             │  │ Path: /axe          │  │ Path: /projects     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘

┌─────────────────────┐
│     OpenWebUI       │
│                     │
│ Zielgruppe:         │
│ • Externe User      │
│ • Bezahlte User     │
│                     │
│ Zweck:              │
│ • Multi-LLM Chat    │
│ • Model Selection   │
│ • API Access        │
│ • Payment/Subs      │
│                     │
│ Port: 8080          │
│ Domain: chat.*      │
└─────────────────────┘
```

### 1.2 Integration Points

```
AXE UI (Floating Widget)
  ↓ Can be embedded in:
  ├─→ FeWoHeroes (Booking System)
  ├─→ SatoshiFlow (Finance Dashboard)
  ├─→ brain_control_ui (Business Dashboard)
  └─→ External Projects (via npm package)

Control Deck
  ↓ Manages:
  ├─→ Agents (CRUD, Lifecycle)
  ├─→ Missions (Queue, Status)
  ├─→ NeuroRail (Trace Explorer, Budget)
  └─→ System Health (Telemetry, Logs)

brain_control_ui
  ↓ Integrates:
  ├─→ AXE UI (embedded widget)
  ├─→ Control Deck (iframe for admin access)
  ├─→ Business Logic (FeWoHeroes, SatoshiFlow)
  └─→ Template System (reusable components)

OpenWebUI
  ↓ Standalone
  ├─→ No direct integration
  ├─→ API-basiert
  └─→ Separate Auth
```

---

## 2. Design System (Shared)

### 2.1 Core Principles

**Design Philosophy:**
- **Mobile-First**: Alle UIs starten mit mobiler Ansicht
- **Overlay/Modal/Canvas**: Keine Seitenwechsel für Einstellungen
- **Modular/Plugin**: Erweiterbar wie Odoo oder WebDev Baukasten
- **Accessibility**: WCAG 2.1 AA Standard (4.5:1 Kontrast)
- **Dark Mode First**: Dark als Standard, Light optional

**UI Patterns (statt Seitenwechsel):**
```
Einstellungen öffnen    → Overlay (rechts slide-in)
Details anzeigen        → Modal (zentriert)
Code bearbeiten         → Canvas (split-screen)
Kontextmenü             → Popover (cursor position)
Benachrichtigungen      → Toast (top-right)
```

### 2.2 Color Palette

**Dark Theme (Standard):**
```css
--background: 222.2 84% 4.9%        /* #020817 - Sehr dunkel */
--foreground: 210 40% 98%           /* #F8FAFC - Fast weiß */

--card: 222.2 84% 4.9%              /* #020817 - Karten-Hintergrund */
--card-foreground: 210 40% 98%     /* #F8FAFC */

--primary: 217.2 91.2% 59.8%        /* #3B82F6 - Blau (Aktionen) */
--primary-foreground: 222.2 47.4% 11.2%  /* #1E293B */

--secondary: 217.2 32.6% 17.5%      /* #1E293B - Sekundär Blau */
--secondary-foreground: 210 40% 98%

--muted: 217.2 32.6% 17.5%          /* #1E293B - Gedämpft */
--muted-foreground: 215 20.2% 65.1% /* #94A3B8 */

--accent: 217.2 32.6% 17.5%         /* #1E293B - Akzent */
--accent-foreground: 210 40% 98%

--destructive: 0 62.8% 30.6%        /* #991B1B - Rot (Fehler) */
--destructive-foreground: 210 40% 98%

--border: 217.2 32.6% 17.5%         /* #1E293B */
--input: 217.2 32.6% 17.5%
--ring: 224.3 76.3% 48%             /* #2563EB - Focus Ring */

--radius: 0.5rem                     /* 8px - Abgerundete Ecken */
```

**Status Colors:**
```css
--success: 142.1 76.2% 36.3%        /* #22C55E - Grün */
--warning: 38 92% 50%               /* #F59E0B - Orange */
--error: 0 84.2% 60.2%              /* #EF4444 - Rot */
--info: 199 89% 48%                 /* #06B6D4 - Cyan */
```

### 2.3 Typography

**Font Stack:**
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
             Roboto, "Helvetica Neue", Arial, sans-serif;
```

**Type Scale:**
```css
--text-xs: 0.75rem     /* 12px */
--text-sm: 0.875rem    /* 14px */
--text-base: 1rem      /* 16px */
--text-lg: 1.125rem    /* 18px */
--text-xl: 1.25rem     /* 20px */
--text-2xl: 1.5rem     /* 24px */
--text-3xl: 1.875rem   /* 30px */
--text-4xl: 2.25rem    /* 36px */
```

### 2.4 Spacing & Layout

**Spacing Scale (Tailwind):**
```css
gap-2  = 0.5rem  (8px)
gap-4  = 1rem    (16px)
gap-6  = 1.5rem  (24px)
gap-8  = 2rem    (32px)

p-2  = 0.5rem  (8px)
p-4  = 1rem    (16px)
p-6  = 1.5rem  (24px)
```

**Breakpoints:**
```css
sm: 640px    /* Mobile landscape */
md: 768px    /* Tablet */
lg: 1024px   /* Desktop */
xl: 1280px   /* Large Desktop */
2xl: 1536px  /* Extra Large */
```

### 2.5 Component Library (shadcn/ui)

**Alle UIs nutzen:**
- Button, Card, Input, Label, Select, Textarea
- Dialog, Sheet, Popover, Tooltip
- Tabs, Accordion, Collapsible
- Badge, Avatar, Separator
- Alert, Toast
- Table, DataTable (TanStack Table)

**Zusätzlich für Control Deck:**
- Command (⌘K Search)
- Skeleton (Loading)
- Progress, Slider
- Calendar, DatePicker

**Zusätzlich für AXE UI:**
- ResizablePanel (split-screen)
- DropdownMenu
- Combobox (Autocomplete)

---

## 3. Control Deck - Admin Panel

### 3.1 Übersicht

**Zweck:** System-Administration und Monitoring von BRAiN selbst
**Nutzer:** BRAiN-Admins, Entwickler
**Status:** ✅ Implementiert (20+ Seiten, 80+ Komponenten)
**Redesign Fokus:** Mobile-first, Dark-Mode-Konsistenz, Overlay-Patterns

### 3.2 Aktuelle Struktur (App Router)

```
app/
├── page.tsx                        # Landing Page
├── dashboard/page.tsx              # Main Dashboard
├── core/
│   ├── agents/page.tsx             # Agent Management
│   ├── agents/[agentId]/page.tsx   # Agent Details
│   └── modules/page.tsx            # Module Registry
├── missions/page.tsx               # Mission Control
├── supervisor/page.tsx             # Supervisor Panel
├── immune/page.tsx                 # Security Dashboard
├── settings/page.tsx               # System Settings
├── neurosis/page.tsx               # Future: NeuroRail UI
└── debug/page.tsx                  # Debug Tools
```

### 3.3 Dashboard Layout (Mobile-First)

**Mobile (<768px):**
```
┌────────────────────────────┐
│ ☰  BRAiN Control Deck   🔔 │  ← Header (sticky)
├────────────────────────────┤
│                            │
│  📊 Active Missions: 8     │  ← Metric Cards
│                            │     (stacked)
├────────────────────────────┤
│  🤖 Running Agents: 14     │
├────────────────────────────┤
│  💾 System Load: 52%       │
├────────────────────────────┤
│                            │
│  [Chart: CPU Usage]        │  ← Charts
│                            │     (full width)
├────────────────────────────┤
│  [Chart: Memory]           │
├────────────────────────────┤
│                            │
│  Recent Activities         │  ← Activity Feed
│  • Mission #123 completed  │
│  • Agent 'coder' started   │
│                            │
└────────────────────────────┘
```

**Desktop (≥1024px):**
```
┌──────────────────────────────────────────────────────────────┐
│ ☰  BRAiN Control Deck                           🔔 👤 ⚙️    │
├────────┬─────────────────────────────────────────────────────┤
│        │  📊 Active     🤖 Running    💾 System    ⚡ Queue  │
│ Menu   │     8 (+2)       14 (4)       52%         3 pending│
│        ├─────────────────────────────────────────────────────┤
│ • Home │                                                     │
│ • Agent│  ┌────────────────┐  ┌────────────────┐           │
│ • Miss.│  │ CPU Usage      │  │ Memory Usage   │           │
│ • Super│  │ [Line Chart]   │  │ [Area Chart]   │           │
│ • Immu.│  │ 12:00 - 18:00  │  │ 12:00 - 18:00  │           │
│ • Neuro│  └────────────────┘  └────────────────┘           │
│        │                                                     │
│ ━━━━━  │  Recent Activities                                │
│ System │  ┌──────────────────────────────────────────┐    │
│ • Logs │  │ ✅ Mission #123 completed (2m ago)       │    │
│ • Metr.│  │ 🚀 Agent 'coder' started (5m ago)        │    │
│ • Setti│  │ ⚠️  Queue capacity at 80% (10m ago)      │    │
│        │  └──────────────────────────────────────────┘    │
└────────┴─────────────────────────────────────────────────────┘
```

### 3.4 Redesign Improvements

**1. Settings als Overlay (statt eigene Seite):**
```typescript
// Vorher: /settings (neue Seite)
// Nachher: Overlay von rechts

<Sheet>
  <SheetTrigger asChild>
    <Button variant="ghost" size="icon">
      <Settings className="h-5 w-5" />
    </Button>
  </SheetTrigger>
  <SheetContent side="right" className="w-[400px] sm:w-[540px]">
    <SheetHeader>
      <SheetTitle>System Settings</SheetTitle>
    </SheetHeader>
    <Tabs defaultValue="general">
      <TabsList>
        <TabsTrigger value="general">General</TabsTrigger>
        <TabsTrigger value="llm">LLM</TabsTrigger>
        <TabsTrigger value="security">Security</TabsTrigger>
      </TabsList>
      <TabsContent value="general">
        {/* Settings Form */}
      </TabsContent>
    </Tabs>
  </SheetContent>
</Sheet>
```

**2. Agent Details als Modal (statt eigene Seite):**
```typescript
// Vorher: /core/agents/[agentId] (neue Seite)
// Nachher: Modal

<Dialog>
  <DialogTrigger asChild>
    <Card className="cursor-pointer hover:border-primary">
      {/* Agent Card */}
    </Card>
  </DialogTrigger>
  <DialogContent className="max-w-3xl">
    <DialogHeader>
      <DialogTitle>Agent: {agent.name}</DialogTitle>
    </DialogHeader>
    <Tabs defaultValue="overview">
      <TabsList>
        <TabsTrigger value="overview">Overview</TabsTrigger>
        <TabsTrigger value="missions">Missions</TabsTrigger>
        <TabsTrigger value="logs">Logs</TabsTrigger>
      </TabsList>
      {/* Tab Content */}
    </Tabs>
  </DialogContent>
</Dialog>
```

**3. ⌘K Command Palette (globale Suche):**
```typescript
// Überall verfügbar mit Cmd+K / Ctrl+K
<Command>
  <CommandInput placeholder="Search agents, missions, settings..." />
  <CommandList>
    <CommandGroup heading="Agents">
      <CommandItem onSelect={() => openAgent('coder')}>
        Coder Agent
      </CommandItem>
    </CommandGroup>
    <CommandGroup heading="Missions">
      <CommandItem onSelect={() => openMission('123')}>
        Mission #123
      </CommandItem>
    </CommandGroup>
    <CommandGroup heading="Actions">
      <CommandItem onSelect={() => openSettings()}>
        Open Settings
      </CommandItem>
    </CommandGroup>
  </CommandList>
</Command>
```

### 3.5 NeuroRail Integration (Future)

**Trace Explorer UI:**
```
┌────────────────────────────────────────────────────────────┐
│ NeuroRail - Trace Explorer                                 │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Mission: m_abc123def456                                   │
│    ↓                                                       │
│  Plan: p_xyz789uvw012  [sequential]                        │
│    ↓                                                       │
│  Job: j_qwe456rty789   [llm_call]  ⏱ 2.3s  ✅ SUCCEEDED │
│    ↓                                                       │
│  Attempt: a_asd123fgh456  [attempt #1]                     │
│                                                            │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Audit Events                                      │    │
│  │ • execution_start   (2024-12-30 23:00:00)         │    │
│  │ • execution_success (2024-12-30 23:00:02)         │    │
│  └──────────────────────────────────────────────────┘    │
│                                                            │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Metrics                                           │    │
│  │ Duration: 2.3s                                    │    │
│  │ Tokens: 1,234                                     │    │
│  │ Cost: $0.0045                                     │    │
│  └──────────────────────────────────────────────────┘    │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 4. AXE UI - Code Creation + CANVAS

### 4.1 Übersicht

**Zweck:** Code erstellen mit BRAiN + Chat für alle Nutzer
**Nutzer:** Entwickler, Support, alle BRAiN-Nutzer
**Besonderheit:** Kann als Floating Widget in andere Apps integriert werden
**Redesign Fokus:** CANVAS Split-Screen (wie Claude Code) + Event-Architektur

### 4.2 AXE Modi

```typescript
export type AxeMode = 'assistant' | 'builder' | 'support' | 'debug';

// assistant: Allgemeine Hilfe, Chat
// builder:   Code-Erstellung, CANVAS aktiv
// support:   Support-Anfragen, Ticket-System
// debug:     Fehler-Analyse, Log-Inspektion
```

### 4.3 Layout States

**1. Minimized (Floating Widget):**
```
                                    ┌─────────┐
                                    │  🤖 AXE │ ← 60x60px
                                    └─────────┘
```

**2. Expanded (Chat Panel):**
```
                         ┌────────────────────┐
                         │ AXE Assistant   ✕ │
                         ├────────────────────┤
                         │                    │
                         │  💬 Chat Messages  │
                         │                    │
                         ├────────────────────┤
                         │  [Input]      [⏎] │
                         └────────────────────┘
                         320x480px
```

**3. Full-Screen CANVAS (Builder Mode):**
```
┌─────────────────────────────────────────────────────────────────┐
│ AXE Builder Mode                                        ✕ 🗗 🗕 │
├──────────────────────────────────┬──────────────────────────────┤
│                                  │                              │
│  💬 Chat & Context               │  📝 CANVAS                   │
│                                  │                              │
│  User: "Create React component  │  ```typescript               │
│         for login form"          │  import React from 'react';  │
│                                  │                              │
│  AXE: "I'll create a login form  │  export function LoginForm() │
│        component with validation.│    const [email, setEmail]   │
│        Review the code →"        │      = useState('');         │
│                                  │                              │
│  [Context Panel]                 │    return (                  │
│  • File: LoginForm.tsx           │      <form>                  │
│  • Dependencies:                 │        <input               │
│    - react                       │          type="email"        │
│    - zod (validation)            │          value={email}       │
│                                  │          onChange={...}      │
│  [Apply] [Reject] [Edit]         │        />                    │
│                                  │      </form>                 │
│                                  │    );                        │
│                                  │  }                           │
│                                  │  ```                         │
│                                  │                              │
│                                  │  [✓ Apply] [✗ Reject]        │
│                                  │                              │
├──────────────────────────────────┴──────────────────────────────┤
│  [Minimize] [Chat History] [Settings]                           │
└─────────────────────────────────────────────────────────────────┘
```

### 4.4 CANVAS Layout (Split-Screen)

**Responsive Breakpoints:**

**Mobile (<768px):** CANVAS nicht verfügbar, nur Chat
**Tablet (768px-1024px):** Tabs (Chat | CANVAS)
**Desktop (>1024px):** Split-Screen 40/60

**Desktop Layout:**
```typescript
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from "@/components/ui/resizable";

<ResizablePanelGroup direction="horizontal">
  {/* Left Panel: Chat */}
  <ResizablePanel defaultSize={40} minSize={30} maxSize={50}>
    <div className="h-full flex flex-col">
      {/* Chat Messages */}
      <ScrollArea className="flex-1 p-4">
        {messages.map(msg => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
      </ScrollArea>

      {/* Context Panel */}
      <div className="border-t p-4">
        <h3 className="text-sm font-semibold mb-2">Context</h3>
        <Badge>File: {currentFile}</Badge>
        <Badge>Mode: {mode}</Badge>
      </div>

      {/* Input */}
      <div className="border-t p-4">
        <Textarea
          placeholder="Describe what you want to build..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <Button onClick={sendMessage}>Send</Button>
      </div>
    </div>
  </ResizablePanel>

  <ResizableHandle />

  {/* Right Panel: CANVAS */}
  <ResizablePanel defaultSize={60} minSize={50}>
    <div className="h-full flex flex-col">
      {/* File Tabs */}
      <Tabs value={activeFile} onValueChange={setActiveFile}>
        <TabsList>
          <TabsTrigger value="LoginForm.tsx">LoginForm.tsx</TabsTrigger>
          <TabsTrigger value="schema.ts">schema.ts</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Code Editor */}
      <div className="flex-1 relative">
        <CodeEditor
          language="typescript"
          value={code}
          onChange={setCode}
          theme="vs-dark"
        />

        {/* Diff Overlay (wenn AXE Änderungen vorschlägt) */}
        {hasPendingChanges && (
          <div className="absolute top-0 right-0 m-4 flex gap-2">
            <Button onClick={applyChanges} variant="default">
              ✓ Apply Changes
            </Button>
            <Button onClick={rejectChanges} variant="destructive">
              ✗ Reject
            </Button>
          </div>
        )}
      </div>
    </div>
  </ResizablePanel>
</ResizablePanelGroup>
```

### 4.5 Event Architecture

**Event Types:**
```typescript
export type AxeEventType =
  | 'axe_message'          // User sendet Nachricht
  | 'axe_feedback'         // User gibt Feedback (👍👎)
  | 'axe_click'            // User klickt Button/Link
  | 'axe_context_snapshot' // AXE nimmt Context-Snapshot
  | 'axe_error';           // Fehler tritt auf

export interface AxeEventBase {
  event_id: string;        // uuid
  event_type: AxeEventType;
  timestamp: string;       // ISO 8601
  app_id: string;          // "fewoheros" | "satoshiflow" | "brain_control"
  user_id?: string;        // Optional (wenn angemeldet)
  session_id: string;      // Browser session
  mode: AxeMode;           // 'assistant' | 'builder' | 'support' | 'debug'
  client?: AxeClientContext;
}

export interface AxeClientContext {
  user_agent: string;
  screen_width: number;
  screen_height: number;
  locale: string;
  timezone: string;
}

// Beispiel Event: User sendet Nachricht
export interface AxeMessageEvent extends AxeEventBase {
  event_type: 'axe_message';
  payload: {
    message: string;
    context?: Record<string, any>;
    training_enabled: boolean;
    anonymization_level: AxeAnonymizationLevel;
  };
}
```

**Event Flow:**
```
User Action (z.B. Chat-Nachricht)
  ↓
Frontend: onSendMessage()
  ↓
Create AxeMessageEvent
  ↓
if (telemetry.enabled && training_mode !== 'off')
  ↓
  Anonymize (based on anonymization_level)
  ↓
  Send to Backend: POST /api/axe/events
  ↓
  Backend: Store in PostgreSQL (axe_events table)
  ↓
  Optional: Train model (if training_mode === 'global' or 'per_app')
```

### 4.6 Privacy & Telemetry Configuration

**UI für Privacy Settings (Overlay):**
```typescript
<Sheet>
  <SheetTrigger>
    <Button variant="ghost">Privacy Settings</Button>
  </SheetTrigger>
  <SheetContent>
    <SheetHeader>
      <SheetTitle>AXE Privacy & Telemetry</SheetTitle>
    </SheetHeader>

    {/* Training Mode */}
    <div className="space-y-4">
      <Label>Training Mode</Label>
      <Select value={trainingMode} onValueChange={setTrainingMode}>
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="global">
            Global Training (hilft allen Nutzern)
          </SelectItem>
          <SelectItem value="per_app">
            App-spezifisch (nur für diese App)
          </SelectItem>
          <SelectItem value="off">
            Aus (kein Training)
          </SelectItem>
        </SelectContent>
      </Select>

      {/* Anonymization Level */}
      <Label>Anonymization Level</Label>
      <Select value={anonymizationLevel} onValueChange={setAnonymizationLevel}>
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="none">
            None (volle Daten für bestes Training)
          </SelectItem>
          <SelectItem value="pseudonymized">
            Pseudonymized (IDs ersetzt, Patterns erhalten)
          </SelectItem>
          <SelectItem value="strict">
            Strict (alle PII entfernt)
          </SelectItem>
        </SelectContent>
      </Select>

      {/* Telemetry Toggle */}
      <div className="flex items-center justify-between">
        <Label>Telemetry Enabled</Label>
        <Switch checked={telemetryEnabled} onCheckedChange={setTelemetryEnabled} />
      </div>
    </div>
  </SheetContent>
</Sheet>
```

**Anonymization Logic:**
```typescript
function anonymizeEvent(
  event: AxeEvent,
  level: AxeAnonymizationLevel
): AxeEvent {
  if (level === 'none') return event;

  const anonymized = { ...event };

  if (level === 'pseudonymized') {
    // Ersetze user_id mit Hash
    if (anonymized.user_id) {
      anonymized.user_id = hashUserId(anonymized.user_id);
    }

    // Ersetze Email-Adressen im Payload
    if (anonymized.payload?.message) {
      anonymized.payload.message = anonymized.payload.message
        .replace(/\b[\w.-]+@[\w.-]+\.\w+\b/g, 'user@example.com');
    }
  }

  if (level === 'strict') {
    // Entferne alle PII
    delete anonymized.user_id;
    delete anonymized.client?.user_agent;

    // Entferne PII aus Nachricht
    if (anonymized.payload?.message) {
      anonymized.payload.message = removePII(anonymized.payload.message);
    }
  }

  return anonymized;
}
```

### 4.7 Floating Widget Integration (npm package)

**Installation in externe Projekte:**
```bash
npm install @brain/axe-widget
```

**Usage:**
```typescript
import { FloatingAxe } from '@brain/axe-widget';

function App() {
  return (
    <>
      {/* Your app content */}
      <div>
        <h1>My Application</h1>
      </div>

      {/* AXE Widget */}
      <FloatingAxe
        appId="fewoheros"
        backendUrl="https://dev.brain.falklabs.de"
        mode="assistant"
        theme="dark"
        position={{ bottom: 20, right: 20 }}
        defaultOpen={false}
        locale="de"
        userId={currentUser?.id}
        sessionId={sessionId}
        extraContext={{
          currentPage: 'booking',
          bookingId: '12345'
        }}
        onEvent={(event) => console.log('AXE Event:', event)}
      />
    </>
  );
}
```

---

## 5. brain_control_ui - Business Dashboard

### 5.1 Übersicht

**Zweck:** Business Dashboard für Projekt-Management (FeWoHeroes, SatoshiFlow, Kurse)
**Nutzer:** Business-User, Projekt-Manager, Kunden
**Status:** ⚠️ Existiert, aber braucht **komplettes Redesign**
**Redesign Fokus:** Modular/Plugin-System (wie Odoo), Vorlagen-System, moderne Business-UI

### 5.2 Modulare Architektur (Plugin-System)

**Inspiriert von Odoo:**
```
brain_control_ui/
├── core/                           # Core System
│   ├── plugin-loader/              # Plugin-Loader
│   ├── routing/                    # Dynamisches Routing
│   ├── auth/                       # Authentication
│   └── theme/                      # Theme System
│
├── plugins/                        # ✨ Plugins (modular)
│   ├── fewoheros/                  # FeWoHeroes Plugin
│   │   ├── manifest.json           # Plugin-Metadata
│   │   ├── routes.tsx              # Plugin-Routes
│   │   ├── components/             # Plugin-Komponenten
│   │   ├── api/                    # Plugin-API-Calls
│   │   └── i18n/                   # Übersetzungen
│   │
│   ├── satoshiflow/                # SatoshiFlow Plugin
│   │   ├── manifest.json
│   │   ├── routes.tsx
│   │   ├── components/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Transactions.tsx
│   │   │   └── Charts.tsx
│   │   └── api/
│   │
│   ├── courses/                    # Kurs-Verwaltung Plugin
│   │   ├── manifest.json
│   │   ├── routes.tsx
│   │   ├── components/
│   │   │   ├── CourseList.tsx
│   │   │   ├── CourseEditor.tsx
│   │   │   └── StudentManagement.tsx
│   │   └── api/
│   │
│   └── analytics/                  # Analytics Plugin
│       ├── manifest.json
│       └── ...
│
└── templates/                      # ✨ Vorlagen-System
    ├── booking-system/             # Vorlage: Buchungssystem
    ├── finance-dashboard/          # Vorlage: Finanz-Dashboard
    └── content-management/         # Vorlage: CMS
```

### 5.3 Plugin Manifest

```json
// plugins/fewoheros/manifest.json
{
  "id": "fewoheros",
  "name": "FeWoHeroes Booking System",
  "version": "1.0.0",
  "description": "Ferienwohnung Buchungssystem mit Kalender und Gäste-Management",
  "author": "BRAiN Team",
  "icon": "🏡",
  "category": "business",

  "routes": [
    {
      "path": "/fewoheros",
      "component": "Dashboard",
      "label": "Dashboard",
      "icon": "LayoutDashboard"
    },
    {
      "path": "/fewoheros/properties",
      "component": "Properties",
      "label": "Properties",
      "icon": "Building"
    },
    {
      "path": "/fewoheros/bookings",
      "component": "Bookings",
      "label": "Bookings",
      "icon": "Calendar"
    }
  ],

  "permissions": ["read:bookings", "write:bookings", "manage:properties"],

  "dependencies": ["@brain/calendar", "@brain/payment"],

  "settings": [
    {
      "key": "booking_email_notifications",
      "label": "Email Notifications",
      "type": "boolean",
      "default": true
    },
    {
      "key": "booking_advance_days",
      "label": "Advance Booking Days",
      "type": "number",
      "default": 90
    }
  ]
}
```

### 5.4 Dashboard Layout (Modular)

**Desktop Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│ ⚡ BRAiN Business      [🔍 Search]           🔔 👤 ⚙️          │
├──────────┬──────────────────────────────────────────────────────┤
│          │                                                      │
│ 🏠 Home  │  ┌─────────────────────────────────────────────┐   │
│          │  │ Quick Actions                                │   │
│ Projects │  │ [+ New Booking] [+ New Property] [Report]    │   │
│ • FeWo.. │  └─────────────────────────────────────────────┘   │
│ • Satosh.│                                                      │
│ • Courses│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│          │  │ Revenue  │ │ Bookings │ │ Occupancy│           │
│ ━━━━━━━  │  │ 45.2K €  │ │ +32 new  │ │ 78%      │           │
│ Tools    │  │ +12%     │ │ ━━━━━    │ │ ▲ 5%     │           │
│ • Analyt.│  └──────────┘ └──────────┘ └──────────┘           │
│ • Reports│                                                      │
│ • AXE    │  ┌─────────────────────────────────────────────┐   │
│          │  │ Recent Bookings                              │   │
│ ━━━━━━━  │  │ • #1234 - Munich Apartment (€120/night)     │   │
│ Settings │  │ • #1235 - Berlin Studio (€85/night)         │   │
│          │  │ • #1236 - Hamburg Loft (€150/night)         │   │
│          │  └─────────────────────────────────────────────┘   │
│          │                                                      │
│          │  [+ Install New Plugin]                             │
│          │                                                      │
└──────────┴──────────────────────────────────────────────────────┘
```

### 5.5 Plugin Installation Flow

**Plugin Store (Modal):**
```typescript
<Dialog>
  <DialogTrigger asChild>
    <Button>+ Install Plugin</Button>
  </DialogTrigger>
  <DialogContent className="max-w-4xl">
    <DialogHeader>
      <DialogTitle>Plugin Store</DialogTitle>
    </DialogHeader>

    <div className="grid grid-cols-3 gap-4">
      {/* Plugin Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <span className="text-2xl">📊</span>
            <CardTitle>Analytics Pro</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Advanced analytics dashboard with custom reports
          </p>
          <Badge variant="secondary" className="mt-2">Business</Badge>
        </CardContent>
        <CardFooter>
          <Button onClick={() => installPlugin('analytics-pro')}>
            Install
          </Button>
        </CardFooter>
      </Card>

      {/* More plugins... */}
    </div>
  </DialogContent>
</Dialog>
```

**Installation Process:**
```typescript
async function installPlugin(pluginId: string) {
  // 1. Download plugin
  const plugin = await fetchPlugin(pluginId);

  // 2. Verify manifest
  if (!validateManifest(plugin.manifest)) {
    throw new Error('Invalid plugin manifest');
  }

  // 3. Check permissions
  if (!hasRequiredPermissions(plugin.manifest.permissions)) {
    throw new Error('Missing permissions');
  }

  // 4. Install dependencies
  await installDependencies(plugin.manifest.dependencies);

  // 5. Register routes
  registerPluginRoutes(plugin.manifest.routes);

  // 6. Initialize plugin
  await plugin.onInstall();

  // 7. Reload app
  window.location.reload();
}
```

### 5.6 Vorlagen-System (Templates)

**Template Selection (Onboarding):**
```
┌────────────────────────────────────────────────────────────┐
│ Welcome to BRAiN Business! Choose a template to start:    │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ 🏠 Booking   │  │ 💰 Finance   │  │ 📚 Content   │   │
│  │ System       │  │ Dashboard    │  │ Management   │   │
│  │              │  │              │  │              │   │
│  │ • Calendar   │  │ • Invoices   │  │ • CMS        │   │
│  │ • Properties │  │ • Reports    │  │ • Blog       │   │
│  │ • Guests     │  │ • Analytics  │  │ • Media      │   │
│  │              │  │              │  │              │   │
│  │ [Use This]   │  │ [Use This]   │  │ [Use This]   │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                            │
│  [Start from Scratch]                                      │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Template Application:**
```typescript
async function applyTemplate(templateId: string) {
  const template = templates[templateId];

  // 1. Install required plugins
  for (const plugin of template.plugins) {
    await installPlugin(plugin);
  }

  // 2. Create default data
  await seedDatabase(template.seedData);

  // 3. Apply theme
  applyTheme(template.theme);

  // 4. Set default settings
  updateSettings(template.settings);

  // 5. Navigate to dashboard
  router.push(template.defaultRoute);
}
```

### 5.7 FeWoHeroes Plugin (Beispiel)

**Dashboard:**
```typescript
// plugins/fewoheros/components/Dashboard.tsx

export function FeWoHeroesDashboard() {
  const { data: stats } = useFewoStats();
  const { data: recentBookings } = useRecentBookings({ limit: 5 });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">FeWoHeroes Dashboard</h1>
        <div className="flex gap-2">
          <Button onClick={() => openNewBookingModal()}>
            + New Booking
          </Button>
          <Button variant="outline" onClick={() => openReportModal()}>
            📊 Report
          </Button>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard
          title="Total Revenue"
          value={formatCurrency(stats.totalRevenue)}
          change={stats.revenueChange}
          icon={DollarSign}
        />
        <MetricCard
          title="Active Bookings"
          value={stats.activeBookings}
          change={stats.bookingsChange}
          icon={Calendar}
        />
        <MetricCard
          title="Properties"
          value={stats.totalProperties}
          change={stats.propertiesChange}
          icon={Building}
        />
        <MetricCard
          title="Occupancy Rate"
          value={`${stats.occupancyRate}%`}
          change={stats.occupancyChange}
          icon={TrendingUp}
        />
      </div>

      {/* Recent Bookings */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Bookings</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Booking ID</TableHead>
                <TableHead>Property</TableHead>
                <TableHead>Guest</TableHead>
                <TableHead>Check-in</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentBookings?.map(booking => (
                <TableRow key={booking.id}>
                  <TableCell>#{booking.id}</TableCell>
                  <TableCell>{booking.property.name}</TableCell>
                  <TableCell>{booking.guest.name}</TableCell>
                  <TableCell>{formatDate(booking.checkIn)}</TableCell>
                  <TableCell>
                    <Badge variant={getStatusVariant(booking.status)}>
                      {booking.status}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* AXE Widget Integration */}
      <FloatingAxe
        appId="fewoheros"
        mode="assistant"
        extraContext={{
          currentPage: 'dashboard',
          activeBookings: stats.activeBookings
        }}
      />
    </div>
  );
}
```

---

## 6. OpenWebUI - Multi-LLM Chat

### 6.1 Übersicht

**Zweck:** Multi-LLM Chat für externe/bezahlte Nutzer
**Nutzer:** Externe User (nicht BRAiN-Nutzer)
**Status:** ❌ Derzeit deaktiviert (https://chat.falklabs.de/)
**Deployment:** Eigener Container, separate Auth

### 6.2 Integration Strategy

**OpenWebUI als Eigenständiger Service:**
```yaml
# docker-compose.yml
services:
  openwebui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: openwebui
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - openwebui_data:/app/backend/data
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OLLAMA_BASE_URL=http://ollama:11434
      - WEBUI_AUTH=true
      - WEBUI_SECRET_KEY=${OPENWEBUI_SECRET_KEY}
    restart: unless-stopped
    networks:
      - brain_internal
```

**Nginx Reverse Proxy:**
```nginx
# /etc/nginx/conf.d/chat.brain.conf
server {
    listen 443 ssl http2;
    server_name chat.falklabs.de;

    ssl_certificate /etc/letsencrypt/live/chat.falklabs.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chat.falklabs.de/privkey.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket Support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 6.3 Payment Integration (Future)

**Subscription Tiers:**
```typescript
export interface SubscriptionTier {
  id: string;
  name: string;
  price: number;
  currency: string;
  features: {
    models: string[];              // ['gpt-4', 'claude-3-opus', 'llama3.2']
    requests_per_day: number;      // 100, 1000, unlimited
    context_length: number;        // 4k, 8k, 32k tokens
    priority_support: boolean;
    custom_branding: boolean;
  };
}

const tiers: SubscriptionTier[] = [
  {
    id: 'free',
    name: 'Free',
    price: 0,
    currency: 'EUR',
    features: {
      models: ['llama3.2'],
      requests_per_day: 20,
      context_length: 4096,
      priority_support: false,
      custom_branding: false
    }
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 19.99,
    currency: 'EUR',
    features: {
      models: ['gpt-4', 'claude-3-opus', 'llama3.2'],
      requests_per_day: 1000,
      context_length: 32768,
      priority_support: true,
      custom_branding: false
    }
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 99.99,
    currency: 'EUR',
    features: {
      models: ['all'],
      requests_per_day: -1, // unlimited
      context_length: 128000,
      priority_support: true,
      custom_branding: true
    }
  }
];
```

**Stripe Integration:**
```typescript
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

async function createCheckoutSession(userId: string, tierId: string) {
  const tier = tiers.find(t => t.id === tierId);
  if (!tier) throw new Error('Invalid tier');

  const session = await stripe.checkout.sessions.create({
    customer_email: user.email,
    payment_method_types: ['card'],
    line_items: [
      {
        price_data: {
          currency: tier.currency.toLowerCase(),
          product_data: {
            name: `OpenWebUI ${tier.name}`,
            description: `Access to ${tier.features.models.length} models`
          },
          unit_amount: tier.price * 100, // cents
          recurring: {
            interval: 'month'
          }
        },
        quantity: 1
      }
    ],
    mode: 'subscription',
    success_url: `https://chat.falklabs.de/payment/success?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `https://chat.falklabs.de/payment/cancel`
  });

  return session.url;
}
```

### 6.4 Custom Branding (Enterprise)

**White-Label UI:**
```typescript
// Enterprise customers can customize:
interface CustomBranding {
  logo: string;          // URL to custom logo
  primary_color: string; // #3B82F6
  company_name: string;  // "ACME Corp AI Assistant"
  favicon: string;       // URL to favicon
  support_email: string; // support@acme.com
  terms_url: string;     // https://acme.com/terms
  privacy_url: string;   // https://acme.com/privacy
}

// Applied at runtime via CSS variables
function applyBranding(branding: CustomBranding) {
  document.documentElement.style.setProperty('--primary', branding.primary_color);
  document.title = branding.company_name;
  // Update logo, favicon, etc.
}
```

---

## 7. Implementation Roadmap

### 7.1 Priority Order

**Phase 1: Control Deck Improvements** (2 Wochen)
- ✅ Basis bereits implementiert
- 🔄 Settings als Overlay (Sheet)
- 🔄 Agent Details als Modal (Dialog)
- 🔄 ⌘K Command Palette
- 🔄 Mobile-First Responsiveness
- ⏳ NeuroRail Trace Explorer UI (future)

**Phase 2: AXE UI mit CANVAS** (3 Wochen)
- 🔄 CANVAS Split-Screen Layout (ResizablePanel)
- 🔄 Code Editor Integration (Monaco/CodeMirror)
- 🔄 Apply/Reject Workflow
- 🔄 Event Architecture Implementation
- 🔄 Privacy Settings UI
- 🔄 Floating Widget npm Package

**Phase 3: brain_control_ui Redesign** (4 Wochen)
- ⏳ Plugin-Loader System
- ⏳ Dynamic Routing
- ⏳ Plugin Store UI
- ⏳ Template System
- ⏳ FeWoHeroes Plugin Migration
- ⏳ SatoshiFlow Plugin Migration
- ⏳ Courses Plugin

**Phase 4: OpenWebUI Integration** (1 Woche)
- ⏳ Docker Container Setup
- ⏳ Nginx Reverse Proxy
- ⏳ SSL Certificate (chat.falklabs.de)
- ⏳ Payment Integration (Stripe)
- ⏳ Custom Branding (Enterprise)

### 7.2 Week-by-Week Breakdown

**Week 1-2: Control Deck**
- [ ] Day 1-2: Settings Overlay (Sheet component)
- [ ] Day 3-4: Agent Details Modal (Dialog component)
- [ ] Day 5-6: Command Palette (Command component)
- [ ] Day 7-10: Mobile Responsiveness Testing

**Week 3-5: AXE UI CANVAS**
- [ ] Week 3: ResizablePanel Layout + Code Editor
- [ ] Week 4: Event Architecture Backend + Frontend
- [ ] Week 5: Privacy Settings + Floating Widget Package

**Week 6-9: brain_control_ui**
- [ ] Week 6: Plugin-Loader + Dynamic Routing
- [ ] Week 7: Plugin Store UI + Template System
- [ ] Week 8-9: Plugin Migration (FeWoHeroes, SatoshiFlow, Courses)

**Week 10: OpenWebUI**
- [ ] Day 1-2: Docker Setup + Nginx Config
- [ ] Day 3-4: SSL + Testing
- [ ] Day 5: Payment Integration (Stripe Checkout)

### 7.3 Technical Dependencies

**Control Deck:**
- shadcn/ui: Sheet, Dialog, Command (⌘K)
- React Query: für API calls
- Zustand: für UI state (sidebar open/close)

**AXE UI:**
- shadcn/ui: ResizablePanel
- Monaco Editor oder CodeMirror: Code Editor
- React Query: Event API calls
- npm package: @brain/axe-widget

**brain_control_ui:**
- Dynamic Imports: für Plugin-Loader
- React Router: für dynamisches Routing
- Plugin Manifest: JSON Schema Validation

**OpenWebUI:**
- Docker: Containerization
- Nginx: Reverse Proxy
- Stripe: Payment Processing
- Let's Encrypt: SSL Certificates

### 7.4 Testing Strategy

**Unit Tests:**
- Komponenten (Jest + React Testing Library)
- Utility Functions
- API Clients

**Integration Tests:**
- API Endpoints (Supertest)
- Plugin-Loader
- Event System

**E2E Tests:**
- Control Deck: Agent CRUD, Mission Queue
- AXE UI: Chat + CANVAS Workflow
- brain_control_ui: Plugin Installation

**Manual Testing:**
- Mobile Responsiveness (alle Breakpoints)
- Accessibility (WCAG 2.1 AA)
- Cross-Browser (Chrome, Firefox, Safari)

### 7.5 Success Metrics

**Control Deck:**
- ✅ Alle 20+ Seiten mobile-responsive
- ✅ Settings Overlay < 300ms Load Time
- ✅ Command Palette (⌘K) funktioniert

**AXE UI:**
- ✅ CANVAS Split-Screen funktioniert
- ✅ Code Apply/Reject Workflow
- ✅ Event Tracking mit Privacy Settings
- ✅ Floating Widget in 3+ Projekten integriert

**brain_control_ui:**
- ✅ 3+ Plugins installiert und funktionsfähig
- ✅ Template System mit 3+ Vorlagen
- ✅ Plugin Store UI vollständig

**OpenWebUI:**
- ✅ chat.falklabs.de erreichbar (HTTPS)
- ✅ Payment Integration (Stripe Checkout)
- ✅ Custom Branding für Enterprise

---

## Appendix

### A. Figma Mockups (TODO)

**Zu erstellen:**
- Control Deck: Mobile + Desktop
- AXE UI: Minimized, Expanded, Full-Screen CANVAS
- brain_control_ui: Dashboard, Plugin Store, Template Selection
- OpenWebUI: Pricing Page, Chat Interface

### B. Component Library Checklist

**Bereits vorhanden (shadcn/ui):**
- [x] Button, Card, Input, Label, Select, Textarea
- [x] Dialog, Popover, Tooltip
- [x] Tabs, Accordion
- [x] Badge, Avatar, Separator
- [x] Alert, Toast

**Noch hinzuzufügen:**
- [ ] Command (⌘K Search)
- [ ] Sheet (Mobile Sidebar)
- [ ] Skeleton (Loading States)
- [ ] ResizablePanel (Split-Screen)
- [ ] Calendar, DatePicker
- [ ] Combobox (Autocomplete)

### C. API Endpoints Übersicht

**Control Deck:**
- `GET /api/agents/info` - Agent System Info
- `POST /api/agents/chat` - Chat mit Agent
- `GET /api/missions/queue` - Mission Queue
- `GET /api/neurorail/v1/identity/trace/{entity_type}/{entity_id}` - Trace Chain

**AXE UI:**
- `POST /api/axe/message` - AXE Chat Message
- `POST /api/axe/events` - AXE Event Tracking
- `GET /api/axe/context` - AXE Context Snapshot

**brain_control_ui:**
- `GET /api/plugins` - Liste aller Plugins
- `POST /api/plugins/install` - Plugin installieren
- `GET /api/templates` - Liste aller Vorlagen
- `POST /api/fewoheros/bookings` - FeWoHeroes Buchung erstellen

**OpenWebUI:**
- Eigene OpenAI-kompatible API
- Keine direkten BRAiN API Calls

### D. Deployment Checklist

**Alle UIs:**
- [ ] .env Variablen konfiguriert
- [ ] Docker Build erfolgreich
- [ ] Nginx Reverse Proxy konfiguriert
- [ ] SSL Zertifikate (Let's Encrypt)
- [ ] Health Checks funktionieren
- [ ] Monitoring (Prometheus, Grafana)

**Spezifisch pro UI:**
- [ ] Control Deck: Port 3001, Path /
- [ ] AXE UI: Port 3002, Path /axe
- [ ] brain_control_ui: Port 3003, Path /projects
- [ ] OpenWebUI: Port 8080, Domain chat.falklabs.de

---

**Ende des UI Redesign Konzepts v2.0**

**Nächste Schritte:**
1. **Option A:** Control Deck Improvements starten (Settings Overlay)
2. **Option B:** AXE UI CANVAS Design vertiefen (Mockups, Prototyp)
3. **Option C:** brain_control_ui Plugin-System designen (Architektur)

**Welche Option soll ich als nächstes ausführen?**
