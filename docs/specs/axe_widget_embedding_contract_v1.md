# AXE Floating Widget Embedding Contract v1

## Purpose

Define a stable contract for embedding AXE chat as a **Floating Widget** (mobile-first, installable chat interface) on external websites and applications.

This document specifies:
- Widget initialization API (props, lifecycle, security)
- Embedding security model (origin validation, trust-tier integration)
- Plugin registry access from embedded context
- Network configuration and fallback handling

## Design Principles

1. **Zero-Install Embedding:** External sites add one `<script>` tag or `import` statement; widget initializes automatically.
2. **Origin-Safe:** Strict origin validation; widgets only initialize on allowlisted domains.
3. **Trust-Tier Aligned:** Backend validates requests via DMZ gateway; widget respects trust boundaries.
4. **Plugin-Ready:** Embedded widgets can load plugins dynamically; plugins remain scoped to widget instance.
5. **Mobile-First:** Assumes touch interfaces, responsive, installable on mobile (PWA).
6. **Fail-Closed:** Missing config → widget doesn't initialize; no fallback chat leakage.

## Embedding Methods

### Option A: Script Embed (Recommended for Phase 1)

External site adds:

```html
<script
  src="https://axe.example.com/embed.js"
  data-app-id="mysite-chat-widget"
  data-backend-url="https://api.brain.example.com"
  data-origin-allowlist="mysite.com,app.mysite.com"
  async
></script>
```

Script auto-initializes `window.AXEWidget` global with singleton FloatingAxe instance.

### Option B: NPM Package (Phase 2+)

```typescript
import { FloatingAxe } from "@axe-ui/widget";

const widget = new FloatingAxe({
  appId: "mysite-chat-widget",
  backendUrl: "https://api.brain.example.com",
  originAllowlist: ["mysite.com", "app.mysite.com"],
});

widget.initialize();
```

## Widget Configuration

### Required Props

```typescript
interface FloatingAxeConfig {
  /** Unique application identifier for origin validation + rate limiting */
  appId: string;

  /** Backend API base URL (e.g., "https://api.brain.example.com") */
  backendUrl: string;

  /** Comma-separated allowed origins (must include current window.location.origin) */
  originAllowlist: string | string[];
}
```

### Optional Props

```typescript
interface FloatingAxeConfigOptional {
  /** Custom position: "bottom-right" | "bottom-left" | "top-right" | "top-left" (default: "bottom-right") */
  position?: "bottom-right" | "bottom-left" | "top-right" | "top-left";

  /** Custom theme: "light" | "dark" (default: "light") */
  theme?: "light" | "dark";

  /** Session ID for chat continuity (auto-generated if not provided) */
  sessionId?: string;

  /** Enable debug logging to console (default: false) */
  debug?: boolean;

  /** Plugins to auto-load on widget init (array of plugin manifests) */
  plugins?: PluginManifest[];

  /** CSS custom properties (--axe-primary-color, --axe-font-family, etc.) */
  customCss?: Record<string, string>;

  /** Callback when widget initializes successfully */
  onReady?: (widget: FloatingAxeInstance) => void;

  /** Callback when widget encounters an initialization error */
  onError?: (error: AXEEmbeddingError) => void;
}
```

## Security Model

### Origin Validation

1. **Config Time:** Parse `originAllowlist` in config; normalize to set of FQDNs.
2. **Init Time:** Validate `window.location.origin` is in allowlist.
   - If mismatch: throw `AXEEmbeddingError` with code `ORIGIN_MISMATCH`.
   - Widget does not initialize; no partial UI rendered.
3. **Request Time:** Backend-side validation (DMZ gateway, trust-tier) still applies.
   - Frontend origin check is defense-in-depth; trust backend as authoritative.

### AppId Purpose

- Used by backend for:
  - Rate limiting per-application
  - Analytics/audit logging (which app is consuming AXE)
  - Feature flags or plugin allowlists per app
- Frontend includes `appId` in `X-App-Id` header on all API calls from widget.

### Trust-Tier Alignment

