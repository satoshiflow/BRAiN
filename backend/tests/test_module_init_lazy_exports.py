from __future__ import annotations

import importlib


def test_course_factory_init_exposes_service_symbols_lazily() -> None:
    module = importlib.import_module("app.modules.course_factory")

    assert callable(module.get_course_factory_service)
    assert module.CourseFactoryService is not None


def test_webgenesis_init_exposes_runtime_symbols_lazily() -> None:
    module = importlib.import_module("app.modules.webgenesis")

    assert callable(module.get_webgenesis_service)
    assert callable(module.get_release_manager)
    assert callable(module.get_ops_service)
    assert callable(module.get_health_service)
    assert callable(module.get_rollback_service)
    assert module.router is not None
