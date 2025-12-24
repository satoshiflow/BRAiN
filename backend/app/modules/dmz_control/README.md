# DMZ Control Module

**Version:** 1.0.0
**Phase:** B.3 - DMZ Control Backend

---

## Overview

The DMZ Control module manages the lifecycle of DMZ gateway services via Docker Compose API.

**Purpose:**
- Start/stop DMZ services programmatically
- Query DMZ status
- Enforce DMZ shutdown during Sovereign Mode

---

## API Endpoints

### GET /api/dmz/status

Get current DMZ status and service information.

**Response:**
```json
{
  "status": "running",
  "services": [
    {
      "name": "brain-dmz-telegram",
      "status": "running",
      "ports": ["8001:8000"]
    }
  ],
  "service_count": 1,
  "running_count": 1,
  "message": "All 1 DMZ service(s) running"
}
```

**Status Values:**
- `running` - All services running
- `stopped` - All services stopped
- `starting` - Services starting
- `stopping` - Services stopping
- `error` - Partial state or error
- `unknown` - Cannot determine status

---

### POST /api/dmz/start

Start all DMZ services.

**Request:**
```json
{
  "action": "start",
  "force": false,
  "timeout": 30
}
```

**Response:**
```json
{
  "success": true,
  "action": "start",
  "previous_status": "stopped",
  "current_status": "running",
  "services_affected": ["brain-dmz-telegram"],
  "message": "DMZ started successfully (1 services)"
}
```

---

### POST /api/dmz/stop

Stop all DMZ services.

**Request:**
```json
{
  "action": "stop",
  "force": false,
  "timeout": 30
}
```

**Response:**
```json
{
  "success": true,
  "action": "stop",
  "previous_status": "running",
  "current_status": "stopped",
  "services_affected": ["brain-dmz-telegram"],
  "message": "DMZ stopped successfully"
}
```

---

## Service Architecture

```
DMZControlService
├── get_status() -> DMZStatusResponse
│   └── Runs: docker compose -f docker-compose.dmz.yml ps
│
├── start(request) -> DMZControlResponse
│   └── Runs: docker compose -f docker-compose.dmz.yml up -d
│
└── stop(request) -> DMZControlResponse
    └── Runs: docker compose -f docker-compose.dmz.yml down
```

---

## Sovereign Mode Integration

When Sovereign Mode is activated, the DMZ is automatically stopped:

1. **Sovereign Mode service** calls `dmz_control.stop()`
2. **Audit event emitted**: `sovereign.dmz_stopped`
3. **DMZ services stopped** via Docker Compose
4. **Verification**: Status checked to confirm all services stopped
5. **Fail-Closed**: If stop fails, Sovereign Mode activation fails

---

## Security

### Access Control
- **TODO**: Add admin/owner authentication middleware
- All operations logged
- All operations auditable

### Fail-Closed Design
- No partial states allowed
- Stop operation must succeed completely
- If stop fails, error is raised and operation is rolled back

### Audit Trail
- All DMZ control operations are audited
- Audit events:
  - `dmz.started`
  - `dmz.stopped`
  - `dmz.stop_failed`

---

## Usage Examples

### Python (Internal)
```python
from backend.app.modules.dmz_control import get_dmz_control_service

service = get_dmz_control_service()

# Get status
status = await service.get_status()
print(f"DMZ status: {status.status}")

# Stop DMZ
response = await service.stop(DMZControlRequest(action="stop"))
if response.success:
    print(f"DMZ stopped: {response.message}")
```

### cURL (External)
```bash
# Get status
curl http://localhost:8000/api/dmz/status

# Start DMZ
curl -X POST http://localhost:8000/api/dmz/start \
  -H "Content-Type: application/json" \
  -d '{"action": "start", "force": false}'

# Stop DMZ
curl -X POST http://localhost:8000/api/dmz/stop \
  -H "Content-Type: application/json" \
  -d '{"action": "stop", "force": false}'
```

---

## Files

```
backend/app/modules/dmz_control/
├── __init__.py          # Module exports
├── schemas.py           # Pydantic models
├── service.py           # DMZControlService
├── router.py            # FastAPI router
└── README.md            # This file
```

---

## Dependencies

- **Docker Compose**: System must have `docker compose` command available
- **Permissions**: Backend process must have permission to run docker commands
- **Compose File**: `docker-compose.dmz.yml` must exist in project root

---

## Error Handling

### DMZ already running (start)
- Returns success with message "DMZ already running (no action needed)"
- No error raised (idempotent)

### DMZ already stopped (stop)
- Returns success with message "DMZ already stopped (no action needed)"
- No error raised (idempotent)

### Partial state detected
- Status returns `error` with message describing inconsistent state
- Example: "Partial state: 0/1 services running (inconsistent state)"

### Docker Compose command fails
- Returns error response with stderr output
- Logs error with full context
- Raises HTTPException with 500 status code

---

## Future Enhancements

### Phase B (Current)
- ✅ Basic start/stop/status operations
- ✅ Docker Compose integration
- ✅ Sovereign Mode enforcement
- ❌ Authentication/authorization (TODO)

### Future Phases
- [ ] Real-time status streaming (WebSocket)
- [ ] Service-level control (start/stop individual gateways)
- [ ] Health monitoring and auto-restart
- [ ] Metrics collection (uptime, request counts)
- [ ] Rate limiting for DMZ operations

---

**Last Updated:** 2025-12-24
**Version:** 1.0.0 (Phase B.3 - Initial Implementation)