- Widget always sends requests through configured `backendUrl` (no mixed-origin requests).
- Backend validates via DMZ gateway + trust-tier:
  - `LOCAL`: allowed if `AXE_FUSION_ALLOW_LOCAL_REQUESTS=true`
  - `DMZ`: always allowed
  - `EXTERNAL`: blocked (403 Forbidden)
- If backend rejects widget request → widget shows error state + retry UI (no silent failures).

### Rate Limiting

- Backend rate limits per `appId` + `sessionId` pair.
- Widget respects backend 429 responses; shows user-friendly backoff message.
- Burst protection: widget debounces rapid-fire chat messages (e.g., max 1 message per 500ms).

## Widget Lifecycle

### Initialization

```
1. Script loads / import executes
2. Browser idle → async init starts
3. Origin validation (throw if mismatch)
4. DOM: render floating chat button + hidden panel container
5. Service Worker register (PWA install support)
6. Plugin registry init + auto-load plugins from config
7. Session ID generate (or reuse from config)
8. Call onReady() callback
```

### State Transitions

```
UNINITIALIZED
  ↓ [initialize() called]
INITIALIZING
  ├─ [success] → READY
  └─ [error] → INITIALIZATION_ERROR
READY
  ├─ [panel open] → ACTIVE
  ├─ [message sent] → WAITING
  └─ [destroy() called] → DESTROYED
ACTIVE / WAITING
  ├─ [message received] → ACTIVE
  └─ [error during chat] → ERROR
ERROR
  ├─ [retry] → WAITING
  └─ [close panel] → READY
DESTROYED
  └─ [cleanup done, remove from DOM]
```

### Cleanup

```
widget.destroy()
  1. Plugin cleanup hooks: plugin.onUnmount()
  2. Event bus unsubscribe all
  3. Service worker unregister (optional, depends on config)
  4. DOM: remove floating button + panel
  5. State → DESTROYED
```

## API Contracts (Widget ↔ Backend)

### Chat Endpoint

**Request:**

```
POST /api/axe/chat
Headers:
  Content-Type: application/json
  X-App-Id: <appId>
  X-Session-Id: <sessionId>
  X-Request-Id: <unique-uuid>

Body:
{
  "model": "axellm",
  "messages": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ],
  "temperature": 0.7
}
```

**Response (Success 200):**

```json
{
  "text": "Assistant response text",
  "raw": {
    "model": "axellm",
    "tokens": { "input": 42, "output": 128 }
  }
}
```

**Response (Error 429):**

```json
{
  "error": "TooManyRequests",
  "message": "Rate limit exceeded for appId=mysite-chat-widget",
  "retryAfter": 60
}
```

**Response (Error 403):**

```json
{
  "error": "Forbidden",
  "message": "AXE endpoint is only accessible via DMZ gateways",
  "trust_tier": "EXTERNAL",
  "request_id": "req-12345"
}
```

### Health Endpoint

**Request:**

```
GET /api/axe/health
Headers:
  X-App-Id: <appId>
  X-Request-Id: <unique-uuid>
```

**Response (Success 200):**

```json
{
  "status": "ok",
  "axellm": "online",
  "version": "1.0.0"
}
```

**Response (Error 503):**

```json
{
  "status": "unavailable",
  "error": "Backend service temporarily unavailable"
}
```

## Plugin Integration (from Widget)

### Plugin Registration from Embedded Context

Plugins loaded in widget context have access to same hooks + event bus as in-app plugins, but scoped to widget instance.

**Example: Auto-loaded Plugin**

```typescript
// From widget config
const widget = new FloatingAxe({
  appId: "mysite-chat",
  plugins: [
    {
      id: "my-custom-plugin",
      version: "1.0.0",
      apiVersion: "v1",
      permissions: ["chat:read", "ui:composer.actions"],
      hooks: {
        onMount: async (ctx) => {
          console.log("Plugin initialized in widget");
        },
        onCommand: async (cmd, args, ctx) => {
          // Handle custom slash commands
        },
      },
    },
  ],
});
```

### Widget as Plugin Consumer

Widgets are plugin registries themselves; external sites can register their own plugins dynamically:

```typescript
const widget = window.AXEWidget;

widget.registerPlugin({
  id: "my-brand-plugin",
  version: "1.0.0",
  apiVersion: "v1",
  permissions: ["chat:read"],
  hooks: {
    onResult: async (result, ctx) => {
      // Customize result rendering
    },
  },
});
```

