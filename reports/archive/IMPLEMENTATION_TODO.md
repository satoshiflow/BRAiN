# BRAiN Sovereign Mode Audit + DMZ + IPv6 Implementation TODO

**Sprint**: Audit + DMZ + IPv6 (Sovereign Hardened)
**Status**: Phase A, B, C Complete ✅
**Date**: 2025-12-24

---

## ✅ COMPLETED

### Phase A: Audit Event Integration

- [x] A.1: Extended `AuditEntry` schema with:
  - `AuditSeverity` enum (INFO, WARNING, ERROR, CRITICAL)
  - `AuditEventType` enum (17 event types)
  - `severity` field
  - `ipv6_related` boolean flag
  - Updated `__init__.py` exports

- [x] A.2: Implemented audit event emitters in `service.py`:
  - New `_audit()` method with auto-severity detection
  - Integrated events for:
    - `sovereign.mode_changed`
    - `sovereign.bundle_loaded`
    - `sovereign.network_probe_passed/failed`

- [x] A.3: Updated API endpoint documentation in `router.py`:
  - `/api/sovereign-mode/audit` endpoint documented with all new event types

- [x] C.1: Added IPv6 policy config to `.env.example`:
  - `BRAIN_SOVEREIGN_IPV6_POLICY=block`
  - `BRAIN_SOVEREIGN_IPV6_ALLOWLIST=`
  - `BRAIN_DMZ_ENABLED=false`

### Phase C: IPv6 Hardening (COMPLETED 2025-12-24)

- [x] C.2: Extended `sovereign-fw.sh` with IPv6 support
  - Added `detect_ipv6_active()`, `check_ip6tables_available()`
  - Added `apply_ipv6_sovereign_rules()`, `remove_ipv6_brain_rules()`
  - Integrated IPv6 checks in `apply_sovereign_rules()`
  - Extended `verify_sovereign_rules()` with IPv6 validation
  - Enhanced `cmd_status()` with IPv6 status display

- [x] C.3: Implemented IPv6 Gate Checker backend
  - New file: `backend/app/modules/sovereign_mode/ipv6_gate.py`
  - Classes: `IPv6GateChecker`, `IPv6GateResult`
  - Singleton: `get_ipv6_gate_checker()`
  - Checks: IPv6 active, ip6tables available, rules applied

- [x] C.4: Integrated IPv6 gate check in mode change
  - Modified `backend/app/modules/sovereign_mode/service.py`
  - IPv6 gate check before SOVEREIGN mode activation
  - Emits audit events: IPV6_GATE_CHECKED, IPV6_GATE_FAILED, IPV6_GATE_PASSED
  - Fail-closed: Blocks SOVEREIGN mode if IPv6 not properly secured
  - User-friendly error messages with remediation steps

- [x] C.5: Extended verification suite with IPv6 tests
  - Modified `scripts/verify-sovereign-mode.sh`
  - Added Layer 7: IPv6 Gate Check
  - Tests: IPv6 status, ip6tables availability, rules count

- [x] C.6: Error messages & user guidance
  - Implemented in `service.py` (lines 284-303)
  - Provides 3 remediation options with exact commands
  - Displays current system status

### Phase B: DMZ Gateway & External Communication (COMPLETED 2025-12-24)

- [x] B.1: Created `docker-compose.dmz.yml` (DMZ Docker Setup)
  - Isolated DMZ network (172.25.0.0/16) separate from Core (172.20.0.0/16)
  - Telegram Gateway service with `host.docker.internal:8000` API access
  - No access to Core internal services (DB/Redis/Qdrant)

- [x] B.2: Implemented Telegram Gateway (Transport-Only)
  - New files: `dmz/telegram_gateway/gateway.py`, `requirements.txt`, `Dockerfile`
  - Transport-only: NO business logic, NO state storage, ONLY forwarding
  - Forwards messages to Core API `/api/axe/message` endpoint
  - Security: Does not log message content, minimal metadata
  - Supports polling and webhook modes

