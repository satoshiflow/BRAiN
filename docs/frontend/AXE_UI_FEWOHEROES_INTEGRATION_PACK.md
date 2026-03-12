# AXE UI FeWoHeroes Integration Pack

## Purpose

Provide copy/paste integration material for FeWoHeroes (or similar partner apps) using the canonical FloatingAXE runtime.

## Integration Paths

### 1) Script Embed (recommended for fast rollout)

Use this snippet on the host page where the floating assistant should appear:

```html
<script
  src="https://<axe-ui-domain>/embed.js"
  data-app-id="fewoheroes-widget"
  data-backend-url="https://api.<your-domain>"
  data-origin-allowlist="https://app.fewoheroes.de"
  data-position="bottom-right"
  data-theme="light"
  data-debug="false"
  async
></script>
```

Required attributes:
- `data-app-id`
- `data-origin-allowlist`

Recommended attributes:
- `data-backend-url` (explicit in staging/prod)
- `data-theme`, `data-position`
- `data-webhook-url`, `data-webhook-secret` when webhook telemetry is enabled

### 2) React/NPM Integration

Use the canonical widget export in React apps:

```tsx
import FloatingAxe from "@/src/widget";

export function FeWoHeroesAssistant() {
  return (
    <FloatingAxe
      appId="fewoheroes-widget"
      backendUrl="https://api.<your-domain>"
      originAllowlist={["https://app.fewoheroes.de"]}
      position="bottom-right"
      theme="light"
      branding={{
        headerTitle: "FeWoHeroes Concierge",
        primaryColor: "#0e7490",
        secondaryColor: "#0f766e",
      }}
    />
  );
}
```

## Branding Profiles

### Profile A: FeWoHeroes Coastal

```json
{
  "branding": {
    "headerTitle": "FeWoHeroes Concierge",
    "primaryColor": "#0e7490",
    "secondaryColor": "#0f766e"
  },
  "theme": "light",
  "position": "bottom-right"
}
```

### Profile B: FeWoHeroes Alpine

```json
{
  "branding": {
    "headerTitle": "FeWoHeroes Gastgeberhilfe",
    "primaryColor": "#334155",
    "secondaryColor": "#1e293b"
  },
  "theme": "dark",
  "position": "bottom-left"
}
```

## Go-Live Checklist

### CORS + Origin Security

- Backend CORS includes FeWoHeroes origins only.
- `data-origin-allowlist` contains canonical origins (scheme + host + optional port).
- No wildcard allowlist entries are used in production.

### Trust-Tier + Access Policy

- AXE backend trust-tier policy for external widget ingress is explicitly configured.
- Local fallback flags are disabled in production.
- Mutating endpoints remain auth-guarded server-side.

### Rate Limits + Abuse Controls

- Per-app and per-session limits configured for `/api/axe/chat`.
- Webhook replay window/signature checks are active.
- Alerting exists for abnormal traffic spikes and repeated denied requests.

### Observability + Operations

- Browser errors from widget init are captured.
- AXE API latency/error dashboards include widget traffic dimension (`appId`).
- Embed telemetry events are observed (`runtime_mount_success`, `runtime_mount_fallback`, `embed_init_blocked`).
- On-call runbook includes rollback path (disable script include or feature flag).

## Verification Before Launch

Run in `frontend/axe_ui`:

```bash
npm run lint
npm run typecheck
npm run build
npm run test:e2e -- --project=chromium
```

Manual checks:
- Widget opens/closes and sends messages on FeWoHeroes staging.
- Offline badge transitions (`offline` -> `retrying` -> `synced`) behave as expected.
- Origin mismatch intentionally blocks initialization.
