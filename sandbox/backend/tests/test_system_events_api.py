"""
Test System Events CRUD API

Tests all endpoints for the system events service including:
- Create event
- Get event by ID
- List events with filtering
- Update event
- Delete event
- Get statistics
"""
import sys
import os
from datetime import datetime, timedelta

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
import pytest


# Import the app - will need to be adjusted based on deployment
# For v3: from backend.main_minimal_v3 import app
# For standard: from backend.main import app
try:
    from backend.main_minimal_v3 import app
except ImportError:
    from backend.main import app

client = TestClient(app)


class TestSystemEventsAPI:
    """Test suite for System Events CRUD operations"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        # Store created event IDs for cleanup
        self.created_event_ids = []
        yield
        # Cleanup: delete all created events
        for event_id in self.created_event_ids:
            try:
                client.delete(f"/api/events/{event_id}")
            except Exception:
                pass  # Ignore cleanup errors

    def test_create_event_minimal(self):
        """Test creating an event with minimal required fields"""
        payload = {
            "event_type": "test_event",
            "severity": "info",
            "message": "This is a test event"
        }

        response = client.post("/api/events", json=payload)

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert data["event_type"] == "test_event"
        assert data["severity"] == "info"
        assert data["message"] == "This is a test event"
        assert data["details"] is None
        assert data["source"] is None
        assert "timestamp" in data
        assert "created_at" in data

        self.created_event_ids.append(data["id"])

    def test_create_event_full(self):
        """Test creating an event with all fields"""
        payload = {
            "event_type": "deployment",
            "severity": "warning",
            "message": "Deployment to production initiated",
            "details": {
                "environment": "production",
                "version": "1.0.0",
                "user": "admin"
            },
            "source": "deployment_service"
        }

        response = client.post("/api/events", json=payload)

        assert response.status_code == 201
        data = response.json()

        assert data["event_type"] == "deployment"
        assert data["severity"] == "warning"
        assert data["message"] == "Deployment to production initiated"
        assert data["details"]["environment"] == "production"
        assert data["details"]["version"] == "1.0.0"
        assert data["source"] == "deployment_service"

        self.created_event_ids.append(data["id"])

    def test_create_event_all_severities(self):
        """Test creating events with all severity levels"""
        severities = ["info", "warning", "error", "critical"]

        for severity in severities:
            payload = {
                "event_type": "test_severity",
                "severity": severity,
                "message": f"Testing {severity} severity"
            }

            response = client.post("/api/events", json=payload)

            assert response.status_code == 201
            data = response.json()
            assert data["severity"] == severity

            self.created_event_ids.append(data["id"])

    def test_create_event_validation_error(self):
        """Test validation errors on event creation"""
        # Missing required field
        response = client.post("/api/events", json={
            "event_type": "test",
            "message": "Missing severity"
        })
        assert response.status_code == 422

        # Invalid severity
        response = client.post("/api/events", json={
            "event_type": "test",
            "severity": "invalid_severity",
            "message": "Test"
        })
        assert response.status_code == 422

        # Empty event_type
        response = client.post("/api/events", json={
            "event_type": "",
            "severity": "info",
            "message": "Test"
        })
        assert response.status_code == 422

    def test_get_event_by_id(self):
        """Test retrieving an event by ID"""
        # Create an event first
        create_response = client.post("/api/events", json={
            "event_type": "test_get",
            "severity": "info",
            "message": "Testing get by ID"
        })
        event_id = create_response.json()["id"]
        self.created_event_ids.append(event_id)

        # Get the event
        response = client.get(f"/api/events/{event_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == event_id
        assert data["event_type"] == "test_get"
        assert data["severity"] == "info"

    def test_get_event_not_found(self):
        """Test getting a non-existent event"""
        response = client.get("/api/events/999999")
        assert response.status_code == 404

    def test_list_events(self):
        """Test listing events without filters"""
        # Create multiple events
        for i in range(3):
            response = client.post("/api/events", json={
                "event_type": f"test_list_{i}",
                "severity": "info",
                "message": f"Test event {i}"
            })
            self.created_event_ids.append(response.json()["id"])

        # List events
        response = client.get("/api/events")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 3  # At least our 3 events

    def test_list_events_with_limit(self):
        """Test listing events with limit parameter"""
        response = client.get("/api/events?limit=5")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) <= 5

    def test_list_events_with_offset(self):
        """Test listing events with offset parameter"""
        # Get first page
        response1 = client.get("/api/events?limit=2&offset=0")
        data1 = response1.json()

        # Get second page
        response2 = client.get("/api/events?limit=2&offset=2")
        data2 = response2.json()

        # Ensure different results (if enough events exist)
        if len(data1) == 2 and len(data2) > 0:
            assert data1[0]["id"] != data2[0]["id"]

    def test_list_events_filter_by_type(self):
        """Test filtering events by event_type"""
        # Create events with specific type
        for i in range(2):
            response = client.post("/api/events", json={
                "event_type": "test_filter_type",
                "severity": "info",
                "message": f"Filter test {i}"
            })
            self.created_event_ids.append(response.json()["id"])

        # Filter by type
        response = client.get("/api/events?event_type=test_filter_type")

        assert response.status_code == 200
        data = response.json()

        # All returned events should have the filtered type
        for event in data:
            assert event["event_type"] == "test_filter_type"

    def test_list_events_filter_by_severity(self):
        """Test filtering events by severity"""
        # Create events with different severities
        severities = ["info", "warning", "error"]
        for severity in severities:
            response = client.post("/api/events", json={
                "event_type": "test_filter_severity",
                "severity": severity,
                "message": f"Testing {severity}"
            })
            self.created_event_ids.append(response.json()["id"])

        # Filter by severity
        response = client.get("/api/events?severity=error")

        assert response.status_code == 200
        data = response.json()

        # All returned events should have the filtered severity
        for event in data:
            assert event["severity"] == "error"

    def test_list_events_filter_combined(self):
        """Test filtering events by both type and severity"""
        # Create event with specific type and severity
        response = client.post("/api/events", json={
            "event_type": "test_combined_filter",
            "severity": "critical",
            "message": "Combined filter test"
        })
        event_id = response.json()["id"]
        self.created_event_ids.append(event_id)

        # Filter by both
        response = client.get(
            "/api/events?event_type=test_combined_filter&severity=critical"
        )

        assert response.status_code == 200
        data = response.json()

        # Should find our event
        event_ids = [e["id"] for e in data]
        assert event_id in event_ids

    def test_update_event(self):
        """Test updating an event"""
        # Create an event
        create_response = client.post("/api/events", json={
            "event_type": "test_update",
            "severity": "info",
            "message": "Original message"
        })
        event_id = create_response.json()["id"]
        self.created_event_ids.append(event_id)

        # Update the event
        update_payload = {
            "message": "Updated message",
            "severity": "warning"
        }

        response = client.put(f"/api/events/{event_id}", json=update_payload)

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == event_id
        assert data["message"] == "Updated message"
        assert data["severity"] == "warning"

    def test_update_event_partial(self):
        """Test partial update (only some fields)"""
        # Create an event
        create_response = client.post("/api/events", json={
            "event_type": "test_partial_update",
            "severity": "info",
            "message": "Original message",
            "source": "test_source"
        })
        event_id = create_response.json()["id"]
        self.created_event_ids.append(event_id)

        # Update only message
        response = client.put(f"/api/events/{event_id}", json={
            "message": "New message"
        })

        assert response.status_code == 200
        data = response.json()

        # Message updated, others unchanged
        assert data["message"] == "New message"
        assert data["event_type"] == "test_partial_update"
        assert data["severity"] == "info"
        assert data["source"] == "test_source"

    def test_update_event_not_found(self):
        """Test updating a non-existent event"""
        response = client.put("/api/events/999999", json={
            "message": "This should fail"
        })
        assert response.status_code == 404

    def test_delete_event(self):
        """Test deleting an event"""
        # Create an event
        create_response = client.post("/api/events", json={
            "event_type": "test_delete",
            "severity": "info",
            "message": "To be deleted"
        })
        event_id = create_response.json()["id"]

        # Delete the event
        response = client.delete(f"/api/events/{event_id}")

        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(f"/api/events/{event_id}")
        assert get_response.status_code == 404

    def test_delete_event_not_found(self):
        """Test deleting a non-existent event"""
        response = client.delete("/api/events/999999")
        assert response.status_code == 404

    def test_get_event_stats(self):
        """Test getting event statistics"""
        # Create some events for stats
        events_to_create = [
            {"event_type": "test_stats_1", "severity": "info", "message": "Test 1"},
            {"event_type": "test_stats_1", "severity": "warning", "message": "Test 2"},
            {"event_type": "test_stats_2", "severity": "error", "message": "Test 3"},
        ]

        for event_data in events_to_create:
            response = client.post("/api/events", json=event_data)
            self.created_event_ids.append(response.json()["id"])

        # Get stats
        response = client.get("/api/events/stats")

        assert response.status_code == 200
        data = response.json()

        # Verify stats structure
        assert "total_events" in data
        assert "events_by_severity" in data
        assert "events_by_type" in data
        assert "recent_events" in data
        assert "last_event_timestamp" in data

        # Verify some data
        assert data["total_events"] >= 3
        assert isinstance(data["events_by_severity"], dict)
        assert isinstance(data["events_by_type"], dict)

    def test_event_caching(self):
        """Test that caching works (get same event twice)"""
        # Create an event
        create_response = client.post("/api/events", json={
            "event_type": "test_cache",
            "severity": "info",
            "message": "Testing cache"
        })
        event_id = create_response.json()["id"]
        self.created_event_ids.append(event_id)

        # Get the event twice
        response1 = client.get(f"/api/events/{event_id}")
        response2 = client.get(f"/api/events/{event_id}")

        # Both should return the same data
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()

    def test_event_cache_invalidation_on_update(self):
        """Test that cache is invalidated when event is updated"""
        # Create an event
        create_response = client.post("/api/events", json={
            "event_type": "test_cache_invalidation",
            "severity": "info",
            "message": "Original"
        })
        event_id = create_response.json()["id"]
        self.created_event_ids.append(event_id)

        # Get the event (caches it)
        response1 = client.get(f"/api/events/{event_id}")
        original_message = response1.json()["message"]

        # Update the event
        client.put(f"/api/events/{event_id}", json={
            "message": "Updated"
        })

        # Get the event again (should fetch updated version)
        response2 = client.get(f"/api/events/{event_id}")
        updated_message = response2.json()["message"]

        assert original_message == "Original"
        assert updated_message == "Updated"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
