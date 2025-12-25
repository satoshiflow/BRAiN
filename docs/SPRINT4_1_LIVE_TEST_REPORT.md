# Sprint IV.1 - Live Integration Test Report

**Date:** 2025-12-25
**Test Suite:** `backend/tests/test_odoo_live_integration.py`
**Status:** ✅ **READY FOR EXECUTION**
**Sprint:** Sprint IV.1 - Operational Acceptance

---

## Executive Summary

Comprehensive live integration test suite created for Sprint IV Odoo integration. Tests are **skip-safe** (automatically skip if Odoo not available) and cover all critical functionality including security fixes.

**Test Coverage:** 15 tests across 7 categories
**Execution Mode:** Skip-safe (CI-friendly)
**Prerequisites:** Running Odoo 19 instance with configured ENV variables

---

## Test Suite Overview

### Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| **Connection & Authentication** | 2 | Verify Odoo connection and version |
| **Module Listing** | 2 | List all/filtered modules |
| **Module Generation** | 1 | Generate module from text spec |
| **Module Installation** | 2 | Install with idempotency check |
| **Module Upgrade** | 1 | Upgrade to new version |
| **Module Rollback** | 1 | Rollback to previous version |
| **Security** | 3 | Trust tier, path traversal, timeout |
| **Cleanup** | 1 | Remove test artifacts |
| **Summary** | 1 | Test execution summary |
| **TOTAL** | **15** | **Full coverage** |

---

## Test Execution Modes

### Mode 1: Skip-Safe (Default - CI Friendly)

Tests automatically skip if Odoo not available:

```bash
# Skip if ODOO_BASE_URL not configured
pytest backend/tests/test_odoo_live_integration.py

# Expected output if Odoo unavailable:
# SKIPPED [1] test_odoo_live_integration.py:29: Skipping live Odoo tests: ODOO_BASE_URL not configured
```

### Mode 2: Force Execute (Fail if Unavailable)

Force tests to run (fail if Odoo unavailable):

```bash
# Force execution
ODOO_FORCE_LIVE_TESTS=true pytest backend/tests/test_odoo_live_integration.py -v

# Expected: Tests run or fail with error
```

---

## Environment Requirements

### Required ENV Variables

```bash
# Odoo Connection
ODOO_BASE_URL=http://localhost:8069
ODOO_DB_NAME=odoo_test
ODOO_ADMIN_USER=admin
ODOO_ADMIN_PASSWORD=admin

# Odoo Paths
ODOO_ADDONS_PATH=/opt/odoo/addons

# Security & Performance
ODOO_TIMEOUT_SECONDS=30
ODOO_ENFORCE_TRUST_TIER=true
```

### Odoo Instance Requirements

- **Odoo Version:** 19.0+
- **Modules:** base, web (standard modules)
- **Permissions:** Admin user with module install/upgrade rights
- **Network:** Accessible from test environment
- **Disk Space:** ~10MB for test module artifacts

---

## Test Details

### Test 1-2: Connection & Authentication

**Purpose:** Verify basic Odoo connectivity

**Tests:**
1. `test_odoo_connection` - Connect and authenticate
2. `test_odoo_version_19` - Verify Odoo 19

**Expected Results:**
- ✅ Connection successful
- ✅ UID > 0 (authenticated)
- ✅ server_version starts with "19."

**Failure Scenarios:**
- ❌ Connection refused → Odoo not running
- ❌ Authentication failed → Wrong credentials
- ❌ Wrong version → Odoo < 19 (incompatible)

---

### Test 3-4: Module Listing

**Purpose:** Verify module query functionality

**Tests:**
1. `test_list_all_modules` - List all modules
2. `test_list_installed_modules` - Filter by state

**Expected Results:**
- ✅ Returns non-empty list
- ✅ Contains "base" and "web" modules
- ✅ Filtered list contains only installed modules

**Failure Scenarios:**
- ❌ Empty list → Database empty or query failed
- ❌ Missing base modules → Odoo installation broken

---

### Test 5: Module Generation

**Purpose:** Generate Odoo module from text specification

**Test:** `test_generate_test_module`

**Module Spec:**
- Name: `brain_test_module`
- Version: 1.0.0
- Model: `brain.test.record` with 4 fields
- Views: Tree + Form
- Security: User access rule

**Expected Results:**
- ✅ Module generated successfully
- ✅ Files created: `__manifest__.py`, models, views, security
- ✅ Stored in registry with version tracking

**Failure Scenarios:**
- ❌ Generation failed → Parser or generator bug
- ❌ Invalid manifest → Template error
- ❌ Storage failed → Path validation or disk issue

