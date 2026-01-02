# WebGenesis Storage Layout - Sprint II

**Version:** 2.0.0
**Sprint:** Sprint II (Operational Hardening + DNS Automation)
**Last Updated:** 2025-12-25

---

## Overview

Sprint II extends the Sprint I storage layout with:
- **Release snapshots** for rollback capability
- **Release metadata** tracking
- **File locking** for operation safety
- **Enhanced manifests** with lifecycle and health status

---

## Directory Structure

```
storage/webgenesis/
└── {site_id}/                          # Site directory (e.g., my-site_1703001234)
    ├── spec.json                       # Original website specification
    ├── manifest.json                   # Site metadata & status (ENHANCED Sprint II)
    ├── .lock                           # File lock for operation safety (NEW Sprint II)
    │
    ├── source/                         # Generated source code (Sprint I)
    │   ├── index.html
    │   ├── about.html
    │   ├── contact.html
    │   └── ...
    │
    ├── build/                          # Build artifacts (Sprint I)
    │   ├── index.html
    │   ├── about.html
    │   ├── contact.html
    │   ├── artifact_hash.txt           # SHA-256 hash of build artifacts
    │   └── ...
    │
    ├── docker-compose.yml              # Current deployment configuration (Sprint I)
    │
    └── releases/                       # Release snapshots (NEW Sprint II)
        ├── rel_1703001234_a3f5c8e9/    # Release 1 (oldest)
        │   ├── release.json            # Release metadata
        │   ├── docker-compose.yml      # Frozen compose file for this release
        │   └── artifact_hash.txt       # Reference to build artifacts
        │
        ├── rel_1703002000_b4c7d9e2/    # Release 2
        │   ├── release.json
        │   ├── docker-compose.yml
        │   └── artifact_hash.txt
        │
        ├── rel_1703002500_c5d8e3f1/    # Release 3
        │   └── ...
        │
        ├── rel_1703003000_d6e9f4g2/    # Release 4
        │   └── ...
        │
        └── rel_1703003500_e7f0g5h3/    # Release 5 (newest, current)
            └── ...
```

---

## File Specifications

### 1. `.lock` - File Lock (NEW Sprint II)

**Purpose:** Prevent concurrent operations on the same site

**Format:** Empty file (presence indicates lock)

**Usage:**
```python
import fcntl

lock_file = site_dir / ".lock"
with open(lock_file, "w") as f:
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
    try:
        # Perform operation
        pass
    finally:
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Release lock
```

**Lock Scope:** Per-site (all operations on a site share the same lock)

**Operations Requiring Lock:**
- `start_site()`
- `stop_site()`
- `restart_site()`
- `deploy_project()`
- `rollback_to_release()`
- `remove_site()`

---

### 2. `manifest.json` - ENHANCED (Sprint II)

**Changes from Sprint I:**
- Added `current_release_id` field
- Added `last_health_check_at` field
- Added `last_health_status` field
- Added `lifecycle_status` field (container state)

**Example:**
```json
{
  "site_id": "my-site_1703001234",
  "name": "my-site",
  "spec_version": "1.0.0",
  "spec_hash": "a1b2c3d4e5f6...",
  "artifact_hash": "f6e5d4c3b2a1...",
  "status": "deployed",
  "template": "static_html",

  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T14:30:00Z",
  "generated_at": "2025-01-01T12:05:00Z",
  "built_at": "2025-01-01T12:10:00Z",
  "deployed_at": "2025-01-01T12:15:00Z",

  "deployed_url": "http://localhost:8080",
  "deployed_ports": [8080],
  "docker_container_id": "abc123def456",
  "docker_image_tag": "nginx:alpine",

  "source_path": "/storage/webgenesis/my-site_1703001234/source",
  "build_path": "/storage/webgenesis/my-site_1703001234/build",
  "deploy_path": "/storage/webgenesis/my-site_1703001234",

  "current_release_id": "rel_1703003500_e7f0g5h3",
  "last_health_check_at": "2025-01-01T14:30:00Z",
  "last_health_status": "healthy",
  "lifecycle_status": "running",

  "last_error": null,
  "error_count": 0,
  "metadata": {}
}
```

---

### 3. `releases/{release_id}/release.json` - Release Metadata (NEW Sprint II)

**Purpose:** Store metadata for each release snapshot

**Release ID Format:** `rel_{timestamp}_{short_hash}`
- `timestamp`: Unix timestamp (10 digits)
- `short_hash`: First 8 characters of artifact_hash

**Example Release ID:** `rel_1703001234_a3f5c8e9`

