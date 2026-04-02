# Paperclip Handoff Token and Deep-Link Contract

Status: Draft v1 (backend + CD3 + bounded MissionCenter handoff implemented locally)  
Owner: BRAiN Runtime + CD3  
Date: 2026-04-01

## Implementation Snapshot

Current local implementation covers:

- `POST /api/external-apps/paperclip/handoff`
- `POST /api/external-apps/paperclip/handoff/exchange`
- `GET /api/external-apps/paperclip/executions/{task_id}`
- `POST /api/external-apps/paperclip/actions`
- `GET /api/external-apps/paperclip/action-requests`
- `POST /api/external-apps/paperclip/action-requests/{request_id}/approve`
- `POST /api/external-apps/paperclip/action-requests/{request_id}/reject`
- CD3 `External Operations` drill-down action
- bounded Paperclip MissionCenter handoff UI served by `paperclip_worker`

Recommended local topology:

- upstream Paperclip execution API: `http://localhost:3110`
- bounded Paperclip handoff UI: `http://localhost:3111`

## 1. Purpose

Define the controlled navigation contract from BRAiN surfaces (primarily CD3, later AXE) into Paperclip.

This contract exists so users can open the correct operational context in Paperclip without turning Paperclip into a second authority surface.

## 2. Design Goals

1. Preserve BRAiN as source of truth.
2. Preserve tenant/correlation/mission continuity.
3. Allow direct operator drill-down into Paperclip operational context.
4. Avoid long-lived trust tokens in URLs.
5. Keep initial implementation simple enough for local + staging rollout.

## 3. Non-Goals

This contract does not:

- transfer governance authority to Paperclip
- allow direct policy mutation in Paperclip
- create a generic SSO platform for every external app
- bypass approval/permit rules

## 4. Primary Use Case

Example flow:

1. Operator opens CD3 `External Operations`.
2. CD3 shows a `SkillRun` currently delegated to `paperclip`.
3. Operator clicks `Open in Paperclip`.
4. BRAiN backend creates a short-lived signed handoff token.
5. Browser opens Paperclip with that token and a bounded target context.
6. Paperclip resolves the token through BRAiN or validates it locally and opens the correct company/project/issue view.

## 5. Handoff Model

## 5.1 Initial recommendation

Start with:

- short-lived signed handoff token
- deep-link target payload
- read-only / bounded operational landing page in Paperclip

Do not start with:

- full iframe embedding
- broad write privileges
- permanent Paperclip sessions derived from BRAiN directly

## 5.2 Token type

Token class:

- `paperclip_handoff_token`

Properties:

- short-lived
- single-purpose
- scoped to one target context
- signed by BRAiN backend

TTL recommendation:

- 60 to 300 seconds

## 6. Token Claims

Minimum claims:

- `iss`: `brain-backend`
- `aud`: `paperclip-ui`
- `sub`: operator principal id
- `tenant_id`
- `skill_run_id` (optional when not run-linked)
- `mission_id` (optional)
- `decision_id` (optional)
- `correlation_id`
- `target_type`
- `target_ref`
- `permissions`
- `iat`
- `exp`
- `jti`

## 6.1 Allowed `target_type`

- `company`
- `project`
- `issue`
- `agent`
- `execution`

## 6.2 Allowed `permissions`

Initial v1 allowed permissions:

- `view`
- `request_escalation`
- `request_approval`

Not in v1:

- unrestricted `edit`
- policy mutation
- connector management

## 7. Deep-Link Resolution

## 7.1 Suggested browser flow

CD3/AXE opens:

`/handoff/paperclip?token=<signed_token>`

Paperclip then:

1. validates token or exchanges it with BRAiN
2. resolves `target_type + target_ref`
3. loads the correct operational page
4. shows governance banner

## 7.2 Recommended banner text

- `Governed by BRAiN`
- `Sensitive actions require BRAiN approval`

## 8. Backend API Contract

## 8.1 Create handoff token

Proposed endpoint:

- `POST /api/external-apps/paperclip/handoff`

Request body:

```json
{
  "target_type": "issue",
  "target_ref": "paperclip-issue-123",
  "skill_run_id": "uuid-optional",
  "mission_id": "mission-optional",
  "decision_id": "decision-optional",
  "permissions": ["view"]
}
```

Response body:

```json
{
  "handoff_url": "https://paperclip.example/handoff/paperclip?token=...",
  "expires_at": "2026-04-01T12:00:00Z",
  "jti": "handoff_123"
}
```

## 8.2 Optional token exchange endpoint

If Paperclip should not validate tokens directly:

- `POST /api/external-apps/paperclip/handoff/exchange`

Purpose:

- Paperclip sends token to BRAiN backend
- BRAiN returns resolved, validated handoff context

