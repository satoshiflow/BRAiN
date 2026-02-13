# BRAiN v0.3.0 Security & Stability Roadmap

**Audit Date:** 2026-02-12  
**Modules Audited:** 45/45 (100% Complete)  
**Total Issues Found:** 160+ (15 Critical, 30+ High, 60+ Medium, 50+ Low)

---

## Executive Summary

**DO NOT DEPLOY TO PRODUCTION** in current state. Critical security vulnerabilities allow unauthenticated remote code execution, arbitrary file access, and complete data loss.

### Critical Blocking Issues
1. **NO AUTHENTICATION SYSTEM** - Foundation for all security missing
2. **Skills Module:** Security Score 2/10 - Unauthenticated RCE via shell commands
3. **Factory Executor:** Syntax error prevents module import
4. **Memory/Learning:** No persistence - complete data loss on restart
5. **Physical Gateway:** Hardcoded master cryptographic key
6. **Sovereign Mode:** Ephemeral keys make signatures unverifiable

### Auth Architecture (NEW)
**See:** `docs/AUTH_MASTER_KNOWLEDGE_BASE.md`

- **V1 (Current):** OIDC + Authentik + Auth.js
- **V2 (Q2):** Enterprise RBAC + Multi-Tenant
- **V3 (Q3):** Agent Reputation + Wallet Binding
- **V4 (Q4+):** Sovereign AI Identity

---

## Phase 0: Authentication Foundation (Week 0-1) - AUTH SYSTEM

**Priority: HIGHEST - Blocks all other security work**

Based on AUTH_MASTER_KNOWLEDGE_BASE.md, implement OIDC-based auth system:

### 0.1 Auth Infrastructure Setup
| Task | Owner | Effort |
|------|-------|--------|
| Configure Authentik OIDC Provider | DevOps | 2h |
| Set up Auth.js in Next.js Frontend | Kimi | 4h |
| Create JWT Middleware (FastAPI) | Kimi | 4h |
| Create JWT Middleware (Node) | Kimi | 2h |
| Cookie Security Hardening | Claude | 2h |

### 0.2 Auth Integration
| Task | Owner | Effort |
|------|-------|--------|
| Login/Logout Flow Implementation | Kimi | 4h |
| Session Refresh Logic | Kimi | 2h |
| JWKS Dynamic Fetch | Kimi | 2h |
| Security Review (CSRF, Session Fixation) | Claude | 4h |

### 0.3 Agent Identity
| Task | Owner | Effort |
|------|-------|--------|
| Client Credentials Flow | Kimi | 4h |
| Agent Token Validation | Kimi | 2h |
| Agent vs Human Token Separation | Claude | 2h |
| Scope Validation | Kimi | 2h |

**Deliverables:**
- [ ] Dashboard requires login
- [ ] APIs reject invalid tokens  
- [ ] Agents authenticate independently
- [ ] IdP configurable (Authentik/Keycloak)

---

## Phase A: Emergency Fixes (Week 1-2) - DEPLOY BLOCKERS

### A1. Fix Critical Syntax/Runtime Errors
| Module | Issue | Fix | Effort |
|--------|-------|-----|--------|
| factory_executor | `await` outside async function (base.py:409) | Make method async | 30 min |
| immune | Missing enum values cause crash | Add RESOURCE_EXHAUSTION, AGENT_FAILURE, PERFORMANCE_DEGRADATION | 15 min |
| governor | RecoveryStrategy not serializable | Convert to proper Enum | 30 min |
| governor | Missing timedelta import | Add import | 5 min |

### A2. Add Authentication to Core Modules
**Requires: Phase 0 Auth System complete**

| Module | Endpoints | Fix | Effort |
|--------|-----------|-----|--------|
| skills | ALL | Add `@require_role(UserRole.OPERATOR)` | 2h |
| missions | ALL | Add `@require_auth` | 2h |
| safe_mode | /enable, /disable | Add `@require_auth` + admin check | 30 min |
| dmz_control | ALL | Add auth before subprocess calls | 1h |
| knowledge_graph | /reset | Add admin auth (destructive endpoint) | 30 min |
| foundation | /config | Add `@require_auth` + admin check | 30 min |
| memory | ALL | Add agent ownership checks | 2h |
| learning | ALL | Add agent ownership checks | 2h |

