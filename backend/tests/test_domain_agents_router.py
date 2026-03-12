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
    from app.modules.domain_agents.schemas import DomainAgentConfig, DomainStatus

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