This is safer for early rollout if we want to keep all validation central.

## 8.3 Canonical execution context endpoint

Implemented for bounded Paperclip drill-down:

- `GET /api/external-apps/paperclip/executions/{task_id}`

Purpose:

- return canonical `TaskLease` context for the requested execution
- attach linked `SkillRun` when present
- keep Paperclip on a bounded, read-only contract instead of generic control-plane mutation surfaces

## 8.4 Governed action request endpoint

Implemented for bounded write-back requests from Paperclip:

- `POST /api/external-apps/paperclip/actions`

Request body:

- `token`: signed handoff token
- `action`: one of `request_approval`, `request_retry`, `request_escalation`
- `reason`: operator rationale

Behavior:

- validates signed handoff token
- requires that the handoff was actually opened first
- checks token permission and current execution state
- records a durable control-plane/audit event instead of letting Paperclip mutate runtime state directly

## 8.5 Operator inbox and decisions

Implemented for ControlDeck v3:

- `GET /api/external-apps/paperclip/action-requests`
- `POST /api/external-apps/paperclip/action-requests/{request_id}/approve`
- `POST /api/external-apps/paperclip/action-requests/{request_id}/reject`

Decision model:

- requests are event-sourced from `external_action_request`
- operators/admins review pending items in ControlDeck
- approval/rejection writes another durable control-plane event
- approved retry requests create a new governed `SkillRun` plus a new external worker `TaskLease`
- approved escalation requests create a real supervisor domain escalation handoff

This keeps Paperclip bounded:

- Paperclip may request action
- ControlDeck operators may decide
- BRAiN remains the only runtime authority that can materialize the next execution step

Supervisor integration details:

- `request_escalation` approval now materializes `DomainEscalationRequest`
- domain key is now resolved deterministically from execution context, for example:
  - `external_apps.paperclip.execution.axe_worker_bridge`
  - `external_apps.paperclip.execution.paperclip_work`
- approval event stores `supervisor_escalation_id` in `execution_result`

ControlDeck surfaces:

- `External Operations` now shows a Supervisor preview panel with deep-links
- dedicated Supervisor inbox page: `/supervisor`
- dedicated Supervisor detail page: `/supervisor/{escalationId}`

## 9. Security Rules

## 9.1 Hard requirements

1. token must be short-lived
2. token must be audience-bound to Paperclip
3. token must be signed by BRAiN
4. token must include tenant/correlation continuity
5. token must not grant more than the requested bounded action set

## 9.2 Recommended implementation strategy

v1 recommendation:

- signed JWT or HMAC-backed opaque token
- BRAiN-side verification endpoint available
- Paperclip trusts BRAiN as issuer

## 9.3 Replay protection

Recommended:

- include `jti`
- optionally persist handoff issue/consume event in `control_plane_events`
- deny or flag repeated use beyond policy threshold

## 10. Audit / Traceability

Every handoff should emit at least:

- `external.handoff.paperclip.created.v1`
- `external.handoff.paperclip.opened.v1`
- `external.handoff.paperclip.exchange_failed.v1` (if applicable)

Event payload should include:

- `jti`
- `tenant_id`
- `principal_id`
- `target_type`
- `target_ref`
- `skill_run_id`
- `mission_id`
- `decision_id`
- `correlation_id`

## 11. CD3 Integration Requirements

CD3 must be able to:

1. show `Open in Paperclip`
2. know whether Paperclip is enabled for the tenant/environment
3. pass current contextual ids into handoff creation
4. display failure reason if handoff creation is denied

## 12. AXE Integration Requirements

AXE may support the same handoff later, but as secondary scope.

Examples:

- `Open company in Paperclip`
- `Show this task in Paperclip`

AXE should not become the primary management UI for repeated operational drill-down.

## 13. Failure Modes

Expected failure classes:

- `PAPERCLIP_DISABLED`
- `HANDOFF_POLICY_BLOCKED`
- `TENANT_CONTEXT_MISSING`
- `TARGET_NOT_MAPPED`
- `TOKEN_EXPIRED`
- `TOKEN_INVALID`
- `EXCHANGE_FAILED`

## 14. Rollout Plan

### Phase 1

- backend issues signed token
- CD3 deep-link button
- Paperclip landing route consumes token
- read-only landing target

### Phase 2

- richer target mapping (`company`, `project`, `issue`, `agent`)
- audit timeline visibility in CD3

### Phase 3

- bounded write-through requests from Paperclip back to BRAiN

## 15. Acceptance Criteria

This contract is successful when:

1. operator can jump from CD3 to the correct Paperclip context in one step
2. tenant/correlation/mission continuity is preserved
3. no governance authority is transferred to Paperclip
4. handoff is auditable and time-bounded
5. failed handoffs produce clear operator-visible reasons
