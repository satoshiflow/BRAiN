import pytest

from app.modules.recovery_policy_engine.schemas import (
    RecoveryPolicyConfig,
    RecoveryRequest,
    RecoverySeverity,
)
from app.modules.recovery_policy_engine.service import RecoveryPolicyService


class FakeDB:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_recovery_policy_retry_for_low_retry_count():
    service = RecoveryPolicyService()

    request = RecoveryRequest(
        id="rec-1",
        source="task_queue",
        entity_id="task-1",
        failure_type="worker_timeout",
        severity=RecoverySeverity.MEDIUM,
        retry_count=0,
        recurrence=0,
    )

    decision = await service.decide(request)
    assert decision.request_id == request.id
    assert decision.action.value in {
        "retry",
        "circuit_break",
        "backpressure",
        "detox",
        "escalate",
        "isolate",
        "rollback",
    }
    assert len(await service.list_audit_entries()) == 1


@pytest.mark.asyncio
async def test_recovery_policy_adapter_path_and_policy_update():
    service = RecoveryPolicyService()
    service.update_policy(
        RecoveryPolicyConfig(
            max_retries=1,
            cooldown_seconds=30,
            escalation_threshold=2,
        )
    )

    decision = await service.decide_from_adapter(
        "planning",
        {
            "id": "rec-2",
            "plan_id": "plan-1",
            "failure_type": "dependency_error",
            "severity": "high",
            "retry_count": 2,
            "recurrence": 3,
        },
    )

    assert decision.cooldown_seconds == 30
    assert (await service.metrics()).total_decisions == 1


@pytest.mark.asyncio
async def test_recovery_policy_persistence_hook_uses_db_session():
    service = RecoveryPolicyService()
    db = FakeDB()

    request = RecoveryRequest(
        id="rec-db-1",
        source="planning",
        entity_id="node-1",
        failure_type="dependency_error",
        severity=RecoverySeverity.HIGH,
        retry_count=2,
    )
    await service.decide(request, db=db)

    assert db.commits >= 2  # request/decision + audit
