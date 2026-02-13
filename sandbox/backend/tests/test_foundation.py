"""
Tests for Foundation Module

Tests ethics enforcement, safety checks, and behavior tree execution.
"""

import sys
import os

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from fastapi.testclient import TestClient

# Import after path is set
from main import app
from app.modules.foundation.schemas import (
    ActionValidationRequest,
    BehaviorTreeNode,
    FoundationConfig,
)
from app.modules.foundation.service import FoundationService


client = TestClient(app)


# ============================================================================
# Service Tests (Unit)
# ============================================================================


class TestFoundationService:
    """Unit tests for FoundationService"""

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test Foundation service initializes correctly"""
        service = FoundationService()

        assert service.config.ethics_enabled is True
        assert service.config.safety_checks is True
        assert service.violations == 0
        assert service.overrides == 0

    @pytest.mark.asyncio
    async def test_validate_safe_action(self):
        """Test validation of a safe action"""
        service = FoundationService()

        request = ActionValidationRequest(
            action="robot.move", params={"distance": 10, "speed": 2}
        )

        result = await service.validate_action(request)

        assert result.valid is True
        assert result.action == "robot.move"
        assert result.severity == "info"

    @pytest.mark.asyncio
    async def test_block_blacklisted_action(self):
        """Test blocking of blacklisted dangerous action"""
        service = FoundationService()

        request = ActionValidationRequest(
            action="delete_all", params={"target": "/data"}
        )

        result = await service.validate_action(request)

        assert result.valid is False
        assert result.severity == "critical"
        assert "blacklisted" in result.reason.lower()
        assert service.overrides == 1

    @pytest.mark.asyncio
    async def test_strict_mode_whitelist(self):
        """Test strict mode with whitelist"""
        config = FoundationConfig(
            strict_mode=True, allowed_actions=["robot.move", "robot.stop"]
        )
        service = FoundationService(config=config)

        # Whitelisted action should pass
        request1 = ActionValidationRequest(action="robot.move", params={})
        result1 = await service.validate_action(request1)
        assert result1.valid is True

        # Non-whitelisted action should fail
        request2 = ActionValidationRequest(action="robot.jump", params={})
        result2 = await service.validate_action(request2)
        assert result2.valid is False
        assert service.violations == 1

    @pytest.mark.asyncio
    async def test_disabled_checks(self):
        """Test that all actions pass when checks disabled"""
        config = FoundationConfig(ethics_enabled=False, safety_checks=False)
        service = FoundationService(config=config)

        # Even dangerous action should pass
        request = ActionValidationRequest(action="delete_all", params={})
        result = await service.validate_action(request)

        assert result.valid is True

    @pytest.mark.asyncio
    async def test_behavior_tree_execution(self):
        """Test behavior tree execution (placeholder)"""
        service = FoundationService()

        tree = BehaviorTreeNode(
            node_id="test_sequence",
            node_type="sequence",
            children=[
                BehaviorTreeNode(
                    node_id="check_battery",
                    node_type="condition",
                    action="battery.check",
                    params={"min_level": 20},
                ),
                BehaviorTreeNode(
                    node_id="move_forward",
                    node_type="action",
                    action="robot.move",
                    params={"distance": 5},
                ),
            ],
        )

        result = await service.execute_behavior_tree(tree)

        assert result.status == "success"
        assert result.node_id == "test_sequence"
        assert len(result.executed_nodes) == 3  # root + 2 children

    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test getting Foundation status"""
        service = FoundationService()

        # Trigger some actions to create metrics
        await service.validate_action(
            ActionValidationRequest(action="safe_action", params={})
        )
        await service.validate_action(
            ActionValidationRequest(action="delete_all", params={})
        )

        status = await service.get_status()

        assert status.active is True
        assert status.ethics_enabled is True
        assert status.total_validations == 2
        assert status.safety_overrides == 1  # delete_all was blocked


# ============================================================================
# API Tests (Integration)
# ============================================================================


