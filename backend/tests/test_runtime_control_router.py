from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, get_current_principal, require_auth
from app.core.database import get_db
from app.modules.runtime_control import router as runtime_control_router_module
from app.modules.runtime_control.router import router as runtime_control_router


def _principal(*roles: str) -> Principal:
    return Principal(
        principal_id="runtime-control-user",
        principal_type=PrincipalType.HUMAN,
        email="runtime-control@example.com",
        name="Runtime Control User",
        roles=list(roles),
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


@contextmanager
def _override_principal(client: TestClient, principal: Principal):
    async def _principal_override() -> Principal:
        return principal

    app = client.app
    app.dependency_overrides[require_auth] = _principal_override
    app.dependency_overrides[get_current_principal] = _principal_override
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_auth, None)
        app.dependency_overrides.pop(get_current_principal, None)


@contextmanager
def _override_unauthorized(client: TestClient):
    async def _unauthorized() -> Principal:
        raise HTTPException(status_code=401, detail="Authentication required")

    app = client.app
    app.dependency_overrides[require_auth] = _unauthorized
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_auth, None)


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(runtime_control_router)

    async def _fake_db():
        yield object()

    app.dependency_overrides[get_db] = _fake_db
    return app


def test_runtime_control_requires_authentication() -> None:
    client = TestClient(_build_test_app())
    with _override_unauthorized(client):
        response = client.get("/api/runtime-control/info")
    assert response.status_code == 401


def test_resolve_applies_risk_policy_and_emergency_override() -> None:
    class _FakeService:
        OVERRIDE_PRIORITY = [
            "emergency_override",
            "governor_override",
            "manual_approved_override",
            "policy_decision",
            "feature_flags",
            "registry_config",
            "hard_defaults",
        ]

        async def resolve_with_persisted_overrides(self, context, db):  # noqa: ANN001
            _ = (context, db)
            return SimpleNamespace(
                decision_id="rdec_test_1",
                effective_config={
                    "flags": {"safe_mode": True},
                    "limits": {"parallel": {"max_worker_tasks": 1}},
                },
                selected_model="llama3.2:latest",
                selected_worker="miniworker",
                selected_route="skillrun.bridge",
                applied_policies=[
                    {
                        "policy_id": "policy.risk.high",
                        "reason": "Risk score >= 0.85",
                        "effect": "force_local_provider_and_approval",
                    }
                ],
                applied_overrides=[],
                explain_trace=[],
                validation={"valid": True, "issues": []},
            )

    runtime_control_router_module.get_runtime_control_service = lambda: _FakeService()

    client = TestClient(_build_test_app())
    with _override_principal(client, _principal("operator")):
        response = client.post(
            "/api/runtime-control/resolve",
            json={
                "context": {
                    "environment": "local",
                    "mission_type": "delivery",
                    "skill_type": "execute",
                    "risk_score": 0.91,
                    "budget_state": {"remaining_credits": 50},
                    "system_health": {"safe_mode": True},
                    "feature_context": {},
                }
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_model"] == "llama3.2:latest"
    assert body["selected_worker"] == "miniworker"
    assert body["effective_config"]["flags"]["safe_mode"] is True
    assert body["effective_config"]["limits"]["parallel"]["max_worker_tasks"] == 1
    assert body["validation"]["valid"] is True
    assert any(item["policy_id"] == "policy.risk.high" for item in body["applied_policies"])


def test_resolve_applies_manual_override() -> None:
    class _FakeService:
        OVERRIDE_PRIORITY = [
            "emergency_override",
            "governor_override",
            "manual_approved_override",
            "policy_decision",
            "feature_flags",
            "registry_config",
            "hard_defaults",
        ]

        async def resolve_with_persisted_overrides(self, context, db):  # noqa: ANN001
            _ = (context, db)
            return SimpleNamespace(
                decision_id="rdec_test_2",
                effective_config={},
                selected_model="llama3.2:latest",
                selected_worker="openclaw",
                selected_route="skillrun.bridge",
                applied_policies=[],
                applied_overrides=[
                    {
                        "level": "manual_approved_override",
                        "key": "workers.selection.default_executor",
                        "value": "openclaw",
                        "reason": "manual execution lane",
                    }
                ],
                explain_trace=[],
                validation={"valid": True, "issues": []},
            )

    runtime_control_router_module.get_runtime_control_service = lambda: _FakeService()

    client = TestClient(_build_test_app())
    with _override_principal(client, _principal("admin")):
        response = client.post(
            "/api/runtime-control/resolve",
            json={
                "context": {
                    "feature_context": {
                        "manual_overrides": [
                            {
                                "key": "workers.selection.default_executor",
                                "value": "openclaw",
                                "reason": "manual execution lane",
                            }
                        ]
                    }
                }
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_worker"] == "openclaw"
    assert body["selected_route"] == "skillrun.bridge"
    assert any(item["level"] == "manual_approved_override" for item in body["applied_overrides"])