## Error Handling

### Error Codes (frontend → external site)

```typescript
type AXEEmbeddingErrorCode =
  | "ORIGIN_MISMATCH"       // Window origin not in allowlist
  | "CONFIG_INVALID"        // Missing required config
  | "BACKEND_UNAVAILABLE"   // Backend not reachable
  | "TRUST_TIER_BLOCKED"    // Backend rejected as EXTERNAL
  | "PLUGIN_LOAD_FAILED"    // Plugin manifest invalid or hook error
  | "SERVICE_WORKER_FAILED" // SW registration failed
  | "UNKNOWN";
```

### Error Callback

```typescript
widget.on("error", (error: AXEEmbeddingError) => {
  console.error(error.code, error.message, error.details);
  // External site can:
  // - Log to sentry
  // - Show user-friendly message
  // - Disable widget or retry
});
```

### Fallback Behavior

- If backend is unreachable: widget shows cached offline message + retry button.
- If service worker fails: widget still works; just no offline support.
- If plugin fails: widget logs error, disables that plugin, continues with others.

## Implementation Roadmap

### Phase 1: Script Embed + Basic Config

- [ ] Create `embed.js` script (singleton FloatingAxe, reads data attributes)
- [ ] Implement FloatingAxe component (React, Tailwind, TypeScript)
- [ ] Origin validation hook
- [ ] Basic error handling + onError callback
- [ ] Demo HTML page + test on external origin

### Phase 2: NPM Package

- [ ] Export FloatingAxeConfig + FloatingAxeInstance types
- [ ] Publish @axe-ui/widget to npm
- [ ] Integration tests: embed script + npm package produce same behavior

### Phase 3: Advanced Features

- [ ] Dynamic plugin registration from widget
- [ ] Offline mode (service worker cache strategy per widget)
- [ ] Analytics middleware (track events per appId)
- [ ] Custom theming CSS vars
- [ ] Floating widget position customization

## Reference Implementation Files

- Frontend component: `frontend/axe_ui/components/FloatingAxe.tsx` (NEW)
- Widget init hook: `frontend/axe_ui/src/hooks/useFloatingAxeInit.ts` (NEW)
- Embed script: `frontend/axe_ui/public/embed.js` (NEW)
- Config types: `frontend/axe_ui/lib/embedConfig.ts` (NEW)
- Demo: `frontend/axe_ui/pages/demo/embed-demo.html` (NEW)

## Verification Checklist

- [ ] Widget initializes on allowlisted origin
- [ ] Widget rejects mismatched origin (no partial UI)
- [ ] Chat messages include X-App-Id + X-Session-Id headers
- [ ] Backend trust-tier validation still enforced
- [ ] Plugins can be registered from widget context
- [ ] Error callbacks fire on init failure
- [ ] Script embed works (data attributes read)
- [ ] NPM import works (props passed to constructor)
- [ ] Mobile: widget renders correctly on iOS/Android
- [ ] PWA: installable from widget floating button

## Security Audit Checklist

- [ ] No XSS: all external input (config, plugin manifests) validated
- [ ] No CSRF: SameSite cookies enforced, POST requires CSRF token (if applicable)
- [ ] Origin isolation: strict comparison of window.location.origin vs allowlist
- [ ] Rate limiting: backend enforces per-appId + per-sessionId
- [ ] Secrets: no hardcoded API keys in embed script
- [ ] CORS: backendUrl must be same-origin or pre-approved CORS
- [ ] Plugin sandbox: plugins execute in widget context, no access to host page globals

## Future Enhancements

1. **Multi-language Support:** Add `lang` prop (default: browser `navigator.language`)
2. **Accessibility:** ARIA labels, keyboard nav, high-contrast theme
3. **Analytics:** Track widget impressions, chat volume per appId
4. **Branding:** Custom logo/header in floating panel
5. **Conversation History:** Persist to localStorage, sync across tabs
6. **A/B Testing:** Feature flags per appId
7. **Webhooks:** Callback to external site on chat events (with backoff + retry)