### A3. Remove Hardcoded Secrets
| Module | Secret Location | Fix | Effort |
|--------|-----------------|-----|--------|
| physical_gateway | security.py:23 | Move to env var | 15 min |
| axe_governance | __init__.py:82 | Move to env var | 15 min |

### A4. Critical Security Patches
| Module | Issue | Fix | Effort |
|--------|-------|-----|--------|
| skills | Shell command injection | Use exec instead of shell, add allowlist | 2h |
| skills | Path traversal | Implement path sandboxing | 1h |
| skills | SSRF vulnerability | Block internal IPs in http_request | 1h |

---

## Phase B: Core Stability (Week 2-3) - PRODUCTION READINESS

### B1. Implement Persistence (HIGH PRIORITY)
| Module | Current | Target | Effort |
|--------|---------|--------|--------|
| memory | In-memory dict | PostgreSQL + Qdrant | 2-3 days |
| learning | In-memory dict | PostgreSQL | 1-2 days |
| dna | In-memory dict | PostgreSQL (ORM exists) | 1 day |
| aro | In-memory dict | PostgreSQL | 1 day |
| foundation | In-memory audit | PostgreSQL append-only | 1 day |
| credits | In-memory events | PostgreSQL event store | 1-2 days |

### B2. Complete Authentication Coverage
| Module | Missing Endpoints | Effort |
|--------|-------------------|--------|
| missions | ALL | 2h |
| foundation | /config | 30 min |
| sovereign_mode | /bundles/*/sign, /keys | 1h |
| aro | ALL | 1h |
| fleet | ALL | 1h |

### B3. Input Validation & Sanitization
| Module | Validation Needed | Effort |
|--------|-------------------|--------|
| missions | Variable substitution, search params | 2h |
| knowledge_graph | Dataset name sanitization | 30 min |
| template_registry | Path traversal protection | 30 min |
| dmz_control | Command parameter sanitization | 1h |

---

## Phase C: Security Hardening (Week 4-5)

### C1. Authorization & Ownership
| Module | Issue | Fix | Effort |
|--------|-------|-----|--------|
| missions | No ownership checks | Add agent ownership validation | 2h |
| memory | Cross-agent access possible | Verify principal owns agent | 1h |
| learning | Cross-agent access | Add ownership checks | 1h |
| course_factory | No ownership validation | Add course ownership | 2h |

### C2. Rate Limiting & DoS Protection
| Module | Endpoint | Limit | Effort |
|--------|----------|-------|--------|
| skills | /execute | 10/min per user | 30 min |
| missions | /instantiate | 5/min per user | 30 min |
| immune | /event | 100/min global | 30 min |
| foundation | /validate | 50/min per user | 30 min |
| knowledge_graph | /add_data | 10MB max payload | 15 min |

### C3. Audit & Logging
| Module | Missing | Fix | Effort |
|--------|---------|-----|--------|
| safe_mode | Audit log for state changes | Add structured audit | 1h |
| skills | Execution audit trail | Log all skill executions | 1h |
| sovereign_mode | Bundle signing audit | Add signing log | 1h |
| paycore | Payment audit | Complete audit trail | 2h |

---

## Phase D: Performance & Reliability (Week 6-8)

### D1. Async I/O Fixes
| Module | Blocking Code | Fix | Effort |
|--------|---------------|-----|--------|
| factory | time.sleep() | asyncio.sleep() | 15 min |
| file skills | read_text() | aiofiles | 2h |
| immune | gc.collect() | run_in_executor | 30 min |
| physical_gateway | subprocess.run() | asyncio subprocess | 1h |

### D2. Database Optimizations
| Module | Issue | Fix | Effort |
|--------|-------|-----|--------|
| missions | No indexes on category/name | Add indexes | 30 min |
| missions | No pagination | Add skip/limit | 1h |
| memory | No eviction policy | Add LRU/size limits | 2h |
| learning | Unbounded aggregation | Add cleanup | 1h |

### D3. Resource Management
| Module | Issue | Fix | Effort |
|--------|-------|-----|--------|
| immune | Unbounded event storage | Add retention policy | 1h |
| knowledge_graph | Unbounded data | Add size limits | 30 min |
| learning | Unbounded metrics | Add pruning | 1h |

---

## Phase E: Code Quality (Week 9-10)

### E1. Type Safety
| Module | Issue | Fix | Effort |
|--------|-------|-----|--------|
| system_health | Any import missing | Add types | 30 min |
| Various | Missing type hints | Add hints | 4h total |

### E2. Documentation
| Module | Needed | Effort |
|--------|--------|--------|
| All | Security considerations | 8h total |
| All | API documentation | 8h total |

### E3. Testing
| Module | Coverage Target | Effort |
|--------|-----------------|--------|
| skills | 80% | 2 days |
| missions | 80% | 1 day |
| foundation | 80% | 1 day |

---

## Module Priority Matrix

### P0 - CRITICAL (Fix This Week)
1. **skills** - RCE vulnerability
2. **factory_executor** - Syntax error blocks import
3. **immune** - Runtime crash on enum access
4. **governor** - Serialization error
5. **physical_gateway** - Hardcoded master key
6. **axe_governance** - Hardcoded secret

### P1 - HIGH (Fix Before Production)
7. **memory** - No persistence
8. **learning** - No persistence
9. **dna** - No persistence
10. **missions** - No auth
11. **safe_mode** - No auth
12. **sovereign_mode** - No auth, ephemeral keys

### P2 - MEDIUM (Fix In Month 2)
13. **foundation** - No auth, in-memory audit
14. **knowledge_graph** - No auth
15. **dmz_control** - Command injection
16. **aro** - No persistence, mock git ops
17. **template_registry** - Path traversal
18. **fleet** - No auth, blocking I/O

### P3 - LOW (Nice to Have)
19. **monitoring** - Minor improvements
20. **metrics** - Payload validation
21. **telemetry** - Deprecation fixes
22. **ros2_bridge** - Mock implementation
23. **vision** - Mock implementation
24. **slam** - Mock implementation

---

## Success Metrics

### Phase A Complete When:
- [ ] All syntax/runtime errors fixed
- [ ] All critical auth gaps closed
- [ ] No hardcoded secrets in codebase
- [ ] Skills module Security Score ≥ 7/10

### Phase B Complete When:
- [ ] All core modules have persistence
- [ ] All endpoints have authentication
- [ ] Basic input validation on all user inputs

### Phase C Complete When:
- [ ] Authorization checks on all agent resources
- [ ] Rate limiting on expensive endpoints
- [ ] Audit logging on security events

### Production Ready When:
- [ ] All P0 and P1 issues resolved
- [ ] Security audit passed
- [ ] Load testing passed
- [ ] Penetration testing passed

---

## Resource Allocation (UPDATED with Auth)

### Phase 0: Auth Foundation (Week 0-1): 80 hours
- **Kimi:** 40h (Auth.js, JWT Middleware, Login Flow)
- **Claude:** 24h (Security Review, Architecture)
- **DevOps:** 16h (Authentik Setup, Config)

### Phase A: Emergency Fixes (Week 1-2): 40 hours
- Senior Dev: 20h (syntax fixes, auth integration, secrets)
- Security Expert: 20h (skills hardening)

### Phase B: Core Stability (Week 2-4): 120 hours
- Senior Dev: 60h (persistence implementation)
- Backend Dev: 60h (auth coverage, validation)

### Phase C: Security Hardening (Week 4-6): 80 hours
- Security Expert: 40h (authorization, audit)
- Senior Dev: 40h (rate limiting, optimization)

### Phase D+E: Performance & Quality (Week 6-10): 200 hours
- Backend Team: Full implementation of remaining items

**Total Estimate:** ~520 hours (13 weeks with 1 FTE)  
**Critical Path:** Phase 0 Auth → Phase A Fixes → Phase B Persistence

---

## Risk Assessment

### HIGH RISK - Immediate Action Required
- Skills RCE could compromise entire system
- No auth on DMZ control could allow infrastructure takeover
- Data loss on restart unacceptable for production

### MEDIUM RISK - Address Before Production
- Missing audit trails for compliance
- Performance issues under load
- Incomplete implementations (mock code)

### LOW RISK - Can Address Post-Launch
- Code style issues
- Documentation gaps
- Optional features

---

**Next Steps:**
1. Review and approve roadmap
2. Assign Phase A tasks to developers
3. Set up security review process
4. Schedule weekly progress checks

**Contact:** BRAiN Security Team  
**Review Cycle:** Weekly  
**Target Production:** Week 10 (with all P0/P1 complete)
