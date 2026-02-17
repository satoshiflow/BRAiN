"""
Tests for Policy Engine Module

Tests policy evaluation, rule matching, and CRUD operations.
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
from app.modules.policy.service import PolicyEngine
from app.modules.policy.schemas import (
    PolicyEvaluationContext,
    PolicyCreateRequest,
    PolicyRule,
    PolicyCondition,
    PolicyConditionOperator,
    PolicyEffect,
)


client = TestClient(app)


# ============================================================================
# Service Tests (Unit)
# ============================================================================


class TestPolicyEngine:
    """Unit tests for PolicyEngine"""

    @pytest.mark.asyncio
    async def test_engine_initialization(self):
        """Test Policy Engine initializes with default policies"""
        engine = PolicyEngine()

        assert len(engine.policies) == 2  # admin + guest
        assert "admin_full_access" in engine.policies
        assert "guest_read_only" in engine.policies

    @pytest.mark.asyncio
    async def test_admin_allow_all(self):
        """Test admin role can do anything"""
        engine = PolicyEngine()

        context = PolicyEvaluationContext(
            agent_id="admin_001",
            agent_role="admin",
            action="delete_everything",  # Even dangerous action
        )

        result = await engine.evaluate(context)

        assert result.allowed is True
        assert result.effect == PolicyEffect.ALLOW
        assert result.matched_rule == "admin_allow_all"

    @pytest.mark.asyncio
    async def test_guest_read_allowed(self):
        """Test guest can read data"""
        engine = PolicyEngine()

        context = PolicyEvaluationContext(
            agent_id="guest_001", agent_role="guest", action="data.read"
        )

        result = await engine.evaluate(context)

        assert result.allowed is True
        assert result.effect == PolicyEffect.ALLOW
        assert "guest_read_allow" in result.matched_rule

    @pytest.mark.asyncio
    async def test_guest_write_denied(self):
        """Test guest cannot write data"""
        engine = PolicyEngine()

        context = PolicyEvaluationContext(
            agent_id="guest_001", agent_role="guest", action="data.write"
        )

        result = await engine.evaluate(context)

        assert result.allowed is False
        assert result.effect == PolicyEffect.DENY
        assert "guest_write_deny" in result.matched_rule

    @pytest.mark.asyncio
    async def test_custom_policy(self):
        """Test creating and evaluating custom policy"""
        engine = PolicyEngine()

        # Create policy for robots with low battery
        request = PolicyCreateRequest(
            name="Low Battery Policy",
            rules=[
                PolicyRule(
                    rule_id="low_battery_deny",
                    name="Deny Movement on Low Battery",
                    effect=PolicyEffect.DENY,
                    conditions=[
                        PolicyCondition(
                            field="environment.battery_level",
                            operator=PolicyConditionOperator.LESS_THAN,
                            value=20,
                        )
                    ],
                    priority=100,
                )
            ],
        )

        policy = await engine.create_policy(request)
        assert policy.policy_id is not None

        # Test: battery < 20 should deny
        context = PolicyEvaluationContext(
            agent_id="robot_001",
            action="robot.move",
            environment={"battery_level": 15},
        )

        result = await engine.evaluate(context)
        assert result.allowed is False

        # Test: battery >= 20 should use default
        context2 = PolicyEvaluationContext(
            agent_id="robot_001",
            action="robot.move",
            environment={"battery_level": 80},
        )

        result2 = await engine.evaluate(context2)
        # Will be denied by default policy (no matching rule)

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Test rules are evaluated by priority (highest first)"""
        engine = PolicyEngine()

        # Add policy with multiple rules
        request = PolicyCreateRequest(
            name="Priority Test Policy",
            rules=[
                PolicyRule(
                    rule_id="low_priority_allow",
                    name="Low Priority Allow",
                    effect=PolicyEffect.ALLOW,
                    conditions=[
                        PolicyCondition(
                            field="action",
                            operator=PolicyConditionOperator.CONTAINS,
                            value="test",
                        )
                    ],
                    priority=10,  # Lower priority
                ),
                PolicyRule(
                    rule_id="high_priority_deny",
                    name="High Priority Deny",
                    effect=PolicyEffect.DENY,
                    conditions=[
                        PolicyCondition(
                            field="action",
                            operator=PolicyConditionOperator.CONTAINS,
                            value="test",
                        )
                    ],
                    priority=100,  # Higher priority (should match first)
                ),
            ],
        )

        await engine.create_policy(request)

        context = PolicyEvaluationContext(agent_id="test", action="test_action")

        result = await engine.evaluate(context)

        # High priority rule should match first (deny)
        assert result.allowed is False
        assert result.matched_rule == "high_priority_deny"

    @pytest.mark.asyncio
    async def test_condition_operators(self):
        """Test all condition operators"""
        engine = PolicyEngine()

        # Test EQUALS
        policy = await engine.create_policy(
            PolicyCreateRequest(
                name="Operator Test",
                rules=[
                    PolicyRule(
                        rule_id="equals_test",
                        name="Equals Test",
                        effect=PolicyEffect.ALLOW,
                        conditions=[
                            PolicyCondition(
                                field="agent_role",
                                operator=PolicyConditionOperator.EQUALS,
                                value="tester",
                            )
                        ],
                        priority=200,
                    )
                ],
            )
        )

        context = PolicyEvaluationContext(
            agent_id="test", agent_role="tester", action="test"
        )
        result = await engine.evaluate(context)
        assert result.allowed is True

        # Test IN operator
        policy2 = await engine.create_policy(
            PolicyCreateRequest(
                name="IN Operator Test",
                rules=[
                    PolicyRule(
                        rule_id="in_test",
                        name="IN Test",
                        effect=PolicyEffect.DENY,
                        conditions=[
                            PolicyCondition(
                                field="action",
                                operator=PolicyConditionOperator.IN,
                                value=["delete", "destroy", "remove"],
                            )
                        ],
                        priority=300,
                    )
                ],
            )
        )

        context2 = PolicyEvaluationContext(agent_id="test", action="delete")
        result2 = await engine.evaluate(context2)
        assert result2.allowed is False

    @pytest.mark.asyncio
    async def test_policy_crud(self):
        """Test policy CRUD operations"""
        engine = PolicyEngine()

        initial_count = len(engine.policies)

        # Create
        policy = await engine.create_policy(
            PolicyCreateRequest(name="Test Policy", rules=[])
        )
        assert len(engine.policies) == initial_count + 1

        # Read
        retrieved = await engine.get_policy(policy.policy_id)
        assert retrieved is not None
        assert retrieved.name == "Test Policy"

        # Update
        from app.modules.policy.schemas import PolicyUpdateRequest

        updated = await engine.update_policy(
            policy.policy_id, PolicyUpdateRequest(name="Updated Policy")
        )
        assert updated.name == "Updated Policy"

        # Delete
        deleted = await engine.delete_policy(policy.policy_id)
        assert deleted is True
        assert len(engine.policies) == initial_count

    @pytest.mark.asyncio
    async def test_stats(self):
        """Test policy statistics"""
        engine = PolicyEngine()

        # Trigger some evaluations
        await engine.evaluate(
            PolicyEvaluationContext(
                agent_id="admin", agent_role="admin", action="test"
            )
        )
        await engine.evaluate(
            PolicyEvaluationContext(
                agent_id="guest", agent_role="guest", action="write"
            )
        )

        stats = await engine.get_stats()

        assert stats.total_evaluations >= 2
        assert stats.total_policies >= 2
        assert stats.total_allows >= 1
        assert stats.total_denies >= 1


