import os
import sys

# PROJECT_ROOT = ...\brain_modular_refactor
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_connectors_info():
    resp = client.get("/api/connectors/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Connector Hub"


def test_agents_info():
    resp = client.get("/api/agents/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Agent Manager"
