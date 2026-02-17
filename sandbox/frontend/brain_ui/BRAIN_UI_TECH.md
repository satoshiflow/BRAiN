# BRAiN UI – Frontend Tech Spec

## Zweck

BRAiN UI ist die immersive Benutzeroberfläche für das BRAiN Framework:
- Conversational Interface (Chat, später Voice/Video)
- Avatar/Circle-Präsenz mit emotionalen Zuständen
- Kontext-Canvas für Dokumente, Tools, Inspector

Das Control Center (`frontend/brain_control_ui/`) bleibt davon getrennt und dient
dem Betrieb & Debugging, **nicht** der Endnutzer-Interaktion.

---

## Projektstruktur

Repository-Root (relevanter Ausschnitt):

- `frontend/`
  - `brain_control_ui/`   → Operator-/Admin-UI (separates Projekt, andere App)
  - `brain_ui/`           → diese UI (BRAiN UI Dev)
- `backend/`              → FastAPI-Backend, Missions, AXE, etc. (eigenes Projekt)

### BRAiN UI Pfade

- `frontend/brain_ui/app/`
  - `ui/`
    - `layout.tsx`        → Shell/Chrome für BRAiN UI
    - `page.tsx`          → Onboarding (circle vs avatar)
    - `chat/`
      - `page.tsx`        → Haupt-Chat mit Avatar + Canvas
- `frontend/brain_ui/src/`
  - `lib/`
    - `brainApi.ts`       → zentraler API-Client zum Backend
  - `brain-ui/`
    - `state/`
      - `presenceStore.ts` → Mode (circle/avatar), affect-state, UI-Flags
    - `components/`
      - `BrainPresence.tsx`
      - `ChatShell.tsx`
      - `CanvasPanel.tsx`
      - `SettingsModal.tsx`

---

## Laufzeit & Ports

- **BRAiN UI Dev (dieses Projekt)**
  - Dev-Port: `3002`
  - Start:
    ```bash
    cd frontend/brain_ui
    npm install     # einmalig
    npm run dev -p 3002
    ```
  - Haupt-Route: `http://localhost:3002/ui`
  - Chat-Route: `http://localhost:3002/ui/chat`

- **BRAiN Control Center**
  - Pfad: `frontend/brain_control_ui/`
  - Port: z.B. `3000` oder `3001` (abhängig von deinem Setup)
  - Haupt-Routen: `/brain`, `/brain/debug`, …

- **Backend (BRAiN API)**
  - Basis-URL: `http://localhost:8000`
  - Alle Endpoints liegen unter `/api/...`
  - Beispiele:
    - `/api/health`
    - `/api/missions/info`
    - `/api/agents/info`
    - `/api/axe/...` (AXE-Info, Message, etc.)

---

## Umgebungsvariablen (BRAiN UI)

Datei: `frontend/brain_ui/.env.local`

```bash
# Basis-URL für das BRAiN Backend (FastAPI)
NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8000

# später: WebSocket-Base, Voice-Server usw.
# NEXT_PUBLIC_BRAIN_WS_BASE=ws://localhost:8000
