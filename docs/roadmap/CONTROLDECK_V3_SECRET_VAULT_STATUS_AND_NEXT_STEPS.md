# ControlDeck v3 Secret Vault - Status and Next Steps

## Current Delivered State

This delivery introduced a secure ControlDeck v3 secret/config governance surface and integrated it with the existing BRAiN runtime and auth model.

Implemented now:

- Vault metadata and masked value listing in ControlDeck and backend.
- Secure update path with server-side validation and RBAC checks.
- Secret generation flows for supported keys (password/token and RSA private key class).
- Encryption-at-rest for secret writes/generation via `CONFIG_VAULT_ENCRYPTION_KEY`.
- Approval-style rotation workflow:
  - request rotation (pending),
  - list pending requests,
  - approve and activate,
  - reject and clear.
- Auditing hooks for vault updates and rotation decisions.
- OpenClaw TaskLease bridge remains functional after these changes.

## What To Test Now (Functional Validation)

Use this as the immediate test checklist while we keep scope frozen:

1. Vault read visibility and masking
   - Verify definitions and values load in ControlDeck Settings.
   - Verify secret values are masked in UI/API.

2. Vault update path
   - Update a non-secret/sensitive key.
   - Verify value persists and appears as `db_override`.

3. Secret generation path
   - Generate a secret-capable key.
   - Verify masked UI result and encrypted storage shape in DB.

4. Rotation approval path
   - Create pending request from UI.
   - Approve from pending queue and verify activation.
   - Repeat with reject and verify pending item disappears.

5. Regression checks
   - Trigger `/openclaw ...` through AXE chat and confirm Task+SkillRun terminal success.

## Required Runtime Preconditions

- `CONFIG_VAULT_ENCRYPTION_KEY` must be set for secret writes and generation.
- Local schema must include `config_entries`.
- Auth roles must be available (`viewer`, `operator`, `admin`) for RBAC gating paths.

## Deferred Extensions (Planned Later)

These are intentionally postponed until functional testing feedback is complete:

1. Policy-driven approval decisions
   - Automatic route to `auto_approve`, `governor_review`, `human_required`.
   - Remove click-first requirement for low-risk operations.

2. Context-based decision scoring
   - Combine risk, KARMA/trust, budget/cost pressure, environment scope, and incident history.

3. Event-driven rotation triggers
   - Trigger on anomaly, failed-auth threshold, deploy events, policy changes, or leak suspicion.

4. Closed governance loop hardening
   - `event -> risk eval -> policy decision -> approval route -> rotation -> audit correlation`.

5. Rotation safety lifecycle
   - staged rollout, health checks, and rollback automation.

6. UX hardening
   - queue filters, mandatory rationale templates, bulk operations, and breakglass reveal workflow.

7. External secret manager integration
   - optional adapters to Vault/KMS while preserving BRAiN governance as canonical layer.

## Security Invariants To Keep

- No plaintext secret values in list responses or logs.
- No governance bypass for sensitive/secret mutation paths.
- No blanket always-auto approval rules.
- No blind/contextless rotation activation.
