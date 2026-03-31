# ControlDeck v3 Secret Surface Implementation Plan (No-Code)

## Goal

Make all operationally relevant secrets and sensitive runtime config for CD3-visible workflows discoverable, editable, and rotatable in ControlDeck v3, without creating a second governance/runtime system.

Primary outcome:
- ControlDeck becomes the governed edit surface for secret/config management.
- BRAiN backend remains canonical source for enforcement, validation, audit, and rollout behavior.

## Guardrails

- No secret values stored in frontend code or browser storage.
- No plaintext secret echo in API responses or logs.
- All secret mutations must produce auditable events.
- Sensitive changes must support approval gates where policy requires.
- Existing runtime path remains canonical (AXE/SkillRun/TaskQueue stay unchanged).

## Scope (based on repository secret inventory)

### A) Identity/Auth Secrets
- `BRAIN_JWT_PRIVATE_KEY`
- `JWT_SECRET_KEY` (legacy path)
- `BRAIN_ADMIN_PASSWORD`
- `BRAIN_OPERATOR_PASSWORD`
- `BRAIN_VIEWER_PASSWORD`

### B) Provider/API Secrets
- `OPENAI_API_KEY`
- `OPENROUTER_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENWEBUI_API_KEY`

### C) Infrastructure Credentials / Sensitive Endpoints
- `DATABASE_URL`
- `REDIS_URL`
- `QDRANT_URL`
- Provider base URLs and runtime endpoints (`OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL`, `OPENWEBUI_HOST`, `OLLAMA_HOST`)

### D) Security-Sensitive Runtime Controls
- `JWT_ISSUER`, `JWT_AUDIENCE`, `JWT_JWKS_URL`
- `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `AGENT_TOKEN_EXPIRE_HOURS`, `JWKS_CACHE_TTL_SECONDS`
- `LOCAL_LLM_MODE`
- `BRAIN_CAPABILITY_ALLOW_INMEMORY_FALLBACK`
- `SKILL_MARKETPLACE_EXTERNAL_ENABLED`
- `BRAIN_AUTO_LEARN_ON_SKILLRUN`

### E) CD3 Frontend Runtime Config (non-secret but governed)
- `NEXT_PUBLIC_BRAIN_API_BASE`, `NEXT_PUBLIC_BRAIN_API_PATH`, local/prod variants
- `NEXT_PUBLIC_CONTROL_DECK_BASE`, path variants
- `NEXT_PUBLIC_AXE_UI_BASE`
- `NEXT_PUBLIC_APP_ENV`

## Target UX in ControlDeck v3

## 1. Config Vault Screen
- Sections: Auth, Providers, Infrastructure, Runtime Controls, Frontend Routing.
- Each field has classification badge: `secret`, `sensitive`, `public-config`.
- Secret fields are masked-by-default with explicit reveal action and RBAC check.

## 2. Edit Modes
- `Plain editable`: non-secret config.
- `Masked editable`: secret values, never returned in full after save.
- `Generate`: for passwords, JWT secret, RSA keypair generation workflow.
- `Rotate`: staged replacement with pre-check and commit/rollback semantics.

## 3. Validation UX
- Inline validation before save:
  - DSN/URL format
  - key shape/prefix checks
  - PEM parse for RSA private key
  - numeric bounds for token TTLs
- Server-side validation is authoritative; UI only assists.

## Backend Contract Plan (no code yet)

Introduce a dedicated governed config API namespace, for example:
- `GET /api/control/config/definitions`
- `GET /api/control/config/values`
- `POST /api/control/config/values/{key}`
- `POST /api/control/config/generate/{key}`
- `POST /api/control/config/rotate/{key}`
- `POST /api/control/config/validate/{key}`

Rules:
- Definition endpoint exposes metadata only (type, class, validator, mutability, approval requirement).
- Value endpoint returns masked payload for secret fields.
- Update/generate/rotate operations emit audit + control-plane event.

## Data Model Plan

Use DB-backed canonical config registry (not `.env` as source of truth at runtime):
- `config_definitions` (metadata)
- `config_values` (encrypted-at-rest value blobs + version)
- `config_change_requests` (approval workflow)
- `config_rotation_events` (rotation lifecycle)

Optional bootstrap:
- One-time import from environment on startup/migration.
- Explicit precedence rules: DB config > env fallback > hard default.

## Security and Governance Plan

- RBAC tiers:
  - Viewer: list metadata and masked values.
  - Operator: update non-breakglass keys.
  - Admin/Security: rotate secrets and key material.
- Approval policy required for:
  - JWT key material
  - DB/Redis credentials
  - Provider API key changes in production
- Audit record fields:
  - actor, key, action, before/after fingerprint, request id, approval id, rollout status.

## Generator/Rotation Workflows

## 1. Passwords
- Generate strong random candidate.
- Save as pending.
- Trigger health check of dependent service.
- Commit or rollback.

## 2. JWT Secrets / RSA Keys
- Generate new key material with versioning.
- Maintain active + previous verification window.
- Publish JWKS changes before final cutover.

## 3. Provider API Keys
- Save new key as staged version.
- Run lightweight provider validation call.
- Promote on success, rollback on failure.

## 4. DSN Credentials
- Prefer split-form editor (host, port, user, pass, db, tls).
- Compose DSN server-side.
- Connection test required before activation.

## Phased Delivery Plan

Phase 0: Inventory freeze and key classification
- Finalize managed-key catalog and sensitivity classes.

Phase 1: Read-only control plane
- Definitions + masked values visible in CD3.
- RBAC + audit for reads.

Phase 2: Safe edit
- Non-secret and masked secret updates with validation.

Phase 3: Generate/rotate
- Password/JWT/provider rotation workflows.
- Approval integration and rollback paths.

Phase 4: Hardening
- Add policy gates, rate limits, anomaly alerts, and usage telemetry.

## Done Criteria

- All in-scope keys are visible in CD3 with proper classification.
- Secret edits are masked, validated, audited, and policy-enforced.
- Generator/rotation exists for key classes listed above.
- No secret values leaked to frontend bundles, browser local storage, or plain logs.
- Runbook documents breakglass and rollback behavior.

## Notes

- This document is implementation planning only (no runtime/code changes included).
- Secret inventory was derived from repository usage paths tied to CD3 and its backend dependencies.

## Strategic TODO (Autonomy Upgrade)

- Policy-driven approval by default (not manual click-first):
  - auto-approve low-risk and non-critical scope,
  - governor/human approval for higher risk tiers.
- Context-based decision score for approval routing using:
  - risk score,
  - KARMA/agent trust signal,
  - budget/cost pressure,
  - environment scope (dev/test/prod),
  - recent stability/incident history.
- Event-driven rotation triggers (instead of cron-only):
  - anomaly detection,
  - failed auth threshold,
  - deployment events,
  - policy change events,
  - leak suspicion events.
- Closed governance loop target:
  - event -> risk evaluation -> policy decision -> approval route -> rotation -> audit trail.
- Hard constraints for this upgrade:
  - no bypass of governance,
  - no blanket always-auto approvals,
  - no contextless blind rotations,
  - no hardcoded production bypass rules.
