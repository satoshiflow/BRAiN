"""E2E-style contract tests for auth refresh endpoint behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.auth import router as auth_router
from app.core.database import get_db
from app.schemas.auth import TokenPair
from app.services.auth_service import AuthService


@pytest.fixture
def auth_client() -> TestClient:
    app = FastAPI()
    app.include_router(auth_router)

    async def _fake_db():
        yield object()

    app.dependency_overrides[get_db] = _fake_db
    return TestClient(app)


def test_refresh_returns_503_when_database_is_unavailable(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _raise_db_error(*_args, **_kwargs):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(AuthService, "refresh_access_token", _raise_db_error)

    response = auth_client.post(
        "/api/auth/refresh",
        json={"refresh_token": "stale-refresh-token"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Authentication backend temporarily unavailable"
    }


def test_refresh_returns_rotated_token_pair(auth_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        AuthService,
        "refresh_access_token",
        AsyncMock(
            return_value=TokenPair(
                access_token="new-access-token",
                refresh_token="new-refresh-token",
                token_type="bearer",
                expires_in=900,
            )
        ),
    )

    response = auth_client.post(
        "/api/auth/refresh",
        json={"refresh_token": "valid-refresh-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "token_type": "bearer",
        "expires_in": 900,
    }
