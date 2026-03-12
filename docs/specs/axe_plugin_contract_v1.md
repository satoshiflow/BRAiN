# AXE Plugin Contract v1

## Purpose

Define a stable extension model so AXE chat features can be added incrementally without modifying core chat runtime.

## Core Principles

1. Core chat runtime stays minimal and stable.
2. Feature growth happens via plugins/modules.
3. All plugin execution is permission-scoped and tenant-aware.
4. UI extension points are explicit slots, not ad-hoc component coupling.

## Plugin Manifest

```json
{
  "id": "slash-commands",
  "version": "1.0.0",
  "apiVersion": "v1",
  "permissions": ["chat:read", "chat:write", "ui:composer.actions"],
  "uiSlots": ["composer.actions", "message.actions", "result.cards"],
  "commands": ["help", "status", "mission"]
}
```

## Runtime Hooks

- `onMount(context)`
- `onMessage(message, context)`
- `onCommand(command, args, context)`
- `onResult(result, context)`
- `onError(error, context)`

All hooks must be side-effect bounded via timeout and error boundaries.

## UI Slots

- `composer.actions`
- `message.actions`
- `result.cards`
- `sidepanel.tabs`

## Security + Governance

- Plugins are loaded from trusted registry entries only.
- Permissions are evaluated per app/tenant.
- Mutating actions require explicit capability permission checks backend-side.
- Trust-tier and audit guarantees remain enforced by backend contracts.

## Backend Alignment

- Chat transport contract remains stable (`POST /api/axe/chat`).
- Plugin-originated actions map to capability adapters in backend modules.
- EventStream remains backend internal; plugin UIs consume API/WS projections.

## Initial Reference Plugins

1. `slash-commands`
2. `result-cards`
3. `mobile-actions`

## Done Criteria v1

- Plugin manifest validation in frontend runtime.
- One plugin can be enabled/disabled per app config.
- Core chat requires no source edits to integrate a new plugin.
