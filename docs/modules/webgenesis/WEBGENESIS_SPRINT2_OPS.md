# WebGenesis Sprint II - Operational Features Guide

**Version:** Sprint II (2.0.0)
**Last Updated:** 2025-12-25
**Author:** WebGenesis Team

---

## Table of Contents

1. [Overview](#overview)
2. [Lifecycle Management](#lifecycle-management)
3. [Release System](#release-system)
4. [Health Monitoring](#health-monitoring)
5. [Rollback Procedures](#rollback-procedures)
6. [Configuration Reference](#configuration-reference)
7. [Troubleshooting](#troubleshooting)
8. [Security Considerations](#security-considerations)

---

## Overview

Sprint II extends WebGenesis with production-ready operational features:

- **Lifecycle Management** - Start/stop/restart/remove deployed sites
- **Release Snapshots** - Rollback-capable deployment history
- **Health Monitoring** - HTTP health checks with auto-rollback
- **Retention Policies** - Automatic cleanup of old releases

### Key Principles

1. **Non-Destructive** - Operations preserve deployment data by default
2. **Idempotent** - Safe to retry operations
3. **Auditable** - All operations logged comprehensively
4. **Fail-Safe** - Graceful degradation on errors

---

## Lifecycle Management

### Overview

Control the runtime state of deployed sites using standard Docker Compose lifecycle operations.

**Trust Tier Requirement:** LOCAL or DMZ only (EXTERNAL blocked with HTTP 403)

### Operations

#### Start Site

Start a stopped container:

```bash
POST /api/webgenesis/{site_id}/start
```

**Headers (DMZ):**
```
x-dmz-gateway-id: telegram_gateway
x-dmz-gateway-token: <token>
```

**Response:**
```json
{
  "success": true,
  "site_id": "my-site_20250101120000",
  "operation": "start",
  "lifecycle_status": "running",
  "message": "Site started successfully",
  "warnings": []
}
```

**Use Cases:**
- Resume site after scheduled maintenance
- Restart after resource limit hit
- Manual recovery from stopped state

---

#### Stop Site

Stop a running container (graceful shutdown):

```bash
POST /api/webgenesis/{site_id}/stop
```

**Response:**
```json
{
  "success": true,
  "site_id": "my-site_20250101120000",
  "operation": "stop",
  "lifecycle_status": "stopped",
  "message": "Site stopped successfully",
  "warnings": []
}
```

**Use Cases:**
- Scheduled maintenance windows
- Resource conservation (temporary pause)
- Pre-deployment preparation

**⚠️ Note:** Container remains on disk. Use `remove` to delete.

---

#### Restart Site

Restart a site (stop + start):

```bash
POST /api/webgenesis/{site_id}/restart
```

**Response:**
```json
{
  "success": true,
  "site_id": "my-site_20250101120000",
  "operation": "restart",
  "lifecycle_status": "running",
  "message": "Site restarted successfully",
  "warnings": []
}
```

**Use Cases:**
- Apply configuration changes
- Clear memory/cache issues
- Routine refresh

---

#### Remove Site

Delete container and optionally site data:

```bash
DELETE /api/webgenesis/{site_id}
```

**Body:**
```json
{
  "keep_data": true
}
```

**Response:**
```json
{
  "success": true,
  "site_id": "my-site_20250101120000",
  "message": "Site removed successfully (data preserved)",
  "data_removed": false,
  "warnings": []
}
```

**Parameters:**
- `keep_data: true` (default) - Delete container only, preserve files
- `keep_data: false` - **DESTRUCTIVE** - Delete all site data including releases

**Use Cases:**
- Clean shutdown before redeployment (`keep_data: true`)
- Complete site deletion (`keep_data: false`)
- Resource cleanup

**⚠️ WARNING:** `keep_data: false` is **irreversible**. All releases, source, and build artifacts are permanently deleted.

---

### Lifecycle Status States

| Status | Description | Operations Allowed |
|--------|-------------|-------------------|
| `running` | Container active and serving | stop, restart, remove |
| `stopped` | Container exists but not running | start, remove |
| `exited` | Container finished/crashed | start, remove |
| `restarting` | Container in restart loop | stop, remove |
| `paused` | Container paused (rare) | restart, remove |
| `dead` | Container non-responsive | remove |
| `created` | Container created, never started | start, remove |
| `unknown` | Status cannot be determined | manual intervention |

---

## Release System

### Overview

Every successful deployment creates an immutable release snapshot for rollback capability.

**Storage Structure:**
```
storage/webgenesis/{site_id}/
├── releases/
│   ├── rel_1735660800_a1b2c3d4/   # Release snapshot
│   │   ├── release.json             # Metadata
│   │   ├── artifact_hash.txt        # Build hash reference
│   │   └── docker-compose.yml       # Frozen config
│   ├── rel_1735664400_e5f6g7h8/   # Newer release
│   │   └── ...
│   └── ...
├── docker-compose.yml              # Current/active config
├── manifest.json                   # Site manifest
└── ...
```

### Release ID Format

```
rel_{timestamp}_{hash[:8]}
```

**Example:** `rel_1735660800_a1b2c3d4`

- `rel_` - Fixed prefix
- `1735660800` - Unix timestamp (10 digits)
- `a1b2c3d4` - First 8 chars of artifact hash (hex)

**Properties:**
- Sortable by timestamp (chronological order)
- Collision-resistant (hash suffix)
- Human-readable timestamp
- Regex-validatable: `^rel_\d{10}_[a-f0-9]{8}$`

---

### List Releases

View release history for rollback selection:

```bash
GET /api/webgenesis/{site_id}/releases
```

**Trust Tier:** Any (no restriction)

**Response:**
```json
{
  "site_id": "my-site_20250101120000",
  "releases": [
    {
      "release_id": "rel_1735664400_e5f6g7h8",
      "site_id": "my-site_20250101120000",
      "artifact_hash": "e5f6g7h8...",
      "created_at": "2025-01-01T13:00:00Z",
      "deployed_url": "http://localhost:8080",
      "health_status": "healthy",
      "metadata": {
        "deploy_method": "docker-compose",
        "container_id": "abc123..."
      }
    },
    {
      "release_id": "rel_1735660800_a1b2c3d4",
      "site_id": "my-site_20250101120000",
      "artifact_hash": "a1b2c3d4...",
      "created_at": "2025-01-01T12:00:00Z",
      "deployed_url": "http://localhost:8080",
      "health_status": "healthy"
    }
  ],
  "total_count": 2
}
```

**Use Cases:**
- Select release for rollback
- Audit deployment history
- Investigate past deployments

---

### Retention Policy

Automatic cleanup of old releases to prevent disk bloat.

**Configuration:**
```bash
# .env
BRAIN_WEBGENESIS_RELEASE_KEEP=5  # Keep 5 newest releases
```

**Default:** 5 releases

**Behavior:**
- Triggered during deployment (after new release created)
- Deletes releases beyond `RELEASE_KEEP` limit (oldest first)
- Never deletes current active release
- Audit log records all deletions

**Example:**
```
Releases: rel_001, rel_002, rel_003, rel_004, rel_005, rel_006
Keep: 5
Action: Delete rel_001 (oldest)
Result: rel_002, rel_003, rel_004, rel_005, rel_006
```

**Manual Override:**
Edit retention via `ReleaseManager.prune_old_releases()` in code.

---

## Health Monitoring

### Overview

HTTP health checks verify deployment success with configurable retries and backoff.

**Configuration:**
```bash
# .env
BRAIN_WEBGENESIS_HEALTH_TIMEOUT=60   # Total timeout (seconds)
BRAIN_WEBGENESIS_HEALTH_RETRIES=3    # Retry attempts
BRAIN_WEBGENESIS_HEALTH_BACKOFF=5    # Backoff between retries (seconds)
```

**Defaults:**
- Timeout: 60 seconds
- Retries: 3 attempts
- Backoff: 5 seconds (linear)

---

### Health Check Workflow

1. **Deployment Completes** - Docker Compose up succeeds
2. **Wait** - Initial backoff (5s)
3. **HTTP GET** - Fetch `http://localhost:{port}{healthcheck_path}`
4. **Evaluate:**
   - `200-399` → Healthy ✅
   - `400-599` → Unhealthy ❌
   - Timeout/Error → Retry
5. **Retry Logic:**
   - Retry up to 3 times
   - 5-second linear backoff between attempts
   - Total timeout: 60 seconds
6. **Result:**
   - Success → Deployment succeeds, create release
   - Failure → Log warning, deployment succeeds (health check non-blocking)

**⚠️ Important:** Health check failures **do NOT** fail deployment. They are logged as warnings only.

---

### Health Status States

| Status | Description | Meaning |
|--------|-------------|---------|
| `healthy` | HTTP 2xx/3xx response | Site operational |
| `unhealthy` | HTTP 4xx/5xx response | Site error state |
| `starting` | Container starting (first 30s) | Grace period |
| `unknown` | Cannot determine status | Check logs |

---

### Customizing Health Checks

**In Website Spec (`spec.deploy.healthcheck_path`):**

```json
{
  "deploy": {
    "healthcheck_path": "/health",
    "..."
  }
}
```

**Default:** `/` (root page)

**Recommendations:**
- Use dedicated health endpoints (`/health`, `/status`)
- Return 200 for healthy, 503 for unhealthy
- Keep health endpoints lightweight (no DB queries)
- Test health endpoint before deployment

---

## Rollback Procedures

### Overview

Restore site to a previous release in case of deployment failures or regressions.

**Trust Tier:** LOCAL or DMZ only

---

### Rollback to Previous Release (Auto)

Automatically selects the release immediately before the current one:

```bash
POST /api/webgenesis/{site_id}/rollback
```

**Body:**
```json
{
  "current_release_id": "rel_1735664400_e5f6g7h8"
}
```

**Response:**
```json
{
  "success": true,
  "site_id": "my-site_20250101120000",
  "from_release": "rel_1735664400_e5f6g7h8",
  "to_release": "rel_1735660800_a1b2c3d4",
  "lifecycle_status": "running",
  "health_status": "healthy",
  "message": "Rollback completed to release rel_1735660800_a1b2c3d4",
  "warnings": []
}
```

**Behavior:**
- If `current_release_id` specified: Return release immediately before it
- If `current_release_id` omitted: Return 2nd newest release
- If no previous release: Return error

---

### Rollback to Specific Release

Target a specific release by ID:

```bash
POST /api/webgenesis/{site_id}/rollback
```

**Body:**
```json
{
  "release_id": "rel_1735660800_a1b2c3d4"
}
```

**Response:**
```json
{
  "success": true,
  "site_id": "my-site_20250101120000",
  "from_release": "rel_1735664400_e5f6g7h8",
  "to_release": "rel_1735660800_a1b2c3d4",
  "lifecycle_status": "running",
  "health_status": "healthy",
  "message": "Rollback completed to release rel_1735660800_a1b2c3d4",
  "warnings": []
}
```

---

### Rollback Workflow

1. **Select Target Release**
   - Auto-select previous OR specified release ID
   - Validate release exists

2. **Validate Release**
   - Check `docker-compose.yml` exists in release snapshot
   - Verify file integrity

3. **Stop Current Container**
   - `docker-compose down` (graceful shutdown)
   - 60-second timeout

4. **Copy Frozen Config**
   - Copy `docker-compose.yml` from release to site root
   - Atomic file operation

5. **Start with Old Config**
   - `docker-compose up -d` (detached mode)
   - 60-second timeout

6. **Health Check**
   - HTTP GET to verify rollback success
   - 3 retries with 5-second backoff

7. **Update Manifest**
   - Update `current_release_id` to target
   - Update `last_health_status`
   - Update `updated_at` timestamp

---

### Fail-Safe Behavior

**Rollback errors do NOT throw exceptions:**

- All errors logged as `CRITICAL`
- Returns `RollbackResponse(success=False, warnings=[...])`
- Site may be in degraded state (manual intervention needed)

**Warnings Include:**
- Container stop failures
- Health check failures
- Manifest update failures

**Example Degraded State:**
```json
{
  "success": false,
  "message": "Failed to start container with old config",
  "lifecycle_status": "exited",
  "health_status": "unhealthy",
  "warnings": [
    "CRITICAL: docker-compose up failed - ..."
  ]
}
```

**Recovery:**
- Check container logs: `docker compose logs`
- Manually inspect docker-compose.yml
- Escalate to ops team if needed

---

### Best Practices

1. **Test rollbacks in staging** before production
2. **Verify health endpoints** before deploying
3. **Monitor rollback warnings** - they indicate issues
4. **Keep 5+ releases** for rollback flexibility
5. **Document known-good releases** for emergency rollback
6. **Automate rollback triggers** for critical failures

---

## Configuration Reference

### Environment Variables

```bash
# Release Retention
BRAIN_WEBGENESIS_RELEASE_KEEP=5  # Number of releases to keep (default: 5)

# Health Monitoring
BRAIN_WEBGENESIS_HEALTH_TIMEOUT=60   # Total health check timeout (seconds)
BRAIN_WEBGENESIS_HEALTH_RETRIES=3    # Number of retry attempts
BRAIN_WEBGENESIS_HEALTH_BACKOFF=5    # Backoff between retries (seconds)
```

### File Locking

**Concurrent Operation Safety:**

All lifecycle operations use file-based exclusive locks (`fcntl.LOCK_EX`) to prevent race conditions.

**Lock File:** `storage/webgenesis/{site_id}/.lock`

**Behavior:**
- Blocks until lock acquired
- Released automatically on operation completion
- Prevents concurrent start/stop/restart/remove/rollback
- Timeout: None (waits indefinitely)

**Manual Lock Cleanup:**
```bash
rm storage/webgenesis/{site_id}/.lock
```

**⚠️ Warning:** Only remove locks if operation crashed and lock file stale.

---

## Troubleshooting

### Common Issues

#### Issue: Container Won't Start After Rollback

**Symptoms:**
- Rollback returns `lifecycle_status: exited`
- Health check fails
- Site inaccessible

**Diagnosis:**
```bash
# Check container logs
docker compose -f storage/webgenesis/{site_id}/docker-compose.yml logs

# Check container status
docker ps -a | grep webgenesis-{site_id}
```

**Solutions:**
1. Verify docker-compose.yml syntax
2. Check port conflicts: `netstat -tuln | grep {port}`
3. Manually start: `docker compose up -d`
4. Rollback to earlier release

---

#### Issue: Health Check Always Fails

**Symptoms:**
- Deployment succeeds but logs health warnings
- Releases created despite failures

**Diagnosis:**
```bash
# Test health endpoint manually
curl http://localhost:{port}{healthcheck_path}

# Check container logs
docker compose logs web
```

**Solutions:**
1. Verify `healthcheck_path` in spec (default: `/`)
2. Increase `BRAIN_WEBGENESIS_HEALTH_TIMEOUT`
3. Check nginx config in container
4. Verify site HTML/CSS loads properly

---

#### Issue: Disk Space Exhausted (Too Many Releases)

**Symptoms:**
- Deployment fails with disk space errors
- `/storage` partition full

**Diagnosis:**
```bash
# Check disk usage
df -h
du -sh storage/webgenesis/*/releases

# Count releases per site
find storage/webgenesis/*/releases -type d -name "rel_*" | wc -l
```

**Solutions:**
1. Reduce `BRAIN_WEBGENESIS_RELEASE_KEEP` (e.g., 3 instead of 5)
2. Manually delete old releases:
   ```bash
   rm -rf storage/webgenesis/{site_id}/releases/rel_OLD_ID
   ```
3. Run prune manually (Python):
   ```python
   from backend.app.modules.webgenesis.releases import get_release_manager
   import asyncio

   manager = get_release_manager()
   asyncio.run(manager.prune_old_releases(site_id="my-site", keep=3))
   ```

---

#### Issue: Operation Hangs Indefinitely

**Symptoms:**
- Lifecycle operation never completes
- API request times out

**Diagnosis:**
```bash
# Check if lock file exists
ls -la storage/webgenesis/{site_id}/.lock

# Check if Docker Compose hung
ps aux | grep docker-compose
```

**Solutions:**
1. Kill hung Docker Compose process
2. Remove stale lock file:
   ```bash
   rm storage/webgenesis/{site_id}/.lock
   ```
3. Retry operation

---

#### Issue: Rollback Selects Wrong Release

**Symptoms:**
- Rollback doesn't target expected release
- Wrong version deployed

**Diagnosis:**
```bash
# List releases (newest first)
GET /api/webgenesis/{site_id}/releases

# Check current_release_id in manifest
cat storage/webgenesis/{site_id}/manifest.json | grep current_release_id
```

**Solutions:**
1. Always specify exact `release_id` for rollback
2. Verify `current_release_id` in manifest is correct
3. Use releases list endpoint to confirm target

---

### Debug Logging

**Enable debug logs:**
```bash
# .env
LOG_LEVEL=DEBUG
```

**Check logs:**
```bash
# Container logs
docker compose -f backend/docker-compose.yml logs -f backend

# Grep for WebGenesis ops
docker compose logs backend | grep -i "webgenesis\|lifecycle\|rollback"
```

---

## Security Considerations

### Trust Tier Enforcement

**Lifecycle Operations:**
- **Allowed:** LOCAL, DMZ
- **Blocked:** EXTERNAL (HTTP 403)

**Releases List:**
- **Allowed:** ANY (no restriction)

**Rationale:**
- Lifecycle ops execute system commands (`docker-compose`)
- EXTERNAL access too risky for container control
- DMZ authenticated via gateway tokens
- Releases list read-only, safe for any tier

---

### Path Safety

**All file operations use `safe_path_join()`:**
- Validates base path (`storage/webgenesis`)
- Prevents `../` path traversal
- Blocks absolute paths
- Rejects directory separators in IDs

**Validated Patterns:**
- Site IDs: `^[a-zA-Z0-9_-]+$`
- Release IDs: `^rel_\d{10}_[a-f0-9]{8}$`

---

### Subprocess Safety

**Docker Compose Commands:**
- Argument arrays only (no `shell=True`)
- Timeouts enforced (60 seconds)
- `check=True` for error detection
- Output captured and logged

**Prevented:**
```python
# ❌ NEVER
subprocess.run(f"docker-compose down {user_input}", shell=True)

# ✅ ALWAYS
subprocess.run(["docker-compose", "down"], cwd=str(site_dir), timeout=60)
```

---

### File Locking

**Concurrent Operation Protection:**
- Exclusive locks (`fcntl.LOCK_EX`)
- Per-site granularity
- Automatic cleanup via context manager
- Blocks until acquired (no timeout)

**Attack Surface:**
- Lock files world-readable (not secret)
- Denial-of-service via lock exhaustion (mitigated by timeouts upstream)

---

### Audit Trail

**All operations logged:**
- Lifecycle: start/stop/restart/remove
- Rollback: from/to releases, health status
- Release: creation, pruning (with deleted IDs)

**Log Format:**
```
[INFO] 🚀 Starting site: site_id=my-site, trust_tier=dmz, source=telegram_gateway
[INFO] ✅ Site started: site_id=my-site
```

**Integration:**
- Future: WebGenesis audit events
- Current: Loguru structured logs

---

## Summary

Sprint II operational features provide production-ready site management:

✅ **Lifecycle control** - Start/stop/restart/remove
✅ **Release snapshots** - Rollback capability
✅ **Health monitoring** - Automated verification
✅ **Retention policies** - Disk space management
✅ **Fail-safe rollback** - Graceful error handling
✅ **Security enforcement** - Trust tier + path safety

**Next Steps:**
- Configure ENV variables for your environment
- Test lifecycle operations in staging
- Establish rollback procedures for your team
- Monitor health check warnings
- Review retention policy for disk capacity

**Support:**
- Issues: Create GitHub issue
- Questions: Check CLAUDE.md documentation
- Logs: Enable DEBUG level for detailed traces

---

**Document Version:** Sprint II (2.0.0)
**Last Updated:** 2025-12-25
