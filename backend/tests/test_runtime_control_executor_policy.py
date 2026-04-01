from __future__ import annotations

from app.modules.runtime_control.schemas import RuntimeDecisionContext
from app.modules.runtime_control.service import RuntimeControlResolverService


def _context() -> RuntimeDecisionContext:
    return RuntimeDecisionContext(
        tenant_id="tenant-a",
        environment="local",
        mission_type="delivery",
        skill_type="execute",
        risk_score=0.1,
        budget_state={},
        system_health={},
        feature_context={},
    )


def test_is_executor_allowed_respects_external_toggle() -> None:
    service = RuntimeControlResolverService()
    cfg = service._hard_defaults()  # noqa: SLF001
    assert service.is_executor_allowed(cfg, "openclaw") is True
    assert service.is_executor_allowed(cfg, "paperclip") is False


def test_resolve_falls_back_when_default_executor_disabled() -> None:
    service = RuntimeControlResolverService()
    ctx = _context().model_copy(
        update={
            "feature_context": {
                "manual_overrides": [
                    {
                        "key": "workers.selection.default_executor",
                        "value": "paperclip",
                        "reason": "test override",
                    }
                ]
            }
        }
    )

    decision = service.resolve(ctx)

    assert decision.selected_worker == "miniworker"
    assert decision.selected_route == "skillrun.bridge"