# ============================================================================
# API Tests (Integration)
# ============================================================================


class TestPolicyAPI:
    """Integration tests for Policy API endpoints"""

    def test_get_stats(self):
        """Test GET /api/policy/stats"""
        response = client.get("/api/policy/stats")

        assert response.status_code == 200
        data = response.json()

        assert "total_policies" in data
        assert "total_evaluations" in data

    def test_list_policies(self):
        """Test GET /api/policy/policies"""
        response = client.get("/api/policy/policies")

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "policies" in data
        assert data["total"] >= 2  # At least admin + guest

    def test_create_policy_api(self):
        """Test POST /api/policy/policies"""
        payload = {
            "name": "API Test Policy",
            "version": "1.0.0",
            "description": "Test policy via API",
            "rules": [],
            "default_effect": "deny",
        }

        response = client.post("/api/policy/policies", json=payload)

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "API Test Policy"
        assert "policy_id" in data

    def test_evaluate_policy_allow(self):
        """Test POST /api/policy/evaluate (allow)"""
        payload = {
            "agent_id": "admin_001",
            "agent_role": "admin",
            "action": "test_action",
        }

        response = client.post("/api/policy/evaluate", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["allowed"] is True
        assert data["effect"] == "allow"

    def test_evaluate_policy_deny(self):
        """Test POST /api/policy/evaluate (deny)"""
        payload = {
            "agent_id": "guest_001",
            "agent_role": "guest",
            "action": "data.delete",
        }

        response = client.post("/api/policy/evaluate", json=payload)

        # Should return 403 on deny
        assert response.status_code == 403
        data = response.json()["detail"]

        assert "denied" in data["error"].lower()

    def test_test_rule_endpoint(self):
        """Test POST /api/policy/test-rule (doesn't raise 403)"""
        payload = {
            "agent_id": "guest_001",
            "agent_role": "guest",
            "action": "data.delete",
        }

        response = client.post("/api/policy/test-rule", json=payload)

        # test-rule returns 200 even on deny
        assert response.status_code == 200
        data = response.json()

        assert data["allowed"] is False

    def test_get_policy_by_id(self):
        """Test GET /api/policy/policies/{policy_id}"""
        response = client.get("/api/policy/policies/admin_full_access")

        assert response.status_code == 200
        data = response.json()

        assert data["policy_id"] == "admin_full_access"
        assert data["name"] == "Admin Full Access"

    def test_get_nonexistent_policy(self):
        """Test GET /api/policy/policies/{policy_id} (not found)"""
        response = client.get("/api/policy/policies/nonexistent")

        assert response.status_code == 404

    def test_default_policies_endpoint(self):
        """Test GET /api/policy/default-policies"""
        response = client.get("/api/policy/default-policies")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert "admin_full_access" in data
        assert "guest_read_only" in data


# ============================================================================
# Edge Cases
# ============================================================================


class TestPolicyEdgeCases:
    """Edge case tests"""

    @pytest.mark.asyncio
    async def test_no_policies(self):
        """Test evaluation with no policies"""
        engine = PolicyEngine()

        # Clear all policies
        engine.policies = {}

        context = PolicyEvaluationContext(agent_id="test", action="test")
        result = await engine.evaluate(context)

        # Should default to deny
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_empty_conditions(self):
        """Test rule with no conditions (always matches)"""
        engine = PolicyEngine()

        policy = await engine.create_policy(
            PolicyCreateRequest(
                name="Always Allow",
                rules=[
                    PolicyRule(
                        rule_id="always_allow",
                        name="Always Allow",
                        effect=PolicyEffect.ALLOW,
                        conditions=[],  # No conditions
                        priority=500,
                    )
                ],
            )
        )

        context = PolicyEvaluationContext(agent_id="anyone", action="anything")
        result = await engine.evaluate(context)

        assert result.allowed is True
        assert result.matched_rule == "always_allow"


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
