# AXE Presence Surface Contract (Frontend Mock to Backend Handoff)

## Purpose

This document defines a **simple integration path** for future backend support of AXE's 2035 UI surfaces.
The current frontend uses lightweight mocked presence concepts. This spec keeps backend work easy, incremental, and compatible with existing AXE modules.

## Scope

- Frontend already renders presence-oriented UI language:
  - Memory lane (sessions)
  - Intent surface (chat)
  - Presence beacon (API/system signal)
- Backend extension is optional and should stay minimal.
- No breaking changes to existing AXE chat/session endpoints.

## Current Frontend Mock Concepts

The UI currently implies these concepts without dedicated backend payloads:

- presence status labels (`linked`, `degraded`, `offline`)
- relay capability tags (external agents, robot relay, knowledge stream)
- compact runtime hints for operator action

## Recommended Backend Module

If implemented, add a small module:

- `backend/app/modules/axe_presence/`

Suggested files:

- `router.py`
- `schemas.py`
- `service.py`

The module should only aggregate existing signals and return compact responses.

## Proposed Endpoints (Optional)

### 1) `GET /api/axe/presence`

Returns top-level system presence for AXE shell/header.

Example response:

```json
{
  "status": "linked",
  "label": "BRAiN relay online",
  "signal": "ok",
  "last_seen": "2026-03-12T15:31:44Z",
  "action_hint": "safe_to_operate"
}
```

### 2) `GET /api/axe/relays`

Returns lightweight relay/capability list for future UI chips/panels.

Example response:

```json
{
  "relays": [
    {
      "id": "external_agents",
      "label": "External Agents",
      "status": "ready",
      "signal": "ok",
      "capabilities": ["dispatch", "sync"],
      "last_seen": "2026-03-12T15:31:44Z",
      "action_hint": "handoff_available"
    },
    {
      "id": "robot_relay",
      "label": "Robot Relay",
      "status": "standby",
      "signal": "warn",
      "capabilities": ["queue", "simulate"],
      "last_seen": "2026-03-12T15:29:12Z",
      "action_hint": "confirm_before_execute"
    }
  ]
}
```

### 3) `GET /api/axe/runtime/surface`

Returns compact operator-facing surface summary (optional dashboard usage).

Example response:

```json
{
  "status": "ok",
  "active_agents": 5,
  "pending_missions": 12,
  "uptime": "2h 34m",
  "signal": "ok"
}
```

## Field Model (Keep It Simple)

Use only simple serializable fields:

- `status`: string enum (`linked`, `ready`, `standby`, `degraded`, `offline`)
- `label`: short human-readable text
- `signal`: string enum (`ok`, `warn`, `error`)
- `capabilities`: string array
- `last_seen`: ISO timestamp string
- `action_hint`: short action-oriented hint

## Integration Rules

1. Reuse existing auth patterns from current AXE routes.
2. Keep responses compact and stable.
3. Do not block existing AXE chat/session flows if presence endpoints are unavailable.
4. Frontend should gracefully fallback to current local UI defaults.
5. Avoid coupling to heavy orchestration internals in v1.

## Frontend Fallback Behavior

Until backend endpoints exist, frontend should:

- continue using existing API health checks for the beacon
- keep relay/robot states as static placeholders
- treat missing presence API as non-fatal UI condition

## Backend Agent Checklist

- [ ] create `axe_presence` module with simple schemas/service/router
- [ ] register router in `backend/main.py`
- [ ] add targeted tests for response shape and fallback behavior
- [ ] keep endpoint auth consistent with existing AXE conventions
- [ ] avoid introducing breaking changes to `/api/axe/chat` or `/api/axe/sessions`
