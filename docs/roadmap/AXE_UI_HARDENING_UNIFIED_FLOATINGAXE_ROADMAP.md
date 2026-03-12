# AXE UI Hardening + Unified FloatingAXE Roadmap

## Mission

AXE UI becomes one unified **FloatingAXE widget** for external products (for example FeWoHeroes), acting as the communication interface to BRAiN.

Core outcome:
- one widget contract,
- one runtime path,
- secure embedding,
- incremental feature growth through extensions.

## Product Direction

1. One FloatingAXE runtime for all embed consumers.
2. Security-first and fail-closed by default.
3. Mobile-first UX with stable desktop behavior.
4. Explicit local/staging/prod separation.
5. Extensibility via plugin/capability contracts, not core rewrites.

---

## Loop Execution Standard (`/loop`)

Every iteration must follow:

1. `GROUNDING`
   - validate current state,
   - confirm target files,
   - list blockers and assumptions.
2. `STRUCTURE`
   - define the exact implementation scope,
   - define required tests and acceptance checks,
   - define rollback boundaries.
3. `CREATION`
   - implement only the scoped tasks.
4. `EVALUATION`
   - run required checks,
   - capture pass/fail and deviations.
5. `FINALIZATION`
   - update docs,
   - summarize changes,
   - define next loop scope.

### Required verification per loop

- `npm run lint`
- `npm run typecheck`
- `npm run build`
- `npm run test:e2e` (at minimum chromium during intermediate loops; full matrix before phase close)

---

## Priority Scope (Start Now)

## Phase A (P1) - Embed Runtime to Real Widget Mount

### Objective

Remove fallback-first behavior from `embed.js` and mount the real widget runtime in embed contexts.

### Implementation Tasks

1. Build and expose a real widget bundle for embed usage.
2. Refactor `public/embed.js` to mount the real widget first.
3. Keep fallback UI only for hard-load failures.
4. Keep `window.AXEWidget` API stable (`open`, `close`, `sendMessage`, `on`, `destroy`).
5. Route `sendMessage` to real backend transport.
6. Add lifecycle/error telemetry for embed startup path.

### Acceptance Criteria

- Embedded pages render the real widget runtime, not only mock/fallback.
- Message flow performs actual backend request handling.
- Fallback path is only used when widget runtime cannot load.
- E2E tests for open/close/send message pass.

### Risks

- Bundle loading mismatch in external hosts.
- Runtime API drift between embed and app.

### Controls

- keep one adapter surface on `window.AXEWidget`,
- add contract tests for method signatures and behavior.

---

## Phase B (P2) - Origin Security Hardening (Fail-Closed)

### Objective

Implement strict, non-bypassable origin validation for embedding.

### Implementation Tasks

1. Replace substring checks with strict URL parsing and canonical origin comparison.
2. Validate allowlist inputs as valid URL/host entries.
3. Deny invalid configuration by default.
4. Render nothing on origin mismatch and emit explicit error code.
5. Add negative tests for common bypass attempts.

### Acceptance Criteria

- No `includes`-style origin checks remain.
- Mismatched origin always blocks initialization.
- Security-negative test suite passes.
- Error contract remains deterministic (`ORIGIN_MISMATCH`, `CONFIG_INVALID`).

### Risks

- Overly strict matching blocks valid staging domains.

### Controls

- support explicit wildcard policy only if documented and tested,
- keep exact-match as default mode.

---

## Phase C (P3) - Env and Backend Routing Consistency

### Objective

Guarantee consistent environment routing and eliminate backend URL drift.

### Scope

- unify `backendUrl` source for embed runtime,
- align API client behavior with env contract,
- verify local/staging/prod matrix with smoke checks.

---

## Phase D (P4) - One FloatingAxe Implementation

### Objective

Converge on one production FloatingAxe implementation.

### Status

- Completed (2026-03-10): canonical runtime/export surface standardized on `frontend/axe_ui/src/widget.ts` and `frontend/axe_ui/components/FloatingAxe.tsx`; legacy `frontend/axe_ui/src/components/FloatingAxe.tsx` now acts as compatibility wrapper.

### Scope

- remove runtime duplication between old and new component paths,
- define one canonical import/export surface,
- migrate test/demo pages to the canonical implementation,
- deprecate legacy path.

### Product Fit (FeWoHeroes)

The FloatingAXE widget is the communication interface for projects like FeWoHeroes.
Feature growth happens incrementally on this single runtime surface.

---

## Phase E (P5) - Webhook Security Completion

- replace placeholder signatures with HMAC-SHA256,
- include timestamp/request id/signature headers,
- enforce replay window checks.

Status:
- Completed (2026-03-10): frontend webhook send paths now use HMAC-SHA256 signatures with `X-AXE-Timestamp`, `X-AXE-Request-Id`, `X-AXE-Signature` headers and replay-window filtering for stale/replayed sends.

## Phase F (P6) - Plugin Runtime Maturity

- complete dynamic plugin registration and hook validation,
- enforce plugin timeouts and error boundaries,
- align permissions with capability contracts.

Status:
- Completed (2026-03-10): plugin contract validation now enforces hook + ui-slot permission requirements, runtime hook/event execution is timeout-bounded with fault isolation, dynamic plugins are initialized safely post-registration, and plugin runtime hang-resilience is covered by dedicated tests.

## Phase G (P7) - Offline/Sync Completion

- finalize offline queue + replay behavior,
- provide clear UI states (`offline`, `retrying`, `synced`).

Status:
- Completed (2026-03-10): offline queue now deduplicates by message id, replay is timeout-bounded and non-blocking, and canonical FloatingAxe panel surfaces explicit `offline` / `retrying` / `synced` state badges.

## Phase H (P8) - FeWoHeroes Integration Pack

- integration guide and copy/paste embed snippets,
- branding profile examples,
- go-live checklist (CORS, trust-tier, rate limits, observability).

Status:
- Completed (2026-03-10): FeWoHeroes integration pack published with script + React integration snippets, branding profiles, and operational go-live checklist.

---

## `/loop` Prompt Template (Copy/Paste)

Use this per iteration:

```text
/loop
Goal: Execute next incomplete phase in AXE_UI_HARDENING_UNIFIED_FLOATINGAXE_ROADMAP.md

Process:
1) GROUNDING: Identify current phase status, touched files, blockers.
2) STRUCTURE: Define exact tasks and verification checks for this loop.
3) CREATION: Implement only scoped tasks.
4) EVALUATION: Run lint, typecheck, build, and relevant e2e scope.
5) FINALIZATION: Update roadmap progress and summarize changes.

Rules:
- Fail closed on security-sensitive behavior.
- Keep one canonical FloatingAxe runtime direction.
- Do not expand scope outside current phase.
```

---

## Definition of Done (Program Level)

- One canonical FloatingAXE runtime is used in production and embedding.
- Secure embed contract with strict origin validation is enforced.
- Env routing is deterministic across local/staging/prod.
- E2E matrix is stable for desktop and mobile profiles.
- FeWoHeroes integration can be executed from documentation without ad-hoc code changes.
