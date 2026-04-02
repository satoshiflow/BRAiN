from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from jose import jwt

from app.core.auth_deps import Principal, PrincipalType
from app.modules.external_apps.schemas import (
    PaperclipActionRequest,
    PaperclipActionRequestDecision,
    PaperclipExecutionContextResponse,
    PaperclipHandoffExchangeRequest,
    PaperclipHandoffRequest,
)
from app.modules.external_apps.service import OPENCLAW_CONFIG, PaperclipHandoffService


class _FakeDb:
    def __init__(self, events=None) -> None:
        self.commits = 0
        self.events = list(events or [])

    async def commit(self) -> None:
        self.commits += 1

    async def execute(self, _query):  # noqa: ANN001
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: self.events))


def _principal() -> Principal:
    return Principal(
        principal_id="operator-1",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator",
        roles=["operator"],
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


@pytest.mark.asyncio
async def test_create_handoff_embeds_expected_claims(monkeypatch) -> None:
    service = PaperclipHandoffService()
    fake_db = _FakeDb()

    class _FakeRuntimeService:
        async def resolve_with_persisted_overrides(self, context, db):  # noqa: ANN001
            _ = (context, db)
            return SimpleNamespace(decision_id="rdec_123", effective_config={})

        @staticmethod
        def is_executor_allowed(effective_config, executor_name):  # noqa: ANN001
            _ = effective_config
            return executor_name == "paperclip"

        @staticmethod
        def is_connector_allowed(effective_config, connector_name):  # noqa: ANN001
            _ = effective_config
            return connector_name == "paperclip"

    async def _record_event_stub(**kwargs):  # noqa: ANN001
        return None

    monkeypatch.setenv("BRAIN_EXTERNAL_APP_HANDOFF_SECRET", "handoff-secret")
    monkeypatch.setenv("PAPERCLIP_APP_BASE_URL", "https://paperclip.example")
    monkeypatch.setenv("PAPERCLIP_HANDOFF_PATH", "/handoff/paperclip")
    monkeypatch.setattr("app.modules.external_apps.service.get_runtime_control_service", lambda: _FakeRuntimeService())
    monkeypatch.setattr("app.modules.external_apps.service.record_control_plane_event", _record_event_stub)

    response = await service.create_handoff(
        fake_db,
        principal=_principal(),
        payload=PaperclipHandoffRequest(
            target_type="issue",
            target_ref="issue-123",
            skill_run_id="run-123",
            mission_id="mission-1",
            permissions=["view", "request_approval"],
        ),
        backend_base_url="http://127.0.0.1:8000",
    )

    assert response.target_type == "issue"
    assert response.target_ref == "issue-123"
    assert response.jti.startswith("handoff_")
    assert fake_db.commits == 1

    parsed = urlparse(response.handoff_url)
    params = parse_qs(parsed.query)
    token = params["token"][0]
    assert params["exchange_url"][0] == "http://127.0.0.1:8000/api/external-apps/paperclip/handoff/exchange"
    claims = jwt.decode(token, "handoff-secret", algorithms=["HS256"], audience="paperclip-ui")
    assert claims["sub"] == "operator-1"
    assert claims["tenant_id"] == "tenant-a"
    assert claims["skill_run_id"] == "run-123"
    assert claims["mission_id"] == "mission-1"
    assert claims["decision_id"] == "rdec_123"
    assert claims["target_type"] == "issue"
    assert claims["target_ref"] == "issue-123"
    assert claims["permissions"] == ["view", "request_approval"]


@pytest.mark.asyncio
async def test_create_handoff_rejects_disabled_executor(monkeypatch) -> None:
    service = PaperclipHandoffService()

    class _FakeRuntimeService:
        async def resolve_with_persisted_overrides(self, context, db):  # noqa: ANN001
            _ = (context, db)
            return SimpleNamespace(decision_id="rdec_123", effective_config={})

        @staticmethod
        def is_executor_allowed(effective_config, executor_name):  # noqa: ANN001
            _ = (effective_config, executor_name)
            return False

        @staticmethod
        def is_connector_allowed(effective_config, connector_name):  # noqa: ANN001
            _ = (effective_config, connector_name)
            return True

    monkeypatch.setenv("BRAIN_EXTERNAL_APP_HANDOFF_SECRET", "handoff-secret")
    monkeypatch.setattr("app.modules.external_apps.service.get_runtime_control_service", lambda: _FakeRuntimeService())

    with pytest.raises(PermissionError, match="Paperclip executor is currently disabled"):
        await service.create_handoff(
            _FakeDb(),
            principal=_principal(),
            payload=PaperclipHandoffRequest(target_type="issue", target_ref="issue-123"),
            backend_base_url="http://127.0.0.1:8000",
        )


@pytest.mark.asyncio
async def test_openclaw_create_handoff_uses_openclaw_contract(monkeypatch) -> None:
    service = PaperclipHandoffService(OPENCLAW_CONFIG)

    class _FakeRuntimeService:
        async def resolve_with_persisted_overrides(self, context, db):  # noqa: ANN001
            _ = (context, db)
            return SimpleNamespace(decision_id="rdec_openclaw", effective_config={})

        @staticmethod
        def is_executor_allowed(effective_config, executor_name):  # noqa: ANN001
            _ = effective_config
            return executor_name == "openclaw"

        @staticmethod
        def is_connector_allowed(effective_config, connector_name):  # noqa: ANN001
            _ = effective_config
            return connector_name == "openclaw"

    async def _record_event_stub(**kwargs):  # noqa: ANN001
        _ = kwargs
        return None

    monkeypatch.setenv("BRAIN_EXTERNAL_APP_HANDOFF_SECRET", "handoff-secret")
    monkeypatch.setenv("OPENCLAW_APP_BASE_URL", "https://openclaw.example")
    monkeypatch.setattr("app.modules.external_apps.service.get_runtime_control_service", lambda: _FakeRuntimeService())
    monkeypatch.setattr("app.modules.external_apps.service.record_control_plane_event", _record_event_stub)

    response = await service.create_handoff(
        _FakeDb(),
        principal=_principal(),
        payload=PaperclipHandoffRequest(target_type="issue", target_ref="issue-321", permissions=["view", "request_escalation"]),
        backend_base_url="http://127.0.0.1:8000",
    )

    assert response.app_slug == "openclaw"
    assert "/handoff/openclaw" in response.handoff_url
    token = parse_qs(urlparse(response.handoff_url).query)["token"][0]
    claims = jwt.decode(token, "handoff-secret", algorithms=["HS256"], audience="openclaw-ui")
    assert claims["target_ref"] == "issue-321"


@pytest.mark.asyncio
async def test_request_action_allows_non_execution_escalation(monkeypatch) -> None:
    service = PaperclipHandoffService()
    fake_db = _FakeDb(events=[SimpleNamespace()])
    events = []

    async def _record_event_stub(**kwargs):  # noqa: ANN001
        events.append(kwargs)

    monkeypatch.setenv("BRAIN_EXTERNAL_APP_HANDOFF_SECRET", "handoff-secret")
    monkeypatch.setattr("app.modules.external_apps.service.record_control_plane_event", _record_event_stub)

    token = jwt.encode(
        {
            "iss": "brain-backend",
            "aud": "paperclip-ui",
            "sub": "operator-1",
            "tenant_id": "tenant-a",
            "mission_id": "mission-1",
            "decision_id": "rdec_123",
            "correlation_id": "corr-1",
            "target_type": "issue",
            "target_ref": "issue-123",
            "permissions": ["view", "request_escalation"],
            "iat": 1_700_000_000,
            "exp": 4_700_000_000,
            "jti": "handoff_123",
        },
        "handoff-secret",
        algorithm="HS256",
    )

    response = await service.request_action(
        fake_db,
        payload=PaperclipActionRequest(token=token, action="request_escalation", reason="Escalate issue context"),
    )

    assert response.target_type == "issue"
    assert response.app_slug == "paperclip"
    assert events[0]["payload"]["target_type"] == "issue"


@pytest.mark.asyncio
async def test_exchange_handoff_returns_validated_context(monkeypatch) -> None:
    service = PaperclipHandoffService()
    fake_db = _FakeDb()
    events = []

    async def _record_event_stub(**kwargs):  # noqa: ANN001
        events.append(kwargs)
        return None

    monkeypatch.setenv("BRAIN_EXTERNAL_APP_HANDOFF_SECRET", "handoff-secret")
    monkeypatch.setattr("app.modules.external_apps.service.record_control_plane_event", _record_event_stub)

    token = jwt.encode(
        {
            "iss": "brain-backend",
            "aud": "paperclip-ui",
            "sub": "operator-1",
            "tenant_id": "tenant-a",
            "skill_run_id": "run-123",
            "mission_id": "mission-1",
            "decision_id": "rdec_123",
            "correlation_id": "corr-1",
            "target_type": "execution",
            "target_ref": "task-123",
            "permissions": ["view", "request_approval"],
            "iat": 1_700_000_000,
            "exp": 4_700_000_000,
            "jti": "handoff_123",
        },
        "handoff-secret",
        algorithm="HS256",
    )

    response = await service.exchange_handoff(
        fake_db,
        payload=PaperclipHandoffExchangeRequest(token=token),
    )

    assert response.jti == "handoff_123"
    assert response.target_type == "execution"
    assert response.target_ref == "task-123"
    assert response.permissions == ["view", "request_approval"]
    assert response.suggested_path == "/app/executions/task-123"
    assert fake_db.commits == 1
    assert events[0]["event_type"] == "external.handoff.paperclip.opened.v1"


@pytest.mark.asyncio
async def test_exchange_handoff_rejects_replayed_token(monkeypatch) -> None:
    service = PaperclipHandoffService()
    fake_db = _FakeDb(events=[SimpleNamespace()])

    monkeypatch.setenv("BRAIN_EXTERNAL_APP_HANDOFF_SECRET", "handoff-secret")

    token = jwt.encode(
        {
            "iss": "brain-backend",
            "aud": "paperclip-ui",
            "sub": "operator-1",
            "tenant_id": "tenant-a",
            "skill_run_id": "run-123",
            "mission_id": "mission-1",
            "decision_id": "rdec_123",
            "correlation_id": "corr-1",
            "target_type": "execution",
            "target_ref": "task-123",
            "permissions": ["view", "request_approval"],
            "iat": 1_700_000_000,
            "exp": 4_700_000_000,
            "jti": "handoff_123",
        },
        "handoff-secret",
        algorithm="HS256",
    )

    with pytest.raises(PermissionError, match="already consumed"):
        await service.exchange_handoff(
            fake_db,
            payload=PaperclipHandoffExchangeRequest(token=token),
        )


@pytest.mark.asyncio
async def test_record_exchange_failure_emits_failure_event(monkeypatch) -> None:
    service = PaperclipHandoffService()
    fake_db = _FakeDb()
    events = []

    async def _record_event_stub(**kwargs):  # noqa: ANN001
        events.append(kwargs)
        return None

    monkeypatch.setattr("app.modules.external_apps.service.record_control_plane_event", _record_event_stub)

    token = jwt.encode(
        {
            "sub": "operator-1",
            "tenant_id": "tenant-a",
            "skill_run_id": "run-123",
            "mission_id": "mission-1",
            "decision_id": "rdec_123",
            "correlation_id": "corr-1",
            "target_type": "execution",
            "target_ref": "task-123",
            "jti": "handoff_123",
        },
        "irrelevant-secret",
        algorithm="HS256",
    )

    await service.record_exchange_failure(
        fake_db,
        payload=PaperclipHandoffExchangeRequest(token=token),
        reason="Handoff token already consumed",
    )

    assert fake_db.commits == 1
    assert events[0]["event_type"] == "external.handoff.paperclip.exchange_failed.v1"
    assert events[0]["payload"]["reason"] == "Handoff token already consumed"


@pytest.mark.asyncio
async def test_get_execution_context_returns_task_and_skill_run(monkeypatch) -> None:
    service = PaperclipHandoffService()
    task_id = "task-123"
    run_id = uuid4()
    now = datetime.now(timezone.utc)

    task = SimpleNamespace(
        id=uuid4(),
        task_id=task_id,
        name="Paperclip TaskLease",
        description="External execution",
        task_type="paperclip_work",
        category="skill_engine",
        tags=["tasklease", "paperclip"],
        status="completed",
        priority=75,
        payload={"prompt": "Review issue", "worker_type": "paperclip", "executor_type": "paperclip"},
        config={"required_worker": "paperclip"},
        tenant_id="tenant-a",
        mission_id="mission-1",
        skill_run_id=run_id,
        correlation_id="corr-1",
        scheduled_at=None,
        deadline_at=None,
        claimed_by="paperclip-worker",
        claimed_at=None,
        started_at=None,
        completed_at=None,
        max_retries=0,
        retry_count=0,
        result=None,
        error_message=None,
        execution_time_ms=None,
        wait_time_ms=None,
        created_by="operator-1",
        created_at=now,
        updated_at=now,
    )
    run = SimpleNamespace(
        id=run_id,
        tenant_id="tenant-a",
        skill_key="axe.worker.bridge",
        skill_version=1,
        state="succeeded",
        input_payload={},
        plan_snapshot={},
        provider_selection_snapshot={"runtime_decision": {"decision_id": "rdec_1"}},
        requested_by="operator-1",
        requested_by_type="human",
        trigger_type="api",
        policy_decision_id=None,
        policy_decision={},
        policy_snapshot={},
        risk_tier="normal",
        correlation_id="corr-1",
        causation_id=None,
        idempotency_key="idem-1",
        mission_id="mission-1",
        created_at=now,
        started_at=None,
        finished_at=None,
        deadline_at=None,
        retry_count=0,
        state_sequence=1,
        state_changed_at=None,
        cost_estimate=None,
        cost_actual=None,
        output_payload={},
        input_artifact_refs=[],
        output_artifact_refs=[],
        evidence_artifact_refs=[],
        evaluation_summary={},
        failure_code=None,
        failure_reason_sanitized=None,
    )

    class _TaskQueueStub:
        async def get_task(self, db, requested_task_id):  # noqa: ANN001
            _ = db
            return task if requested_task_id == task_id else None

    class _SkillEngineStub:
        async def get_run(self, db, requested_run_id, tenant_id):  # noqa: ANN001
            _ = (db, tenant_id)
            return run if requested_run_id == run_id else None

    monkeypatch.setattr("app.modules.external_apps.service.get_task_queue_service", lambda: _TaskQueueStub())
    monkeypatch.setattr("app.modules.external_apps.service.get_skill_engine_service", lambda: _SkillEngineStub())

    response = await service.get_execution_context(_FakeDb(), task_id=task_id, principal=_principal())

    assert isinstance(response, PaperclipExecutionContextResponse)
    assert response.target_ref == task_id
    assert response.task.task_id == task_id
    assert response.skill_run is not None
    assert str(response.skill_run.id) == str(run_id)


@pytest.mark.asyncio
async def test_get_execution_context_hides_other_tenant_tasks(monkeypatch) -> None:
    service = PaperclipHandoffService()
    task = SimpleNamespace(task_id="task-123", tenant_id="tenant-b", skill_run_id=None)

    class _TaskQueueStub:
        async def get_task(self, db, requested_task_id):  # noqa: ANN001
            _ = (db, requested_task_id)
            return task

    monkeypatch.setattr("app.modules.external_apps.service.get_task_queue_service", lambda: _TaskQueueStub())

    with pytest.raises(ValueError, match="not found"):
        await service.get_execution_context(_FakeDb(), task_id="task-123", principal=_principal())


@pytest.mark.asyncio
async def test_get_execution_context_exposes_available_actions(monkeypatch) -> None:
    service = PaperclipHandoffService()
    now = datetime.now(timezone.utc)
    task = SimpleNamespace(
        id=uuid4(),
        task_id="task-123",
        name="Paperclip TaskLease",
        description=None,
        task_type="paperclip_work",
        category=None,
        tags=[],
        status="failed",
        priority=75,
        payload={},
        config={},
        tenant_id="tenant-a",
        mission_id=None,
        skill_run_id=uuid4(),
        correlation_id=None,
        scheduled_at=None,
        deadline_at=None,
        claimed_by=None,
        claimed_at=None,
        started_at=None,
        completed_at=None,
        max_retries=0,
        retry_count=0,
        result=None,
        error_message=None,
        execution_time_ms=None,
        wait_time_ms=None,
        created_by=None,
        created_at=now,
        updated_at=now,
    )
    run = SimpleNamespace(
        id=uuid4(),
        tenant_id="tenant-a",
        skill_key="axe.worker.bridge",
        skill_version=1,
        state="waiting_approval",
        input_payload={},
        plan_snapshot={},
        provider_selection_snapshot={},
        requested_by="operator-1",
        requested_by_type="human",
        trigger_type="api",
        policy_decision_id=None,
        policy_decision={},
        policy_snapshot={},
        risk_tier="normal",
        correlation_id="corr-1",
        causation_id=None,
        idempotency_key="idem-1",
        mission_id=None,
        created_at=now,
        started_at=None,
        finished_at=None,
        deadline_at=None,
        retry_count=0,
        state_sequence=1,
        state_changed_at=None,
        cost_estimate=None,
        cost_actual=None,
        output_payload={},
        input_artifact_refs=[],
        output_artifact_refs=[],
        evidence_artifact_refs=[],
        evaluation_summary={},
        failure_code=None,
        failure_reason_sanitized=None,
    )

    async def _load_stub(db, *, task_id, principal_tenant_id, cross_tenant):  # noqa: ANN001
        _ = (db, task_id, principal_tenant_id, cross_tenant)
        return task, run

    monkeypatch.setattr(service, "_load_execution_entities", _load_stub)

    response = await service.get_execution_context(_FakeDb(), task_id="task-123", principal=_principal())

    assert sorted(response.available_actions) == ["request_approval", "request_escalation", "request_retry"]


@pytest.mark.asyncio
async def test_request_action_records_control_plane_event(monkeypatch) -> None:
    service = PaperclipHandoffService()
    fake_db = _FakeDb(events=[SimpleNamespace()])
    events = []
    task = SimpleNamespace(task_id="task-123", tenant_id="tenant-a", mission_id="mission-1", skill_run_id=uuid4(), correlation_id="corr-1", status="failed")
    run = SimpleNamespace(state="failed")

    async def _record_event_stub(**kwargs):  # noqa: ANN001
        events.append(kwargs)

    async def _load_stub(db, *, task_id, principal_tenant_id, cross_tenant):  # noqa: ANN001
        _ = (db, principal_tenant_id, cross_tenant)
        assert task_id == "task-123"
        return task, run

    monkeypatch.setenv("BRAIN_EXTERNAL_APP_HANDOFF_SECRET", "handoff-secret")
    monkeypatch.setattr(service, "_load_execution_entities", _load_stub)
    monkeypatch.setattr("app.modules.external_apps.service.record_control_plane_event", _record_event_stub)

    token = jwt.encode(
        {
            "iss": "brain-backend",
            "aud": "paperclip-ui",
            "sub": "operator-1",
            "tenant_id": "tenant-a",
            "skill_run_id": str(task.skill_run_id),
            "mission_id": "mission-1",
            "decision_id": "rdec_123",
            "correlation_id": "corr-1",
            "target_type": "execution",
            "target_ref": "task-123",
            "permissions": ["view", "request_retry", "request_escalation"],
            "iat": 1_700_000_000,
            "exp": 4_700_000_000,
            "jti": "handoff_123",
        },
        "handoff-secret",
        algorithm="HS256",
    )

    response = await service.request_action(
        fake_db,
        payload=PaperclipActionRequest(token=token, action="request_retry", reason="Please retry after fixing connector state."),
    )

    assert response.action == "request_retry"
    assert response.target_ref == "task-123"
    assert fake_db.commits == 1
    assert events[0]["entity_type"] == "external_action_request"
    assert events[0]["payload"]["action"] == "request_retry"


@pytest.mark.asyncio
async def test_request_action_rejects_missing_permission(monkeypatch) -> None:
    service = PaperclipHandoffService()
    monkeypatch.setenv("BRAIN_EXTERNAL_APP_HANDOFF_SECRET", "handoff-secret")

    token = jwt.encode(
        {
            "iss": "brain-backend",
            "aud": "paperclip-ui",
            "sub": "operator-1",
            "tenant_id": "tenant-a",
            "target_type": "execution",
            "target_ref": "task-123",
            "permissions": ["view"],
            "iat": 1_700_000_000,
            "exp": 4_700_000_000,
            "jti": "handoff_123",
        },
        "handoff-secret",
        algorithm="HS256",
    )

    with pytest.raises(PermissionError, match="does not permit"):
        await service.request_action(
            _FakeDb(),
            payload=PaperclipActionRequest(token=token, action="request_escalation", reason="Needs review"),
        )


@pytest.mark.asyncio
async def test_request_action_requires_activated_handoff(monkeypatch) -> None:
    service = PaperclipHandoffService()
    monkeypatch.setenv("BRAIN_EXTERNAL_APP_HANDOFF_SECRET", "handoff-secret")

    token = jwt.encode(
        {
            "iss": "brain-backend",
            "aud": "paperclip-ui",
            "sub": "operator-1",
            "tenant_id": "tenant-a",
            "target_type": "execution",
            "target_ref": "task-123",
            "permissions": ["view", "request_retry"],
            "iat": 1_700_000_000,
            "exp": 4_700_000_000,
            "jti": "handoff_123",
        },
        "handoff-secret",
        algorithm="HS256",
    )

    with pytest.raises(PermissionError, match="not been activated"):
        await service.request_action(
            _FakeDb(),
            payload=PaperclipActionRequest(token=token, action="request_retry", reason="Please retry"),
        )


@pytest.mark.asyncio
async def test_list_action_requests_aggregates_status(monkeypatch) -> None:
    service = PaperclipHandoffService()
    now = datetime.now(timezone.utc)
    events = [
        SimpleNamespace(
            entity_id="actreq_1",
            event_type="external.action_request.paperclip.requested.v1",
            actor_id="operator-1",
            created_at=now,
            payload={
                "request_id": "actreq_1",
                "tenant_id": "tenant-a",
                "principal_id": "operator-1",
                "action": "request_retry",
                "reason": "retry",
                "target_ref": "task-1",
            },
        ),
        SimpleNamespace(
            entity_id="actreq_1",
            event_type="external.action_request.paperclip.approved.v1",
            actor_id="admin-1",
            created_at=now,
            payload={
                "request_id": "actreq_1",
                "tenant_id": "tenant-a",
                "action": "request_retry",
                "target_ref": "task-1",
                "approved_by": "admin-1",
                "decision_reason": "approved",
                "execution_result": {"new_task_id": "task-2"},
            },
        ),
    ]

    response = await service.list_action_requests(_FakeDb(events=events), principal=_principal())

    assert response.total == 1
    assert response.items[0].status == "approved"
    assert response.items[0].execution_result["new_task_id"] == "task-2"


@pytest.mark.asyncio
async def test_retry_execution_request_creates_new_run_and_task(monkeypatch) -> None:
    service = PaperclipHandoffService()
    task = SimpleNamespace(
        task_id="task-123",
        name="Paperclip TaskLease",
        description="External execution",
        task_type="paperclip_work",
        category="skill_engine",
        tags=["tasklease", "paperclip"],
        priority=75,
        payload={"executor_type": "paperclip", "prompt": "Retry me"},
        config={"required_worker": "paperclip"},
        max_retries=3,
        retry_delay_seconds=60,
    )
    previous_run = SimpleNamespace(
        id=uuid4(),
        skill_key="axe.worker.bridge",
        skill_version=1,
        input_payload={"worker_type": "paperclip", "prompt": "Retry me"},
        mission_id="mission-1",
        deadline_at=None,
        correlation_id="corr-1",
        policy_snapshot={"upstream_decision": {"governance_snapshot": {"source": "axe"}}},
    )
    new_run = SimpleNamespace(id=uuid4(), tenant_id="tenant-a", mission_id="mission-1", correlation_id="corr-2", deadline_at=None, skill_key="axe.worker.bridge", skill_version=1)
    created = {}

    async def _load_stub(db, *, task_id, principal_tenant_id, cross_tenant):  # noqa: ANN001
        _ = (db, task_id, principal_tenant_id, cross_tenant)
        return task, previous_run

    class _SkillEngineStub:
        async def create_run(self, db, payload, principal):  # noqa: ANN001
            _ = (db, principal)
            created["skill_payload"] = payload
            return new_run

    class _TaskQueueStub:
        async def create_task(self, db, task_data, created_by=None, created_by_type=None):  # noqa: ANN001
            _ = (db, created_by, created_by_type)
            created["task_data"] = task_data
            return SimpleNamespace(task_id=task_data.task_id)

    monkeypatch.setattr(service, "_load_execution_entities", _load_stub)
    monkeypatch.setattr(service, "_build_execution_permit", lambda **kwargs: {"signature": "sig", **kwargs})
    monkeypatch.setattr("app.modules.external_apps.service.get_skill_engine_service", lambda: _SkillEngineStub())
    monkeypatch.setattr("app.modules.external_apps.service.get_task_queue_service", lambda: _TaskQueueStub())

    result = await service._retry_execution_request(  # noqa: SLF001
        _FakeDb(),
        principal=_principal(),
        request=SimpleNamespace(request_id="actreq_1", target_ref="task-123", skill_run_id=str(previous_run.id)),
    )

    assert result["retry_of_task_id"] == "task-123"
    assert result["new_skill_run_id"] == str(new_run.id)
    assert created["skill_payload"].trigger_type.value == "retry"
    assert created["task_data"].payload["retry_request_id"] == "actreq_1"


@pytest.mark.asyncio
async def test_approve_action_request_records_approval_event(monkeypatch) -> None:
    service = PaperclipHandoffService()
    fake_db = _FakeDb()
    events = []
    pending = SimpleNamespace(
        request_id="actreq_1",
        action="request_retry",
        status="pending",
        tenant_id="tenant-a",
        target_type="execution",
        target_ref="task-123",
        skill_run_id="run-123",
        mission_id="mission-1",
        correlation_id="corr-1",
        decision_id="rdec-1",
    )
    approved = SimpleNamespace(request_id="actreq_1")
    calls = {"count": 0}

    async def _get_request(db, *, principal, request_id):  # noqa: ANN001
        _ = (db, principal, request_id)
        calls["count"] += 1
        return pending if calls["count"] == 1 else approved

    async def _record_event_stub(**kwargs):  # noqa: ANN001
        events.append(kwargs)

    async def _retry_stub(db, *, principal, request):  # noqa: ANN001
        _ = (db, principal, request)
        return {"new_task_id": "task-999", "new_skill_run_id": "run-999"}

    monkeypatch.setattr(service, "_get_action_request_or_raise", _get_request)
    monkeypatch.setattr(service, "_retry_execution_request", _retry_stub)
    monkeypatch.setattr("app.modules.external_apps.service.record_control_plane_event", _record_event_stub)

    response = await service.approve_action_request(
        fake_db,
        principal=_principal(),
        request_id="actreq_1",
        payload=PaperclipActionRequestDecision(reason="Approved in ControlDeck"),
    )

    assert response.request_id == "actreq_1"
    assert fake_db.commits == 1
    assert events[0]["event_type"] == "external.action_request.paperclip.approved.v1"
    assert events[0]["payload"]["execution_result"]["new_task_id"] == "task-999"


@pytest.mark.asyncio
async def test_escalate_execution_request_creates_supervisor_handoff(monkeypatch) -> None:
    service = PaperclipHandoffService()
    task = SimpleNamespace(task_id="task-123", task_type="paperclip_work", payload={"prompt": "Need supervisor"}, config={"required_worker": "paperclip"})
    run = SimpleNamespace(risk_tier="high")
    captured = {}

    async def _load_stub(db, *, task_id, principal_tenant_id, cross_tenant):  # noqa: ANN001
        _ = (db, task_id, principal_tenant_id, cross_tenant)
        return task, run

    async def _create_handoff_stub(payload, db=None):  # noqa: ANN001
        captured["payload"] = payload
        return SimpleNamespace(escalation_id="esc_123", status="queued")

    monkeypatch.setattr(service, "_load_execution_entities", _load_stub)
    monkeypatch.setattr("app.modules.external_apps.service.create_domain_escalation_handoff", _create_handoff_stub)

    result = await service._escalate_execution_request(  # noqa: SLF001
        _FakeDb(),
        principal=_principal(),
        request=SimpleNamespace(
            request_id="actreq_1",
            principal_id="operator-1",
            tenant_id="tenant-a",
            target_type="execution",
            target_ref="task-123",
            skill_run_id="run-123",
            decision_id="rdec-1",
            mission_id="mission-1",
            correlation_id="corr-1",
            reason="Needs supervisor review",
        ),
    )

    assert result["supervisor_escalation_id"] == "esc_123"
    assert captured["payload"].domain_key == "external_apps.paperclip.execution.paperclip_work"
    assert captured["payload"].context["action_request_id"] == "actreq_1"


def test_resolve_supervisor_domain_key_prefers_skill_key() -> None:
    service = PaperclipHandoffService()

    domain_key = service._resolve_supervisor_domain_key(  # noqa: SLF001
        task=SimpleNamespace(task_type="paperclip_work", payload={"intent": "worker_bridge_execute"}),
        skill_run=SimpleNamespace(skill_key="axe.worker.bridge"),
        request=SimpleNamespace(target_type="execution"),
    )

    assert domain_key == "external_apps.paperclip.execution.axe_worker_bridge"


@pytest.mark.asyncio
async def test_approve_escalation_request_records_supervisor_result(monkeypatch) -> None:
    service = PaperclipHandoffService()
    fake_db = _FakeDb()
    events = []
    pending = SimpleNamespace(
        request_id="actreq_esc",
        action="request_escalation",
        status="pending",
        tenant_id="tenant-a",
        target_type="execution",
        target_ref="task-123",
        skill_run_id="run-123",
        mission_id="mission-1",
        correlation_id="corr-1",
        decision_id="rdec-1",
        principal_id="operator-1",
        reason="Needs supervisor",
    )
    approved = SimpleNamespace(request_id="actreq_esc")
    calls = {"count": 0}

    async def _get_request(db, *, principal, request_id):  # noqa: ANN001
        _ = (db, principal, request_id)
        calls["count"] += 1
        return pending if calls["count"] == 1 else approved

    async def _record_event_stub(**kwargs):  # noqa: ANN001
        events.append(kwargs)

    async def _escalate_stub(db, *, principal, request):  # noqa: ANN001
        _ = (db, principal, request)
        return {"supervisor_escalation_id": "esc_123", "supervisor_status": "queued"}

    monkeypatch.setattr(service, "_get_action_request_or_raise", _get_request)
    monkeypatch.setattr(service, "_escalate_execution_request", _escalate_stub)
    monkeypatch.setattr("app.modules.external_apps.service.record_control_plane_event", _record_event_stub)

    response = await service.approve_action_request(
        fake_db,
        principal=_principal(),
        request_id="actreq_esc",
        payload=PaperclipActionRequestDecision(reason="Escalate to supervisor"),
    )

    assert response.request_id == "actreq_esc"
    assert events[0]["payload"]["execution_result"]["supervisor_escalation_id"] == "esc_123"
