from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("BRAIN_TEST_COMPAT_MODE", "true")
os.environ.setdefault("BRAIN_EVENTSTREAM_MODE", "degraded")

from app.core.auth_deps import (  # noqa: E402
    Principal,
    PrincipalType,
    get_current_principal,
    require_auth,
    require_operator,
)


def _build_test_principal() -> Principal:
    return Principal(
        principal_id="pytest-operator",
        principal_type=PrincipalType.HUMAN,
        email="pytest@example.com",
        name="Pytest Operator",
        roles=["operator", "admin"],
        scopes=["read", "write"],
        tenant_id="test-tenant",
    )


@pytest.fixture(scope="session")
def test_app():
    from backend.main import app

    async def _test_principal_override() -> Principal:
        return _build_test_principal()

    app.dependency_overrides[require_auth] = _test_principal_override
    app.dependency_overrides[require_operator] = _test_principal_override
    app.dependency_overrides[get_current_principal] = _test_principal_override

    return app


@pytest.fixture(scope="session")
def client(test_app):
    return TestClient(test_app)
