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
