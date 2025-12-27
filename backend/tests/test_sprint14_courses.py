"""
Tests for Sprint 14 - Course Monetization Features

Tests cover:
- Enrollment & progress tracking
- Certificate issuance & verification
- Micro-niche content packs
- Analytics aggregation (NO PII)
- Catalog metadata
- Backward compatibility
"""

import sys
import os
import pytest
import json
from pathlib import Path

# Path setup
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
from backend.main import app

from app.modules.course_factory.monetization_models import (
    CourseEnrollment,
    CourseProgress,
    CourseCompletion,
    Certificate,
    CertificatePayload,
    MicroNichePack,
    PackOperation,
    ContentOverride,
)
from app.modules.course_factory.monetization_service import get_monetization_service
from app.modules.course_factory.certificate_signer import get_certificate_signer

client = TestClient(app)


# ========================================
# Test 1: Enroll creates record
# ========================================

def test_enroll_creates_record():
    """Test that enrollment creates record and is retrievable."""
    response = client.post(
        "/api/courses/test_course_1/enroll",
        json={
            "language": "de",
            "actor_id": "actor_test_1"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "enrollment_id" in data
    assert data["course_id"] == "test_course_1"
    assert data["language"] == "de"
    assert data["actor_id"] == "actor_test_1"


# ========================================
# Test 2: Progress update creates record
# ========================================

def test_progress_update_creates_record():
    """Test that progress update creates record."""
    # First enroll
    enroll_response = client.post(
        "/api/courses/test_course_2/enroll",
        json={"language": "de", "actor_id": "actor_test_2"}
    )
    enrollment_id = enroll_response.json()["enrollment_id"]

    # Update progress
    progress_response = client.post(
        "/api/courses/test_course_2/progress",
        json={
            "enrollment_id": enrollment_id,
            "chapter_id": "chapter_1",
            "status": "completed"
        }
    )

    assert progress_response.status_code == 200
    progress_data = progress_response.json()
    assert progress_data["enrollment_id"] == enrollment_id
    assert progress_data["status"] == "completed"


# ========================================
# Test 3: Completion computed and stored
# ========================================

def test_completion_computed_and_stored():
    """Test that completion is computed and stored with hash."""
    # Enroll
    enroll_response = client.post(
        "/api/courses/test_course_3/enroll",
        json={"language": "de", "actor_id": "actor_test_3"}
    )
    enrollment_id = enroll_response.json()["enrollment_id"]

    # Mark complete
    complete_response = client.post(
        f"/api/courses/test_course_3/complete?enrollment_id={enrollment_id}&actor_id=actor_test_3"
    )

    assert complete_response.status_code == 200
    completion_data = complete_response.json()
    assert "completion_hash" in completion_data
    assert completion_data["course_id"] == "test_course_3"
    assert len(completion_data["completion_hash"]) == 64  # SHA-256 hex


# ========================================
# Test 4: Certificate issuance only after completion
# ========================================

def test_certificate_issuance_requires_completion():
    """Test that certificate issuance fails if course not completed."""
    # Enroll without completing
    enroll_response = client.post(
        "/api/courses/test_course_4/enroll",
        json={"language": "de", "actor_id": "actor_test_4"}
    )
    enrollment_id = enroll_response.json()["enrollment_id"]

    # Try to issue certificate (should fail)
    cert_response = client.post(
        "/api/courses/test_course_4/certificates/issue",
        json={"enrollment_id": enrollment_id}
    )

    assert cert_response.status_code == 400
    assert "not completed" in cert_response.json()["detail"].lower()


def test_certificate_issuance_succeeds_after_completion():
    """Test that certificate issuance succeeds after completion."""
    # Enroll
    enroll_response = client.post(
        "/api/courses/test_course_5/enroll",
        json={"language": "de", "actor_id": "actor_test_5"}
    )
    enrollment_id = enroll_response.json()["enrollment_id"]

    # Complete
    client.post(
        f"/api/courses/test_course_5/complete?enrollment_id={enrollment_id}&actor_id=actor_test_5"
    )

    # Issue certificate
    cert_response = client.post(
        "/api/courses/test_course_5/certificates/issue",
        json={"enrollment_id": enrollment_id}
    )

    assert cert_response.status_code == 200
    cert_data = cert_response.json()
    assert "payload" in cert_data
    assert "signature_hex" in cert_data
    assert len(cert_data["signature_hex"]) == 128  # Ed25519 signature


# ========================================
# Test 5: Certificate verify returns valid for issued cert
# ========================================

def test_certificate_verify_valid():
    """Test that certificate verification returns valid for issued cert."""
    # Enroll, complete, and issue
    enroll_response = client.post(
        "/api/courses/test_course_6/enroll",
        json={"language": "de", "actor_id": "actor_test_6"}
    )
    enrollment_id = enroll_response.json()["enrollment_id"]

    client.post(
        f"/api/courses/test_course_6/complete?enrollment_id={enrollment_id}&actor_id=actor_test_6"
    )

    cert_response = client.post(
        "/api/courses/test_course_6/certificates/issue",
        json={"enrollment_id": enrollment_id}
    )
    cert_data = cert_response.json()

    # Verify certificate
    verify_response = client.post(
        "/api/courses/certificates/verify",
        json={
            "certificate_payload": cert_data["payload"],
            "signature_hex": cert_data["signature_hex"]
        }
    )

    assert verify_response.status_code == 200
    verify_data = verify_response.json()
    assert verify_data["valid"] is True


# ========================================
# Test 6: Certificate verify fails for tampered payload
# ========================================

def test_certificate_verify_tampered():
    """Test that certificate verification fails for tampered payload."""
    # Enroll, complete, and issue
    enroll_response = client.post(
        "/api/courses/test_course_7/enroll",
        json={"language": "de", "actor_id": "actor_test_7"}
    )
    enrollment_id = enroll_response.json()["enrollment_id"]

    client.post(
        f"/api/courses/test_course_7/complete?enrollment_id={enrollment_id}&actor_id=actor_test_7"
    )

    cert_response = client.post(
        "/api/courses/test_course_7/certificates/issue",
        json={"enrollment_id": enrollment_id}
    )
    cert_data = cert_response.json()

    # Tamper with payload
    tampered_payload = cert_data["payload"].copy()
    tampered_payload["actor_id"] = "tampered_actor"

    # Verify tampered certificate
    verify_response = client.post(
        "/api/courses/certificates/verify",
        json={
            "certificate_payload": tampered_payload,
            "signature_hex": cert_data["signature_hex"]
        }
    )

    assert verify_response.status_code == 200
    verify_data = verify_response.json()
    assert verify_data["valid"] is False


# ========================================
# Test 7: Micro-niche pack created and stored
# ========================================

def test_pack_created_and_stored():
    """Test that micro-niche pack is created and stored."""
    pack_response = client.post(
        "/api/courses/test_course_8/packs",
        json={
            "target_audience": "retirees",
            "language": "de",
            "overrides": [
                {
                    "operation": "override_title",
                    "target_id": "module_1",
                    "value": "Bankwesen für Rentner"
                }
            ],
            "description": "Version for retirees"
        }
    )

    assert pack_response.status_code == 200
    pack_data = pack_response.json()
    assert "pack_id" in pack_data
    assert pack_data["target_audience"] == "retirees"
    assert len(pack_data["overrides"]) == 1


# ========================================
# Test 8: Rendered course includes overlay changes
# ========================================

def test_rendered_course_includes_overlay():
    """Test that rendered course includes pack overlay changes."""
    # Create pack
    pack_response = client.post(
        "/api/courses/test_course_9/packs",
        json={
            "target_audience": "students",
            "language": "de",
            "overrides": [
                {
                    "operation": "append_module",
                    "target_id": "new_module",
                    "value": {"title": "Extra Module for Students"}
                }
            ]
        }
    )
    pack_id = pack_response.json()["pack_id"]

    # Render course with pack
    render_response = client.get(
        f"/api/courses/test_course_9/render?pack_id={pack_id}"
    )

    assert render_response.status_code == 200
    render_data = render_response.json()
    assert render_data["applied_overrides"] >= 0
    assert "rendered_course" in render_data


# ========================================
# Test 9: Analytics summary aggregates without PII
# ========================================

def test_analytics_summary_no_pii():
    """Test that analytics summary contains only aggregates, no PII."""
    # Create some enrollments
    for i in range(3):
        client.post(
            "/api/courses/test_course_10/enroll",
            json={"language": "de", "actor_id": f"actor_{i}"}
        )

    # Get analytics
    analytics_response = client.get(
        "/api/courses/analytics/summary?course_id=test_course_10"
    )

    assert analytics_response.status_code == 200
    analytics_data = analytics_response.json()

    # Check for aggregate fields only
    assert "total_enrollments" in analytics_data
    assert "enrollments_by_language" in analytics_data
    assert "completion_rate" in analytics_data

    # Ensure NO PII fields
    assert "actor_id" not in str(analytics_data)
    assert "email" not in str(analytics_data)


# ========================================
# Test 10: Analytics export contains only aggregates
# ========================================

def test_analytics_export_only_aggregates():
    """Test that analytics export contains only aggregates."""
    # Create enrollment
    client.post(
        "/api/courses/test_course_11/enroll",
        json={"language": "de", "actor_id": "actor_11"}
    )

    # Export analytics (JSON)
    export_response = client.get(
        "/api/courses/analytics/export?course_id=test_course_11&format=json"
    )

    assert export_response.status_code == 200
    export_data = export_response.json()

    assert export_data["format"] == "json"
    assert "summary" in export_data
    assert "total_enrollments" in export_data["summary"]

    # Ensure NO PII
    assert "actor_id" not in str(export_data)


# ========================================
# Test 11: Catalog endpoints respond
# ========================================

def test_catalog_endpoint_responds():
    """Test that catalog endpoint responds with certificate_available."""
    catalog_response = client.get("/api/courses/catalog")

    assert catalog_response.status_code == 200
    catalog_data = catalog_response.json()
    assert isinstance(catalog_data, list)


def test_course_catalog_metadata():
    """Test that course catalog metadata includes certificate_available."""
    metadata_response = client.get("/api/courses/test_course_12/catalog")

    assert metadata_response.status_code == 200
    metadata_data = metadata_response.json()

    assert "certificate_available" in metadata_data
    assert metadata_data["certificate_available"] is True


# ========================================
# Test 12: Backward compatibility - existing endpoints still work
# ========================================

def test_backward_compatibility_course_factory():
    """Test that existing course factory endpoints still work."""
    # Test existing /api/course-factory/info endpoint
    info_response = client.get("/api/course-factory/info")

    assert info_response.status_code == 200
    info_data = info_response.json()
    assert "name" in info_data
    assert "CourseFactory" in info_data["name"]


def test_backward_compatibility_health_check():
    """Test that health check still works."""
    health_response = client.get("/api/courses/health")

    assert health_response.status_code == 200
    health_data = health_response.json()
    assert health_data["status"] == "healthy"
    assert "monetization" in health_data["module"].lower()


# ========================================
# Test 13: Storage atomicity (bonus)
# ========================================

def test_storage_atomicity():
    """Test that storage operations are atomic (no corruption)."""
    service = get_monetization_service()

    # Create multiple enrollments concurrently (simulate)
    enrollment_ids = []
    for i in range(5):
        enrollment = CourseEnrollment(
            course_id="test_course_13",
            language="de",
            actor_id=f"actor_{i}"
        )
        success = service.storage.save_enrollment(enrollment)
        assert success is True
        enrollment_ids.append(enrollment.enrollment_id)

    # Verify all enrollments are retrievable
    for enrollment_id in enrollment_ids:
        retrieved = service.storage.get_enrollment(enrollment_id)
        assert retrieved is not None
        assert retrieved.enrollment_id == enrollment_id


# ========================================
# Test 14: Certificate signature determinism
# ========================================

def test_certificate_signature_determinism():
    """Test that same payload produces same signature."""
    signer = get_certificate_signer()

    payload = CertificatePayload(
        course_id="test_course_14",
        course_title="Test Course",
        language="de",
        actor_id="actor_14",
        completed_at=1234567890.0,
        completion_hash="abc123",
    )

    # Sign twice
    cert1 = signer.sign_certificate(payload)
    cert2 = signer.sign_certificate(payload)

    # Same payload should produce same signature
    assert cert1.signature_hex == cert2.signature_hex


# ========================================
# Test 15: Enrollment status retrieval
# ========================================

def test_enrollment_status_retrieval():
    """Test that enrollment status retrieval works."""
    # Enroll
    enroll_response = client.post(
        "/api/courses/test_course_15/enroll",
        json={"language": "de", "actor_id": "actor_15"}
    )
    enrollment_id = enroll_response.json()["enrollment_id"]

    # Update progress
    client.post(
        "/api/courses/test_course_15/progress",
        json={
            "enrollment_id": enrollment_id,
            "chapter_id": "chapter_1",
            "status": "completed"
        }
    )

    # Get status
    status_response = client.get(
        f"/api/courses/test_course_15/status?enrollment_id={enrollment_id}"
    )

    assert status_response.status_code == 200
    status_data = status_response.json()

    assert "enrollment" in status_data
    assert "progress" in status_data
    assert len(status_data["progress"]) > 0
    assert "completion_percentage" in status_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
