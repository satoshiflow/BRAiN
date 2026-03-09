# AXE Chat Extensibility Roadmap

## Objective

Evolve AXE into a mobile-first, installable chat interface where new capabilities are delivered through plugins/modules.

## Phase A - Mobile + PWA Baseline

- Add installable web app support (manifest, service worker, icons, install prompt).
- Keep online-first behavior for API traffic.
- Ensure mobile sidebar and top-level navigation are touch-safe.

## Phase B - Plugin Foundation

- Implement plugin registry and manifest validation.
- Add frontend event bus and UI slot rendering.
- Define permission gates and plugin lifecycle hooks.

## Phase C - First Plugins

- Slash commands plugin.
- Result cards plugin.
- Mobile quick-actions plugin.

## Phase D - External Widget Productization

- Finalize embedding contract for external websites.
- Add app-level plugin enablement via backend config.
- Publish integration docs and sample embed project.

## Verification

- Mobile UX checks on iOS Safari + Android Chrome.
- PWA install checks (A2HS / Add to Home Screen).
- Contract tests for plugin lifecycle and permission checks.
