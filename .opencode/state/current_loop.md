version: 1
last_updated: "2026-03-10T11:58:26Z"
loop_status: active

mission:
  scope: "Execute next incomplete phase in AXE_UI_HARDENING_UNIFIED_FLOATINGAXE_ROADMAP.md"
  type: roadmap
  allowed_types:
    - roadmap
    - audit
    - bugfix
    - migration
    - refactor
    - architecture
    - docs
  goal: "Execute roadmap phases incrementally to harden AXE UI and converge on one canonical FloatingAXE runtime"

current_subtask: "Roadmap baseline complete; next step: run final packaging/release pass"

completed:
  - timestamp: "2026-03-10T09:22:16Z"
    step: "Phase A: exposed public/widget-runtime.js and updated public/embed.js to mount real runtime first with fallback-only-on-runtime-load-failure"
  - timestamp: "2026-03-10T09:28:10Z"
    step: "Phase A: wired runtime sendMessage to backend /api/axe/chat and added interactive panel input/send controls in widget-runtime.js"
  - timestamp: "2026-03-10T09:31:39Z"
    step: "Phase A: added embed startup telemetry events (init start, runtime mount success, fallback activation, init failure, API ready)"
  - timestamp: "2026-03-10T09:38:23Z"
    step: "Phase A: added Playwright contract coverage for runtime-first mount and fallback-only activation when widget-runtime.js is unavailable"
  - timestamp: "2026-03-10T09:43:01Z"
    step: "Phase B: replaced includes-based origin matching in lib/embedConfig.ts with strict URL/host parsing and canonical exact origin/host checks"
  - timestamp: "2026-03-10T09:46:45Z"
    step: "Phase B: added origin hardening tests for substring bypass, malformed URL entries, exact host:port matching, and wildcard rejection"
  - timestamp: "2026-03-10T09:50:27Z"
    step: "Phase B: made initialization error mapping deterministic by preserving AXEEmbeddingError codes via isEmbeddingError guard"
  - timestamp: "2026-03-10T09:57:50Z"
    step: "Phase B: enforced fail-closed origin checks in public/embed.js (ORIGIN_MISMATCH/CONFIG_INVALID), updated embed demo allowlist, and added embed-level negative tests for mismatch and malformed allowlist"
  - timestamp: "2026-03-10T10:10:11Z"
    step: "Phase C: unified embed backend routing source in public/embed.js with env-aware default inference and canonical backend URL normalization; added e2e coverage for omitted data-backend-url"
  - timestamp: "2026-03-10T10:37:29Z"
    step: "Phase C: aligned runtime sendMessage URL resolution in public/widget-runtime.js with shared env-aware canonical backend routing defaults"
  - timestamp: "2026-03-10T10:43:08Z"
    step: "Phase C: added embed env-matrix e2e checks for local inferred backend default and staging/production URL canonicalization behavior"
  - timestamp: "2026-03-10T11:01:11Z"
    step: "Phase D: converged on canonical FloatingAxe surface via src/widget.ts, migrated widget-test page to canonical usage, and converted legacy src/components/FloatingAxe.tsx into a compatibility wrapper"
  - timestamp: "2026-03-10T11:18:47Z"
    step: "Phase E: replaced placeholder webhook signatures with real HMAC-SHA256 signing, added X-AXE-Timestamp/X-AXE-Request-Id/X-AXE-Signature headers, and enforced replay-window dropping for stale/replayed webhook sends"
  - timestamp: "2026-03-10T11:34:01Z"
    step: "Phase F: completed plugin contract validation, dynamic plugin registration hardening, timeout-bounded hook/event execution, and fault-isolating plugin error boundaries to prevent runtime hangs"
  - timestamp: "2026-03-10T11:47:06Z"
    step: "Phase G: finalized offline queue replay hardening with dedupe + timeout-bounded replay and surfaced explicit offline/retrying/synced widget states"
  - timestamp: "2026-03-10T11:58:26Z"
    step: "Phase H: published FeWoHeroes integration pack with copy/paste embed + React snippets, branding profiles, and go-live checklist for CORS/trust-tier/rate-limits/observability"

next_candidates:
  - priority: high
    step: "Program closeout: prepare clean commit set and release-ready handoff summary"
  - priority: medium
    step: "Program closeout: remove or ignore local test artifacts (frontend/axe_ui/test-results/)"
  - priority: medium
    step: "Program closeout: run full Playwright matrix (beyond chromium) before release tag"

blockers:
  - none

validation:
  - timestamp: "2026-03-10T11:58:26Z"
    check: "frontend/axe_ui verification (lint, typecheck, build, playwright chromium)"
    result: pass

notes:
  - "embed.js no longer attempts CDN React bootstrap; it now loads widget-runtime.js from the same base path and mounts it first"
  - "fallback widget path is retained and only used when runtime bundle load or mount API resolution fails"
  - "runtime sendMessage now performs real backend transport against backendUrl/api/axe/chat and emits message-sent/message-received/error events"
  - "embed telemetry is published through window CustomEvent('axe:embed-telemetry') with deterministic event names"
  - "contract tests now assert runtime-first success path and fallback activation path using telemetry events"
  - "origin validation no longer uses substring matching; allowlist URL entries must be canonical origins and host entries must be exact hostname[:port]"
  - "security-negative origin tests are now part of playwright chromium suite via e2e/origin-validation.spec.ts"
  - "error code classification no longer depends on message string matching and now preserves explicit AXEEmbeddingError codes"
  - "embed runtime now blocks initialization on invalid/mismatched origin allowlists and emits embed_init_blocked telemetry with deterministic code"
  - "embed backend URL now resolves from data-backend-url or env-aware default and is normalized to canonical origin"
  - "widget-runtime sendMessage now uses the same env-aware canonical backend resolution strategy as embed.js to avoid routing drift"
  - "e2e now covers backend routing matrix assumptions: local inferred default, staging URL canonicalization, production URL canonicalization"
  - "Phase D canonicalization complete: src/index.ts now re-exports canonical widget surface, and legacy src/components/FloatingAxe.tsx no longer contains a separate runtime implementation"
  - "Phase E webhook hardening now uses shared HMAC-SHA256 signing input (timestamp.requestId.payload), adds deterministic AXE signature headers, and applies replay-window checks before dispatch"
  - "Phase F plugin runtime now validates capability-aligned plugin contracts and enforces timeout/error boundaries to keep the widget responsive under faulty or hanging plugins"
  - "Phase G adds explicit sync-state UX plus offline queue dedupe/replay controls so connectivity loss no longer risks duplicated or blocking message sync"
  - "Phase H delivers FeWoHeroes-ready integration docs with embed snippets, branding profiles, and operational launch checklist"

stop_condition: ""
