# BRAiN Control Deck – UI Layout

Stand: v0.2.x

Dieses Dokument beschreibt die Struktur des BRAiN Control Deck Frontends
(Next.js + shadcn/ui + React Query) sowie die Designprinzipien des Layouts.

## 1. High-Level Struktur

- Framework: **Next.js App Router**
- UI-Bibliothek: **shadcn/ui** (Radix + Tailwind)
- State/Data-Fetching: **@tanstack/react-query**
- Routing-Gruppe: `(control-center)` für alle BRAiN-Deck-Seiten

```text
src/app
  ├─ layout.tsx                 # Root Layout (ReactQueryProvider, globals.css)
  └─ (control-center)/
       ├─ layout.tsx            # Sidebar + Header + Page Shell
       ├─ page.tsx              # Overview / Dashboard
       ├─ agents/page.tsx       # Agents Deck
       ├─ missions/page.tsx     # Missions Deck (geplant)
       └─ settings/
            ├─ page.tsx         # Settings Overview
            ├─ llm/page.tsx     # LLM Config
            └─ agents/page.tsx  # Agent Config
```

## 2. Provider-Hierarchie

### Root Layout (`src/app/layout.tsx`)

Verantwortung:

- lädt `globals.css`
- setzt `ReactQueryProvider` mit globalem `QueryClient`

```tsx
<html lang="de">
  <body>
    <ReactQueryProvider>{children}</ReactQueryProvider>
  </body>
</html>
```

### Control Center Layout (`src/app/(control-center)/layout.tsx`)

Verantwortung:

- shadcn-kompatibles Shell-Layout
- Sidebar und Header für alle Control-Deck-Seiten
- einheitlicher Page-Padding & Hintergrund

```tsx
<SidebarProvider>
  <AppSidebar />
  <SidebarInset>
    <SiteHeader />
    <main>{children}</main>
  </SidebarInset>
</SidebarProvider>
```

## 3. Kern-Komponenten

### `AppSidebar`

Pfad: `src/components/app-sidebar.tsx`

- Linke Hauptnavigation (Overview, Agents, Missions)
- Sektion „Decks“ (LLM Config, Agent Config, Lifecycle, Supervisor)
- Cluster-Badge mit Status („Local Dev · 0 kritische Incidents“)
- Futuristischer Look mit goldenen Akzenten

### `SiteHeader`

Pfad: `src/components/site-header.tsx`

- shadcn-Style Header mit:
  - `SidebarTrigger` (ein-/ausklappbare Sidebar)
  - dynamischem Titel (abhängig von `pathname`)
  - Env-/System-Status-Badge („System Online“)

### `SidebarProvider` / `SidebarInset`

Pfad: `src/components/ui/sidebar.tsx`

- einfacher Context, der `collapsed` State für die Sidebar hält
- `SidebarInset` ist der Wrapper für Header + Page Content

## 4. React Query Hooks & API

- API-Layer: `src/lib/brainApi.ts`
- Hooks:
  - `useSupervisorStatus` (`/api/health`)
  - `useAgentsInfo`, `useSupervisorAgents` (`/api/agents/info`, `/api/missions/agents/info`)
  - `useMissionQueue`, `useMissionHealth` (`/api/missions/...`)
  - `useLLMConfig`, `useUpdateLLMConfig`, `useResetLLMConfig`, `useLLMTest`

Alle Hooks laufen innerhalb von `ReactQueryProvider` (Root Layout) und werden im Dashboard, Agents Deck und Settings verwendet.

## 5. Designprinzipien

- **Layout ist fixiert**:
  - linke Sidebar (AppSidebar)
  - oberer Header (SiteHeader)
  - Content-Bereich mit Cards/Decks

- **Optik**:
  - Fokus auf ein **BRAiN Dark Theme** mit goldenen Akzenten
  - Cards mit „soft“ Schatten und abgerundeten Ecken
  - Typografie: kleine Caps für Sektionstitel (`tracking`, `uppercase`)

- **Navigation**:
  - Hauptnavigation: Overview, Agents, Missions
  - Sekundär: LLM Config, Agent Config, Lifecycle, Supervisor
  - Lifecycle & Supervisor aktuell als „Soon“ markiert (kein Routing-Break)

## 6. Nächste Schritte

- Farbkonzept: konsistentes BRAiN Dark Theme (Hintergrund, Cards, Texte, Akzente)
- Optional später: Light/Dark Toggle über CSS-Variablen & Kontext
- Lifecycle-UI anbinden, sobald Backend-/Agent Lifecycle-API integriert ist
