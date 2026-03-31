from __future__ import annotations

import pytest

from app.modules.domain_agents.schemas import (
    ControlMode,
    DecisionOutcome,
    DecisionContext,
    DomainAgentConfig,
    DomainBudgetProfile,
    DomainDecompositionRequest,
    DomainResolution,
    DomainReviewOutcome,
    RoutingDecisionResponse,
    SensitivityClass,
    SpecialistCandidate,
    DomainStatus,
    TaskProfile,
)
from app.modules.domain_agents.service import (
    DomainAgentRegistry,
    DomainAgentService,
    get_domain_agent_service,
)
from app.core.auth_deps import Principal, PrincipalType


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


def test_build_skill_run_drafts_carries_upstream_decision_artifacts() -> None:
    registry = DomainAgentRegistry()
    config = DomainAgentConfig(
        domain_key="programming",
        display_name="Programming",
        status=DomainStatus.ACTIVE,
        allowed_skill_keys=["code.implement", "code.test"],
        allowed_capability_keys=["code.write", "code.test"],
    )
    service = DomainAgentService(registry)

    request = DomainDecompositionRequest(
        domain_key="programming",
        task_name="Implement endpoint",
        mission_id="m-1",
        tenant_id="tenant-a",
    )
    resolution = DomainResolution(
        domain_key="programming",
        confidence=0.8,
        selected_skill_keys=["code.implement"],
        selected_capability_keys=["code.write"],
        selected_specialists=[],
        decomposition_notes=[],
        requires_supervisor_review=False,
    )

    drafts = service.build_skill_run_drafts(
        request=request,
        config=config,
        resolution=resolution,
        trigger_type="mission",
        mission_id="m-1",
        causation_id="cause-1",
        input_payload={"ticket": "ABC"},
        tenant_id="tenant-a",
        decision_context_id="ctx-1",
        purpose_evaluation_id="pe-1",
        routing_decision_id="rd-1",
        governance_snapshot={"control_mode": "brain_first"},
    )

    assert len(drafts) == 1
    assert drafts[0].decision_context_id == "ctx-1"
    assert drafts[0].purpose_evaluation_id == "pe-1"
    assert drafts[0].routing_decision_id == "rd-1"
    assert drafts[0].governance_snapshot["control_mode"] == "brain_first"


@pytest.mark.asyncio
async def test_route_programming_worker_prefers_miniworker_for_small_scoped_task(monkeypatch):
    service = get_domain_agent_service()

    async def _create_routing_decision(db, *, decision_context, decision, principal):  # noqa: ANN001
        _ = db, principal
        return RoutingDecisionResponse(
            id="route-1",
            tenant_id="tenant-a",
            decision_context_id=decision_context.decision_context_id,
            task_profile_id=decision.task_profile_id,
            purpose_evaluation_id=decision.purpose_evaluation_id,
            worker_candidates=decision.worker_candidates,
            filtered_candidates=decision.filtered_candidates,
            scoring_breakdown=decision.scoring_breakdown,
            selected_worker=decision.selected_worker,
            selected_skill_or_plan=decision.selected_skill_or_plan,
            strategy=decision.strategy,
            reasoning=decision.reasoning,
            governance_snapshot={},
            mission_id=None,
            correlation_id=None,
            created_by=principal.principal_id,
        )

    monkeypatch.setattr(service, "create_routing_decision", _create_routing_decision)

    decision = await service.route_programming_worker(
        db=None,  # type: ignore[arg-type]
        principal=Principal(
            principal_id="axe-user",
            principal_type=PrincipalType.HUMAN,
            name="AXE User",
            email="axe@example.com",
            roles=["operator"],
            scopes=["read", "write"],
            tenant_id="tenant-a",
        ),
        intent_summary="Replace line 3 with a guarded return",
        file_scope=["backend/app/modules/axe_worker_runs/service.py"],
        execution_mode="proposal",
        message_id="msg-1",
        session_id="sess-1",
        tenant_id="tenant-a",
    )

    assert decision.selected_worker == "miniworker"


def test_decide_programming_worker_prefers_opencode_for_sensitive_bounded_apply() -> None:
    service = get_domain_agent_service()

    decision = service._decide_programming_worker(
        decision_context=DecisionContext(
            decision_context_id="ctx-1",
            tenant_id="tenant-a",
            requested_by="axe-user",
            intent_summary="Apply security fix across auth and secrets paths",
            sensitivity_class=SensitivityClass.SENSITIVE,
            context={},
        ),
        task_profile=TaskProfile(
            task_profile_id="task-1",
            task_class="programming.worker_dispatch",
            description="Apply security fix across auth and secrets paths",
            constraints={"file_scope_count": 4, "execution_mode": "bounded_apply"},
        ),
        worker_pool=service._default_programming_worker_pool(),
        purpose_evaluation_id=None,
    )

    assert decision.selected_worker == "opencode"


def test_derive_control_mode_brain_first_for_standard_accept() -> None:
    mode = DomainAgentService._derive_control_mode(
        sensitivity_class=SensitivityClass.STANDARD,
        outcome=DecisionOutcome.ACCEPT,
        policy_allowed=True,
        policy_requires_audit=False,
    )
    assert mode == ControlMode.BRAIN_FIRST


def test_derive_control_mode_human_required_for_sensitive_core() -> None:
    mode = DomainAgentService._derive_control_mode(
        sensitivity_class=SensitivityClass.SENSITIVE_CORE,
        outcome=DecisionOutcome.ACCEPT,
        policy_allowed=True,
        policy_requires_audit=False,
    )
    assert mode == ControlMode.HUMAN_REQUIRED


def test_derive_control_mode_human_optional_when_policy_audit_required() -> None:
    mode = DomainAgentService._derive_control_mode(
        sensitivity_class=SensitivityClass.STANDARD,
        outcome=DecisionOutcome.ACCEPT,
        policy_allowed=True,
        policy_requires_audit=True,
    )
    assert mode == ControlMode.HUMAN_OPTIONAL
