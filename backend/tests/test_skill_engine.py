from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import importlib
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.core.capabilities.schemas import CapabilityExecutionResponse, CapabilityExecutionSuccess
from app.core.database import get_db
from app.modules.skill_engine.router import router as skill_engine_router
from app.modules.skill_engine.schemas import SkillRunCreate, TriggerType
from app.modules.skill_engine.service import SkillEngineService


class FakeSkillDefinition:
    def __init__(self) -> None:
        self.skill_key = "demo.skill"
        self.version = 2
        self.quality_profile = "standard"
        self.risk_tier = "medium"


def build_principal() -> Principal:
    return Principal(
        principal_id="operator-123",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator",
        roles=["operator"],
        scopes=["write"],
        tenant_id="tenant-a",
    )


@contextmanager
def override_auth_principal(client: TestClient, principal: Principal):
    client.app.dependency_overrides[require_auth] = lambda: principal
    try:
        yield
    finally:
        client.app.dependency_overrides.pop(require_auth, None)


@contextmanager
def override_auth_unauthorized(client: TestClient):
    async def _unauthorized():
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})

    client.app.dependency_overrides[require_auth] = _unauthorized
    try:
        yield
    finally:
        client.app.dependency_overrides.pop(require_auth, None)


def test_build_plan_snapshot_contains_capability_nodes() -> None:
    snapshot = SkillEngineService.build_plan_snapshot(
        FakeSkillDefinition(),
        [
            {"capability_key": "text.generate", "capability_version": 1, "provider_binding_id": "binding.text.generate.ollama.v1"},
            {"capability_key": "connectors.health.check", "capability_version": 1, "provider_binding_id": "binding.connectors.health.default.v1"},
        ],
    )
    assert snapshot["skill_key"] == "demo.skill"
    assert len(snapshot["nodes"]) == 2
    assert snapshot["nodes"][1]["depends_on"] == [snapshot["nodes"][0]["node_id"]]


def test_summarize_evaluation_marks_failures() -> None:
    success = CapabilityExecutionResponse(
        capability_key="text.generate",
        capability_version=1,
        provider_binding_id="binding.text.generate.ollama.v1",
        result=CapabilityExecutionSuccess(output={"text": "ok"}, latency_ms=1.0),
    )
    failure = CapabilityExecutionResponse.model_validate(
        {
            "capability_key": "connectors.health.check",
            "capability_version": 1,
            "provider_binding_id": "binding.connectors.health.default.v1",
            "result": {
                "status": "failed",
                "error_code": "CAP-FAIL",
                "retryable": False,
                "provider_unavailable": False,
                "provider_content_blocked": False,
                "timeout": False,
                "sanitized_message": "nope",
            },
        }
    )
    summary = SkillEngineService.summarize_evaluation([success, failure])
    assert summary["overall_score"] == 0.0
    assert summary["issues_detected"] == ["CAP-FAIL"]


def test_skill_run_state_machine_rules() -> None:
    assert SkillEngineService.is_transition_allowed("queued", "planning") is True
    assert SkillEngineService.is_transition_allowed("planning", "waiting_approval") is True
    assert SkillEngineService.is_transition_allowed("running", "cancel_requested") is True
    assert SkillEngineService.is_transition_allowed("cancel_requested", "cancelled") is True
    assert SkillEngineService.is_transition_allowed("queued", "succeeded") is False