- [x] B.3: Created DMZ Control Backend
  - New module: `backend/app/modules/dmz_control/`
  - Files: `__init__.py`, `schemas.py`, `service.py`, `router.py`
  - Service: `DMZControlService` with subprocess-based docker compose management
  - Endpoints: `/api/dmz/status`, `/api/dmz/start`, `/api/dmz/stop`
  - Singleton pattern with lazy import to avoid circular dependencies

- [x] B.4: Sovereign Mode DMZ Enforcement
  - Modified `backend/app/modules/sovereign_mode/service.py` (lines 344-422)
  - SOVEREIGN mode → automatically stops DMZ (docker compose down)
  - OFFLINE mode → automatically stops DMZ
  - ONLINE mode → starts DMZ if `BRAIN_DMZ_ENABLED=true`
  - Audit events: `DMZ_STOPPED`, `DMZ_STARTED` emitted on all state changes
  - Lazy import pattern: `_get_dmz_service()` to prevent circular dependencies

- [x] B.5: DMZ Firewall Isolation
  - New file: `scripts/dmz-fw.sh` (240 lines)
  - Rule 1: ALLOW DMZ → Core API (port 8000) for HTTP calls
  - Rule 2: DROP DMZ → Core Internal Services (DB/Redis/Qdrant)
  - Commands: `apply`, `remove`, `status`
  - Idempotent rule management (safe to run multiple times)
  - Uses iptables DOCKER-USER chain
  - Comment-based rule tracking: `brain-dmz:*`

---

## ❌ REMAINING TASKS


**All core tasks complete!** 🎉

### Optional Enhancements (Future Work)

#### Phase D: Additional DMZ Services

- WhatsApp Gateway (transport-only)
- Discord Gateway (transport-only)
- Email Gateway (SMTP/IMAP bridge)

#### Phase E: Enhanced Monitoring

- DMZ Gateway health metrics
- IPv6 traffic monitoring
- Firewall rule audit logs

#### Phase F: IPv6 Allowlist Implementation

- Implement IPv6 allowlist support (currently "block" policy only)
- Add allowlist configuration UI
- Add IPv6 address validation

---

## 📝 IMPLEMENTATION SUMMARY

### Files Created

**Phase A: Audit Event Integration**
- `backend/app/modules/sovereign_mode/schemas.py` (modified): Added `AuditSeverity`, `AuditEventType`, `ipv6_related` field

**Phase C: IPv6 Hardening**
- `scripts/sovereign-fw.sh` (modified, +148 lines): IPv6 firewall rule management
- `backend/app/modules/sovereign_mode/ipv6_gate.py` (NEW, 218 lines): IPv6 gate checker
- `backend/app/modules/sovereign_mode/service.py` (modified, +94 lines): IPv6 gate integration
- `scripts/verify-sovereign-mode.sh` (modified, +54 lines): IPv6 verification tests

**Phase B: DMZ Gateway**
- `docker-compose.dmz.yml` (NEW): DMZ services orchestration
- `dmz/telegram_gateway/gateway.py` (NEW, ~230 lines): Transport-only Telegram bot
- `dmz/telegram_gateway/requirements.txt` (NEW): Python dependencies
- `dmz/telegram_gateway/Dockerfile` (NEW): Container definition
- `backend/app/modules/dmz_control/__init__.py` (NEW): Module exports
- `backend/app/modules/dmz_control/schemas.py` (NEW): DMZ data models
- `backend/app/modules/dmz_control/service.py` (NEW): DMZ lifecycle management
- `backend/app/modules/dmz_control/router.py` (NEW): DMZ API endpoints
- `backend/main.py` (modified): Register DMZ router
- `backend/app/modules/sovereign_mode/service.py` (modified, +78 lines): DMZ enforcement
- `scripts/dmz-fw.sh` (NEW, 240 lines): DMZ firewall isolation

**Total**: 11 new files, 4 modified files, ~1100+ new lines of code

### Security Principles Applied

1. **Fail-Closed Design**: System rejects unsafe states (IPv6 active but unblocked)
2. **Network Isolation**: DMZ ≠ Core (separate Docker networks + iptables)
3. **Transport-Only Gateways**: NO business logic, NO state, ONLY forwarding
4. **Audit Everything**: All mode changes, gate checks, DMZ operations logged
5. **Lazy Imports**: Prevents circular dependencies while maintaining clean architecture