---

### Test 6-7: Module Installation (Idempotency)

**Purpose:** Install module and verify idempotent behavior

**Tests:**
1. `test_install_test_module_first_time` - First install
2. `test_install_test_module_idempotent` - Second install (same version)

**Expected Results:**

**First Install:**
- ✅ Module installed successfully
- ✅ Status: installed
- ✅ No warnings

**Second Install (Idempotency Check):**
- ✅ Operation succeeds (idempotent)
- ✅ Warning: "Module already installed"
- ✅ No state change

**Failure Scenarios:**
- ❌ First install fails → Module broken or Odoo error
- ❌ Second install fails → Not idempotent (blocker)
- ❌ No warning on second install → Idempotency not detected

---

### Test 8: Module Upgrade

**Purpose:** Upgrade module to new version

**Test:** `test_upgrade_test_module`

**Upgrade Path:** v1.0.0 → v1.1.0

**Changes:**
- Add new field: `test_field` (Char)
- Update manifest version

**Expected Results:**
- ✅ Upgrade successful
- ✅ Version: 1.1.0
- ✅ New field available in Odoo

**Failure Scenarios:**
- ❌ Upgrade failed → Migration issue or Odoo error
- ❌ Data loss → Field definitions broken
- ❌ Wrong version → Version tracking broken

---

### Test 9: Module Rollback

**Purpose:** Rollback module to previous version

**Test:** `test_rollback_test_module`

**Rollback Path:** v1.1.0 → v1.0.0

**Expected Results:**
- ✅ Rollback successful
- ✅ Version: 1.0.0
- ✅ New field removed (v1.1.0 changes reverted)

**Failure Scenarios:**
- ❌ Rollback failed → Version not retained
- ❌ Data loss → Rollback unsafe
- ❌ Partial rollback → Inconsistent state

---

### Test 10-12: Security Enforcement

**Purpose:** Verify security fixes from PR review

**Tests:**
1. `test_trust_tier_enforcement_enabled` - Default enabled
2. `test_trust_tier_blocks_non_localhost` - 403 for remote requests
3. `test_path_traversal_protection` - Block malicious paths

**Expected Results:**

**Trust Tier:**
- ✅ ODOO_ENFORCE_TRUST_TIER defaults to "true"
- ✅ Non-localhost request raises HTTPException 403
- ✅ Error message: "LOCAL trust tier required"

**Path Traversal:**
- ✅ Valid paths pass: "my_module", "1.0.0"
- ✅ Malicious paths fail: "../../../etc/passwd"
- ✅ Error message descriptive

**Failure Scenarios:**
- ❌ Trust tier not enforced → Security bypass (CRITICAL)
- ❌ Path traversal allowed → File system compromise (HIGH)
- ❌ No error message → Poor UX

---

### Test 13: Timeout Configuration

**Purpose:** Verify XML-RPC timeout configuration

**Test:** `test_timeout_configuration`

**Expected Results:**
- ✅ ODOO_TIMEOUT_SECONDS defaults to 30
- ✅ Timeout applied to client
- ✅ Custom timeout respected

**Failure Scenarios:**
- ❌ No timeout → Hang risk (stability issue)
- ❌ Wrong default → Configuration broken
- ❌ Timeout not applied → Implementation bug

---

### Test 14: Cleanup

**Purpose:** Remove test artifacts

**Test:** `test_cleanup_test_module`

**Expected Results:**
- ✅ Module uninstalled or marked for removal
- ✅ No orphaned data

**Failure Scenarios:**
- ❌ Uninstall not implemented → Skip test (non-blocker)
- ❌ Cleanup fails → Manual cleanup required

---

### Test 15: Summary

**Purpose:** Display test execution summary

**Test:** `test_live_integration_summary`

**Output Example:**
```
======================================================================
🎉 LIVE INTEGRATION TESTS SUMMARY
======================================================================
✅ Odoo Version: 19.0-20251215
✅ Protocol Version: 1
✅ Connection: Working
✅ Authentication: Working
✅ Module Generation: Working
✅ Module Installation: Working (Idempotent)
✅ Module Upgrade: Working
✅ Module Rollback: Working
✅ Trust Tier Enforcement: Working
✅ Path Traversal Protection: Working
✅ Timeout Configuration: Working
======================================================================
All Sprint IV.1 live integration tests passed!
======================================================================
```

---

## Execution Instructions

### Step 1: Prepare Odoo Environment

**Option A: Docker Compose (Recommended)**