@pytest.fixture
def skill_engine_app() -> FastAPI:
    app = FastAPI()
    app.include_router(skill_engine_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    return app


@pytest.fixture
def skill_engine_client(skill_engine_app: FastAPI) -> TestClient:
    return TestClient(skill_engine_app)


def test_skill_engine_routes_require_authentication(skill_engine_client: TestClient) -> None:
    with override_auth_unauthorized(skill_engine_client):
        response = skill_engine_client.get("/api/skill-runs")
    assert response.status_code == 401


def test_skill_engine_execute_route_uses_service(skill_engine_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    principal = build_principal()
    run_id = uuid4()
    skill_engine_router_module = importlib.import_module("app.modules.skill_engine.router")

    class FakeService:
        async def execute_run(self, db, run_id_arg, principal_arg):
            return {
                "skill_run": {
                    "id": run_id_arg,
                    "tenant_id": principal_arg.tenant_id,
                    "skill_key": "demo.skill",
                    "skill_version": 1,
                    "state": "succeeded",
                    "input_payload": {},
                    "plan_snapshot": {},
                    "provider_selection_snapshot": {},
                    "requested_by": principal_arg.principal_id,
                    "requested_by_type": principal_arg.principal_type.value,
                    "trigger_type": "api",
                    "policy_decision_id": None,
                    "policy_decision": {"allowed": True},
                    "policy_snapshot": {"allowed": True},
                    "risk_tier": "medium",
                    "correlation_id": "corr-1",
                    "causation_id": None,
                    "idempotency_key": "idem-1",
                    "mission_id": None,
                    "created_at": datetime.now(timezone.utc),
                    "started_at": datetime.now(timezone.utc),
                    "finished_at": datetime.now(timezone.utc),
                    "deadline_at": None,
                    "retry_count": 0,
                    "state_sequence": 2,
                    "state_changed_at": datetime.now(timezone.utc),
                    "cost_estimate": 0.0,
                    "cost_actual": 0.0,
                    "output_payload": {"text.generate": {"text": "ok"}},
                    "input_artifact_refs": [],
                    "output_artifact_refs": [],
                    "evidence_artifact_refs": [],
                    "evaluation_summary": {"overall_score": 1.0},
                    "failure_code": None,
                    "failure_reason_sanitized": None,
                },
                "capability_results": [],
            }

    monkeypatch.setattr(skill_engine_router_module, "get_skill_engine_service", lambda: FakeService())
    with override_auth_principal(skill_engine_client, principal):
        response = skill_engine_client.post(f"/api/skill-runs/{run_id}/execute")
    assert response.status_code == 200
    assert response.json()["skill_run"]["state"] == "succeeded"


@pytest.mark.asyncio
async def test_create_run_preserves_upstream_decision_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSkillRegistry:
        async def resolve_definition(self, db, skill_key, tenant_id, selector, version_value):
            _ = db
            _ = skill_key
            _ = tenant_id
            _ = selector
            _ = version_value
            return SimpleNamespace(
                skill_key="demo.skill",
                version=3,
                quality_profile="standard",
                risk_tier="medium",
                purpose="demo purpose",
                required_capabilities=[{"capability_key": "text.generate", "version_selector": "active"}],
                tenant_id="tenant-a",
            )

    class FakePlanningService:
        def decompose_task(self, request):
            _ = request
            return SimpleNamespace(plan=SimpleNamespace(plan_id="plan-1", nodes=[{"id": "n1"}]))

    class FakeDB:
        def add(self, item):
            _ = item

        async def flush(self):
            return None

        async def commit(self):
            return None

        async def refresh(self, model):
            _ = model
            return None

    service = SkillEngineService(
        skill_registry=FakeSkillRegistry(),
        planning_service=FakePlanningService(),
    )

    async def _fake_find_existing(*args, **kwargs):
        _ = args
        _ = kwargs
        return None

    async def _fake_resolve_bindings(*args, **kwargs):
        _ = args
        _ = kwargs
        return (
            [
                {
                    "capability_key": "text.generate",
                    "capability_version": 1,
                    "provider_binding_id": "binding.text.generate.ollama.v1",
                    "selection_strategy": "priority",
                    "selection_reason": "default",
                    "binding_snapshot": {},
                }
            ],
            0.0,
        )

    async def _fake_policy(*args, **kwargs):
        _ = args
        _ = kwargs
        return {"allowed": True, "effect": "allow", "requires_audit": False}

    async def _fake_event(**kwargs):
        _ = kwargs
        return None

    monkeypatch.setattr(service, "_find_existing_by_idempotency", _fake_find_existing)
    monkeypatch.setattr(service, "_resolve_capability_bindings", _fake_resolve_bindings)
    monkeypatch.setattr(service, "_evaluate_policy", _fake_policy)

    skill_service_module = importlib.import_module("app.modules.skill_engine.service")
    monkeypatch.setattr(skill_service_module, "record_control_plane_event", _fake_event)

    payload = SkillRunCreate(
        skill_key="demo.skill",
        input_payload={"x": 1},
        idempotency_key="idem-upstream-1",
        trigger_type=TriggerType.MISSION,
        mission_id="m-1",
        causation_id="cause-1",
        decision_context_id="ctx-1",
        purpose_evaluation_id="pe-1",
        routing_decision_id="rd-1",
        governance_snapshot={"control_mode": "brain_first"},
    )

    model = await service.create_run(FakeDB(), payload, build_principal())
    upstream = model.plan_snapshot.get("upstream_decision")
    runtime_decision = model.plan_snapshot.get("runtime_decision")
    assert upstream["decision_context_id"] == "ctx-1"
    assert upstream["purpose_evaluation_id"] == "pe-1"
    assert upstream["routing_decision_id"] == "rd-1"
    assert runtime_decision["decision_id"] is not None
    assert runtime_decision["selected_route"] is not None
    assert model.policy_snapshot["upstream_decision"]["governance_snapshot"]["control_mode"] == "brain_first"
    assert model.policy_snapshot["runtime_decision"]["decision_id"] == runtime_decision["decision_id"]


@pytest.mark.asyncio
async def test_evaluate_policy_allows_guarded_fallback_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    service = SkillEngineService()

    class FakePolicyEngine:
        async def evaluate(self, context, request_id=None):
            _ = (context, request_id)
            return SimpleNamespace(
                allowed=False,
                effect=SimpleNamespace(value="deny"),
                matched_rule=None,
                matched_policy=None,
                reason="No matching policies configured - default deny",
                requires_audit=False,
            )

    skill_engine_service_module = importlib.import_module("app.modules.skill_engine.service")
    monkeypatch.setattr(skill_engine_service_module, "get_policy_engine", lambda db_session: FakePolicyEngine())

    payload = SkillRunCreate(
        skill_key="demo.skill",
        input_payload={"x": 1},
        idempotency_key="idem-policy-fallback-1",
    )
    skill_definition = SimpleNamespace(
        skill_key="demo.skill",
        version=1,
        risk_tier="medium",
        fallback_policy="allowed",
    )

    decision = await service._evaluate_policy(db=None, principal=build_principal(), skill_definition=skill_definition, payload=payload)

    assert decision["allowed"] is True
    assert decision["effect"] == "audit"
    assert decision["requires_audit"] is True
    assert decision["policy_defaulted"] is True
    assert decision["fallback_policy"] == "allowed"


@pytest.mark.asyncio
async def test_evaluate_policy_keeps_deny_when_fallback_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    service = SkillEngineService()

    class FakePolicyEngine:
        async def evaluate(self, context, request_id=None):
            _ = (context, request_id)
            return SimpleNamespace(
                allowed=False,
                effect=SimpleNamespace(value="deny"),
                matched_rule=None,
                matched_policy=None,
                reason="No matching policies configured - default deny",
                requires_audit=False,
            )

    skill_engine_service_module = importlib.import_module("app.modules.skill_engine.service")
    monkeypatch.setattr(skill_engine_service_module, "get_policy_engine", lambda db_session: FakePolicyEngine())

    payload = SkillRunCreate(
        skill_key="demo.skill",
        input_payload={"x": 1},
        idempotency_key="idem-policy-fallback-2",
    )
    skill_definition = SimpleNamespace(
        skill_key="demo.skill",
        version=1,
        risk_tier="medium",
        fallback_policy="forbidden",
    )

    with pytest.raises(PermissionError, match="No matching policies configured"):
        await service._evaluate_policy(db=None, principal=build_principal(), skill_definition=skill_definition, payload=payload)
