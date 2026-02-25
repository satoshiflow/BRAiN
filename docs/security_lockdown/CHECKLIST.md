# Security Lockdown Checklist

Checklist for tracking security hardening tasks across BRAiN backend.

---

## Knowledge Graph Reset Protection (Subagent E)

### Implementation Status

| Task | Status | Notes |
|------|--------|-------|
| Find Knowledge Graph reset endpoint | ✅ Complete | Found at `DELETE /api/knowledge-graph/reset` in `/app/modules/knowledge_graph/router.py` |
| Add admin role protection | ✅ Complete | Both `/reset/request` and `/reset/confirm` require `require_admin_user` dependency |
| Add confirmation token system | ✅ Complete | 2-step process with UUID tokens, 5-min expiration, single-use |
| Add audit logging | ✅ Complete | Logs to sovereign mode audit service (fallback to loguru), includes IP, timestamp, actor |
| Deprecate old endpoint | ✅ Complete | Old `DELETE /reset` now returns HTTP 410 with migration instructions |
| Document in RESULTS.md | ✅ Complete | Full documentation in `docs/security_lockdown/RESULTS.md` |

### Code Review Checklist

- [x] No hardcoded secrets
- [x] Proper error handling
- [x] Input validation on confirmation token
- [x] Proper HTTP status codes (403, 410, etc.)
- [x] Audit trail for all actions
- [x] Clear deprecation path for old endpoint

### Production Readiness

- [ ] Move token storage to Redis (currently in-memory)
- [ ] Add rate limiting per IP
- [ ] Consider soft-delete/archive before hard delete
- [ ] Add notification alerts for reset events
- [ ] Backup confirmation before destructive operations

### Security Verification

```bash
# Test 1: Non-admin cannot request reset
curl -X POST http://localhost:8000/api/knowledge-graph/reset/request \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -d '{"reason": "test"}'
# Expected: 403 Forbidden

# Test 2: Invalid token rejected
curl -X POST http://localhost:8000/api/knowledge-graph/reset/confirm \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"confirmation_token": "invalid", "confirm_delete": true}'
# Expected: 400 Bad Request - Invalid token

# Test 3: Old endpoint returns 410
curl -X DELETE http://localhost:8000/api/knowledge-graph/reset
# Expected: 410 Gone - Deprecation message

# Test 4: Missing confirm_delete fails
curl -X POST http://localhost:8000/api/knowledge-graph/reset/confirm \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"confirmation_token": "valid-token", "confirm_delete": false}'
# Expected: 400 Bad Request - Must set confirm_delete=True
```

---

## Other Security Tasks (Future)

### Authentication & Authorization
- [ ] Implement rate limiting across all endpoints
- [ ] Add API key authentication option
- [ ] Implement JWT refresh token mechanism
- [ ] Add MFA for admin operations

### Data Protection
- [ ] Encrypt sensitive data at rest
- [ ] Implement data retention policies
- [ ] Add data export functionality (GDPR compliance)

### Audit & Compliance
- [ ] Centralize audit logging service
- [ ] Implement log aggregation (ELK stack)
- [ ] Add alerting for suspicious activities

### Infrastructure
- [ ] Enable HTTPS-only communication
- [ ] Configure security headers (HSTS, CSP)
- [ ] Implement DDoS protection

---

*Last updated: 2026-02-25*
