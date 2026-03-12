from __future__ import annotations

import pytest

from app.modules.domain_agents.schemas import (
    DomainAgentConfig,
    DomainBudgetProfile,
    DomainDecompositionRequest,
    DomainResolution,
    DomainReviewOutcome,
    SpecialistCandidate,
    DomainStatus,
)
from app.modules.domain_agents.service import (
    DomainAgentRegistry,
    DomainAgentService,
    get_domain_agent_service,
)


def test_domain_agent_service_decompose_selects_allowed_capabilities() -> None:
    registry = DomainAgentRegistry()
    registry.register(
        DomainAgentConfig(
            domain_key="programming",
            display_name="Programming",
            status=DomainStatus.ACTIVE,
            allowed_skill_keys=["code.implement"],
            allowed_capability_keys=["code.write", "code.test"],
        )
    )
    service = DomainAgentService(registry)

    resolution = service.decompose(
        DomainDecompositionRequest(
            domain_key="programming",
            task_name="Implement endpoint",
            available_capabilities=["code.write", "code.review", "code.test"],
        )
    )

    assert resolution.domain_key == "programming"
    assert resolution.selected_capability_keys == ["code.write", "code.test"]
    assert resolution.requires_supervisor_review is False


def test_programming_domain_default_has_impl_and_tests() -> None:
    service = get_domain_agent_service()

    resolution = service.decompose(
        DomainDecompositionRequest(
            domain_key="programming",
            task_name="Build API endpoint",
            task_description="Create feature endpoint",
            available_capabilities=["code.write", "code.test", "code.analyze"],
        )
    )

    assert "code.implement" in resolution.selected_skill_keys
    assert "code.test" in resolution.selected_skill_keys


def test_programming_domain_escalates_high_risk_keywords() -> None:
    service = get_domain_agent_service()

    resolution = service.decompose(
        DomainDecompositionRequest(
            domain_key="programming",
            task_name="Update production payment auth flow",
            available_capabilities=["code.write", "code.test"],
        )
    )

    decision = service.review_resolution(resolution)
    assert decision.outcome == DomainReviewOutcome.ESCALATE
    assert decision.should_escalate is True


def test_programming_review_requires_test_skill() -> None:
    service = get_domain_agent_service()

    decision = service.review_resolution(
        DomainResolution(
            domain_key="programming",
            confidence=0.8,
            selected_skill_keys=["code.implement"],
            selected_capability_keys=["code.write"],
            selected_specialists=[],
            decomposition_notes=[],
            requires_supervisor_review=False,
        )
    )

    assert decision.outcome == DomainReviewOutcome.REVISE


def test_domain_agent_service_denies_blocked_domain() -> None:
    registry = DomainAgentRegistry()
    registry.register(
        DomainAgentConfig(
            domain_key="finance",
            display_name="Finance",
            status=DomainStatus.BLOCKED,
            allowed_skill_keys=["finance.plan"],
            allowed_capability_keys=["finance.model"],
        )
    )
    service = DomainAgentService(registry)

    with pytest.raises(PermissionError):
        service.decompose(
            DomainDecompositionRequest(
                domain_key="finance",
                task_name="Create strategy",
                available_capabilities=["finance.model"],
            )
        )


def test_domain_agent_review_escalates_when_resolution_is_gated() -> None:
    registry = DomainAgentRegistry()
    service = DomainAgentService(registry)

    from app.modules.domain_agents.schemas import DomainResolution

    decision = service.review_resolution(
        DomainResolution(
            domain_key="research",
            confidence=0.4,
            selected_skill_keys=[],
            selected_capability_keys=[],
            selected_specialists=[],
            decomposition_notes=[],
            requires_supervisor_review=True,
        )
    )

    assert decision.outcome == DomainReviewOutcome.ESCALATE
    assert decision.should_escalate is True


def test_programming_decompose_limits_specialists_by_budget() -> None:
    registry = DomainAgentRegistry()
    registry.register(
        DomainAgentConfig(
            domain_key="programming",
            display_name="Programming",
            status=DomainStatus.ACTIVE,
            allowed_skill_keys=["code.implement", "code.test", "code.review"],
            allowed_capability_keys=["code.write", "code.test", "code.analyze"],
            allowed_specialist_roles=[
                "runtime-engineer",
                "verification-engineer",
                "security-reviewer",
            ],
            budget_profile=DomainBudgetProfile(max_specialists_per_task=2),
        )
    )
    service = DomainAgentService(registry)

    resolution = service.decompose(
        DomainDecompositionRequest(
            domain_key="programming",
            task_name="Implement endpoint",
            task_description="Build with tests and review",
            available_capabilities=["code.write", "code.test"],
        )
    )

    assert len(resolution.selected_specialists) == 2
    assert resolution.selected_specialists[0].role == "runtime-engineer"
    assert resolution.selected_specialists[1].role == "verification-engineer"


def test_decompose_with_config_accepts_resolved_specialists_override() -> None:
    registry = DomainAgentRegistry()
    config = DomainAgentConfig(
        domain_key="programming",
        display_name="Programming",
        status=DomainStatus.ACTIVE,
        allowed_skill_keys=["code.implement", "code.test"],
        allowed_capability_keys=["code.write", "code.test"],
        allowed_specialist_roles=["runtime-engineer"],
    )
    registry.register(config)
    service = DomainAgentService(registry)

    injected_specialists = [
        SpecialistCandidate(
            agent_id="agent-42",
            role="runtime-engineer",
            score=0.9,
            reasons=["resolved from agent registry"],
        )
    ]

    resolution = service.decompose_with_config(
        DomainDecompositionRequest(
            domain_key="programming",
            task_name="Implement endpoint",
            available_capabilities=["code.write", "code.test"],
        ),
        config,
        selected_specialists=injected_specialists,
    )

    assert len(resolution.selected_specialists) == 1
    assert resolution.selected_specialists[0].agent_id == "agent-42"