```bash
# Start Odoo 19 with PostgreSQL
cd /path/to/project
docker compose -f docker-compose.odoo-test.yml up -d

# Expected services:
# - odoo:8069 (Odoo 19)
# - postgres:5432 (Database)

# Verify Odoo is running
curl http://localhost:8069/web/database/selector
```

**Option B: Remote Odoo**

```bash
# Use existing Odoo instance
export ODOO_BASE_URL=https://odoo.example.com
export ODOO_DB_NAME=test_db
export ODOO_ADMIN_USER=admin
export ODOO_ADMIN_PASSWORD=<secure_password>
```

### Step 2: Configure Environment

```bash
# Copy test ENV template
cat > .env.test <<EOF
ODOO_BASE_URL=http://localhost:8069
ODOO_DB_NAME=odoo_test
ODOO_ADMIN_USER=admin
ODOO_ADMIN_PASSWORD=admin
ODOO_ADDONS_PATH=/opt/odoo/addons
ODOO_TIMEOUT_SECONDS=30
ODOO_ENFORCE_TRUST_TIER=true
EOF

# Load environment
export $(cat .env.test | xargs)
```

### Step 3: Run Tests

**Quick Run (Skip if Unavailable):**

```bash
pytest backend/tests/test_odoo_live_integration.py
```

**Verbose Run:**

```bash
pytest backend/tests/test_odoo_live_integration.py -v
```

**With Coverage:**

```bash
pytest backend/tests/test_odoo_live_integration.py --cov=backend/app/modules/odoo_connector
```

**Force Run (Fail if Unavailable):**

```bash
ODOO_FORCE_LIVE_TESTS=true pytest backend/tests/test_odoo_live_integration.py -v
```

### Step 4: Interpret Results

**Success Output:**
```
backend/tests/test_odoo_live_integration.py::test_odoo_connection PASSED
backend/tests/test_odoo_live_integration.py::test_odoo_version_19 PASSED
...
backend/tests/test_odoo_live_integration.py::test_live_integration_summary PASSED

====== 15 passed in 45.23s ======
```

**Skip Output (Odoo Unavailable):**
```
backend/tests/test_odoo_live_integration.py SKIPPED [1]
  Skipping live Odoo tests: ODOO_BASE_URL not configured

====== 1 skipped in 0.02s ======
```

**Failure Output:**
```
backend/tests/test_odoo_live_integration.py::test_odoo_connection FAILED

E   AssertionError: Connection failed: [Errno 111] Connection refused
```

---

## Troubleshooting

### Problem 1: Connection Refused

**Error:**
```
Connection failed: [Errno 111] Connection refused
```

**Solutions:**
1. Check Odoo is running: `docker ps | grep odoo`
2. Verify port: `netstat -tuln | grep 8069`
3. Check ODOO_BASE_URL: `echo $ODOO_BASE_URL`

### Problem 2: Authentication Failed

**Error:**
```
Authentication failed: Access Denied
```

**Solutions:**
1. Verify credentials: Check ODOO_ADMIN_USER and ODOO_ADMIN_PASSWORD
2. Reset admin password:
   ```bash
   docker exec odoo odoo-bin --database=odoo_test --reset-password --login=admin
   ```
3. Check database name: Ensure ODOO_DB_NAME matches existing database

### Problem 3: Module Install Failed

**Error:**
```
Module installation failed: Module not found
```

**Solutions:**
1. Check ODOO_ADDONS_PATH is accessible:
   ```bash
   docker exec odoo ls -la /opt/odoo/addons
   ```
2. Verify module was copied:
   ```bash
   docker exec odoo ls -la /opt/odoo/addons/brain_test_module
   ```
3. Update module list in Odoo:
   - Open Odoo → Apps → Update Apps List

### Problem 4: Tests Skipped

**Error:**
```
SKIPPED [1] Skipping live Odoo tests: ODOO_BASE_URL not configured
```

**Solutions:**
1. Set environment variables:
   ```bash
   export ODOO_BASE_URL=http://localhost:8069
   export ODOO_DB_NAME=odoo_test
   export ODOO_ADMIN_USER=admin
   export ODOO_ADMIN_PASSWORD=admin
   ```
2. Or force test execution:
   ```bash
   ODOO_FORCE_LIVE_TESTS=true pytest backend/tests/test_odoo_live_integration.py
   ```

### Problem 5: Timeout Errors

**Error:**
```
TimeoutError: Operation timed out after 30 seconds
```

**Solutions:**
1. Increase timeout:
   ```bash
   export ODOO_TIMEOUT_SECONDS=60
   ```
2. Check Odoo server load:
   ```bash
   docker stats odoo
   ```
3. Optimize Odoo database:
   ```sql
   VACUUM ANALYZE;  -- In PostgreSQL
   ```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Odoo Live Tests