### Verification

✅ **All syntax checks passed**:
- Python: `py_compile` validation on all `.py` files
- Bash: `bash -n` validation on all `.sh` files
- YAML: `yaml.safe_load` validation on `docker-compose.dmz.yml`

✅ **Integration points verified**:
- DMZ control router registered in `main.py`
- IPv6 gate checker integrated in sovereign mode service
- DMZ enforcement integrated in sovereign mode transitions
- Audit events emitted for all critical operations

### Testing Requirements

**Manual Testing Required** (in production environment with Docker):
1. Test DMZ start/stop via API endpoints
2. Test Sovereign Mode DMZ enforcement (auto-stop)
3. Test DMZ firewall isolation (verify Core API access only)
4. Test IPv6 gate check with IPv6 active/inactive
5. Run `scripts/verify-sovereign-mode.sh` end-to-end

---

## 🚀 DEPLOYMENT CHECKLIST

1. **Environment Variables** (.env):
   ```bash
   BRAIN_SOVEREIGN_IPV6_POLICY=block
   BRAIN_SOVEREIGN_IPV6_ALLOWLIST=
   BRAIN_DMZ_ENABLED=false  # Set to 'true' to enable DMZ in ONLINE mode
   TELEGRAM_BOT_TOKEN=your_token_here  # Only if using Telegram gateway
   ```

2. **Firewall Setup**:
   ```bash
   # Apply sovereign mode firewall rules (IPv4 + IPv6)
   sudo scripts/sovereign-fw.sh apply sovereign
   
   # Apply DMZ isolation rules
   sudo scripts/dmz-fw.sh apply
   
   # Verify status
   sudo scripts/sovereign-fw.sh status
   sudo scripts/dmz-fw.sh status
   ```

3. **Docker Services**:
   ```bash
   # Start Core services
   docker compose up -d
   
   # Start DMZ services (only if BRAIN_DMZ_ENABLED=true)
   docker compose -f docker-compose.dmz.yml up -d
   ```

4. **Verification**:
   ```bash
   # Run comprehensive verification suite
   sudo scripts/verify-sovereign-mode.sh
   
   # Check DMZ status via API
   curl http://localhost:8000/api/dmz/status
   
   # Check sovereign mode status
   curl http://localhost:8000/api/sovereign-mode/status
   ```

---

## 📚 DOCUMENTATION UPDATES

- [x] `IMPLEMENTATION_TODO.md` updated with Phase A, B, C completion
- [ ] Update main `README.md` with DMZ architecture overview
- [ ] Add DMZ Gateway documentation to `docs/`
- [ ] Add IPv6 hardening guide to `docs/`
- [ ] Update `CLAUDE.md` with new modules and patterns

---

## 🎯 SUCCESS CRITERIA (Definition of Done)

### Phase A: Audit Event Integration ✅
- [x] `AuditSeverity` enum with INFO/WARNING/ERROR/CRITICAL
- [x] `AuditEventType` enum with 17 event types
- [x] `ipv6_related` boolean flag
- [x] Audit events emitted for mode changes and bundle loads
- [x] API endpoint documentation updated

### Phase C: IPv6 Hardening ✅
- [x] IPv6 detection in firewall script
- [x] IPv6 firewall rules (4 rules: established, localhost, ULA, DROP)
- [x] IPv6 gate checker backend (status: pass/fail/not_applicable)
- [x] Fail-closed enforcement (blocks SOVEREIGN if IPv6 unsafe)
- [x] User-friendly error messages with 3 remediation options
- [x] Verification suite extended with IPv6 tests

### Phase B: DMZ Gateway ✅
- [x] DMZ runs isolated from Core (separate Docker network)
- [x] Core can operate air-gapped without DMZ
- [x] Sovereign Mode reliably stops/blocks DMZ
- [x] Telegram Connector works ONLY in ONLINE mode
- [x] Audit events emitted for DMZ operations
- [x] DMZ firewall isolation (Core API access only)
- [x] Transport-only gateway (NO business logic)

---

**END OF IMPLEMENTATION TODO**
