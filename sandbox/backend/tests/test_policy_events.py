"""
Test Suite for Policy Module EventStream Integration

Sprint 3: Policy EventStream Migration
Tests all 7 event types for Charter v1.0 compliance.
"""

import sys
import os
import pytest
import time
from typing import List, Dict, Any

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.modules.policy.service import PolicyEngine
from app.modules.policy.schemas import (
    PolicyEvaluationContext,
    PolicyCreateRequest,
    PolicyUpdateRequest,
    PolicyRule,
    PolicyEffect,
    PolicyCondition,
    PolicyConditionOperator,
)


# ============================================================================
# Mock EventStream
# ============================================================================

class MockEvent:
    """Mock Event for testing"""
    def __init__(self, type: str, source: str, target: str, payload: Dict[str, Any]):
        self.id = f"evt_test_{time.time()}"
        self.type = type
        self.source = source
        self.target = target
        self.timestamp = time.time()
        self.payload = payload
        self.meta = {"correlation_id": None, "version": "1.0"}


class MockEventStream:
    """Mock EventStream that captures published events"""
    def __init__(self):
        self.events: List[MockEvent] = []

    async def publish(self, event: MockEvent):
        """Capture event for later verification"""
        self.events.append(event)

    def get_events_by_type(self, event_type: str) -> List[MockEvent]:
        """Get all events of a specific type"""
        return [e for e in self.events if e.type == event_type]

    def clear(self):
        """Clear all captured events"""
        self.events.clear()


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_event_stream():
    """Mock EventStream for testing"""
    # Patch the Event class in service module
    import backend.app.modules.policy.service as service_module
    original_event = service_module.Event
    service_module.Event = MockEvent

    stream = MockEventStream()
    yield stream

    # Restore original Event class
    service_module.Event = original_event


@pytest.fixture
def policy_engine(mock_event_stream):
    """PolicyEngine with mocked EventStream"""
    engine = PolicyEngine(event_stream=mock_event_stream)
    return engine


@pytest.fixture
def sample_context():
    """Sample policy evaluation context"""
    return PolicyEvaluationContext(
        agent_id="test_agent",
        agent_role="admin",
        action="read_data",
        resource="database",
    )


@pytest.fixture
def guest_context():
    """Sample guest context (will be denied write)"""
    return PolicyEvaluationContext(
        agent_id="guest_user",
        agent_role="guest",
        action="delete",  # Changed from "delete_data" to match default policy rule
        resource="database",
    )


# ============================================================================
# Test 1: policy.evaluated Event (ALLOW result)
# ============================================================================

@pytest.mark.asyncio
async def test_policy_evaluated_event_on_allow(policy_engine, mock_event_stream, sample_context):
    """Test that policy.evaluated event is published when action is allowed"""
    # Execute
    result = await policy_engine.evaluate(sample_context)

    # Verify evaluation result
    assert result.allowed is True
    assert result.effect == PolicyEffect.ALLOW
    assert result.matched_policy == "admin_full_access"

    # Verify event was published
    events = mock_event_stream.get_events_by_type("policy.evaluated")
    assert len(events) == 1

    event = events[0]
    assert event.type == "policy.evaluated"
    assert event.source == "policy_engine"
    assert event.payload["agent_id"] == "test_agent"
    assert event.payload["action"] == "read_data"
    assert event.payload["result"]["allowed"] is True
    assert event.payload["result"]["effect"] == "allow"
    assert "evaluation_time_ms" in event.payload
    assert event.payload["evaluation_time_ms"] >= 0


# ============================================================================
# Test 2: policy.evaluated Event (DENY result)
# ============================================================================

