"""
IR Router Extension for WebGenesis Pipeline (Sprint 10)

Extends pipeline router with IR governance support (opt-in, backwards compatible).
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from backend.app.modules.ir_governance import IR, ir_hash
from backend.app.modules.autonomous_pipeline.schemas import (
    ExecutionGraphSpec,
    ExecutionGraphResult,
)
from backend.app.modules.autonomous_pipeline.ir_config import get_ir_config
from backend.app.modules.autonomous_pipeline.ir_gateway import (
    get_ir_gateway,
    IRGatewayBlockedError,
)
from backend.app.modules.autonomous_pipeline.ir_mapper import get_ir_mapper
from backend.app.modules.autonomous_pipeline.execution_graph import create_execution_graph
from backend.app.modules.autonomous_pipeline.evidence_generator import (
    get_evidence_generator,
)
from backend.app.modules.autonomous_pipeline.ir_evidence import get_ir_evidence_generator
from backend.app.modules.ir_governance.diff_audit import get_diff_audit_gate


# Sprint 10: Extended request schemas with IR support
class PipelineExecuteRequest(BaseModel):
    """Request for pipeline execution with optional IR."""
    graph_spec: ExecutionGraphSpec = Field(..., description="Execution graph specification")
    tenant_id: str = Field(default="default", description="Tenant identifier")
    ir: Optional[IR] = Field(None, description="Optional IR for governance (Sprint 10)")
    approval_token: Optional[str] = Field(None, description="Approval token (if IR ESCALATE)")
    execute: bool = Field(default=False, description="Execute (true) or dry-run (false)")


class PipelineDryRunRequest(BaseModel):
    """Request for pipeline dry-run with optional IR."""
    graph_spec: ExecutionGraphSpec = Field(..., description="Execution graph specification")
    tenant_id: str = Field(default="default", description="Tenant identifier")
    ir: Optional[IR] = Field(None, description="Optional IR for governance (Sprint 10)")


# Router extension
router_extension = APIRouter(prefix="/api/pipeline", tags=["autonomous-pipeline-ir"])


@router_extension.post("/execute-ir")
async def execute_pipeline_with_ir(request: PipelineExecuteRequest) -> Dict[str, Any]:
    """
    Execute pipeline with IR governance (Sprint 10).

    **NEW in Sprint 10:** IR governance integration.

    **Execution Modes (based on WEBGENESIS_IR_MODE):**
    - `off`: IR disabled, execute without governance
    - `opt_in`: IR optional, validate if provided
    - `required`: IR mandatory, reject if not provided

    **Dry-Run First (WEBGENESIS_DRY_RUN_DEFAULT=true):**
    - If execute=false → dry-run (safe, no side effects)
    - If execute=true → live execution (real operations)

    **Example Request (with IR):**
    ```json
    {
      "graph_spec": { ...graph... },
      "tenant_id": "tenant_demo",
      "ir": {
        "tenant_id": "tenant_demo",
        "steps": [
          {
            "action": "webgenesis.site.create",
            "provider": "webgenesis.v1",
            "resource": "site:example.com",
            "params": {...},
            "idempotency_key": "graph_123:node_0"
          }
        ]
      },
      "approval_token": "TOKEN_IF_ESCALATE",
      "execute": false
    }
    ```

    **Example Request (legacy, no IR):**
    ```json
    {
      "graph_spec": { ...graph... },
      "tenant_id": "tenant_demo",
      "execute": false
    }
    ```
    """
    config = get_ir_config()
    gateway = get_ir_gateway()
    mapper = get_ir_mapper()

    logger.info(
        f"[PipelineExecuteIR] Request received: tenant={request.tenant_id}, "
        f"ir_provided={request.ir is not None}, execute={request.execute}, "
        f"ir_mode={config.ir_mode}"
    )

    # Step 1: IR Gateway validation
    legacy_request = request.ir is None
    gateway_result = gateway.validate_request(
        ir=request.ir,
        approval_token=request.approval_token,
        legacy_request=legacy_request,
    )

    # Emit gateway audit events
    for event in gateway_result.audit_events:
        logger.info(f"[Audit] {event}")

    # Block if gateway denies
    if not gateway_result.allowed:
        logger.error(f"[PipelineExecuteIR] Request blocked: {gateway_result.block_reason}")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "IR governance blocked execution",
                "reason": gateway_result.block_reason,
                "gateway_result": gateway_result.to_dict(),
            },
        )

    # Step 2: IR → Graph mapping (if IR provided)
    if request.ir:
        logger.info("[PipelineExecuteIR] Mapping IR to graph nodes")

        # Attach IR metadata to graph nodes
        request.graph_spec = mapper.attach_ir_metadata_to_nodes(
            graph_spec=request.graph_spec,
            ir=request.ir,
        )

    # Step 3: Diff-Audit (if IR provided)
    diff_audit_result = None
    if request.ir:
        logger.info("[PipelineExecuteIR] Running diff-audit (IR ↔ DAG)")
        diff_audit_gate = get_diff_audit_gate()

        # Build DAG nodes from graph_spec
        dag_nodes = []
        for node_spec in request.graph_spec.nodes:
            dag_node = {
                "ir_step_id": node_spec.executor_params.get("ir_step_id"),
                "ir_step_hash": node_spec.executor_params.get("ir_step_hash"),
            }
            dag_nodes.append(dag_node)

        diff_audit_result = diff_audit_gate.audit_ir_dag_mapping(request.ir, dag_nodes)

        if not diff_audit_result.success:
            logger.error(
                f"[PipelineExecuteIR] Diff-audit FAILED: "
                f"missing={diff_audit_result.missing_ir_steps}, "
                f"extra={diff_audit_result.extra_dag_nodes}, "
                f"mismatches={len(diff_audit_result.hash_mismatches)}"
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Diff-audit failed: IR ↔ DAG mismatch",
                    "diff_audit_result": diff_audit_result.model_dump(),
                },
            )

        logger.info("[PipelineExecuteIR] Diff-audit PASSED")

    # Step 4: Force dry-run if execute=false or config default
    is_dry_run = not request.execute or config.dry_run_default
    request.graph_spec.dry_run = is_dry_run

    logger.info(
        f"[PipelineExecuteIR] Execution mode: dry_run={is_dry_run} "
        f"(execute={request.execute}, config_default={config.dry_run_default})"
    )

    # Step 5: Create execution graph
    graph = create_execution_graph(request.graph_spec)

    # Step 6: Execute graph
    logger.info(f"[PipelineExecuteIR] Executing graph: {request.graph_spec.graph_id}")
    execution_result = await graph.execute()

    logger.info(
        f"[PipelineExecuteIR] Execution completed: "
        f"success={execution_result.success}, status={execution_result.status}"
    )

    # Step 7: Generate evidence pack
    evidence_generator = get_evidence_generator()
    base_evidence = evidence_generator.generate_evidence_pack(
        execution_result=execution_result,
        graph_spec=request.graph_spec,
    )

    # Step 8: Generate IR evidence pack (if IR used)
    ir_evidence = None
    if request.ir:
        ir_evidence_generator = get_ir_evidence_generator()
        ir_evidence = ir_evidence_generator.generate_ir_evidence_pack(
            base_evidence=base_evidence,
            ir=request.ir,
            ir_validation=gateway_result.validation_result,
            approval_id=gateway_result.approval_result.approval_id if gateway_result.approval_result else None,
            diff_audit_result=diff_audit_result,
        )

        # Save IR evidence pack
        ir_evidence_path = ir_evidence_generator.save_ir_evidence_pack(ir_evidence)
        logger.info(f"[PipelineExecuteIR] IR evidence pack saved: {ir_evidence_path}")

    # Step 9: Build response
    response = {
        "execution_result": execution_result.model_dump(),
        "base_evidence": base_evidence.model_dump(),
        "ir_evidence": ir_evidence.model_dump() if ir_evidence else None,
        "gateway_result": gateway_result.to_dict(),
        "diff_audit_result": diff_audit_result.model_dump() if diff_audit_result else None,
        "execution_mode": {
            "is_dry_run": is_dry_run,
            "execute_requested": request.execute,
            "config_dry_run_default": config.dry_run_default,
        },
    }

    logger.info(
        f"[PipelineExecuteIR] Request completed successfully: "
        f"dry_run={is_dry_run}, ir_used={request.ir is not None}"
    )

    return response


@router_extension.get("/ir/config")
async def get_ir_config_endpoint() -> Dict[str, Any]:
    """
    Get current IR configuration.

    Returns IR mode, approval tier, and other settings.
    """
    config = get_ir_config()
    return {
        "ir_mode": config.ir_mode,
        "require_approval_tier": config.require_approval_tier,
        "max_budget_cents": config.max_budget_cents,
        "dry_run_default": config.dry_run_default,
        "is_ir_enabled": config.is_ir_enabled(),
        "is_ir_required": config.is_ir_required(),
    }
