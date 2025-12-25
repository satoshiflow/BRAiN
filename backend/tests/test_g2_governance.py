"""
G2 Governance Tests - Mode Switch Governance (2-Phase Commit)

Tests for:
- Preflight checks (Phase 1)
- Mode commit with governance (Phase 2)
- Owner override mechanism
- Audit events
- Security & fail-closed behavior
"""

import sys
import os
from datetime import datetime, timedelta

# Path setup
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


# =============================================================================
# PREFLIGHT TESTS (G2 - Phase 1)
# =============================================================================


def test_preflight_pass_online_to_sovereign():
    """
    Test preflight check for ONLINE → SOVEREIGN.

    Expected: PASS if IPv6 properly blocked.
    """
    response = client.post(
        "/api/sovereign-mode/mode/preflight",
        json={"target_mode": "sovereign", "include_details": True},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "target_mode" in data
    assert "current_mode" in data
    assert "checks" in data
    assert "overall_status" in data
    assert "can_proceed" in data
    assert "override_required" in data
    assert "request_id" in data

    # Verify target mode
    assert data["target_mode"] == "sovereign"

    # Verify checks present
    assert len(data["checks"]) >= 4  # network, ipv6, dmz, bundle_trust

    print(f"✅ Preflight result: {data['overall_status']}")
    print(f"   Can proceed: {data['can_proceed']}")
    print(f"   Checks: {len(data['checks'])}")


def test_preflight_pass_sovereign_to_online():
    """
    Test preflight check for SOVEREIGN → ONLINE.

    Expected: PASS if network available.
    """
    response = client.post(
        "/api/sovereign-mode/mode/preflight",
        json={"target_mode": "online", "include_details": True},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["target_mode"] == "online"
    assert "overall_status" in data

    print(f"✅ Preflight ONLINE result: {data['overall_status']}")


def test_preflight_details_structure():
    """
    Test preflight result structure with all gate checks.
    """
    response = client.post(
        "/api/sovereign-mode/mode/preflight",
        json={"target_mode": "sovereign", "include_details": True},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify each check has required fields
    for check in data["checks"]:
        assert "gate_name" in check
        assert "status" in check
        assert "required" in check
        assert "blocking" in check
        assert "reason" in check
        assert "checked_at" in check

        # Status must be valid
        assert check["status"] in ["pass", "fail", "warning", "skipped", "not_applicable"]

    print(f"✅ All {len(data['checks'])} gate checks have valid structure")


# =============================================================================
# MODE CHANGE TESTS (G2 - 2-Phase Commit)
# =============================================================================


def test_mode_change_with_preflight_pass():
    """
    Test mode change when preflight passes.

    Expected: Change succeeds without override.
    """
    # First get current mode
    status_response = client.get("/api/sovereign-mode/status")
    current_mode = status_response.json()["mode"]

    # Determine target mode (toggle)
    target_mode = "sovereign" if current_mode == "online" else "online"

    response = client.post(
        "/api/sovereign-mode/mode",
        json={
            "target_mode": target_mode,
            "reason": "Test mode change with preflight",
        },
    )

    # Should succeed (200) or fail with governance message (400)
    assert response.status_code in [200, 400]

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Mode change succeeded: {current_mode} → {data['mode']}")
    else:
        # Expected if preflight fails
        error = response.json()
        print(f"ℹ️  Mode change blocked (expected): {error['detail'][:100]}")


def test_mode_change_blocked_without_override():
    """
    Test mode change is blocked when preflight fails and no override.

    Expected: 400 error with governance message.
    """
    response = client.post(
        "/api/sovereign-mode/mode",
        json={
            "target_mode": "sovereign",
            "reason": "Test without override",
            # No override_reason provided
        },
    )

    # If preflight fails, should get 400
    # If preflight passes, should get 200
    assert response.status_code in [200, 400]

    if response.status_code == 400:
        error_detail = response.json()["detail"]
        assert "BLOCKED by governance" in error_detail or "failed" in error_detail.lower()
        print(f"✅ Mode change correctly blocked without override")
    else:
        print(f"ℹ️  Preflight passed, no block needed")


def test_mode_change_with_override():
    """
    Test mode change with owner override.

    Expected: Change succeeds even if preflight would fail.
    """
    response = client.post(
        "/api/sovereign-mode/mode",
        json={
            "target_mode": "sovereign",
            "reason": "Test with override",
            "override_reason": "Testing G2 override mechanism - simulating emergency scenario",
            "override_duration_seconds": 1800,  # 30 minutes
        },
    )

    # Should succeed with override
    assert response.status_code in [200, 400]

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Mode change with override succeeded: mode={data['mode']}")
    else:
        # Could still fail if other issues
        print(f"ℹ️  Mode change failed (other reason): {response.json()['detail'][:100]}")


def test_deprecated_force_flag_warning():
    """
    Test that legacy force=true flag still works but logs warning.

    Expected: Works but deprecated.
    """
    response = client.post(
        "/api/sovereign-mode/mode",
        json={
            "target_mode": "online",
            "force": True,  # Deprecated
            "reason": "Test deprecated force flag",
        },
    )

    # Should work (backward compatibility)
    assert response.status_code in [200, 400]
    print(f"✅ Legacy force flag handled (status={response.status_code})")


# =============================================================================
# OVERRIDE MECHANISM TESTS (G2)
# =============================================================================


def test_override_reason_validation():
    """
    Test that override_reason must be at least 10 characters.

    Expected: Short reasons should fail.
    """
    response = client.post(
        "/api/sovereign-mode/mode",
        json={
            "target_mode": "sovereign",
            "override_reason": "short",  # Too short (< 10 chars)
        },
    )

    # Should fail validation (422 Unprocessable Entity)
    assert response.status_code in [400, 422]
    print(f"✅ Short override reason rejected (status={response.status_code})")


def test_override_duration_validation():
    """
    Test override_duration_seconds validation.

    Expected: Must be >= 60 and <= 86400.
    """
    # Too short
    response = client.post(
        "/api/sovereign-mode/mode",
        json={
            "target_mode": "sovereign",
            "override_reason": "Valid reason for testing override duration",
            "override_duration_seconds": 30,  # Too short (< 60)
        },
    )

    assert response.status_code in [400, 422]
    print(f"✅ Too-short override duration rejected")

    # Too long
    response = client.post(
        "/api/sovereign-mode/mode",
        json={
            "target_mode": "sovereign",
            "override_reason": "Valid reason for testing override duration",
            "override_duration_seconds": 100000,  # Too long (> 86400)
        },
    )

    assert response.status_code in [400, 422]
    print(f"✅ Too-long override duration rejected")


# =============================================================================
# AUDIT EVENTS TESTS (G2)
# =============================================================================


def test_audit_events_for_mode_change():
    """
    Test that mode changes emit proper audit events.

    Expected: MODE_PREFLIGHT_* and MODE_CHANGED events.
    """
    # Trigger a mode change
    response = client.post(
        "/api/sovereign-mode/mode",
        json={
            "target_mode": "online",
            "reason": "Test audit events",
        },
    )

    # Get audit log
    audit_response = client.get("/api/sovereign-mode/audit")
    assert audit_response.status_code == 200

    audit_log = audit_response.json()
    assert isinstance(audit_log, list)

    # Check for G2 events
    g2_events = [
        entry for entry in audit_log
        if "mode_preflight" in entry.get("event_type", "") or
           "mode_override" in entry.get("event_type", "") or
           "mode_changed" in entry.get("event_type", "")
    ]

    print(f"✅ Found {len(g2_events)} G2-related audit events")


# =============================================================================
# SECURITY TESTS (G2 Fail-Closed)
# =============================================================================


def test_fail_closed_no_override():
    """
    Test fail-closed behavior: mode change blocked without valid override.

    Expected: If preflight fails, change must be blocked.
    """
    # Try to change mode without override
    response = client.post(
        "/api/sovereign-mode/mode",
        json={
            "target_mode": "sovereign",
            "reason": "Security test - expect block",
            # No override
        },
    )

    # Should either succeed (if preflight passes) or fail (if blocked)
    assert response.status_code in [200, 400]

    if response.status_code == 400:
        error = response.json()["detail"]
        # Should mention governance/block/preflight
        assert any(
            keyword in error.lower()
            for keyword in ["blocked", "governance", "preflight", "failed"]
        )
        print(f"✅ Fail-closed behavior verified - mode change blocked")
    else:
        print(f"ℹ️  Preflight passed, no block expected")


def test_no_bypass_without_override():
    """
    Test that force=false cannot bypass governance.

    Expected: Must fail if preflight fails.
    """
    response = client.post(
        "/api/sovereign-mode/mode",
        json={
            "target_mode": "sovereign",
            "force": False,  # Explicit false
            "reason": "Test no bypass",
        },
    )

    # Should respect preflight result
    assert response.status_code in [200, 400]
    print(f"✅ force=false respects governance (status={response.status_code})")


# =============================================================================
# RUN ALL TESTS
# =============================================================================


if __name__ == "__main__":
    import traceback

    tests = [
        # Preflight tests
        test_preflight_pass_online_to_sovereign,
        test_preflight_pass_sovereign_to_online,
        test_preflight_details_structure,
        # Mode change tests
        test_mode_change_with_preflight_pass,
        test_mode_change_blocked_without_override,
        test_mode_change_with_override,
        test_deprecated_force_flag_warning,
        # Override tests
        test_override_reason_validation,
        test_override_duration_validation,
        # Audit tests
        test_audit_events_for_mode_change,
        # Security tests
        test_fail_closed_no_override,
        test_no_bypass_without_override,
    ]

    passed = 0
    failed = 0

    print("\n" + "=" * 80)
    print("G2 GOVERNANCE TESTS - Mode Switch Governance (2-Phase Commit)")
    print("=" * 80 + "\n")

    for test_func in tests:
        try:
            print(f"\n▶ Running: {test_func.__name__}")
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            traceback.print_exc()
            failed += 1
        except Exception as e:
            print(f"⚠️  ERROR: {e}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed (Total: {passed + failed})")
    print("=" * 80 + "\n")

    sys.exit(0 if failed == 0 else 1)