@pytest.mark.asyncio
async def test_policy_evaluated_event_on_deny(policy_engine, mock_event_stream, guest_context):
    """Test that policy.evaluated event is published when action is denied"""
    # Execute
    result = await policy_engine.evaluate(guest_context)

    # Verify evaluation result
    assert result.allowed is False
    assert result.effect == PolicyEffect.DENY

    # Verify event was published
    events = mock_event_stream.get_events_by_type("policy.evaluated")
    assert len(events) == 1

    event = events[0]
    assert event.type == "policy.evaluated"
    assert event.source == "policy_engine"
    assert event.payload["agent_id"] == "guest_user"
    assert event.payload["action"] == "delete"  # Fixed: was "delete_data"
    assert event.payload["result"]["allowed"] is False
    assert event.payload["result"]["effect"] == "deny"


# ============================================================================
# Test 3: policy.denied Event
# ============================================================================

@pytest.mark.asyncio
async def test_policy_denied_event_published(policy_engine, mock_event_stream, guest_context):
    """Test that policy.denied event is published when action is denied"""
    # Execute
    result = await policy_engine.evaluate(guest_context)

    # Verify result is denied
    assert result.allowed is False

    # Verify policy.denied event was published
    denied_events = mock_event_stream.get_events_by_type("policy.denied")
    assert len(denied_events) == 1

    event = denied_events[0]
    assert event.type == "policy.denied"
    assert event.source == "policy_engine"
    assert event.payload["agent_id"] == "guest_user"
    assert event.payload["action"] == "delete"  # Fixed: was "delete_data"
    assert event.payload["matched_policy"] == "guest_read_only"
    assert event.payload["matched_rule"] == "guest_write_deny"
    assert "denied_at" in event.payload


# ============================================================================
# Test 4: policy.warning_triggered Event
# ============================================================================

@pytest.mark.asyncio
async def test_policy_warning_triggered_event(policy_engine, mock_event_stream):
    """Test that policy.warning_triggered event is published for WARN effect"""
    # Create a policy with WARN effect
    warn_rule = PolicyRule(
        rule_id="test_warn",
        name="Test Warning Rule",
        effect=PolicyEffect.WARN,
        conditions=[
            PolicyCondition(
                field="action",
                operator=PolicyConditionOperator.CONTAINS,
                value="deploy"
            )
        ],
        priority=2000,  # Higher than admin_full_access (1000)
        enabled=True,
    )

    warn_policy = await policy_engine.create_policy(
        PolicyCreateRequest(
            name="Warning Test Policy",
            rules=[warn_rule],
            enabled=True,
        )
    )

    # Clear events from policy creation
    mock_event_stream.clear()

    # Execute action that triggers warning
    context = PolicyEvaluationContext(
        agent_id="ops_agent",
        agent_role="operator",
        action="deploy_application",
        resource="production",
    )

    result = await policy_engine.evaluate(context)

    # Verify result
    assert result.allowed is True  # WARN allows action
    assert result.effect == PolicyEffect.WARN
    assert len(result.warnings) > 0

    # Verify policy.warning_triggered event
    warning_events = mock_event_stream.get_events_by_type("policy.warning_triggered")
    assert len(warning_events) == 1

    event = warning_events[0]
    assert event.type == "policy.warning_triggered"
    assert event.source == "policy_engine"
    assert event.payload["agent_id"] == "ops_agent"
    assert event.payload["action"] == "deploy_application"
    assert event.payload["rule_id"] == "test_warn"  # Fixed: field name is rule_id not matched_rule for specific events
    assert "warnings" in event.payload
    assert len(event.payload["warnings"]) > 0


# ============================================================================
# Test 5: policy.audit_required Event
# ============================================================================

