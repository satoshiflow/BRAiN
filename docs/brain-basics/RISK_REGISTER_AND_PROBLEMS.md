# BRAiN Risk Register and Problem Log

Date: 2026-03-03
Scope: Detailed issues discovered during deep analysis (core, frontend, connectors, infra assumptions).

## Severity Key

- Critical: immediate security/availability risk.
- High: major correctness/security/operational risk.
- Medium: important but bounded risk.
- Low: quality/maintainability issue.

## Detailed Risk Table

| ID | Severity | Problem | Evidence | Impact | Action |
|---|---|---|---|---|---|
| R-001 | Critical | Dual auth systems in backend (`security.py` legacy vs `auth_deps` modern) | `backend/app/core/security.py`, `backend/app/core/auth_deps.py`, legacy imports in module routers | Inconsistent auth semantics, policy drift, potential bypass or incorrect denial | Converge to modern stack and deprecate legacy path |
| R-002 | High | Legacy auth allows anonymous fallback behavior in some paths | `backend/app/core/security.py` (`get_current_principal`) | Unexpected guest context in protected assumptions | Remove/disable fallback in production path; migrate dependencies |
| R-003 | High | Event bus stub not production-durable | `backend/app/core/event_bus.py` | Event loss, no retry/backpressure, weak audit reliability | Standardize on `EventStream` backbone |
| R-004 | High | Rate limiter implemented in multiple places with inconsistent storage assumptions | `backend/main.py`, `backend/app/core/rate_limit.py` | Throttling inconsistency and bypass windows under scale | Single limiter strategy + shared Redis storage |
| R-005 | High | `controldeck-v2` auth path inconsistencies and stale compatibility pieces | `frontend/controldeck-v2/src/lib/auth.ts`, `frontend/controldeck-v2/src/lib/auth-server.ts`, `frontend/controldeck-v2/src/app/api/auth/login/route.ts` | Login/session breakage risk and unclear source-of-truth | Remove stale routes, keep one auth contract |
| R-006 | High | `login` import appears broken in auth route | `frontend/controldeck-v2/src/app/api/auth/login/route.ts` imports `{ login }` from `auth-server` (not exported) | Runtime route failure | Remove or rewrite route to canonical Better Auth flow |
| R-007 | High | Connectors lifecycle and send actions are not explicitly role-tightened beyond base auth | `backend/app/modules/connectors/router.py` | Operational misuse risk by authenticated but under-privileged actors | Add operator/admin gates on action/send endpoints |
| R-008 | Medium | Connector error responses return raw exception strings | `backend/app/modules/connectors/router.py` (`error=str(e)`) | Information disclosure to clients | Return sanitized errors; log details server-side |
| R-009 | Medium | Connectors can report connected in handler-only mode without full external integration | `backend/app/modules/connectors/telegram/connector.py`, `backend/app/modules/connectors/whatsapp/connector.py` | False-positive readiness and monitoring blind spots | Introduce explicit degraded status and startup validation |
| R-010 | Medium | Frontend API route/contract sprawl likely to drift from backend reality | `frontend/controldeck-v2/src/lib/api.ts`, `frontend/controldeck-v2/src/hooks/use-api.ts` | UI may call non-existing or stale endpoints | Generate/validate endpoint contract map per sprint |
| R-011 | Medium | Full-stack behavior cannot be reproduced locally due to remote-heavy infrastructure | Deployment model and user constraints | Late discovery of integration bugs | Strengthen static checks + critic-agent + staged verification checklist |
| R-012 | Low | Documentation drift: old findings remain in core docs despite code evolution | `CLAUDE.md` and archived docs | Decision friction and wrong priorities | Keep active analysis in `docs/brain-basics/` and review monthly |
| R-013 | Mitigated | Targeted auth tests previously failed on baseline runtime expectations | `backend/tests/test_auth_flow.py`, `backend/tests/test_module_auth.py`, `reports/self_healing/20260305T125033Z/diagnosis_report.json` | Confidence restored for Sprint 1 auth convergence validation | Closed by auth test harness and token signing fixes (`33 passed`) |
| R-014 | Mitigated | Local JWT key material path instability for auth token tests | `backend/tests/test_auth_flow.py` | Token-flow tests unstable without deterministic signing setup | Closed by deterministic test key setup + RS256 PEM signing compatibility in `AuthService` |
| R-015 | Mitigated | Module auth tests returned wrong status semantics due harness/dependency setup | `backend/tests/test_module_auth.py` | False-negative auth guard results | Closed by request-body contract fix + dependency override strategy aligned to `require_auth` |
| R-016 | Mitigated | PayCore ownership helpers referenced non-existent `tenant_id` on response schema | `backend/app/modules/paycore/router.py`, `backend/app/modules/paycore/schemas.py` | Tenant-scoped access checks could fail unpredictably and hide intent/refund ownership logic defects | Closed by explicit tenant lookup queries in `PayCoreService` and router ownership checks |
| R-017 | Mitigated | PayCore dependency provider accepted `Optional[Request]`, triggering FastAPI dependency field parsing errors in import/test contexts | `backend/app/modules/paycore/service.py`, `backend/tests/test_paycore_ownership.py` | Router import and dependency graph evaluation instability | Closed by Request-typed dependency signature and regression tests for ownership guards |
| R-018 | Mitigated | Auth/JWT paths relied on `datetime.utcnow()` (deprecated in Python 3.12+) causing warning noise and future runtime risk | `backend/app/services/auth_service.py`, `backend/app/models/token.py`, `backend/app/api/routes/auth.py`, `backend/app/core/jwt_middleware.py`, `backend/tests/test_auth_flow.py` | Higher maintenance risk and harder signal/noise in CI diagnostics | Closed by UTC helper migration + pipeline guard (`scripts/check_no_utcnow_auth.py`) + regression pass (`38 passed`) |

