from __future__ import annotations

from contextlib import contextmanager
import importlib
import sys
from types import SimpleNamespace
from typing import cast

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.modules.domain_agents.router import router as domain_agents_router


def build_principal(*roles: str) -> Principal:
    return Principal(
        principal_id="tester",
        principal_type=PrincipalType.HUMAN,
        email="tester@example.com",
        name="Tester",
        roles=list(roles),
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


@contextmanager
def override_auth_principal(client: TestClient, principal: Principal):
    app = cast(FastAPI, client.app)
    app.dependency_overrides[require_auth] = lambda: principal  # type: ignore[attr-defined]
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_auth, None)  # type: ignore[attr-defined]


@contextmanager
def override_auth_unauthorized(client: TestClient):
    async def _unauthorized():
        raise HTTPException(status_code=401, detail="Authentication required")

    app = cast(FastAPI, client.app)
    app.dependency_overrides[require_auth] = _unauthorized  # type: ignore[attr-defined]
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_auth, None)  # type: ignore[attr-defined]


def build_test_app() -> FastAPI:
    from app.modules.domain_agents import router as domain_router_module

    app = FastAPI()
    app.include_router(domain_agents_router)

    async def _db_override():
        yield None

    app.dependency_overrides[domain_router_module._get_db] = _db_override
    return app


def test_domain_agents_router_requires_authentication() -> None:
    app = build_test_app()
    client = TestClient(app)

    with override_auth_unauthorized(client):
        response = client.get("/api/domain-agents/domains")

    assert response.status_code == 401


def test_domain_agents_router_lists_bootstrap_domain() -> None:
    app = build_test_app()
    client = TestClient(app)

    with override_auth_principal(client, build_principal("viewer")):
        response = client.get("/api/domain-agents/domains")

    assert response.status_code == 200
    domains = response.json()
    assert any(item["domain_key"] == "programming" for item in domains)


def test_domain_register_requires_operator_or_admin() -> None:
    app = build_test_app()
    client = TestClient(app)

    payload = {
        "domain_key": "marketing",
        "display_name": "Marketing",
        "status": "active",
        "allowed_skill_keys": ["marketing.campaign"],
        "allowed_capability_keys": ["marketing.strategy"],
    }

    with override_auth_principal(client, build_principal("viewer")):
        response = client.post("/api/domain-agents/domains/register", json=payload)

    assert response.status_code == 403


def test_domain_register_and_decompose_flow(monkeypatch) -> None:
    """POST /register persists via register_db; decompose resolves the registered domain.

    The test overrides register_db to avoid a real DB session while still
    verifying the full register->decompose flow end-to-end.
    """
    app = build_test_app()
    client = TestClient(app)

    from app.modules.domain_agents import service as da_service
    from app.modules.domain_agents.schemas import DomainAgentConfig

    async def _fake_register_db(self, db, config: DomainAgentConfig) -> DomainAgentConfig:
        # Mirror what register_db does: store in in-memory registry and return config
        self.register(config)
        return config

    monkeypatch.setattr(da_service.DomainAgentRegistry, "register_db", _fake_register_db)

    register_payload = {
        "domain_key": "marketing",
        "display_name": "Marketing",
        "status": "active",
        "allowed_skill_keys": ["marketing.campaign"],
        "allowed_capability_keys": ["marketing.strategy", "marketing.content"],
        "allowed_specialist_roles": ["growth-specialist"],
    }
    decompose_payload = {
        "domain_key": "marketing",
        "task_name": "Launch campaign",
        "available_capabilities": ["marketing.strategy", "code.write"],
    }

    with override_auth_principal(client, build_principal("operator")):
        register_response = client.post(
            "/api/domain-agents/domains/register",
            json=register_payload,
        )
        decompose_response = client.post(
            "/api/domain-agents/decompose",
            json=decompose_payload,
        )

    assert register_response.status_code == 201
    assert register_response.json()["domain_key"] == "marketing"
    assert register_response.json()["tenant_id"] == "tenant-a"
    assert decompose_response.status_code == 200
    assert decompose_response.json()["selected_capability_keys"] == ["marketing.strategy"]


