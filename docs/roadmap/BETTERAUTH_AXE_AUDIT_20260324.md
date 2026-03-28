# BetterAuth / AXE Audit (2026-03-24)

## Ist-Analyse

- AXE UI (`frontend/axe_ui`) uses custom backend auth APIs (`/api/auth/login`, `/me`, `/refresh`, `/logout`) and does not integrate BetterAuth directly.
- BetterAuth exists in repo as separate tracks:
  - `better-auth-node/` standalone service
  - `frontend/controldeck-v2` BetterAuth integration
- Default local root stack (`docker-compose*.yml`) does not start `better-auth-node`.
- Hetzner/Coolify BetterAuth presence is documented, but repo evidence is inconsistent (planned domains/services vs current runtime notes).

## Architekturentscheidung

- Chosen approach for AXE hardening now: keep current backend-auth integration and stabilize it first.
- Do not mix a full BetterAuth migration into the active AXE stabilization slice.
- Follow-up migration decision remains open after infrastructure verification (local + Hetzner/Coolify runtime proof).

## Verification Scope for Infrastructure (deferred)

- Local BetterAuth runtime proof (service up, `/health`, `/api/auth/session`) on dedicated stack.
- Hetzner/Coolify runtime proof (`auth.falklabs.de` or active identity domain), service logs, env, and DB backend confirmation.
- Final migration go/no-go based on verified operational state, not docs only.
