"""
CourseFactory Tests - Sprint 12

Tests for course generation with IR governance.
"""

import sys
import os
from pathlib import Path

# Add backend to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from fastapi.testclient import TestClient

# Import main app (will be created)
from backend.main import app

client = TestClient(app)


def test_course_factory_info():
    """Test CourseFactory info endpoint."""
    response = client.get("/api/course-factory/info")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "CourseFactory"
    assert data["version"] == "1.0.0"
    assert "course.create" in data["ir_actions"]


def test_course_factory_health():
    """Test health check endpoint."""
    response = client.get("/api/course-factory/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["module"] == "course_factory"


def test_generate_ir_banking_course():
    """Test IR generation for banking alternatives course."""
    payload = {
        "tenant_id": "test_tenant",
        "title": "Alternativen zu Banken & Sparkassen – Was du heute wissen musst",
        "description": "Ein praxisnaher Grundlagenkurs für Privatpersonen",
        "language": "de",
        "target_audiences": ["private_individuals", "employees"],
        "full_lessons_count": 3,
        "generate_quiz": True,
        "generate_landing_page": True,
        "dry_run": True,
    }

    response = client.post("/api/course-factory/generate-ir", json=payload)
    assert response.status_code == 200

    ir = response.json()
    assert ir["tenant_id"] == "test_tenant"
    assert len(ir["steps"]) >= 3  # At least outline, lessons, quiz


def test_validate_ir_banking_course():
    """Test IR validation for banking course."""
    # First generate IR
    payload = {
        "tenant_id": "test_tenant",
        "title": "Test Course",
        "description": "Test description",
        "language": "de",
        "target_audiences": ["private_individuals"],
        "full_lessons_count": 3,
        "generate_quiz": True,
        "generate_landing_page": True,
        "dry_run": True,
    }

    ir_response = client.post("/api/course-factory/generate-ir", json=payload)
    assert ir_response.status_code == 200
    ir = ir_response.json()

    # Validate IR
    validate_response = client.post("/api/course-factory/validate-ir", json=ir)
    assert validate_response.status_code == 200

    validation = validate_response.json()
    assert validation["status"] in ["PASS", "ESCALATE", "REJECT"]
    assert "risk_tier" in validation


def test_dry_run_banking_course():
    """Test dry-run course generation."""
    payload = {
        "tenant_id": "test_tenant",
        "title": "Alternativen zu Banken & Sparkassen",
        "description": "Test banking course",
        "language": "de",
        "target_audiences": ["private_individuals"],
        "full_lessons_count": 3,
        "generate_quiz": True,
        "generate_landing_page": True,
        "dry_run": True,
    }

    response = client.post("/api/course-factory/dry-run", json=payload)
    assert response.status_code == 200

    result = response.json()
    assert result["success"] is True
    assert result["total_modules"] >= 4
    assert result["total_lessons"] >= 12
    assert result["full_lessons_generated"] == 0  # Dry-run doesn't generate content


@pytest.mark.slow
def test_generate_full_banking_course():
    """
    Test full course generation (slow test).

    This test actually generates the German banking course.
    """
    payload = {
        "tenant_id": "test_tenant",
        "title": "Alternativen zu Banken & Sparkassen – Was du heute wissen musst",
        "description": "Ein praxisnaher Grundlagenkurs für Privatpersonen, Angestellte und Berufseinsteiger",
        "language": "de",
        "target_audiences": ["private_individuals", "employees", "career_starters"],
        "full_lessons_count": 3,
        "generate_quiz": True,
        "generate_landing_page": True,
        "deploy_to_staging": False,
        "dry_run": False,  # Actually generate
    }

    response = client.post("/api/course-factory/generate", json=payload)
    assert response.status_code == 200

    result = response.json()
    assert result["success"] is True
    assert result["total_modules"] == 4
    assert result["total_lessons"] == 15
    assert result["full_lessons_generated"] == 3
    assert result["quiz_questions_count"] == 15

    # Check outline structure
    assert result["outline"] is not None
    assert len(result["outline"]["modules"]) == 4

    # Check quiz
    assert result["quiz"] is not None
    assert len(result["quiz"]["questions"]) == 15

    # Check landing page
    assert result["landing_page"] is not None
    assert "Banken" in result["landing_page"]["hero_title"]

    # Check evidence pack
    assert result["evidence_pack_path"] is not None
    evidence_path = Path(result["evidence_pack_path"])
    assert evidence_path.exists()

    # Check lesson files
    lessons_dir = evidence_path / "lessons"
    assert lessons_dir.exists()
    lesson_files = list(lessons_dir.glob("*.md"))
    assert len(lesson_files) == 3  # 3 full lessons


if __name__ == "__main__":
    # Run specific test
    pytest.main([__file__, "-v", "-s"])
