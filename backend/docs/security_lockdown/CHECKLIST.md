# BRAiN Backend Security Lockdown - Checklist

**Date:** 2026-02-25  
**Status:** IN PROGRESS

---

## Subagent A: Auth Hardening ✅ COMPLETE

- [x] Audit all endpoints for auth requirements
- [x] Verify auth dependencies in `app/core/auth_deps.py`
- [x] Document protected routes
- [x] Identify public endpoints (health, login, register)
- [x] Write results to RESULTS.md

---

## Subagent B: Input Validation & SQL Injection Prevention ⏳ PENDING

- [ ] Audit all user input endpoints
- [ ] Verify SQLAlchemy parameterization
- [ ] Check raw SQL queries
- [ ] Validate file upload endpoints
- [ ] Test for XSS vulnerabilities
- [ ] Write results to RESULTS.md

---

## Subagent C: Dependency & Supply Chain Security ⏳ PENDING

- [ ] Run `pip audit` or `safety check`
- [ ] Check for known CVEs in dependencies
- [ ] Review outdated packages
- [ ] Verify package signatures where possible
- [ ] Document critical dependency risks
- [ ] Write results to RESULTS.md

---

## Subagent D: Secrets & Config Hygiene ✅ COMPLETE

- [x] Search for hardcoded secrets:
  - [x] `SECRET_KEY = "..."` patterns
  - [x] `PASSWORD = "..."` patterns
  - [x] `API_KEY = "..."` patterns
  - [x] `TOKEN = "..."` patterns
  - [x] Default credentials
- [x] Create `.env.example` with all required env vars (no real values)
- [x] Replace hardcoded values with `os.environ.get()` or pydantic Settings
- [x] Ensure secrets are NOT logged:
  - [x] Check logging statements don't print sensitive data
  - [x] No `print(secret_key)` patterns
- [x] Basic git history scan:
  - [x] Check if secrets were committed
  - [x] Document rotation needed
- [x] Update config files:
  - [x] Database connection strings
  - [x] JWT secret keys
  - [x] External API keys
  - [x] Redis passwords
- [x] Write results to RESULTS.md

---

## Subagent E: Error Handling & Information Disclosure ⏳ PENDING

- [ ] Review error handlers for info leakage
- [ ] Check stack traces in production responses
- [ ] Verify debug endpoints are disabled in prod
- [ ] Test for verbose error messages
- [ ] Write results to RESULTS.md

---

## Overall Status

| Subagent | Task | Status |
|----------|------|--------|
| A | Auth Hardening | ✅ Complete |
| B | Input Validation | ⏳ Pending |
| C | Dependency Security | ⏳ Pending |
| D | Secrets Hygiene | ✅ Complete |
| E | Error Handling | ⏳ Pending |

**Overall Progress:** 2/5 Complete (40%)