@pytest.mark.asyncio
async def test_policy_audit_required_event(policy_engine, mock_event_stream):
    """Test that policy.audit_required event is published for AUDIT effect"""
    # Create a policy with AUDIT effect
    audit_rule = PolicyRule(
        rule_id="test_audit",
        name="Test Audit Rule",
        effect=PolicyEffect.AUDIT,
        conditions=[
            PolicyCondition(
                field="action",
                operator=PolicyConditionOperator.CONTAINS,
                value="delete"
            ),
            PolicyCondition(
                field="agent_role",
                operator=PolicyConditionOperator.EQUALS,
                value="admin"
            )
        ],
        priority=2000,  # Higher than admin_full_access (1000)
        enabled=True,
    )

    audit_policy = await policy_engine.create_policy(
        PolicyCreateRequest(
            name="Audit Test Policy",
            rules=[audit_rule],
            enabled=True,
        )
    )

    # Clear events from policy creation
    mock_event_stream.clear()

    # Execute action that triggers audit
    context = PolicyEvaluationContext(
        agent_id="admin_user",
        agent_role="admin",
        action="delete_database",
        resource="customer_db",
    )

    result = await policy_engine.evaluate(context)

    # Verify result
    assert result.allowed is True  # AUDIT allows action
    assert result.effect == PolicyEffect.AUDIT
    assert result.requires_audit is True

    # Verify policy.audit_required event
    audit_events = mock_event_stream.get_events_by_type("policy.audit_required")
    assert len(audit_events) == 1

    event = audit_events[0]
    assert event.type == "policy.audit_required"
    assert event.source == "policy_engine"
    assert event.payload["agent_id"] == "admin_user"
    assert event.payload["action"] == "delete_database"
    assert event.payload["rule_id"] == "test_audit"  # Fixed: field name is rule_id not matched_rule
    # Fixed: requires_audit is top-level in payload (not nested under result)
    assert event.payload["requires_audit"] is True


# ============================================================================
# Test 6: policy.created Event
# ============================================================================

@pytest.mark.asyncio
async def test_policy_created_event(policy_engine, mock_event_stream):
    """Test that policy.created event is published when policy is created"""
    # Clear any existing events
    mock_event_stream.clear()

    # Create policy
    policy = await policy_engine.create_policy(
        PolicyCreateRequest(
            name="Test Policy",
            version="1.0.0",
            description="Test policy creation",
            rules=[],
            enabled=True,
        )
    )

    # Verify policy.created event
    created_events = mock_event_stream.get_events_by_type("policy.created")
    assert len(created_events) == 1

    event = created_events[0]
    assert event.type == "policy.created"
    assert event.source == "policy_engine"
    assert event.payload["policy_id"] == policy.policy_id
    assert event.payload["policy_name"] == "Test Policy"
    assert "created_at" in event.payload


# ============================================================================
# Test 7: policy.updated Event
# ============================================================================

@pytest.mark.asyncio
async def test_policy_updated_event(policy_engine, mock_event_stream):
    """Test that policy.updated event is published when policy is modified"""
    # Create policy first
    policy = await policy_engine.create_policy(
        PolicyCreateRequest(
            name="Original Name",
            version="1.0.0",
            enabled=True,
        )
    )

    # Clear events from creation
    mock_event_stream.clear()

    # Update policy
    updated_policy = await policy_engine.update_policy(
        policy.policy_id,
        PolicyUpdateRequest(
            name="Updated Name",
            enabled=False,
        )
    )

    # Verify policy was updated
    assert updated_policy.name == "Updated Name"
    assert updated_policy.enabled is False

    # Verify policy.updated event
    updated_events = mock_event_stream.get_events_by_type("policy.updated")
    assert len(updated_events) == 1

    event = updated_events[0]
    assert event.type == "policy.updated"
    assert event.source == "policy_engine"
    assert event.payload["policy_id"] == policy.policy_id
    assert "changes" in event.payload
    assert "name" in event.payload["changes"]
    assert event.payload["changes"]["name"]["old"] == "Original Name"
    assert event.payload["changes"]["name"]["new"] == "Updated Name"
    assert "enabled" in event.payload["changes"]
    assert event.payload["changes"]["enabled"]["old"] is True
    assert event.payload["changes"]["enabled"]["new"] is False


# ============================================================================
# Test 8: policy.deleted Event
# ============================================================================

