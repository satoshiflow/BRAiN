from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.core.database import get_db
from app.modules.course_factory.router import router as course_factory_router
from app.modules.webgenesis.router import router as webgenesis_router


def _principal() -> Principal:
    return Principal(
        principal_id="operator-1",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator",
        roles=["operator", "admin"],
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


VALID_WEBGENESIS_SPEC = {
    "spec": {
        "spec_version": "1.0.0",
        "name": "guarded-site",
        "domain": "guarded.example.com",
        "locale_default": "en",
        "locales": ["en"],
        "template": "static_html",
        "pages": [
            {
                "slug": "home",
                "title": "Home",
                "description": "Guard test",
                "sections": [
                    {
                        "section_id": "hero",
                        "type": "hero",
                        "title": "Welcome",
                        "content": "Guard",
                        "data": {},
                        "order": 0,
                    }
                ],
                "layout": "default",
            }
        ],
        "theme": {
            "colors": {
                "primary": "#3B82F6",
                "secondary": "#8B5CF6",
                "accent": "#10B981",
                "background": "#FFFFFF",
                "text": "#1F2937",
            },
            "typography": {
                "font_family": "Inter, system-ui, sans-serif",
                "base_size": "16px",
            },
        },
        "seo": {
            "title": "Guarded Site",
            "description": "Lifecycle guard test",
            "keywords": ["guard"],
            "twitter_card": "summary",
        },
        "deploy": {
            "target": "compose",
            "healthcheck_path": "/",
            "ssl_enabled": False,
        },
    }
}


def test_webgenesis_spec_submit_blocked_when_deprecated(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(webgenesis_router)
    fake_db = object()
    principal = _principal()

    async def _db_override():
        yield fake_db

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.webgenesis.router", fromlist=["router"])
    monkeypatch.setenv("BRAIN_TEST_COMPAT_MODE", "false")

    class FakeLifecycleService:
        async def get_module(self, db, module_id):
            assert db is fake_db
            assert module_id == "webgenesis"
            return SimpleNamespace(lifecycle_status="deprecated")

    class FailIfCalledService:
        def store_spec(self, spec):  # pragma: no cover
            raise AssertionError("store_spec should not be called when lifecycle blocks writes")

    monkeypatch.setattr(route_module, "get_module_lifecycle_service", lambda: FakeLifecycleService())
    monkeypatch.setattr(route_module, "get_webgenesis_service", lambda: FailIfCalledService())

    response = client.post("/api/webgenesis/spec", json=VALID_WEBGENESIS_SPEC)
    assert response.status_code == 409


def test_course_factory_enhance_blocked_when_retired(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(course_factory_router)
    fake_db = object()
    principal = _principal()

    async def _db_override():
        yield fake_db

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.course_factory.router", fromlist=["router"])
    monkeypatch.setenv("BRAIN_TEST_COMPAT_MODE", "false")

    class FakeLifecycleService:
        async def get_module(self, db, module_id):
            assert db is fake_db
            assert module_id == "course_factory"
            return SimpleNamespace(lifecycle_status="retired")

    class FailIfCalledService:
        async def enhance_content(self, request, lessons):  # pragma: no cover
            raise AssertionError("enhance_content should not be called when lifecycle blocks writes")

    monkeypatch.setattr(route_module, "get_module_lifecycle_service", lambda: FakeLifecycleService())
    monkeypatch.setattr(route_module, "get_course_factory_service_with_events", lambda request: FailIfCalledService())

    response = client.post(
        "/api/course-factory/enhance",
        json={
            "course_id": "course-1",
            "lesson_ids": ["lesson-1"],
            "enhancement_types": ["examples"],
            "dry_run": True,
        },
    )
    assert response.status_code == 409