**File Content:**
```json
{
  "release_id": "rel_1703001234_a3f5c8e9",
  "site_id": "my-site_1703001234",
  "artifact_hash": "a3f5c8e9d4b7f2a1...",
  "created_at": "2025-01-01T12:15:00Z",
  "deployed_url": "http://localhost:8080",
  "docker_compose_path": "releases/rel_1703001234_a3f5c8e9/docker-compose.yml",
  "health_status": "healthy",
  "metadata": {
    "deploy_duration_seconds": 5.3,
    "container_id": "abc123def456",
    "ports": [8080]
  }
}
```

---

### 4. `releases/{release_id}/docker-compose.yml` - Frozen Compose File (NEW Sprint II)

**Purpose:** Store exact Docker Compose configuration used for this release

**Content:** Identical copy of `docker-compose.yml` from root at time of deployment

**Why Frozen?**
- Enables exact rollback to previous configuration
- Preserves port mappings, volume mounts, environment variables
- Immutable after creation

**Example:**
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: webgenesis-my-site_1703001234
    ports:
      - "8080:80"
    volumes:
      - ./build:/usr/share/nginx/html:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
```

---

### 5. `releases/{release_id}/artifact_hash.txt` - Artifact Reference (NEW Sprint II)

**Purpose:** Reference the build artifact hash for this release

**Content:** Single line with SHA-256 hash

**Example:**
```
a3f5c8e9d4b7f2a1c6e0b9a8f7d6c5e4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8
```

**Why Reference?**
- Avoid duplicating large build artifacts
- Build artifacts in `build/` are referenced by hash
- Single source of truth for artifact content

---

## Release Management

### Release Creation Flow

1. **Successful Deployment**
   - After `deploy_project()` completes successfully
   - Health check passes

2. **Create Release**
   - Generate `release_id`: `rel_{timestamp}_{artifact_hash[:8]}`
   - Create directory: `releases/{release_id}/`
   - Copy `docker-compose.yml` to release directory
   - Write `release.json` with metadata
   - Write `artifact_hash.txt` with build artifact hash
   - Update manifest with `current_release_id`

3. **Update Manifest**
   - Set `current_release_id`
   - Update `updated_at` timestamp

### Release Retention

**Policy:** Keep N most recent releases (configurable via ENV)

**Default:** `BRAIN_WEBGENESIS_RELEASE_KEEP=5`

**Retention Logic:**
1. After creating a new release
2. List all releases (sorted by timestamp, newest first)
3. If count > N:
   - Delete oldest releases
   - Keep only N newest
   - Audit deletion events

**Example:**
```python
# Keep 5 releases
# Current: 6 releases exist
# Action: Delete oldest 1 release
# Result: 5 releases remain

releases = [
    "rel_1703001234_a3f5c8e9",  # <- DELETE (oldest)
    "rel_1703002000_b4c7d9e2",  # Keep
    "rel_1703002500_c5d8e3f1",  # Keep
    "rel_1703003000_d6e9f4g2",  # Keep
    "rel_1703003500_e7f0g5h3",  # Keep
    "rel_1703004000_f8g1h6i4",  # Keep (newest)
]
```

---

## Rollback Mechanism

### Rollback Flow

1. **Select Target Release**
   - If `release_id` provided: use it
   - If `release_id` is None: use previous release (2nd newest)

2. **Validate Release**
   - Check if release exists
   - Check if `docker-compose.yml` exists
   - Check if `artifact_hash.txt` exists

3. **Stop Current Deployment**
   - Run `docker-compose down` (graceful stop)

4. **Apply Release Configuration**
   - Copy `docker-compose.yml` from release to root
   - Run `docker-compose up -d` (start with old config)

5. **Health Check**
   - Verify container starts
   - Run health check (same as deploy)

6. **Update Manifest**
   - Set `current_release_id` to target release
   - Update `deployed_at` timestamp
   - Update `last_health_status`

7. **Audit Event**
   - Log `webgenesis.rollback_finished` event
   - Include `from_release` and `to_release` in details

### Rollback Safety

**Fail-Safe:**
- If rollback fails: Log CRITICAL audit event
- Do NOT throw exception (fail gracefully)
- Site may be in degraded state (manual intervention needed)
- Return rollback failure in response with error details

**Rollback Failure Scenarios:**
- Target release not found
- Docker Compose command fails
- Health check fails after rollback
- File I/O errors

---

## Storage Size Estimation

### Per Site Estimate

| Component | Size | Notes |
|-----------|------|-------|
| `spec.json` | ~5 KB | Specification JSON |
| `manifest.json` | ~2 KB | Metadata |
| `source/` | ~50 KB | Generated HTML files |
| `build/` | ~50 KB | Build artifacts (same as source) |
| `docker-compose.yml` | ~1 KB | Compose configuration |
| `.lock` | 0 bytes | Empty lock file |
| **Per Release** | ~2 KB | Metadata + frozen compose |

**Total per site (5 releases):**
- Base: ~108 KB
- Releases: ~10 KB (5 × 2 KB)
- **Total: ~118 KB**

### Scaling

| Sites | Storage (GB) | Notes |
|-------|--------------|-------|
| 100 | ~12 MB | Small deployment |
| 1,000 | ~118 MB | Medium deployment |
| 10,000 | ~1.18 GB | Large deployment |
| 100,000 | ~11.8 GB | Enterprise deployment |

**Note:** Actual size varies based on:
- Number of pages per site
- Content size (images, CSS, JS)
- Release retention policy (more releases = more storage)

---

## Cleanup & Maintenance

### Automatic Cleanup

**Release Pruning:**
- Triggered: After each new release creation
- Action: Delete oldest releases beyond retention limit
- Audit: Log `webgenesis.release_pruned` event

**Example:**
```python
async def prune_old_releases(site_id: str, keep: int = 5) -> int:
    """
    Prune old releases, keeping only N most recent.

    Returns:
        Number of releases deleted
    """
    releases_dir = site_dir / "releases"
    releases = sorted(releases_dir.iterdir(), key=lambda x: x.name, reverse=True)

    to_delete = releases[keep:]
    for release_dir in to_delete:
        shutil.rmtree(release_dir)
        # Audit event
        await audit_manager.log_event(
            event_type="webgenesis.release_pruned",
            action="prune_release",
            status="success",
            details={"site_id": site_id, "release_id": release_dir.name}
        )

    return len(to_delete)
