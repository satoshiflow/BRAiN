# Test Status - 2026-02-21

## Problem gefunden & gefixt
**Issue:** `QueryClientProvider` war im `DashboardLayout` (Client Component), aber Next.js versuchte SSR.

**Fix:** 
- Neue Datei: `src/components/providers.tsx` mit QueryClientProvider
- `src/app/layout.tsx` nutzt nun Providers (Server Component bleibt erhalten)
- `src/components/shell/dashboard-layout.tsx` Provider entfernt

## Server Status
- Next.js Dev Server startet auf Port 3456
- Allerdings scheint der Prozess nach "Ready" zu stoppen
- Vermutlich: Dependencies noch nicht vollständig oder Port-Problem

## Nächste Schritte
1. `npm install` komplett durchlaufen lassen
2. Server stabilisieren
3. Tests erneut laufen lassen

## Workaround für sofortiges Testen
Tests laufen lassen mit Playwright's eingebautem WebServer:
```bash
cd /home/oli/projects/BRAiN/BRAiN/frontend/controldeck-v2
npx playwright test --project=chromium --reporter=list
```

Playwright startet dann selbst den Dev Server.