## Auth Convergence Decision Log

Decision:
- Keep: `backend/app/core/auth_deps.py` + `backend/app/core/jwt_middleware.py`.
- Deprecate and eliminate auth dependency use from: `backend/app/core/security.py`.

Rationale:
- Modern path is structured for scopes, roles, issuer/audience checks, and better operational control.
- Legacy path increases drift and complexity.

## Problems to track during implementation

### P-01 Backend auth migration complexity

- Risk: routers currently importing `app.core.security` may have subtle behavior differences when moved.
- Mitigation: migrate module-by-module with tests and a temporary compatibility adapter.

### P-02 Frontend auth transition regressions

- Risk: cleaning stale routes may break existing login assumptions in pages/components.
- Mitigation: implement one canonical session flow and smoke-test all protected routes.

### P-03 Event backbone migration coupling

- Risk: modules expecting local stub behavior may fail after EventStream-only migration.
- Mitigation: define event contract and apply migration in incremental slices.

### P-04 Rate-limit policy side effects

- Risk: stricter limits can break operational tooling or internal workers.
- Mitigation: split limits by human/API/worker principals and test with realistic load patterns.

## Critic-Agent checklist (pre-merge gate)

- Auth path check:
  - no new imports from legacy auth dependency path
  - role/scope checks present on mutating endpoints
- Error-sanitization check:
  - no raw internal exception strings in API responses
- Event check:
  - no new dependency on stub event bus for critical flows
- Rate-limit check:
  - endpoint has explicit limit if expensive or externally triggered
- Frontend auth check:
  - protected routes use canonical session source
  - no duplicate login/session logic

## Sprint-targeted mitigation order

### Sprint 1

- R-001, R-002, R-005, R-006, R-007

### Sprint 2

- R-003, R-004, R-008, R-009

### Sprint 3

- R-010, R-011, R-012 + polish of remaining migration debt