class TestFoundationAPI:
    """Integration tests for Foundation API endpoints"""

    def test_get_status(self):
        """Test GET /api/foundation/status"""
        response = client.get("/api/foundation/status")

        assert response.status_code == 200
        data = response.json()

        assert "active" in data
        assert "ethics_enabled" in data
        assert "safety_checks" in data
        assert "total_validations" in data

    def test_get_config(self):
        """Test GET /api/foundation/config"""
        response = client.get("/api/foundation/config")

        assert response.status_code == 200
        data = response.json()

        assert "ethics_enabled" in data
        assert "safety_checks" in data
        assert "blocked_actions" in data

    def test_update_config(self):
        """Test PUT /api/foundation/config"""
        new_config = {
            "ethics_enabled": False,
            "safety_checks": True,
            "strict_mode": False,
            "blocked_actions": ["test_action"],
        }

        response = client.put("/api/foundation/config", json=new_config)

        assert response.status_code == 200
        data = response.json()

        assert data["ethics_enabled"] is False
        assert data["safety_checks"] is True

    def test_validate_safe_action_api(self):
        """Test POST /api/foundation/validate with safe action"""
        payload = {
            "action": "robot.move",
            "params": {"distance": 10, "speed": 2},
            "context": {"agent_id": "robot_001"},
        }

        response = client.post("/api/foundation/validate", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert data["action"] == "robot.move"

    def test_validate_dangerous_action_api(self):
        """Test POST /api/foundation/validate with dangerous action"""
        payload = {
            "action": "delete_all",
            "params": {"target": "/data"},
            "context": {},
        }

        response = client.post("/api/foundation/validate", json=payload)

        # Should return 403 Forbidden
        assert response.status_code == 403
        data = response.json()

        assert "error" in data["detail"]
        assert data["detail"]["action"] == "delete_all"

    def test_validate_batch(self):
        """Test POST /api/foundation/validate-batch"""
        payload = [
            {"action": "robot.move", "params": {}},
            {"action": "robot.stop", "params": {}},
            {"action": "delete_all", "params": {}},
        ]

        response = client.post("/api/foundation/validate-batch", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert "robot.move" in data
        assert data["robot.move"]["valid"] is True

        assert "delete_all" in data
        assert data["delete_all"]["valid"] is False

    def test_execute_behavior_tree_api(self):
        """Test POST /api/foundation/behavior-tree/execute"""
        tree = {
            "node_id": "test_tree",
            "node_type": "sequence",
            "children": [
                {
                    "node_id": "action1",
                    "node_type": "action",
                    "action": "robot.move",
                    "params": {"distance": 5},
                }
            ],
        }

        response = client.post("/api/foundation/behavior-tree/execute", json=tree)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["node_id"] == "test_tree"
        assert "executed_nodes" in data

    def test_validate_behavior_tree_api(self):
        """Test POST /api/foundation/behavior-tree/validate"""
        tree = {
            "node_id": "test_tree",
            "node_type": "sequence",
            "children": [
                {
                    "node_id": "safe_action",
                    "node_type": "action",
                    "action": "robot.move",
                    "params": {},
                },
                {
                    "node_id": "dangerous_action",
                    "node_type": "action",
                    "action": "delete_all",
                    "params": {},
                },
            ],
        }

        response = client.post("/api/foundation/behavior-tree/validate", json=tree)

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is False  # Contains dangerous action
        assert data["total_actions"] == 2
        assert len(data["issues"]) > 0

    def test_health_endpoint(self):
        """Test GET /api/foundation/health"""
        response = client.get("/api/foundation/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] in ["healthy", "degraded"]
        assert data["module"] == "foundation"
        assert "uptime_seconds" in data


# ============================================================================
# Edge Cases
# ============================================================================


class TestFoundationEdgeCases:
    """Edge case tests"""

    def test_empty_action_name(self):
        """Test validation with empty action name"""
        payload = {"action": "", "params": {}}

        response = client.post("/api/foundation/validate", json=payload)

        # Should still return a response (not crash)
        assert response.status_code in [200, 403]

    def test_nested_behavior_tree(self):
        """Test deeply nested behavior tree"""
        tree = {
            "node_id": "root",
            "node_type": "sequence",
            "children": [
                {
                    "node_id": "level1",
                    "node_type": "selector",
                    "children": [
                        {
                            "node_id": "level2",
                            "node_type": "action",
                            "action": "test",
                            "params": {},
                        }
                    ],
                }
            ],
        }

        response = client.post("/api/foundation/behavior-tree/execute", json=tree)

        assert response.status_code == 200
        data = response.json()
        assert len(data["executed_nodes"]) == 3  # All levels


# ============================================================================
# New Endpoints Tests (C.4)
# ============================================================================


class TestFoundationNewEndpoints:
    """Tests for new Foundation endpoints (/info, /authorize, /audit-log)"""

    def test_get_foundation_info(self):
        """Test GET /api/foundation/info endpoint"""
        response = client.get("/api/foundation/info")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "BRAiN Foundation Layer"
        assert data["version"] == "1.0.0"
        assert "capabilities" in data
        assert len(data["capabilities"]) >= 6
        assert "authorization" in data["capabilities"]
        assert "audit_logging" in data["capabilities"]
        assert data["status"] == "operational"
        assert "uptime" in data
        assert data["uptime"] >= 0

    def test_authorize_action_allowed(self):
        """Test POST /api/foundation/authorize - allowed action"""
        response = client.post(
            "/api/foundation/authorize",
            json={
                "agent_id": "test_agent",
                "action": "read_file",
                "resource": "/data/test.txt",
                "context": {"environment": "test"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["authorized"] is True
        assert "reason" in data
        assert "audit_id" in data
        assert data["audit_id"].startswith("audit_")

    def test_authorize_action_blocked(self):
        """Test POST /api/foundation/authorize - blocked action"""
        response = client.post(
            "/api/foundation/authorize",
            json={
                "agent_id": "test_agent",
                "action": "delete_all",
                "resource": "/data",
                "context": {},
            },
        )

        # Should return 403 Forbidden for blocked actions
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "error" in data["detail"]
        assert data["detail"]["action"] == "delete_all"
        assert "blocked" in data["detail"]["reason"].lower()

    def test_audit_log_query(self):
        """Test GET /api/foundation/audit-log endpoint"""
        # First, create some audit entries via validation
        client.post(
            "/api/foundation/validate",
            json={
                "action": "test_action_1",
                "params": {},
                "context": {"agent_id": "test_agent"},
            },
        )

        client.post(
            "/api/foundation/validate",
            json={
                "action": "test_action_2",
                "params": {},
                "context": {"agent_id": "test_agent"},
            },
        )

        # Query audit log without filters
        response = client.get("/api/foundation/audit-log?limit=100")

        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["total"] >= 2

        # Verify entry structure
        if len(data["entries"]) > 0:
            entry = data["entries"][0]
            assert "audit_id" in entry
            assert "timestamp" in entry
            assert "event_type" in entry
            assert "action" in entry
            assert "outcome" in entry
            assert "reason" in entry

        # Query with filters
        filtered_response = client.get(
            "/api/foundation/audit-log?agent_id=test_agent&limit=10"
        )

        assert filtered_response.status_code == 200
        filtered_data = filtered_response.json()
        assert filtered_data["total"] >= 2


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