on:
  push:
    branches: [main, v2]
  pull_request:

jobs:
  test-odoo:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: odoo_test
          POSTGRES_USER: odoo
          POSTGRES_PASSWORD: odoo
        ports:
          - 5432:5432

      odoo:
        image: odoo:19.0
        env:
          POSTGRES_HOST: postgres
          POSTGRES_DB: odoo_test
          POSTGRES_USER: odoo
          POSTGRES_PASSWORD: odoo
        ports:
          - 8069:8069

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install pytest pytest-asyncio

      - name: Wait for Odoo
        run: |
          timeout 300 bash -c 'until curl -s http://localhost:8069/web/database/selector; do sleep 5; done'

      - name: Run Odoo Live Tests
        env:
          ODOO_BASE_URL: http://localhost:8069
          ODOO_DB_NAME: odoo_test
          ODOO_ADMIN_USER: admin
          ODOO_ADMIN_PASSWORD: admin
          ODOO_ADDONS_PATH: /opt/odoo/addons
          ODOO_FORCE_LIVE_TESTS: true
        run: |
          pytest backend/tests/test_odoo_live_integration.py -v
```

---

## Test Results Template

Use this template to document test execution results:

```markdown
## Test Execution Results

**Date:** YYYY-MM-DD
**Executed By:** [Your Name]
**Environment:** [Development/Staging/Production]
**Odoo Version:** [e.g., 19.0-20251215]

### Configuration

- ODOO_BASE_URL: [URL]
- ODOO_DB_NAME: [Database]
- ODOO_ADMIN_USER: [Username]
- ODOO_ADDONS_PATH: [Path]

### Results

| Test | Status | Duration | Notes |
|------|--------|----------|-------|
| test_odoo_connection | ✅ PASS | 0.5s | - |
| test_odoo_version_19 | ✅ PASS | 0.1s | - |
| test_list_all_modules | ✅ PASS | 1.2s | Found 42 modules |
| test_list_installed_modules | ✅ PASS | 0.8s | 12 installed |
| test_generate_test_module | ✅ PASS | 2.3s | 4 files generated |
| test_install_test_module_first_time | ✅ PASS | 5.1s | - |
| test_install_test_module_idempotent | ✅ PASS | 1.2s | Warning raised |
| test_upgrade_test_module | ✅ PASS | 6.4s | - |
| test_rollback_test_module | ✅ PASS | 5.8s | - |
| test_trust_tier_enforcement_enabled | ✅ PASS | 0.1s | - |
| test_trust_tier_blocks_non_localhost | ✅ PASS | 0.1s | 403 raised |
| test_path_traversal_protection | ✅ PASS | 0.2s | All blocked |
| test_timeout_configuration | ✅ PASS | 0.1s | 30s default |
| test_cleanup_test_module | ✅ PASS | 3.2s | - |
| test_live_integration_summary | ✅ PASS | 0.1s | - |

**Total:** 15/15 passed (100%)
**Duration:** 27.2s
**Status:** ✅ ALL TESTS PASSED

### Issues Found

- None

### Recommendations

- All tests passed successfully
- Ready for production deployment
```

---

## Next Steps

After successful test execution:

1. ✅ **Document Results** - Fill test results template above
2. ✅ **Review Logs** - Check for warnings or deprecations
3. ✅ **Commit Report** - Add filled template to this document
4. ✅ **Merge to v2** - All tests passing, ready to merge
5. ✅ **Deploy** - Deploy to staging/production
6. ✅ **Monitor** - Watch Odoo integration in production

---

## Appendix: Test Module Specification

The test module (`brain_test_module`) has minimal functionality to reduce test complexity:

```
Module: brain_test_module
Version: 1.0.0 → 1.1.0
Category: Technical
License: LGPL-3

Model: brain.test.record
  - name (Char, required)
  - description (Text)
  - sequence (Integer, default=10)
  - active (Boolean, default=True)
  - test_field (Char) [Added in v1.1.0]

Views:
  - Tree: name, sequence, active
  - Form: All fields

Security:
  - User access (read, write, create, delete)
```

---

## References

- **Sprint IV Documentation:** `docs/SPRINT4_AXE_ODOO.md`
- **PR Review Report:** `docs/SPRINT4_1_PR_REVIEW.md`
- **ENV Configuration Guide:** `docs/ODOO_ENV_SETUP.md`
- **Test File:** `backend/tests/test_odoo_live_integration.py`

---

**Live Test Report Complete**

*Sprint IV.1 - Operational Acceptance*
*Version 1.0.0 | 2025-12-25*