```

### Manual Cleanup

**Remove Site (keep data):**
```bash
# Stop container
docker-compose -f storage/webgenesis/{site_id}/docker-compose.yml down

# Data preserved
# Container removed
```

**Remove Site (delete data):**
```bash
# Stop container
docker-compose -f storage/webgenesis/{site_id}/docker-compose.yml down

# Remove all data
rm -rf storage/webgenesis/{site_id}/
```

---

## Migration from Sprint I

### Backward Compatibility

**Existing Sprint I sites work unchanged:**
- No migration required
- `manifest.json` will be updated on next operation
- New fields populated gradually

**Missing Fields:**
- `current_release_id`: `null` (set on next deployment)
- `last_health_check_at`: `null` (set on next health check)
- `last_health_status`: `unknown` (set on next health check)
- `lifecycle_status`: `unknown` (set on next status query)

### First Sprint II Deployment

**What happens:**
1. Deploy as normal
2. Health check runs (new)
3. Release created (new)
4. Manifest updated with Sprint II fields

**No data loss:**
- Existing `source/` preserved
- Existing `build/` preserved
- Existing `docker-compose.yml` becomes first release

---

## Security Considerations

### File Lock Security

**Lock File Location:** Inside site directory
**Permissions:** Owned by backend process
**Lock Type:** Exclusive (LOCK_EX)
**Lock Scope:** Per-site

**Protection Against:**
- Concurrent deploy + rollback
- Concurrent start + stop
- Race conditions in lifecycle operations

### Release Integrity

**Artifact Hashing:**
- Build artifacts hashed with SHA-256
- Release references artifact hash
- Tamper detection via hash verification

**Immutable Releases:**
- Releases are never modified after creation
- Frozen `docker-compose.yml` preserves exact state
- Deletion only during pruning (audit logged)

### Path Safety

**All operations use:**
- `safe_path_join()` for path construction
- Site ID validation (`^[a-zA-Z0-9_-]+$`)
- Base path allowlist enforcement

**No path traversal possible:**
- All paths resolved and validated
- Operations confined to site directory

---

## Troubleshooting

### Issue: Lock file exists but no operation running

**Cause:** Previous operation crashed without releasing lock

**Solution:**
```bash
# Remove stale lock (safe if no operation running)
rm storage/webgenesis/{site_id}/.lock
```

### Issue: Release directory missing

**Cause:** Manual deletion or corruption

**Solution:**
- Site still functional (uses current `docker-compose.yml`)
- Rollback not available until next deployment
- Create new deployment to restore release tracking

### Issue: Too many releases consuming storage

**Cause:** High retention limit

**Solution:**
1. Reduce `BRAIN_WEBGENESIS_RELEASE_KEEP` in ENV
2. Restart backend
3. Next deployment will prune to new limit
4. Or manually delete old releases:
   ```bash
   rm -rf storage/webgenesis/{site_id}/releases/rel_*_old
   ```

---

## Future Enhancements (Sprint III+)

**Potential Additions:**
- Compressed release snapshots (tar.gz)
- Remote storage backend (S3, MinIO)
- Release tagging/naming (v1.0.0, stable, etc.)
- Automatic release cleanup based on age
- Release diffing (show changes between releases)
- Multi-site release coordination

---

**WebGenesis Sprint II Storage Layout v2.0.0**
**Last Updated:** 2025-12-25
