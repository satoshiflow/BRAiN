# Sprint 7.4: Global Kill-Switch & Safe Mode

**Version:** 1.0.0
**Status:** ✅ IMPLEMENTED
**Date:** 2025-12-25

---

## Overview

Sprint 7.4 implements a **global kill-switch** that instantly transitions BRAiN to read-only safe mode. No restart required, fully audited, idempotent.

**When Safe Mode is Enabled:**
- ❌ NO new factory executions
- ❌ NO deployments
- ❌ NO bundle loads
- ✅ Read-only APIs continue
- ✅ Monitoring & metrics continue
- ✅ Audit logging continues

**Activation Methods:**
1. Environment variable: `BRAIN_SAFE_MODE=true`
2. API call: `POST /api/safe-mode/enable`

---

## Quick Start

### Enable Safe Mode

```bash
# Via API
curl -X POST http://localhost:8000/api/safe-mode/enable \
  -H "Content-Type: application/json" \
  -d '{"reason": "Emergency maintenance"}'

# Via Environment (requires restart)
export BRAIN_SAFE_MODE=true
docker compose restart backend
```

### Check Status

```bash
curl http://localhost:8000/api/safe-mode/status
```

### Disable Safe Mode

```bash
curl -X POST http://localhost:8000/api/safe-mode/disable \
  -H "Content-Type: application/json" \
  -d '{"reason": "Maintenance complete"}'
```

---

## API Reference

### GET `/api/safe-mode/status`

**Response:**
```json
{
  "success": true,
  "safe_mode_enabled": true,
  "enabled_at": "2025-12-25T12:00:00Z",
  "enabled_reason": "Emergency maintenance",
  "enabled_by": "api",
  "blocked_operations": [
    "Factory executions",
    "Deployments",
    "Bundle loads"
  ],
  "allowed_operations": [
    "Read-only APIs",
    "Monitoring",
    "Audit log access",
    "Metrics"
  ]
}
```

### POST `/api/safe-mode/enable`

**Request:**
```json
{
  "reason": "Emergency maintenance"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Safe mode enabled successfully",
  "was_enabled": true,
  "safe_mode_enabled": true,
  "enabled_at": "2025-12-25T12:00:00Z"
}
```

**Audit Event:** `system.safe_mode_enabled` (CRITICAL severity)

### POST `/api/safe-mode/disable`

**Request:**
```json
{
  "reason": "Maintenance complete"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Safe mode disabled successfully",
  "was_disabled": true,
  "safe_mode_enabled": false
}
```

**Audit Event:** `system.safe_mode_disabled` (WARNING severity)

---

## How It Works

### Architecture

```
┌──────────────────────────────────────┐
│   Environment Variable Check         │
│   BRAIN_SAFE_MODE=true/false        │
└────────────┬─────────────────────────┘
             │
┌────────────▼─────────────────────────┐
│   SafeModeService (Singleton)        │
│                                      │
│   • safe_mode_enabled (bool)        │
│   • check_and_block(operation)      │
│   • enable_safe_mode(reason)        │
│   • disable_safe_mode(reason)       │
└────────────┬─────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼────┐    ┌───────▼──────┐
│Executor│    │ API Endpoint │
│ Check  │    │    Block     │
└────────┘    └──────────────┘
```

### Execution Flow

1. **Executor attempts to run step**
2. **Safe mode check:**
   ```python
   if SAFE_MODE_AVAILABLE:
       safe_mode = get_safe_mode_service()
       safe_mode.check_and_block("executor_website_step_deploy")
   ```
3. **If safe mode enabled:**
   - Raises `RuntimeError` with detailed message
   - Emits audit event: `system.safe_mode_execution_blocked`
   - Returns actionable error to user
4. **If safe mode disabled:**
   - Execution continues normally

---

## Integration Points

### Executor Integration

**File:** `backend/app/modules/factory_executor/base.py:180-190`

```python
# Sprint 7.4: Safe Mode Check
if SAFE_MODE_AVAILABLE:
    try:
        safe_mode = get_safe_mode_service()
        safe_mode.check_and_block(f"executor_{self.name}_step_{step.step_id}")
    except RuntimeError:
        # Safe mode is enabled - block execution
        raise
```

**Blocked Operations:**
- All executor step executions
- Factory plan executions
- Deployments via executors

---

## Audit Trail

### Audit Events

**1. Safe Mode Enabled**
- **Event Type:** `system.safe_mode_enabled`
- **Severity:** CRITICAL
- **Logged Data:**
  - Reason for enabling
  - Who/what enabled (api, env, manual)
  - Timestamp

**2. Safe Mode Disabled**
- **Event Type:** `system.safe_mode_disabled`
- **Severity:** WARNING
- **Logged Data:**
  - Reason for disabling
  - Who/what disabled
  - Timestamp

**3. Execution Blocked**
- **Event Type:** `system.safe_mode_execution_blocked`
- **Severity:** WARNING
- **Logged Data:**
  - Blocked operation name
  - Timestamp