def test_decompose_resolves_domain_from_db_registry(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    from app.modules.domain_agents import service as da_service
    from app.modules.domain_agents.schemas import DomainAgentConfig, DomainStatus

    async def _fake_get_db(self, db, domain_key: str, tenant_id: str | None):
        _ = self
        _ = db
        _ = tenant_id
        if domain_key != "marketing":
            return None
        return DomainAgentConfig(
            tenant_id="tenant-a",
            owner_scope="tenant",
            domain_key="marketing",
            display_name="Marketing",
            status=DomainStatus.ACTIVE,
            allowed_skill_keys=["marketing.campaign"],
            allowed_capability_keys=["marketing.strategy", "marketing.content"],
            allowed_specialist_roles=["growth-specialist"],
        )

    monkeypatch.setattr(da_service.DomainAgentRegistry, "get_db", _fake_get_db)

    payload = {
        "domain_key": "marketing",
        "task_name": "Launch campaign",
        "available_capabilities": ["marketing.strategy", "code.write"],
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/decompose", json=payload)

    assert response.status_code == 200
    assert response.json()["domain_key"] == "marketing"
    assert response.json()["selected_capability_keys"] == ["marketing.strategy"]


def test_prepare_skill_runs_drafts_without_execution() -> None:
    app = build_test_app()
    client = TestClient(app)

    payload = {
        "decomposition": {
            "domain_key": "programming",
            "task_name": "Build endpoint",
            "available_capabilities": ["code.write", "code.review"],
        },
        "input_payload": {"ticket": "ABC-123"},
        "trigger_type": "mission",
        "execute_now": False,
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/prepare-skill-runs", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["resolution"]["domain_key"] == "programming"
    assert len(body["run_drafts"]) >= 1
    assert body["created_run_ids"] == []


def test_prepare_skill_runs_execute_now_creates_runs(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    class _SkillService:
        async def create_run(self, db, payload, principal):
            _ = db
            _ = payload
            _ = principal
            return SimpleNamespace(id="run-123")

    fake_module = SimpleNamespace(get_skill_engine_service=lambda: _SkillService())
    monkeypatch.setitem(sys.modules, "app.modules.skill_engine.service", fake_module)

    payload = {
        "decomposition": {
            "domain_key": "programming",
            "task_name": "Build endpoint",
            "available_capabilities": ["code.write", "code.test"],
        },
        "input_payload": {"ticket": "ABC-999"},
        "trigger_type": "mission",
        "execute_now": True,
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/prepare-skill-runs", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert len(body["created_run_ids"]) >= 1
    assert body["created_run_ids"][0] == "run-123"


def test_prepare_skill_runs_escalation_emits_audit(monkeypatch) -> None:
    """Escalated resolutions write an audit record and return a supervisor_handoff.

    execute_now=False so the test focuses on the audit/handoff path without
    triggering the execution gate (which correctly returns 409 when escalated).
    """
    app = build_test_app()
    client = TestClient(app)

    router_module = importlib.import_module("app.modules.domain_agents.router")
    calls = []

    async def _fake_audit(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(router_module, "_write_escalation_audit", _fake_audit)

    payload = {
        "decomposition": {
            "domain_key": "programming",
            "task_name": "Patch production payment auth flow",
            "available_capabilities": ["code.write", "code.test"],
        },
        "input_payload": {"ticket": "SEC-1"},
        "trigger_type": "mission",
        # execute_now=False: test only the audit/escalation path, not the execution gate
        "execute_now": False,
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/prepare-skill-runs", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["review"]["should_escalate"] is True
    assert body["created_run_ids"] == []
    assert body["supervisor_handoff"]["domain_key"] == "programming"
    assert body["supervisor_handoff"]["risk_tier"] == "high"
    assert len(calls) == 1
    assert calls[0]["resource_id"] == "programming"


def test_decompose_emits_domain_event(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    router_module = importlib.import_module("app.modules.domain_agents.router")
    calls = []

    async def _fake_emit(event_type: str, payload: dict):
        calls.append((event_type, payload))

    monkeypatch.setattr(router_module, "_emit_domain_event_safe", _fake_emit)

    payload = {
        "domain_key": "programming",
        "task_name": "Implement feature",
        "available_capabilities": ["code.write", "code.test"],
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/decompose", json=payload)

    assert response.status_code == 200
    assert any(item[0] == "domain.agent.decomposed.v1" for item in calls)


def test_execute_now_gated_when_escalation_required(monkeypatch) -> None:
    """execute_now=True on an escalated resolution must return 409.

    When the domain review flags should_escalate=True, execution is gated
    regardless of whether a supervisor_escalation_id is provided. The caller
    must wait for supervisor approval and then re-invoke without execute_now,
    or use a separate approved execution path.
    """
    app = build_test_app()
    client = TestClient(app)

    # "payment" in task_name triggers high-risk escalation in programming domain
    payload = {
        "decomposition": {
            "domain_key": "programming",
            "task_name": "Patch production payment auth flow",
            "available_capabilities": ["code.write", "code.test"],
        },
        "input_payload": {"ticket": "PAY-001"},
        "trigger_type": "mission",
        "execute_now": True,
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/prepare-skill-runs", json=payload)

    assert response.status_code == 409
    assert "supervisor approval" in response.json()["detail"]


def test_execute_now_rejects_non_approved_supervisor_escalation(monkeypatch) -> None:
    """execute_now requires supervisor escalation status=approved when provided."""
    app = build_test_app()
    client = TestClient(app)
    router_module = importlib.import_module("app.modules.domain_agents.router")

    async def _fake_lookup(**kwargs):
        _ = kwargs
        return {
            "escalation_id": "esc-123",
            "status": "in_review",
            "domain_key": "programming",
        }

    monkeypatch.setattr(router_module, "_get_supervisor_escalation_safe", _fake_lookup)

    payload = {
        "decomposition": {
            "domain_key": "programming",
            "task_name": "Patch production payment auth flow",
            "available_capabilities": ["code.write", "code.test"],
        },
        "input_payload": {"ticket": "ABC-777"},
        "trigger_type": "mission",
        "execute_now": True,
        "supervisor_escalation_id": "esc-123",
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/prepare-skill-runs", json=payload)

    assert response.status_code == 409
    assert "approved state" in response.json()["detail"]


def test_execute_now_non_escalated_creates_runs(monkeypatch) -> None:
    """execute_now=True on a non-escalated resolution delegates to skill engine.

    This test verifies that when the domain review does not require escalation
    and no supervisor_escalation_id is supplied, execute_now correctly delegates
    SkillRun creation to the skill engine service layer.
    """
    app = build_test_app()
    client = TestClient(app)

    class _SkillService:
        async def create_run(self, db, payload, principal):
            _ = db
            _ = payload
            _ = principal
            return SimpleNamespace(id="run-approved")

    fake_module = SimpleNamespace(get_skill_engine_service=lambda: _SkillService())
    monkeypatch.setitem(sys.modules, "app.modules.skill_engine.service", fake_module)

    # "Build endpoint" does not contain high-risk markers, so no escalation
    payload = {
        "decomposition": {
            "domain_key": "programming",
            "task_name": "Build endpoint",
            "available_capabilities": ["code.write", "code.test"],
        },
        "input_payload": {"ticket": "ABC-778"},
        "trigger_type": "mission",
        "execute_now": True,
        # No supervisor_escalation_id — non-escalated path
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/prepare-skill-runs", json=payload)

    assert response.status_code == 200
    assert response.json()["created_run_ids"][0] == "run-approved"


def test_execute_now_allows_approved_supervisor_escalation(monkeypatch) -> None:
    """Approved supervisor escalation unblocks execute_now for escalated resolutions."""
    app = build_test_app()
    client = TestClient(app)
    router_module = importlib.import_module("app.modules.domain_agents.router")

    async def _fake_lookup(**kwargs):
        _ = kwargs
        return {
            "escalation_id": "esc-approved",
            "status": "approved",
            "domain_key": "programming",
        }

    class _SkillService:
        async def create_run(self, db, payload, principal):
            _ = db
            _ = payload
            _ = principal
            return SimpleNamespace(id="run-approved-escalation")

    monkeypatch.setattr(router_module, "_get_supervisor_escalation_safe", _fake_lookup)
    fake_module = SimpleNamespace(get_skill_engine_service=lambda: _SkillService())
    monkeypatch.setitem(sys.modules, "app.modules.skill_engine.service", fake_module)

    payload = {
        "decomposition": {
            "domain_key": "programming",
            "task_name": "Patch production payment auth flow",
            "available_capabilities": ["code.write", "code.test"],
        },
        "input_payload": {"ticket": "PAY-APPROVED"},
        "trigger_type": "mission",
        "execute_now": True,
        "supervisor_escalation_id": "esc-approved",
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/prepare-skill-runs", json=payload)

    assert response.status_code == 200
    assert response.json()["created_run_ids"][0] == "run-approved-escalation"


def test_prepare_skill_runs_respects_domain_parallel_budget(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    from app.modules.domain_agents import service as da_service
    from app.modules.domain_agents.schemas import (
        DomainAgentConfig,
        DomainBudgetProfile,
        DomainStatus,
    )

    async def _fake_get_db(self, db, domain_key: str, tenant_id: str | None):
        _ = self
        _ = db
        _ = tenant_id
        if domain_key != "programming":
            return None
        return DomainAgentConfig(
            tenant_id="tenant-a",
            owner_scope="tenant",
            domain_key="programming",
            display_name="Programming",
            status=DomainStatus.ACTIVE,
            allowed_skill_keys=["code.implement", "code.test", "code.review"],
            allowed_capability_keys=["code.write", "code.test", "code.analyze"],
            allowed_specialist_roles=["runtime-engineer", "verification-engineer"],
            budget_profile=DomainBudgetProfile(max_parallel_runs=1),
        )

    monkeypatch.setattr(da_service.DomainAgentRegistry, "get_db", _fake_get_db)

    payload = {
        "decomposition": {
            "domain_key": "programming",
            "task_name": "Review and implement endpoint",
            "available_capabilities": ["code.write", "code.test", "code.analyze"],
        },
        "input_payload": {"ticket": "BUDGET-1"},
        "trigger_type": "mission",
        "execute_now": False,
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/prepare-skill-runs", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert len(body["resolution"]["selected_skill_keys"]) >= 2
    assert len(body["run_drafts"]) == 1


def test_decompose_uses_agent_management_specialists(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    from app.modules.domain_agents import service as da_service
    from app.modules.domain_agents.schemas import DomainAgentConfig, DomainStatus, SpecialistCandidate

    async def _fake_get_db(self, db, domain_key: str, tenant_id: str | None):
        _ = self
        _ = db
        _ = tenant_id
        if domain_key != "programming":
            return None
        return DomainAgentConfig(
            tenant_id="tenant-a",
            owner_scope="tenant",
            domain_key="programming",
            display_name="Programming",
            status=DomainStatus.ACTIVE,
            allowed_skill_keys=["code.implement", "code.test"],
            allowed_capability_keys=["code.write", "code.test"],
            allowed_specialist_roles=["runtime-engineer"],
        )

    async def _fake_select_specialists(self, db, config):
        _ = self
        _ = db
        _ = config
        return [
            SpecialistCandidate(
                agent_id="agent-runtime-01",
                role="runtime-engineer",
                score=0.95,
                reasons=["agent matched allowed_specialist_roles"],
            )
        ]

    monkeypatch.setattr(da_service.DomainAgentRegistry, "get_db", _fake_get_db)
    monkeypatch.setattr(da_service.DomainAgentService, "select_specialists", _fake_select_specialists)

    payload = {
        "domain_key": "programming",
        "task_name": "Implement feature",
        "available_capabilities": ["code.write", "code.test"],
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/decompose", json=payload)

    assert response.status_code == 200
    specialists = response.json()["selected_specialists"]
    assert len(specialists) == 1
    assert specialists[0]["agent_id"] == "agent-runtime-01"


def test_create_purpose_evaluation_rejects_context_mismatch() -> None:
    app = build_test_app()
    client = TestClient(app)

    payload = {
        "decision_context": {
            "decision_context_id": "ctx-1",
            "tenant_id": "tenant-a",
            "requested_by": "tester",
            "request_channel": "api",
            "intent_summary": "Evaluate purpose",
            "requested_autonomy_level": "medium",
            "sensitivity_class": "standard",
            "context": {},
        },
        "evaluation": {
            "decision_context_id": "ctx-other",
            "purpose_profile_id": "governed_autonomous_delivery",
            "outcome": "accept",
            "purpose_score": 0.9,
            "sovereignty_score": 0.95,
            "requires_human_review": False,
            "required_modifications": [],
            "reasons": ["ok"],
            "governance_snapshot": {},
        },
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/purpose-evaluations", json=payload)

    assert response.status_code == 422
    assert "decision_context_id must match" in response.json()["detail"]


def test_create_purpose_evaluation_success(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    from app.modules.domain_agents import service as da_service

    async def _fake_create_purpose(self, db, *, decision_context, evaluation, principal):
        _ = self
        _ = db
        _ = evaluation
        _ = principal
        return {
            "id": "pe-1",
            "tenant_id": decision_context.tenant_id,
            "decision_context_id": decision_context.decision_context_id,
            "purpose_profile_id": "governed_autonomous_delivery",
            "outcome": "accept",
            "purpose_score": 0.9,
            "sovereignty_score": 0.95,
            "requires_human_review": False,
            "required_modifications": [],
            "reasons": ["ok"],
            "governance_snapshot": {},
            "mission_id": None,
            "correlation_id": None,
            "created_by": "tester",
        }

    monkeypatch.setattr(
        da_service.DomainAgentService,
        "create_purpose_evaluation",
        _fake_create_purpose,
    )

    payload = {
        "decision_context": {
            "decision_context_id": "ctx-1",
            "tenant_id": "tenant-a",
            "requested_by": "tester",
            "request_channel": "api",
            "intent_summary": "Evaluate purpose",
            "requested_autonomy_level": "medium",
            "sensitivity_class": "standard",
            "context": {},
        },
        "evaluation": {
            "decision_context_id": "ctx-1",
            "purpose_profile_id": "governed_autonomous_delivery",
            "outcome": "accept",
            "purpose_score": 0.9,
            "sovereignty_score": 0.95,
            "requires_human_review": False,
            "required_modifications": [],
            "reasons": ["ok"],
            "governance_snapshot": {},
        },
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/purpose-evaluations", json=payload)

    assert response.status_code == 201
    assert response.json()["id"] == "pe-1"


def test_create_routing_decision_success(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    from app.modules.domain_agents import service as da_service

    async def _fake_create_routing(self, db, *, decision_context, decision, principal):
        _ = self
        _ = db
        _ = principal
        return {
            "id": "rd-1",
            "tenant_id": decision_context.tenant_id,
            "decision_context_id": decision_context.decision_context_id,
            "task_profile_id": decision.task_profile_id,
            "purpose_evaluation_id": decision.purpose_evaluation_id,
            "worker_candidates": decision.worker_candidates,
            "filtered_candidates": decision.filtered_candidates,
            "scoring_breakdown": decision.scoring_breakdown,
            "selected_worker": decision.selected_worker,
            "selected_skill_or_plan": decision.selected_skill_or_plan,
            "strategy": decision.strategy,
            "reasoning": decision.reasoning,
            "mission_id": None,
            "correlation_id": None,
            "created_by": "tester",
        }

    monkeypatch.setattr(
        da_service.DomainAgentService,
        "create_routing_decision",
        _fake_create_routing,
    )

    payload = {
        "decision_context": {
            "decision_context_id": "ctx-2",
            "tenant_id": "tenant-a",
            "requested_by": "tester",
            "request_channel": "api",
            "intent_summary": "Route task",
            "requested_autonomy_level": "high",
            "sensitivity_class": "sensitive",
            "context": {},
        },
        "task_profile": {
            "task_profile_id": "task-1",
            "task_class": "delivery",
            "description": "Ship feature",
            "required_capabilities": ["code.write"],
            "constraints": {},
            "required_worker_traits": [],
            "optimization_weights": {"capability_fit": 1.0},
            "routing_sensitivity": "medium",
            "split_allowed": False,
        },
        "decision": {
            "routing_decision_id": "route-1",
            "decision_context_id": "ctx-2",
            "task_profile_id": "task-1",
            "purpose_evaluation_id": "pe-1",
            "worker_candidates": ["worker-a"],
            "filtered_candidates": ["worker-a"],
            "scoring_breakdown": {"worker-a": {"total": 0.9}},
            "selected_worker": "worker-a",
            "selected_skill_or_plan": "code.implement",
            "strategy": "single_worker",
            "reasoning": "best fit",
        },
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/routing-decisions", json=payload)

    assert response.status_code == 201
    assert response.json()["id"] == "rd-1"


def test_prepare_skill_runs_propagates_upstream_decision_artifacts(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    from types import SimpleNamespace

    from app.modules.domain_agents import service as da_service
    from app.modules.domain_agents.schemas import DecisionOutcome

    async def _fake_get_purpose(self, db, *, evaluation_id: str, tenant_id: str | None):
        _ = self
        _ = db
        _ = evaluation_id
        _ = tenant_id
        return SimpleNamespace(
            id="pe-1",
            tenant_id="tenant-a",
            decision_context_id="ctx-42",
            purpose_profile_id="governed_autonomous_delivery",
            outcome=DecisionOutcome.ACCEPT,
            purpose_score=0.88,
            sovereignty_score=0.93,
            requires_human_review=False,
            required_modifications=[],
            reasons=["ok"],
            governance_snapshot={},
            mission_id="m-1",
            correlation_id="corr-42",
            created_by="tester",
        )

    async def _fake_get_routing(self, db, *, routing_decision_id: str, tenant_id: str | None):
        _ = self
        _ = db
        _ = routing_decision_id
        _ = tenant_id
        return SimpleNamespace(
            id="rd-1",
            tenant_id="tenant-a",
            decision_context_id="ctx-42",
            task_profile_id="task-1",
            purpose_evaluation_id="pe-1",
            worker_candidates=["worker-a"],
            filtered_candidates=["worker-a"],
            scoring_breakdown={"worker-a": {"total": 0.9}},
            selected_worker="worker-a",
            selected_skill_or_plan="code.implement",
            strategy="single_worker",
            reasoning="best fit",
            governance_snapshot={"control_mode": "brain_first"},
            mission_id="m-1",
            correlation_id="corr-42",
            created_by="tester",
        )

    monkeypatch.setattr(da_service.DomainAgentService, "get_purpose_evaluation", _fake_get_purpose)
    monkeypatch.setattr(da_service.DomainAgentService, "get_routing_decision", _fake_get_routing)

    payload = {
        "decomposition": {
            "domain_key": "programming",
            "task_name": "Build endpoint",
            "available_capabilities": ["code.write", "code.test"],
        },
        "decision_context": {
            "decision_context_id": "ctx-42",
            "tenant_id": "tenant-a",
            "requested_by": "tester",
            "request_channel": "api",
            "mission_id": "m-1",
            "intent_summary": "Ship feature",
            "requested_autonomy_level": "high",
            "sensitivity_class": "standard",
            "context": {},
            "correlation_id": "corr-42",
        },
        "purpose_evaluation_id": "pe-1",
        "routing_decision_id": "rd-1",
        "execute_now": False,
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/prepare-skill-runs", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert len(body["run_drafts"]) >= 1
    draft = body["run_drafts"][0]
    assert draft["decision_context_id"] == "ctx-42"
    assert draft["purpose_evaluation_id"] == "pe-1"
    assert draft["routing_decision_id"] == "rd-1"


def test_prepare_skill_runs_gates_execute_for_human_required_routing(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    from types import SimpleNamespace

    from app.modules.domain_agents import service as da_service

    async def _fake_get_routing(self, db, *, routing_decision_id: str, tenant_id: str | None):
        _ = self
        _ = db
        _ = routing_decision_id
        _ = tenant_id
        return SimpleNamespace(
            id="rd-1",
            tenant_id="tenant-a",
            decision_context_id="ctx-99",
            task_profile_id="task-1",
            purpose_evaluation_id="pe-1",
            worker_candidates=["worker-a"],
            filtered_candidates=["worker-a"],
            scoring_breakdown={},
            selected_worker="worker-a",
            selected_skill_or_plan="code.implement",
            strategy="single_worker",
            reasoning="gated",
            governance_snapshot={"control_mode": "human_required"},
            mission_id="m-1",
            correlation_id="corr-99",
            created_by="tester",
        )

    monkeypatch.setattr(da_service.DomainAgentService, "get_routing_decision", _fake_get_routing)

    payload = {
        "decomposition": {
            "domain_key": "programming",
            "task_name": "Build endpoint",
            "available_capabilities": ["code.write", "code.test"],
        },
        "routing_decision_id": "rd-1",
        "execute_now": True,
    }

    with override_auth_principal(client, build_principal("operator")):
        response = client.post("/api/domain-agents/prepare-skill-runs", json=payload)

    assert response.status_code == 409
    assert "requires human review" in response.json()["detail"]


def test_routing_memory_rebuild_endpoint(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    from app.modules.domain_agents import service as da_service

    async def _fake_rebuild(self, db, *, tenant_id, task_profile_id, principal, limit):
        _ = self
        _ = db
        _ = tenant_id
        _ = principal
        _ = limit
        return {
            "id": "rm-1",
            "tenant_id": "tenant-a",
            "task_profile_id": task_profile_id,
            "task_profile_fingerprint": "task:task-1:abc",
            "worker_outcome_history": [],
            "summary_metrics": {"sample_size": 0},
            "routing_lessons": ["none"],
            "sample_size": 0,
            "derived_from_runs": [],
        }

    monkeypatch.setattr(
        da_service.DomainAgentService,
        "rebuild_routing_memory_projection",
        _fake_rebuild,
    )

    with override_auth_principal(client, build_principal("operator")):
        response = client.post(
            "/api/domain-agents/routing-memory/rebuild",
            json={"task_profile_id": "task-1", "limit": 100},
        )

    assert response.status_code == 200
    assert response.json()["id"] == "rm-1"


def test_routing_memory_replay_endpoint(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    from app.modules.domain_agents import service as da_service

    async def _fake_replay(self, db, *, tenant_id, task_profile_id):
        _ = self
        _ = db
        _ = tenant_id
        return {
            "task_profile_id": task_profile_id,
            "sample_size": 10,
            "baseline_worker": "worker-a",
            "recommended_worker": "worker-b",
            "baseline_success_rate": 0.8,
            "recommended_success_rate": 0.9,
            "baseline_avg_cost": 1.0,
            "recommended_avg_cost": 0.9,
            "recommendation_reason": "better success with lower cost",
        }

    monkeypatch.setattr(
        da_service.DomainAgentService,
        "replay_routing_comparison",
        _fake_replay,
    )

    with override_auth_principal(client, build_principal("operator")):
        response = client.get("/api/domain-agents/routing-memory/replay/task-1")

    assert response.status_code == 200
    assert response.json()["recommended_worker"] == "worker-b"


def test_routing_adaptation_proposal_endpoint(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    from app.modules.domain_agents import service as da_service

    async def _fake_proposal(
        self,
        db,
        *,
        tenant_id,
        principal,
        task_profile_id,
        routing_memory_id,
        proposed_changes,
        sandbox_validated,
        validation_evidence,
    ):
        _ = self
        _ = db
        _ = tenant_id
        _ = principal
        _ = routing_memory_id
        _ = proposed_changes
        _ = sandbox_validated
        _ = validation_evidence
        return {
            "id": "ra-1",
            "tenant_id": "tenant-a",
            "task_profile_id": task_profile_id,
            "routing_memory_id": None,
            "proposed_changes": {"weights": {"capability_fit": 1.1}},
            "status": "review",
            "sandbox_validated": True,
            "validation_evidence": {"replay": "ok"},
            "block_reason": None,
            "created_by": "tester",
        }

    monkeypatch.setattr(
        da_service.DomainAgentService,
        "create_routing_adaptation_proposal",
        _fake_proposal,
    )

    with override_auth_principal(client, build_principal("admin")):
        response = client.post(
            "/api/domain-agents/routing-adaptations/proposals",
            json={
                "task_profile_id": "task-1",
                "proposed_changes": {"weights": {"capability_fit": 1.1}},
                "sandbox_validated": True,
                "validation_evidence": {"replay": "ok"},
            },
        )

    assert response.status_code == 201
    assert response.json()["status"] == "review"


def test_list_routing_adaptation_proposals_endpoint(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    from app.modules.domain_agents import service as da_service

    async def _fake_list(self, db, *, tenant_id, task_profile_id=None, status=None, limit=100):
        _ = self
        _ = db
        _ = tenant_id
        _ = task_profile_id
        _ = status
        _ = limit
        return [
            {
                "id": "ra-1",
                "tenant_id": "tenant-a",
                "task_profile_id": "task-1",
                "routing_memory_id": None,
                "proposed_changes": {},
                "status": "review",
                "sandbox_validated": True,
                "validation_evidence": {},
                "block_reason": None,
                "created_by": "tester",
            }
        ]

    monkeypatch.setattr(
        da_service.DomainAgentService,
        "list_routing_adaptation_proposals",
        _fake_list,
    )

    with override_auth_principal(client, build_principal("operator")):
        response = client.get("/api/domain-agents/routing-adaptations/proposals")

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_transition_routing_adaptation_proposal_endpoint(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    from app.modules.domain_agents import service as da_service

    async def _fake_transition(
        self,
        db,
        *,
        proposal_id,
        tenant_id,
        principal,
        status,
        block_reason,
        validation_evidence_patch,
    ):
        _ = self
        _ = db
        _ = proposal_id
        _ = tenant_id
        _ = principal
        _ = block_reason
        _ = validation_evidence_patch
        return {
            "id": "ra-1",
            "tenant_id": "tenant-a",
            "task_profile_id": "task-1",
            "routing_memory_id": None,
            "proposed_changes": {},
            "status": status,
            "sandbox_validated": True,
            "validation_evidence": {},
            "block_reason": None,
            "created_by": "tester",
        }

    monkeypatch.setattr(
        da_service.DomainAgentService,
        "transition_routing_adaptation_proposal",
        _fake_transition,
    )

    with override_auth_principal(client, build_principal("admin")):
        response = client.post(
            "/api/domain-agents/routing-adaptations/proposals/ra-1/transition",
            json={"status": "approved", "validation_evidence_patch": {"review": "ok"}},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_simulate_routing_adaptation_endpoint(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    from app.modules.domain_agents import service as da_service

    async def _fake_simulate(self, db, *, tenant_id, task_profile_id, proposed_changes):
        _ = self
        _ = db
        _ = tenant_id
        _ = proposed_changes
        return {
            "task_profile_id": task_profile_id,
            "sandbox_mode": True,
            "baseline_worker": "worker-a",
            "recommended_worker": "worker-b",
            "baseline_success_rate": 0.8,
            "recommended_success_rate": 0.9,
            "baseline_avg_cost": 1.0,
            "recommended_avg_cost": 0.9,
            "projected_delta": {"success_rate_gain": 0.1},
            "notes": ["ok"],
        }

    monkeypatch.setattr(
        da_service.DomainAgentService,
        "simulate_routing_adaptation",
        _fake_simulate,
    )

    with override_auth_principal(client, build_principal("operator")):
        response = client.post(
            "/api/domain-agents/routing-adaptations/simulate",
            json={"task_profile_id": "task-1", "proposed_changes": {"weights": {"a": 1}}},
        )

    assert response.status_code == 200
    assert response.json()["projected_delta"]["success_rate_gain"] == 0.1
