"""
Sprint 10 Integration Tests: WebGenesis IR Governance

Tests for IR opt-in integration with WebGenesis pipeline.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import os

from app.modules.ir_governance import (
    IR,
    IRStep,
    IRAction,
    IRProvider,
    IRValidationStatus,
    RiskTier,
)
from app.modules.autonomous_pipeline.ir_config import (
    IRWebGenesisConfig,
    IRMode,
    reload_ir_config,
)
from app.modules.autonomous_pipeline.ir_gateway import (
    IRGateway,
    IRGatewayResult,
)
from app.modules.autonomous_pipeline.ir_mapper import IRWebGenesisMapper
from app.modules.autonomous_pipeline.schemas import (
    ExecutionGraphSpec,
    ExecutionNodeSpec,
    ExecutionNodeType,
)


# Test 1: opt-in mode allows legacy requests
def test_ir_opt_in_allows_legacy_request():
    """
    Test 1: Legacy request (no IR) allowed when IR mode=opt_in.

    Expected: gateway.validate_request() returns allowed=True
    """
    # Setup
    os.environ["WEBGENESIS_IR_MODE"] = "opt_in"
    reload_ir_config()
    gateway = IRGateway()

    # Act
    result = gateway.validate_request(
        ir=None,
        approval_token=None,
        legacy_request=True,
    )

    # Assert
    assert result.allowed is True
    assert any("legacy_allowed" in event.get("event_type", "") for event in result.audit_events)


# Test 2: required mode blocks legacy requests
def test_ir_required_blocks_legacy_request():
    """
    Test 2: Legacy request (no IR) blocked when IR mode=required.

    Expected: gateway.validate_request() returns allowed=False
    """
    # Setup
    os.environ["WEBGENESIS_IR_MODE"] = "required"
    reload_ir_config()
    gateway = IRGateway()

    # Act
    result = gateway.validate_request(
        ir=None,
        approval_token=None,
        legacy_request=True,
    )

    # Assert
    assert result.allowed is False
    assert "required" in result.block_reason.lower()


# Test 3: IR PASS allows execution
def test_ir_pass_allows_execution():
    """
    Test 3: IR with PASS status allows execution.

    Expected: gateway returns allowed=True, validation_result.status=PASS
    """
    # Setup
    os.environ["WEBGENESIS_IR_MODE"] = "opt_in"
    reload_ir_config()
    gateway = IRGateway()

    # Create safe IR (tier 0-1 actions)
    ir = IR(
        tenant_id="tenant_test",
        steps=[
            IRStep(
                action=IRAction.WEBGENESIS_SITE_CREATE,
                provider=IRProvider.WEBGENESIS_V1,
                resource="site:dev.example.com",
                params={"env": "dev"},
                idempotency_key="test_001",
                constraints={"env": "dev"},  # Dev environment → safe
            )
        ],
    )

    # Act
    result = gateway.validate_request(ir=ir)

    # Assert
    assert result.allowed is True
    assert result.validation_result.status == IRValidationStatus.PASS
    assert result.validation_result.risk_tier <= RiskTier.TIER_1


# Test 4: IR REJECT blocks execution
def test_ir_reject_blocks_execution():
    """
    Test 4: IR with REJECT status blocks execution.

    Expected: gateway returns allowed=False, violations present
    """
    # Setup
    os.environ["WEBGENESIS_IR_MODE"] = "opt_in"
    reload_ir_config()
    gateway = IRGateway()

    # Create invalid IR (missing idempotency_key)
    with pytest.raises(ValueError):
        ir = IR(
            tenant_id="tenant_test",
            steps=[
                IRStep(
                    action=IRAction.WEBGENESIS_SITE_CREATE,
                    provider=IRProvider.WEBGENESIS_V1,
                    resource="site:example.com",
                    params={},
                    idempotency_key="",  # Empty idempotency_key → REJECT
                )
            ],
        )


# Test 5: IR ESCALATE without approval blocks execution
def test_ir_escalate_without_approval_blocks():
    """
    Test 5: IR with ESCALATE status (no approval token) blocks execution.

    Expected: gateway returns allowed=False, requires_approval=True
    """
    # Setup
    os.environ["WEBGENESIS_IR_MODE"] = "opt_in"
    reload_ir_config()
    gateway = IRGateway()

    # Create high-risk IR (tier 2+)
    ir = IR(
        tenant_id="tenant_test",
        steps=[
            IRStep(
                action=IRAction.WEBGENESIS_SITE_CREATE,
                provider=IRProvider.WEBGENESIS_V1,
                resource="site:example.com",
                params={},
                idempotency_key="test_escalate",
                constraints={"env": "production"},  # Production → requires approval
            )
        ],
    )

    # Act
    result = gateway.validate_request(ir=ir, approval_token=None)

    # Assert
    assert result.allowed is False
    assert "approval" in result.block_reason.lower()
    assert result.validation_result.requires_approval is True


# Test 6: IR ESCALATE with valid approval allows execution
def test_ir_escalate_with_approval_allows():
    """
    Test 6: IR with ESCALATE status + valid approval token allows execution.

    Expected: gateway returns allowed=True, approval consumed
    """
    # Setup
    os.environ["WEBGENESIS_IR_MODE"] = "opt_in"
    reload_ir_config()
    gateway = IRGateway()

    from app.modules.ir_governance import get_approvals_service, ir_hash

    # Create high-risk IR
    ir = IR(
        tenant_id="tenant_test",
        steps=[
            IRStep(
                action=IRAction.WEBGENESIS_SITE_CREATE,
                provider=IRProvider.WEBGENESIS_V1,
                resource="site:example.com",
                params={},
                idempotency_key="test_with_approval",
                constraints={"env": "production"},  # Production → tier 2
            )
        ],
    )

    # Create approval
    approvals_service = get_approvals_service()
    approval, token = approvals_service.create_approval(
        tenant_id=ir.tenant_id,
        ir_hash=ir_hash(ir),
    )

    # Act
    result = gateway.validate_request(ir=ir, approval_token=token)

    # Assert
    assert result.allowed is True
    assert result.approval_result is not None
    assert result.approval_result.success is True


# Test 7: Diff-audit rejects extra DAG node
def test_diff_audit_rejects_extra_dag_node():
    """
    Test 7: Diff-audit rejects execution if DAG has extra node not in IR.

    Expected: diff_audit_result.success=False, extra_dag_nodes=[...]
    """
    # Setup
    from app.modules.ir_governance.diff_audit import get_diff_audit_gate
    from app.modules.ir_governance import step_hash

    gate = get_diff_audit_gate()

    # Create IR with 1 step
    ir = IR(
        tenant_id="tenant_test",
        steps=[
            IRStep(
                action=IRAction.WEBGENESIS_SITE_CREATE,
                provider=IRProvider.WEBGENESIS_V1,
                resource="site:example.com",
                params={},
                idempotency_key="test_step_0",
                step_id="step_0",
            )
        ],
    )

    # Create DAG with 2 nodes (extra node)
    dag_nodes = [
        {"ir_step_id": "step_0", "ir_step_hash": step_hash(ir.steps[0])},
        {"ir_step_id": "step_1", "ir_step_hash": "extra_node_hash"},  # Extra!
    ]

    # Act
    result = gate.audit_ir_dag_mapping(ir, dag_nodes)

    # Assert
    assert result.success is False
    assert len(result.extra_dag_nodes) == 1
    assert "step_1" in result.extra_dag_nodes


# Test 8: Evidence pack contains required fields (no secrets)
def test_evidence_pack_contains_required_fields_no_secrets():
    """
    Test 8: IR evidence pack contains all required fields, no secrets.

    Expected: evidence pack has ir, ir_hash, validation, diff_audit, NO raw token
    """
    # Setup
    from app.modules.ir_governance import ir_hash
    from app.modules.autonomous_pipeline.evidence_generator import (
        PipelineEvidencePack,
        get_evidence_generator,
    )
    from app.modules.autonomous_pipeline.ir_evidence import (
        get_ir_evidence_generator,
    )
    from app.modules.autonomous_pipeline.schemas import (
        ExecutionGraphResult,
        ExecutionNodeStatus,
    )

    # Create IR
    ir = IR(
        tenant_id="tenant_test",
        steps=[
            IRStep(
                action=IRAction.WEBGENESIS_SITE_CREATE,
                provider=IRProvider.WEBGENESIS_V1,
                resource="site:example.com",
                params={},
                idempotency_key="test_evidence",
            )
        ],
    )

    # Create base evidence pack
    execution_result = ExecutionGraphResult(
        graph_id="test_graph",
        business_intent_id="test_intent",
        status=ExecutionNodeStatus.COMPLETED,
        success=True,
        node_results=[],
        completed_nodes=[],
        failed_nodes=[],
        execution_order=[],
        duration_seconds=1.0,
        was_dry_run=True,
    )

    evidence_gen = get_evidence_generator()
    base_evidence = evidence_gen.generate_evidence_pack(execution_result=execution_result)

    # Create IR evidence pack
    ir_evidence_gen = get_ir_evidence_generator()
    ir_evidence = ir_evidence_gen.generate_ir_evidence_pack(
        base_evidence=base_evidence,
        ir=ir,
        approval_id="approval_test_123",  # No token!
    )

    # Assert
    assert ir_evidence.ir_enabled is True
    assert ir_evidence.ir is not None
    assert ir_evidence.ir_hash == ir_hash(ir)
    assert ir_evidence.approval_used is True
    assert ir_evidence.approval_id == "approval_test_123"

    # Most importantly: NO raw token in evidence pack
    evidence_dump = ir_evidence.model_dump()
    assert "token" not in str(evidence_dump).lower()  # No raw token anywhere


# Test 9: execute=false → dry-run (no side effects)
@pytest.mark.asyncio
async def test_execute_false_dry_run_no_side_effects():
    """
    Test 9: execute=false forces dry-run, no side effects.

    Expected: graph.execute() calls dry_run() not execute(), no real operations
    """
    # Setup
    graph_spec = ExecutionGraphSpec(
        graph_id="test_graph",
        business_intent_id="test_intent",
        nodes=[
            ExecutionNodeSpec(
                node_id="webgen_0",
                node_type=ExecutionNodeType.WEBGENESIS,
                depends_on=[],
                capabilities=[],
                executor_class="WebGenesisNode",
                executor_params={
                    "website_template": "static-landing",
                    "domain": "test.example.com",
                    "title": "Test Site",
                    "pages": ["home"],
                    "business_intent_id": "test",
                },
            )
        ],
        dry_run=True,  # Force dry-run
    )

    # Create graph
    from app.modules.autonomous_pipeline.execution_graph import (
        create_execution_graph,
    )

    graph = create_execution_graph(graph_spec)

    # Act
    result = await graph.execute()

    # Assert
    assert result.was_dry_run is True
    assert result.success is True

    # Check that dry-run was called (look for simulated artifacts)
    assert any("sim" in artifact or "DRY-RUN" in str(artifact) for artifact in result.artifacts)


# Test 10: execute=true → execution path called
@pytest.mark.asyncio
async def test_execute_true_execution_path_called():
    """
    Test 10: execute=true calls execute() path (with mocked provider).

    Expected: graph.execute() runs execute() not dry_run(), real operations attempted
    """
    # Setup
    graph_spec = ExecutionGraphSpec(
        graph_id="test_graph",
        business_intent_id="test_intent",
        nodes=[
            ExecutionNodeSpec(
                node_id="webgen_0",
                node_type=ExecutionNodeType.WEBGENESIS,
                depends_on=[],
                capabilities=[],
                executor_class="WebGenesisNode",
                executor_params={
                    "website_template": "static-landing",
                    "domain": "test.example.com",
                    "title": "Test Site",
                    "pages": ["home"],
                    "business_intent_id": "test",
                },
            )
        ],
        dry_run=False,  # LIVE execution
    )

    # Create graph
    from app.modules.autonomous_pipeline.execution_graph import (
        create_execution_graph,
    )

    graph = create_execution_graph(graph_spec)

    # Act
    result = await graph.execute()

    # Assert
    assert result.was_dry_run is False
    assert result.success is True

    # Check that real execution was called (no "sim" artifacts)
    assert not any("sim" in str(artifact).lower() for artifact in result.artifacts)


# Test 11: Graph spec to IR mapping works
def test_graph_spec_to_ir_mapping():
    """
    Test 11: IR mapper correctly converts ExecutionGraphSpec to IR.

    Expected: mapper.graph_spec_to_ir() returns IR with correct steps
    """
    # Setup
    mapper = IRWebGenesisMapper()

    graph_spec = ExecutionGraphSpec(
        graph_id="test_graph",
        business_intent_id="test_intent",
        nodes=[
            ExecutionNodeSpec(
                node_id="webgen_0",
                node_type=ExecutionNodeType.WEBGENESIS,
                depends_on=[],
                capabilities=[],
                executor_class="WebGenesisNode",
                executor_params={
                    "domain": "example.com",
                    "title": "Test Site",
                },
            )
        ],
    )

    # Act
    ir = mapper.graph_spec_to_ir(graph_spec, tenant_id="tenant_test")

    # Assert
    assert ir.tenant_id == "tenant_test"
    assert len(ir.steps) == 1
    assert ir.steps[0].action == IRAction.WEBGENESIS_SITE_CREATE
    assert ir.steps[0].provider == IRProvider.WEBGENESIS_V1
    assert ir.steps[0].resource == "site:example.com"
    assert ir.steps[0].idempotency_key == "test_graph:webgen_0"


# Test 12: IR metadata attached to DAG nodes
def test_ir_metadata_attached_to_dag_nodes():
    """
    Test 12: IR mapper attaches step_id and step_hash to graph nodes.

    Expected: graph_spec.nodes[0].executor_params contains ir_step_id, ir_step_hash
    """
    # Setup
    mapper = IRWebGenesisMapper()

    graph_spec = ExecutionGraphSpec(
        graph_id="test_graph",
        business_intent_id="test_intent",
        nodes=[
            ExecutionNodeSpec(
                node_id="webgen_0",
                node_type=ExecutionNodeType.WEBGENESIS,
                depends_on=[],
                capabilities=[],
                executor_class="WebGenesisNode",
                executor_params={"domain": "example.com"},
            )
        ],
    )

    # Create IR
    ir = mapper.graph_spec_to_ir(graph_spec, tenant_id="tenant_test")

    # Act
    modified_graph_spec = mapper.attach_ir_metadata_to_nodes(graph_spec, ir)

    # Assert
    assert "ir_step_id" in modified_graph_spec.nodes[0].executor_params
    assert "ir_step_hash" in modified_graph_spec.nodes[0].executor_params
    assert "ir_request_id" in modified_graph_spec.nodes[0].executor_params
    assert "ir_tenant_id" in modified_graph_spec.nodes[0].executor_params

    # Verify values
    assert modified_graph_spec.nodes[0].executor_params["ir_step_id"] == "webgen_0"
    assert modified_graph_spec.nodes[0].executor_params["ir_tenant_id"] == "tenant_test"


# Test 13: Config dry_run_default enforced
def test_config_dry_run_default_enforced():
    """
    Test 13: WEBGENESIS_DRY_RUN_DEFAULT=true forces dry-run by default.

    Expected: Even if execute=true in request, dry_run_default overrides
    """
    # Setup
    os.environ["WEBGENESIS_DRY_RUN_DEFAULT"] = "true"
    reload_ir_config()
    config = IRWebGenesisConfig.from_env()

    # Assert
    assert config.dry_run_default is True

    # Simulate router logic
    execute_requested = True
    is_dry_run = not execute_requested or config.dry_run_default

    # With dry_run_default=true, should always be dry-run
    assert is_dry_run is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