### Example Audit Entries

```json
[
  {
    "id": "safe_mode_enabled_1703001234567",
    "timestamp": "2025-12-25T12:00:00Z",
    "event_type": "system.safe_mode_enabled",
    "severity": "critical",
    "success": true,
    "reason": "Emergency maintenance",
    "triggered_by": "api"
  },
  {
    "id": "execution_blocked_1703001234568",
    "timestamp": "2025-12-25T12:05:00Z",
    "event_type": "system.safe_mode_execution_blocked",
    "severity": "warning",
    "success": false,
    "reason": "Operation blocked: executor_website_step_deploy"
  },
  {
    "id": "safe_mode_disabled_1703001234569",
    "timestamp": "2025-12-25T13:00:00Z",
    "event_type": "system.safe_mode_disabled",
    "severity": "warning",
    "success": true,
    "reason": "Maintenance complete",
    "triggered_by": "api"
  }
]
```

---

## Error Messages

### Execution Blocked Error

When safe mode blocks an execution, users receive:

```
🛑 Operation blocked: BRAiN is in SAFE MODE.
Blocked operation: executor_website_step_deploy
Safe mode enabled at: 2025-12-25T12:00:00Z
Reason: Emergency maintenance
Enabled by: api

To disable safe mode:
1. Via API: POST /api/safe-mode/disable
2. Via ENV: Set BRAIN_SAFE_MODE=false and restart
```

---

## Use Cases

### Use Case 1: Emergency Incident Response

**Scenario:** Critical security issue detected

```bash
# Immediately freeze all operations
curl -X POST http://localhost:8000/api/safe-mode/enable \
  -d '{"reason": "Security incident - investigating"}'

# Investigate issue while system is frozen
# ... investigation ...

# Resume operations after fix
curl -X POST http://localhost:8000/api/safe-mode/disable \
  -d '{"reason": "Security issue resolved"}'
```

### Use Case 2: Planned Maintenance

```bash
# Enable before maintenance window
curl -X POST http://localhost:8000/api/safe-mode/enable \
  -d '{"reason": "Scheduled maintenance 2025-12-25 12:00-13:00"}'

# Perform maintenance safely
# ... database upgrades, config changes, etc. ...

# Disable after maintenance
curl -X POST http://localhost:8000/api/safe-mode/disable \
  -d '{"reason": "Maintenance complete - verified operational"}'
```

### Use Case 3: Pre-Deployment Testing

```bash
# Enable safe mode for testing
export BRAIN_SAFE_MODE=true

# Start backend - safe mode automatically enabled
docker compose up -d backend

# Test read-only operations
curl http://localhost:8000/metrics
curl http://localhost:8000/api/sovereign-mode/status

# Verify executions are blocked
curl -X POST http://localhost:8000/api/factory/execute \
  -d '...'
# Expected: RuntimeError with safe mode message

# Disable for normal operation
export BRAIN_SAFE_MODE=false
docker compose restart backend
```

---

## Design Principles

### 1. Fail-Closed
- Safe mode blocks by default
- No implicit bypasses
- Clear error messages

### 2. Idempotent
- Multiple enable calls → no error
- Multiple disable calls → no error
- State transitions are safe

### 3. No Restart Required
- API activation/deactivation instant
- Environment variable requires restart (by design)
- State persists in-memory

### 4. Full Audit Trail
- Every enable/disable logged
- Every blocked execution logged
- Severity levels appropriate (CRITICAL for enable)

### 5. Read-Only Safe
- Monitoring continues
- Metrics continue
- Audit log readable
- Status checks allowed

---

## Implementation Checklist

✅ **S7.4.1** - SafeModeService implemented
✅ **S7.4.2** - Environment variable support (`BRAIN_SAFE_MODE`)
✅ **S7.4.3** - API endpoints (`/enable`, `/disable`, `/status`)
✅ **S7.4.4** - Audit events added (3 event types)
✅ **S7.4.5** - Executor integration (safe mode checks)
✅ **S7.4.6** - Idempotent enable/disable
✅ **S7.4.7** - Detailed error messages
✅ **S7.4.8** - Full audit trail
✅ **S7.4.9** - Documentation complete

---

## Future Enhancements (Out of Scope)

**Not Implemented (Future Work):**
- Automatic safe mode triggers (e.g., high error rate)
- Scheduled safe mode windows
- Multi-user authorization for disable
- Safe mode levels (partial freeze vs full freeze)
- WebSocket notifications for safe mode changes

---

## Conclusion

Sprint 7.4 delivers an **instant kill-switch** for BRAiN operations, enabling:
- ✅ Emergency incident response
- ✅ Planned maintenance windows
- ✅ Pre-deployment testing
- ✅ Operational safety net

**Key Achievement:** Instant freeze capability with full audit trail and no restart required.

---

**Sprint 7.4 Status:** ✅ COMPLETE
**Next:** Sprint 7 Overview & Acceptance
