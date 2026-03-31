# ControlDeck v3 Secret Vault Contract

## Purpose

Define a secure, governed contract so ControlDeck v3 can display and manage system secrets/config values without exposing plaintext secrets in UI payloads or logs.

## API Surface

All endpoints are under `GET|POST /api/config/vault/*`.

### 1) List Definitions
- `GET /api/config/vault/definitions`
- Returns key metadata only:
  - `key`, `label`, `description`
  - `classification`: `secret | sensitive | public_config`
  - `value_type`: `string | integer | boolean | url | json | pem`
  - `editable`, `generator_supported`, `rotation_supported`
  - `validation` constraints

### 2) List Values
- `GET /api/config/vault/values`
- Optional: `?classification=secret|sensitive|public_config`
- Returns masked values for `secret` classification.
- Payload includes source and status metadata:
  - `effective_source`: `db_override | environment | default`
  - `is_set`, `masked_value`, `updated_at`, `updated_by`

### 3) Upsert Value
- `POST /api/config/vault/values/{key}`
- Request: `{ "value": <json-compatible>, "reason": "...optional..." }`
- Validation is server-side and key-specific.
- Response returns masked/effective metadata, never plaintext for secrets.

### 4) Validate Candidate Value
- `POST /api/config/vault/validate/{key}`
- Request: `{ "value": <candidate> }`
- Returns `{ valid: boolean, errors: string[] }`.

### 5) Generate Value
- `POST /api/config/vault/generate/{key}`
- Generates secure values for generator-capable keys:
  - passwords, random secret tokens, RSA private key.
- Request supports optional params per generator (e.g. password length).
- Response returns generated value once if role allows secret reveal; otherwise masked + stored.

## RBAC and Governance

- Viewer (`viewer`): read definitions + masked values only.
- Operator (`operator`): can edit `public_config` and selected `sensitive` keys.
- Admin (`admin`): full edit/generate for all keys.

Approval gate (future-compatible, policy-driven) for:
- JWT key material
- infrastructure credentials (`DATABASE_URL`, `REDIS_URL` with credential)
- provider API key rotation in production contexts.

## Security Rules

- Secret values are never returned in plaintext from list endpoints.
- Secret update operations do not log raw values.
- Audit event required for every mutation/generation:
  - actor, key, action, classification, source, result, reason.
- Input validation before persistence:
  - URL format + HTTPS checks where required
  - numeric bounds
  - PEM parse for private keys
  - minimum entropy/length for password/token secrets.

## Storage / Resolution

- Canonical store: `config_entries` DB table (existing module).
- Secret entries stored encrypted-at-rest when encryption key is available.
- Effective value resolution order:
  1. DB override
  2. Environment variable
  3. Hardcoded default metadata

## ControlDeck UX Mapping

- Show all managed keys in one table with filter by classification.
- Secret rows: masked value + `Edit` + `Generate` (if supported).
- Non-secret rows: inline edit.
- Validation errors shown inline before submit.
- No secret persistence in browser localStorage.

## Initial Managed Key Set

- Identity/Auth: `BRAIN_JWT_PRIVATE_KEY`, `JWT_SECRET_KEY`, `BRAIN_ADMIN_PASSWORD`, `BRAIN_OPERATOR_PASSWORD`, `BRAIN_VIEWER_PASSWORD`
- Provider secrets: `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `OPENWEBUI_API_KEY`
- Infra/sensitive: `DATABASE_URL`, `REDIS_URL`, `QDRANT_URL`, provider base URLs
- Runtime controls: token expiry and routing/security toggles relevant to CD3 governance.

## Non-Goals (Current Iteration)

- Automatic secret sync to external secret managers.
- Distributed rollout orchestration across multiple clusters.
- Dynamic hot-reload guarantees for every downstream subsystem.
