"""
G4 Governance Monitoring Tests

Tests for:
- G4.1: Governance Metrics (Counter, Gauge, Prometheus export)
- G4.2: Evidence Pack documentation (file existence)
- G4.3: Audit Snapshot Export (JSONL, SHA256)
- G4.4: Governance Status Endpoint (aggregated health)
- Security: No sensitive data leaks
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
# G4.1: GOVERNANCE METRICS TESTS
# =============================================================================


def test_metrics_counter_increment():
    """
    Test Counter increments correctly.
    """
    from backend.app.modules.sovereign_mode.governance_metrics import Counter

    counter = Counter(name="test_counter", description="Test counter")

    # Initial value is 0
    assert counter.get() == 0.0

    # Increment
    counter.inc()
    assert counter.get() == 1.0

    # Increment by amount
    counter.inc(amount=5.0)
    assert counter.get() == 6.0

    print("✅ Counter increments correctly")


def test_metrics_counter_labels():
    """
    Test Counter with labels.
    """
    from backend.app.modules.sovereign_mode.governance_metrics import Counter

    counter = Counter(
        name="test_labeled_counter",
        description="Test counter with labels",
        labels=["status", "type"]
    )

    # Increment with label values
    counter.inc({"status": "success", "type": "http"}, amount=1)
    counter.inc({"status": "fail", "type": "http"}, amount=2)
    counter.inc({"status": "success", "type": "grpc"}, amount=3)

    # Check values
    assert counter.get({"status": "success", "type": "http"}) == 1.0
    assert counter.get({"status": "fail", "type": "http"}) == 2.0
    assert counter.get({"status": "success", "type": "grpc"}) == 3.0

    # Get all values
    all_values = counter.get_all()
    assert len(all_values) == 3

    print("✅ Counter labels work correctly")


def test_metrics_gauge():
    """
    Test Gauge set/get operations.
    """
    from backend.app.modules.sovereign_mode.governance_metrics import Gauge

    gauge = Gauge(name="test_gauge", description="Test gauge")

    # Initial value is 0
    assert gauge.get() == 0.0

    # Set value
    gauge.set(42.5)
    assert gauge.get() == 42.5

    # Increment
    gauge.inc(7.5)
    assert gauge.get() == 50.0

    # Decrement
    gauge.dec(10.0)
    assert gauge.get() == 40.0

    print("✅ Gauge operations work correctly")


def test_metrics_thread_safety():
    """
    Test metrics are thread-safe.
    """
    import threading
    from backend.app.modules.sovereign_mode.governance_metrics import Counter

    counter = Counter(name="thread_test_counter", description="Thread safety test")

    def increment_many():
        for _ in range(1000):
            counter.inc()

    # Run 10 threads incrementing concurrently
    threads = [threading.Thread(target=increment_many) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Should be exactly 10 * 1000 = 10000
    assert counter.get() == 10000.0

    print("✅ Metrics are thread-safe")


def test_governance_metrics_singleton():
    """
    Test GovernanceMetrics singleton pattern.
    """
    from backend.app.modules.sovereign_mode.governance_metrics import (
        get_governance_metrics,
        reset_governance_metrics,
    )

    # Reset to ensure clean state
    reset_governance_metrics()

    # Get instance
    metrics1 = get_governance_metrics()
    metrics2 = get_governance_metrics()

    # Should be same instance
    assert metrics1 is metrics2

    # Record some events
    metrics1.record_mode_switch("sovereign")
    metrics1.record_preflight_failure("network_gate")

    # Should be reflected in both instances (same object)
    assert metrics2.mode_switch_count.get({"target_mode": "sovereign"}) == 1.0
    assert metrics2.preflight_failure_count.get({"gate": "network_gate"}) == 1.0

    print("✅ GovernanceMetrics singleton works correctly")


def test_metrics_prometheus_format():
    """
    Test Prometheus metrics export format.
    """
    from backend.app.modules.sovereign_mode.governance_metrics import (
        get_governance_metrics,
        reset_governance_metrics,
    )

    # Reset and record some events
    reset_governance_metrics()
    metrics = get_governance_metrics()

    metrics.record_mode_switch("sovereign")
    metrics.record_mode_switch("online")
    metrics.record_preflight_failure("network_gate")
    metrics.record_override_usage()
    metrics.set_override_active(True)

    # Export Prometheus format
    prom_text = metrics.get_prometheus_metrics()

    # Verify format
    assert "# HELP sovereign_mode_switch_total" in prom_text
    assert "# TYPE sovereign_mode_switch_total counter" in prom_text
    assert 'sovereign_mode_switch_total{target_mode="sovereign"} 1' in prom_text
    assert 'sovereign_mode_switch_total{target_mode="online"} 1' in prom_text
    assert 'sovereign_preflight_failure_total{gate="network_gate"} 1' in prom_text
    assert "sovereign_override_usage_total 1" in prom_text
    assert "sovereign_override_active 1" in prom_text

    print("✅ Prometheus format export works correctly")


def test_metrics_json_summary():
    """
    Test JSON summary export.
    """
    from backend.app.modules.sovereign_mode.governance_metrics import (
        get_governance_metrics,
        reset_governance_metrics,
    )

    reset_governance_metrics()
    metrics = get_governance_metrics()

    metrics.record_mode_switch("sovereign")
    metrics.record_bundle_signature_failure()
    metrics.record_axe_trust_violation("external")

    summary = metrics.get_summary()

    # Verify structure
    assert "mode_switches" in summary
    assert "override_usage_total" in summary
    assert "bundle_signature_failures" in summary
    assert "axe_trust_violations" in summary
    assert "override_active" in summary
    assert "last_update" in summary

    # Verify values
    assert summary["mode_switches"]["sovereign"] == 1.0
    assert summary["bundle_signature_failures"] == 1.0
    assert summary["axe_trust_violations"]["external"] == 1.0
    assert summary["override_active"] is False

    print("✅ JSON summary export works correctly")


def test_metrics_endpoint():
    """
    Test GET /api/sovereign-mode/metrics endpoint.
    """
    response = client.get("/api/sovereign-mode/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    # Should contain Prometheus format
    content = response.text
    assert "# HELP" in content
    assert "# TYPE" in content

    print("✅ Metrics endpoint returns Prometheus format")


def test_metrics_summary_endpoint():
    """
    Test GET /api/sovereign-mode/metrics/summary endpoint.
    """
    response = client.get("/api/sovereign-mode/metrics/summary")

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "mode_switches" in data
    assert "override_usage_total" in data
    assert "bundle_signature_failures" in data
    assert "axe_trust_violations" in data
    assert "override_active" in data
    assert "last_update" in data

    print("✅ Metrics summary endpoint works correctly")


# =============================================================================
# G4.2: EVIDENCE PACK TESTS
# =============================================================================


def test_evidence_pack_exists():
    """
    Test that Evidence Pack documentation exists.
    """
    evidence_pack_path = os.path.join(ROOT, "docs", "GOVERNANCE_EVIDENCE_PACK.md")

    assert os.path.exists(evidence_pack_path), f"Evidence Pack not found at {evidence_pack_path}"
    assert os.path.isfile(evidence_pack_path)

    # Verify it's not empty
    with open(evidence_pack_path) as f:
        content = f.read()
        assert len(content) > 1000  # Should be substantial

    print("✅ Evidence Pack documentation exists")


def test_evidence_pack_structure():
    """
    Test Evidence Pack contains required sections.
    """
    evidence_pack_path = os.path.join(ROOT, "docs", "GOVERNANCE_EVIDENCE_PACK.md")

    with open(evidence_pack_path) as f:
        content = f.read()

    # Required sections
    required_sections = [
        "# BRAiN Governance Evidence Pack",
        "## 1. What is Sovereign Mode?",
        "## 2. How Can You Prove Sovereign Mode is Active?",
        "## 3. How Are Mode Changes Governed?",
        "## 4. What Protects the System from Unauthorized Bundles?",
        "## 5. What Protects Against External Access to AXE?",
        "## 6. How Are Overrides Logged and Auditable?",
        "## 7. What Metrics Are Available?",
        "## 8. How to Export Audit Logs for Compliance?",
        "## 9. Risk Statement & Limitations",
    ]

    for section in required_sections:
        assert section in content, f"Missing section: {section}"

    print("✅ Evidence Pack has all required sections")


# =============================================================================
# G4.3: AUDIT EXPORT TESTS
# =============================================================================


def test_audit_export_endpoint():
    """
    Test POST /api/sovereign-mode/audit/export endpoint.
    """
    response = client.post(
        "/api/sovereign-mode/audit/export",
        json={
            "start_time": None,
            "end_time": None,
            "event_types": None,
            "include_hash": True,
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert data["success"] is True
    assert "export_id" in data
    assert "event_count" in data
    assert data["format"] == "jsonl"
    assert data["hash_algorithm"] == "SHA256"
    assert "content_hash" in data
    assert "timestamp" in data

    print(f"✅ Audit export endpoint works (exported {data['event_count']} events)")


def test_audit_export_time_filtering():
    """
    Test audit export with time range filtering.
    """
    now = datetime.utcnow()
    start_time = (now - timedelta(hours=24)).isoformat() + "Z"
    end_time = now.isoformat() + "Z"

    response = client.post(
        "/api/sovereign-mode/audit/export",
        json={
            "start_time": start_time,
            "end_time": end_time,
            "event_types": None,
            "include_hash": True,
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    print(f"✅ Audit export with time filtering works ({data['event_count']} events in last 24h)")


def test_audit_export_event_type_filtering():
    """
    Test audit export with event type filtering.
    """
    response = client.post(
        "/api/sovereign-mode/audit/export",
        json={
            "start_time": None,
            "end_time": None,
            "event_types": ["sovereign.mode_changed", "sovereign.bundle_loaded"],
            "include_hash": True,
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    print(f"✅ Audit export with event type filtering works ({data['event_count']} events)")


def test_audit_export_hash_optional():
    """
    Test audit export without hash.
    """
    response = client.post(
        "/api/sovereign-mode/audit/export",
        json={
            "include_hash": False,
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["hash_algorithm"] is None
    assert data["content_hash"] is None

    print("✅ Audit export without hash works")


def test_audit_export_emits_audit_event():
    """
    Test that audit export emits GOVERNANCE_AUDIT_EXPORTED event.
    """
    # Perform export
    response = client.post(
        "/api/sovereign-mode/audit/export",
        json={"include_hash": True}
    )
    assert response.status_code == 200

    # Check audit log for export event
    audit_response = client.get("/api/sovereign-mode/audit")
    assert audit_response.status_code == 200

    audit_log = audit_response.json()
    export_events = [
        e for e in audit_log
        if e.get("event_type") == "sovereign.governance_audit_exported"
    ]

    assert len(export_events) > 0, "GOVERNANCE_AUDIT_EXPORTED event not found"

    print(f"✅ Audit export emits audit event (found {len(export_events)} events)")


# =============================================================================
# G4.4: GOVERNANCE STATUS TESTS
# =============================================================================


def test_governance_status_endpoint():
    """
    Test GET /api/sovereign-mode/governance/status endpoint.
    """
    response = client.get("/api/sovereign-mode/governance/status")

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "overall_governance" in data
    assert "g1_bundle_trust" in data
    assert "g2_mode_governance" in data
    assert "g3_axe_security" in data
    assert "critical_events_24h" in data
    assert "last_update" in data

    # Verify overall_governance is valid health status
    assert data["overall_governance"] in ["healthy", "warning", "critical"]

    print(f"✅ Governance status endpoint works (health: {data['overall_governance']})")


def test_governance_status_g1_structure():
    """
    Test G1 Bundle Trust status structure.
    """
    response = client.get("/api/sovereign-mode/governance/status")
    assert response.status_code == 200

    g1 = response.json()["g1_bundle_trust"]

    # Verify G1 structure
    assert "status" in g1
    assert "bundles_total" in g1
    assert "bundles_validated" in g1
    assert "bundles_quarantined" in g1
    assert "signature_failures_24h" in g1

    assert g1["status"] in ["healthy", "warning", "critical"]
    assert isinstance(g1["bundles_total"], int)

    print(f"✅ G1 status structure correct (bundles: {g1['bundles_total']})")


def test_governance_status_g2_structure():
    """
    Test G2 Mode Governance status structure.
    """
    response = client.get("/api/sovereign-mode/governance/status")
    assert response.status_code == 200

    g2 = response.json()["g2_mode_governance"]

    # Verify G2 structure
    assert "status" in g2
    assert "current_mode" in g2
    assert "override_active" in g2
    assert "preflight_failures_24h" in g2
    assert "mode_switches_24h" in g2

    assert g2["status"] in ["healthy", "warning", "critical"]
    assert isinstance(g2["override_active"], bool)

    print(f"✅ G2 status structure correct (mode: {g2['current_mode']})")


def test_governance_status_g3_structure():
    """
    Test G3 AXE Security status structure.
    """
    response = client.get("/api/sovereign-mode/governance/status")
    assert response.status_code == 200

    g3 = response.json()["g3_axe_security"]

    # Verify G3 structure
    assert "status" in g3
    assert "dmz_running" in g3
    assert "trust_violations_24h" in g3
    assert "external_requests_blocked_24h" in g3

    assert g3["status"] in ["healthy", "warning", "critical"]
    assert isinstance(g3["dmz_running"], bool)

    print(f"✅ G3 status structure correct (violations: {g3['trust_violations_24h']})")


def test_governance_status_critical_events():
    """
    Test critical events listing.
    """
    response = client.get("/api/sovereign-mode/governance/status")
    assert response.status_code == 200

    critical_events = response.json()["critical_events_24h"]

    # Should be a list
    assert isinstance(critical_events, list)

    # If there are events, verify structure
    for event in critical_events:
        assert "timestamp" in event
        assert "event_type" in event
        assert "severity" in event
        assert "reason" in event

    print(f"✅ Critical events listed ({len(critical_events)} in last 24h)")


# =============================================================================
# SECURITY TESTS (No Sensitive Data Leaks)
# =============================================================================


def test_metrics_no_sensitive_data():
    """
    Test that metrics don't contain sensitive data.
    """
    response = client.get("/api/sovereign-mode/metrics")
    assert response.status_code == 200

    content = response.text.lower()

    # Should NOT contain sensitive keywords
    forbidden_keywords = [
        "password", "secret", "api_key", "token", "credential",
        "pii", "email", "phone", "address", "payload"
    ]

    for keyword in forbidden_keywords:
        assert keyword not in content, f"Metrics contain sensitive keyword: {keyword}"

    print("✅ Metrics contain no sensitive data")


def test_metrics_summary_no_sensitive_data():
    """
    Test that metrics summary doesn't contain sensitive data.
    """
    response = client.get("/api/sovereign-mode/metrics/summary")
    assert response.status_code == 200

    data = response.json()
    data_str = str(data).lower()

    # Should NOT contain sensitive keywords
    forbidden_keywords = [
        "password", "secret", "api_key", "token", "credential",
        "pii", "email", "phone", "address", "payload"
    ]

    for keyword in forbidden_keywords:
        assert keyword not in data_str, f"Metrics summary contains sensitive keyword: {keyword}"

    print("✅ Metrics summary contains no sensitive data")


def test_governance_status_no_sensitive_data():
    """
    Test that governance status doesn't leak sensitive data.
    """
    response = client.get("/api/sovereign-mode/governance/status")
    assert response.status_code == 200

    data = response.json()
    data_str = str(data).lower()

    # Should NOT contain sensitive keywords
    forbidden_keywords = [
        "password", "secret", "api_key", "token", "credential",
        "pii", "email", "phone", "payload"
    ]

    for keyword in forbidden_keywords:
        assert keyword not in data_str, f"Governance status contains sensitive keyword: {keyword}"

    print("✅ Governance status contains no sensitive data")


# =============================================================================
# RUN ALL TESTS
# =============================================================================


if __name__ == "__main__":
    import traceback

    tests = [
        # G4.1: Metrics tests
        test_metrics_counter_increment,
        test_metrics_counter_labels,
        test_metrics_gauge,
        test_metrics_thread_safety,
        test_governance_metrics_singleton,
        test_metrics_prometheus_format,
        test_metrics_json_summary,
        test_metrics_endpoint,
        test_metrics_summary_endpoint,
        # G4.2: Evidence Pack tests
        test_evidence_pack_exists,
        test_evidence_pack_structure,
        # G4.3: Audit Export tests
        test_audit_export_endpoint,
        test_audit_export_time_filtering,
        test_audit_export_event_type_filtering,
        test_audit_export_hash_optional,
        test_audit_export_emits_audit_event,
        # G4.4: Governance Status tests
        test_governance_status_endpoint,
        test_governance_status_g1_structure,
        test_governance_status_g2_structure,
        test_governance_status_g3_structure,
        test_governance_status_critical_events,
        # Security tests
        test_metrics_no_sensitive_data,
        test_metrics_summary_no_sensitive_data,
        test_governance_status_no_sensitive_data,
    ]

    passed = 0
    failed = 0

    print("\n" + "=" * 80)
    print("G4 GOVERNANCE MONITORING TESTS")
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
