# BRAIN Supervisor Modul – Backend + Control Center UI

Stand: 2025-11-17T19:38:47.321194Z

Dieses Paket enthält ein vollständiges, aber bewusst schlank gehaltenes Supervisor-Modul
für dein BRAIN-Framework – inklusive FastAPI-Backend und Next.js-Control-Center-Page.

## Struktur

- backend/app/supervisor/
  - __init__.py – Export des Routers
  - schemas.py – Pydantic-Modelle für Supervisor-, Agent- und Control-Strukturen
  - service.py – SupervisorService + AgentRegistry (In-Memory)
  - router.py – FastAPI-Routen (/api/supervisor/...)

- frontend/brain_control_ui/lib/api/supervisor.ts
  - Typed API-Client für das Supervisor-Backend

- frontend/brain_control_ui/app/supervisor/overview/page.tsx
  - Supervisor Overview Page für das Control Center

## Backend-Integration (FastAPI)

1. Module kopieren

Kopiere den Ordner:

- backend/app/supervisor

in dein bestehendes Backend unterhalb von /backend/app.

2. Router in deiner FastAPI-App registrieren

In deiner zentralen main.py (oder wo du deine Router sammelst) ergänzen:

from app.supervisor import router as supervisor_router
app.include_router(supervisor_router)

Damit sind folgende Endpoints verfügbar:

- GET /api/supervisor/status
- GET /api/supervisor/agents
- POST /api/supervisor/control

3. Agenten anbinden (erste einfache Integration)

Du kannst deine bestehenden Agenten direkt im Code beim Start/Heartbeat beim
Supervisor registrieren – z. B. sinngemäß:

from app.supervisor.service import get_supervisor_service
from app.supervisor.schemas import AgentStatus, AgentState

supervisor = get_supervisor_service()

supervisor.registry.upsert_agent(
    AgentStatus(
        id="agent:example",
        name="Example Agent",
        state=AgentState.HEALTHY,
        capabilities=["mission:foo", "mission:bar"],
    )
)

Empfohlen ist, diese Calls an zentralen Stellen deiner Agenten-/Mission-Lifecycle
einzubauen (Start, Shutdown, Heartbeat).

4. Health-Checks für Komponenten

In SupervisorService.get_status() sind die Komponenten (postgres, redis, qdrant)
zunächst hart auf healthy=True gesetzt.

Hier kannst du später deine echten Health-Checks einhängen (z. B. Ping auf DB, Redis,
Qdrant, Mission-System etc.).

## Frontend-Integration (Control Center UI)

1. Dateien kopieren

Kopiere:

- frontend/brain_control_ui/lib/api/supervisor.ts
- frontend/brain_control_ui/app/supervisor/overview/page.tsx

in dein Frontend-Projekt unterhalb von /frontend/brain_control_ui.

2. API Base URL konfigurieren

Stelle sicher, dass dein Control Center die API-Base-URL kennt – z. B. über .env.local:

NEXT_PUBLIC_BRAIN_API_BASE_URL=http://localhost:8000

3. Navigationseintrag (optional)

Falls du eine zentrale Sidebar/Navigation hast, füge dort einen Link ein:

label: "Supervisor"
href: "/supervisor/overview"

Sobald das Modul eingebunden ist und deine Agenten sich beim AgentRegistry melden,
bekommst du im Control Center:

- Globalen Systemzustand (inkl. Dummy-Komponentenstatus)
- Übersicht aller registrierten Agenten
- Simple Control-Actions (Pause/Resume/Kill/Restart), aktuell als simulierte Zustandswechsel
