import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_mission_root_info():
    resp = client.get("/api/missions/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Mission System"
    assert "version" in data

def test_mission_health():
    resp = client.get("/api/missions/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
