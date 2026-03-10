# AXE UI Deploy + Env Runbook

## Purpose

Provide one reliable setup for AXE UI across local, staging, and production, including widget embedding and trust-tier requirements.

## Frontend Env Matrix

### Local (Laptop)

Use in `frontend/axe_ui/.env.local`:

```env
NEXT_PUBLIC_APP_ENV=local
NEXT_PUBLIC_BRAIN_API_BASE=http://127.0.0.1:8000
NEXT_PUBLIC_AXE_DEFAULT_MODEL=qwen2.5:0.5b
```

Notes:
- If `NEXT_PUBLIC_BRAIN_API_BASE` is missing, AXE UI auto-detects local host and falls back to `http://127.0.0.1:8000`.
- Frontend dev server runs at `http://127.0.0.1:3002` (`npm run dev`).

### Staging

Use staging environment variables in deployment system:

```env
NEXT_PUBLIC_APP_ENV=production
NEXT_PUBLIC_BRAIN_API_BASE=https://staging-api.<your-domain>
NEXT_PUBLIC_AXE_DEFAULT_MODEL=qwen2.5:1.5b
```

Notes:
- Keep `NEXT_PUBLIC_APP_ENV=production` for all remote environments.
- Do not rely on hostname auto-detection for staging/prod; set explicit API base.

### Production

Use production environment variables in deployment system:

```env
NEXT_PUBLIC_APP_ENV=production
NEXT_PUBLIC_BRAIN_API_BASE=https://api.<your-domain>
NEXT_PUBLIC_AXE_DEFAULT_MODEL=qwen2.5:1.5b
```

Notes:
- Frontend should never point to localhost in remote environments.
- Prefer immutable deploy artifacts with env injected by platform.

## Backend Trust-Tier Requirements

For AXE endpoints (`/api/axe/chat`, `/api/axe/health`):

- Local development (if direct local access needed):

```env
AXE_FUSION_ALLOW_LOCAL_REQUESTS=true
AXE_FUSION_ALLOW_LOCAL_FALLBACK=true
```

- Remote environments:
  - Use DMZ gateway path.
  - Keep local fallback disabled.
  - Keep fail-closed behavior enabled.

## Widget Embed Configuration

Minimal script embed:

```html
<script
  src="https://<frontend-domain>/embed.js"
  data-app-id="my-app-widget"
  data-backend-url="https://api.<your-domain>"
  data-origin-allowlist="app.<your-domain>,www.<your-domain>"
  async
></script>
```

Recommended:
- Use explicit `data-backend-url` per environment.
- Keep origin allowlist strict (no wildcard broadening).
- Add `data-debug="true"` only in non-production.

## Smoke Checks (All Environments)

1. Frontend health:
   - Open `/chat` and send one message.
2. API routing:
   - Verify browser network calls go to expected `NEXT_PUBLIC_BRAIN_API_BASE`.
3. Trust-tier behavior:
   - Confirm expected allow/deny for local vs remote ingress.
4. Widget behavior:
   - Open embed demo and validate `window.AXEWidget` exists.
5. E2E baseline:
   - Run `npm run test:e2e` in `frontend/axe_ui`.

## Quick Troubleshooting

- `403 Forbidden` on `/api/axe/chat` locally:
  - Set backend `AXE_FUSION_ALLOW_LOCAL_REQUESTS=true`.
- Widget does not appear:
  - Check `data-origin-allowlist` matches `window.location.origin` host.
- Calls go to wrong API:
  - Inspect `NEXT_PUBLIC_BRAIN_API_BASE` and rebuild/restart frontend.
- Playwright startup timeout:
  - Ensure no port conflict on `127.0.0.1:3002`.