@pytest.mark.asyncio
async def test_policy_deleted_event(policy_engine, mock_event_stream):
    """Test that policy.deleted event is published when policy is removed"""
    # Create policy first
    policy = await policy_engine.create_policy(
        PolicyCreateRequest(
            name="Policy To Delete",
            version="1.0.0",
            enabled=True,
        )
    )

    # Clear events from creation
    mock_event_stream.clear()

    # Delete policy
    deleted = await policy_engine.delete_policy(policy.policy_id)
    assert deleted is True

    # Verify policy.deleted event
    deleted_events = mock_event_stream.get_events_by_type("policy.deleted")
    assert len(deleted_events) == 1

    event = deleted_events[0]
    assert event.type == "policy.deleted"
    assert event.source == "policy_engine"
    assert event.payload["policy_id"] == policy.policy_id
    assert event.payload["policy_name"] == "Policy To Delete"
    assert "deleted_at" in event.payload


# ============================================================================
# Test 9: Event Lifecycle - Full DENY Flow
# ============================================================================

@pytest.mark.asyncio
async def test_event_lifecycle_deny(policy_engine, mock_event_stream, guest_context):
    """Test full event lifecycle for denied action: evaluated → denied"""
    # Clear events
    mock_event_stream.clear()

    # Execute denied action
    result = await policy_engine.evaluate(guest_context)
    assert result.allowed is False

    # Verify event sequence
    all_events = mock_event_stream.events
    assert len(all_events) == 2  # policy.evaluated + policy.denied

    # Event 1: policy.evaluated
    assert all_events[0].type == "policy.evaluated"
    assert all_events[0].payload["result"]["allowed"] is False

    # Event 2: policy.denied
    assert all_events[1].type == "policy.denied"
    assert all_events[1].payload["agent_id"] == "guest_user"


# ============================================================================
# Test 10: Graceful Degradation (No EventStream)
# ============================================================================

@pytest.mark.asyncio
async def test_policy_engine_works_without_eventstream(sample_context):
    """Test that PolicyEngine works correctly without EventStream (graceful degradation)"""
    # Create engine WITHOUT EventStream
    engine = PolicyEngine(event_stream=None)

    # Execute evaluation - should work normally
    result = await engine.evaluate(sample_context)

    # Verify evaluation still works
    assert result.allowed is True
    assert result.effect == PolicyEffect.ALLOW
    assert result.matched_policy == "admin_full_access"

    # CRUD operations should also work
    policy = await engine.create_policy(
        PolicyCreateRequest(
            name="Test Policy",
            enabled=True,
        )
    )
    assert policy is not None

    updated = await engine.update_policy(
        policy.policy_id,
        PolicyUpdateRequest(name="Updated")
    )
    assert updated is not None

    deleted = await engine.delete_policy(policy.policy_id)
    assert deleted is True


# ============================================================================
# Test 11: Charter v1.0 Compliance - Event Envelope Structure
# ============================================================================

@pytest.mark.asyncio
async def test_event_envelope_charter_compliance(policy_engine, mock_event_stream, sample_context):
    """Test that events follow Charter v1.0 envelope specification"""
    # Execute action
    await policy_engine.evaluate(sample_context)

    # Get any event
    events = mock_event_stream.events
    assert len(events) > 0

    event = events[0]

    # Verify Charter v1.0 envelope structure
    assert hasattr(event, 'id'), "Event must have id"
    assert hasattr(event, 'type'), "Event must have type"
    assert hasattr(event, 'source'), "Event must have source"
    assert hasattr(event, 'target'), "Event must have target"
    assert hasattr(event, 'timestamp'), "Event must have timestamp"
    assert hasattr(event, 'payload'), "Event must have payload"
    assert hasattr(event, 'meta'), "Event must have meta"

    # Verify source
    assert event.source == "policy_engine"

    # Verify meta structure
    assert "correlation_id" in event.meta
    assert "version" in event.meta
    assert event.meta["version"] == "1.0"

    # Verify payload contains expected fields
    assert isinstance(event.payload, dict)
    assert "agent_id" in event.payload
    assert "action" in event.payload
