# backend/tests/test_axe_endpoints.py

import os
import sys
from fastapi.testclient import TestClient

# PROJECT_ROOT = ...\brain_modular_refactor
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.main import app  # noqa: E402

client = TestClient(app)


def test_axe_info():
    resp = client.get("/api/axe/info")
    assert resp.status_code == 200
    data = resp.json()

    assert "name" in data
    assert "version" in data
    # Name muss nicht zwingend mit "brain" anfangen, aber Axe enthalten
    assert "axe" in data["name"].lower()


def test_axe_message_echo():
    payload = {"message": "Test-AXE", "meta": {"source": "pytest"}}
    resp = client.post("/api/axe/message", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert data.get("input_message") == "Test-AXE"
    assert "reply" in data
