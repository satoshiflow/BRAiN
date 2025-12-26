"""
Autonomous Pipeline Router (Sprint 8)

API endpoints for autonomous business pipeline.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from loguru import logger

from backend.app.modules.autonomous_pipeline.schemas import (
    BusinessIntentInput,
    ResolvedBusinessIntent,
    ExecutionGraphSpec,
    ExecutionGraphResult,
)
from backend.app.modules.autonomous_pipeline.intent_resolver import get_business_intent_resolver
from backend.app.modules.autonomous_pipeline.execution_graph import create_execution_graph
from backend.app.modules.autonomous_pipeline.evidence_generator import (
    get_evidence_generator,
    PipelineEvidencePack,
)


router = APIRouter(prefix="/api/pipeline", tags=["autonomous-pipeline"])


@router.get("/info")
async def get_pipeline_info():
    """
    Get pipeline system information.

    Returns basic information about the autonomous pipeline.
    """
    return {
        "name": "BRAiN Autonomous Business Pipeline",
        "version": "1.0.0",
        "description": "End-to-end autonomous business creation from intent to operation",
        "sprint": "Sprint 8",
        "features": [
            "Business intent resolution (deterministic)",
            "DAG-based execution orchestration",
            "Website generation (WebGenesis)",
            "DNS automation (Hetzner)",
            "Odoo module factory",
            "Dry-run simulation",
            "Evidence pack generation",
            "Full rollback support",
        ],
        "endpoints": [
            "POST /api/pipeline/intent/resolve - Resolve business intent",
            "POST /api/pipeline/execute - Execute pipeline graph",
            "POST /api/pipeline/dry-run - Simulate pipeline execution",
            "POST /api/pipeline/evidence/generate - Generate evidence pack",
        ],
    }


@router.post("/intent/resolve")
async def resolve_business_intent(
    intent_input: BusinessIntentInput
) -> ResolvedBusinessIntent:
    """
    Resolve business intent to structured plan.

    **Input:** Natural language business idea with context

    **Output:** Structured business intent with:
    - Business type classification
    - Monetization strategy
    - Risk assessment
    - Required modules (website, Odoo, etc.)
    - Custom module specifications
    - Governance checks

    **Example Request:**
    ```json
    {
      "vision": "Online consulting agency for digital transformation",
      "target_audience": "Mid-sized enterprises in DACH region",
      "region": "DACH",
      "monetization_type": "hourly_rate",
      "compliance_sensitivity": "high"
    }
    ```
    """
    try:
        resolver = get_business_intent_resolver()
        resolved_intent = resolver.resolve(intent_input)

        logger.info(
            f"Business intent resolved: {resolved_intent.intent_id} "
            f"(type={resolved_intent.business_type.value}, "
            f"risk={resolved_intent.risk_level.value})"
        )

        return resolved_intent

    except Exception as e:
        logger.error(f"Intent resolution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Intent resolution failed: {str(e)}")


@router.post("/execute")
async def execute_pipeline(
    graph_spec: ExecutionGraphSpec
) -> ExecutionGraphResult:
    """
    Execute pipeline graph (LIVE mode).

    **CAUTION:** This performs REAL operations:
    - Generates actual websites
    - Creates DNS records
    - Installs Odoo modules
    - May incur costs (DNS, hosting, etc.)

    **Governance:** All G1-G4 checks apply.

    **Example Request:**
    ```json
    {
      "graph_id": "graph_123",
      "business_intent_id": "intent_abc",
      "nodes": [
        {
          "node_id": "webgen",
          "node_type": "webgenesis",
          "depends_on": [],
          "capabilities": ["dry_run", "rollbackable"],
          "executor_class": "WebGenesisNode",
          "executor_params": {
            "website_template": "nextjs-business",
            "domain": "mycompany.com",
            "title": "My Company",
            "pages": ["home", "about", "contact"]
          }
        }
      ],
      "dry_run": false,
      "auto_rollback": true,
      "stop_on_first_error": true
    }
    ```
    """
    try:
        # Validate graph spec
        if not graph_spec.nodes:
            raise HTTPException(status_code=400, detail="Graph must have at least one node")

        # Create execution graph
        graph = create_execution_graph(graph_spec)

        # Execute graph
        logger.info(f"Executing pipeline graph: {graph_spec.graph_id} (LIVE mode)")
        result = await graph.execute()

        logger.info(
            f"Pipeline execution completed: {result.graph_id} "
            f"(status={result.status.value}, success={result.success})"
        )

        return result

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


@router.post("/dry-run")
async def dry_run_pipeline(
    graph_spec: ExecutionGraphSpec
) -> Dict[str, Any]:
    """
    Simulate pipeline execution (DRY-RUN mode).

    **Safe:** No real operations performed
    - No websites generated
    - No DNS records created
    - No Odoo modules installed
    - Returns simulated results

    **Use this to:**
    - Validate graph structure
    - Preview execution plan
    - Estimate complexity
    - Generate evidence pack without side effects

    **Example Request:**
    Same as `/execute` but will be forced to dry_run=True
    """
    try:
        # Force dry-run mode
        graph_spec.dry_run = True

        # Validate graph spec
        if not graph_spec.nodes:
            raise HTTPException(status_code=400, detail="Graph must have at least one node")

        # Create execution graph
        graph = create_execution_graph(graph_spec)

        # Execute graph in dry-run mode
        logger.info(f"Executing pipeline graph: {graph_spec.graph_id} (DRY-RUN mode)")
        result = await graph.execute()

        # Generate evidence pack
        evidence_generator = get_evidence_generator()
        evidence_pack = evidence_generator.generate_evidence_pack(
            execution_result=result,
            graph_spec=graph_spec,
        )

        logger.info(
            f"Dry-run completed: {result.graph_id} "
            f"(nodes={len(result.execution_order)}, evidence={evidence_pack.pack_id})"
        )

        return {
            "execution_result": result.model_dump(),
            "evidence_pack": evidence_pack.model_dump(),
            "dry_run_report": {
                "graph_id": result.graph_id,
                "nodes_simulated": len(result.execution_order),
                "estimated_duration": result.duration_seconds,
                "would_succeed": result.success,
                "simulated_artifacts": result.artifacts,
            },
        }

    except Exception as e:
        logger.error(f"Dry-run failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dry-run failed: {str(e)}")


@router.post("/evidence/generate")
async def generate_evidence_pack(
    execution_result: ExecutionGraphResult,
    business_intent: ResolvedBusinessIntent | None = None,
    graph_spec: ExecutionGraphSpec | None = None,
) -> PipelineEvidencePack:
    """
    Generate evidence pack from execution result.

    **Purpose:**
    - Audit trail for compliance
    - Proof of execution
    - Cryptographically verifiable (SHA256)

    **Evidence pack contains:**
    - Business intent (resolved)
    - Graph specification
    - Execution results (all nodes)
    - Governance decisions
    - Artifacts generated
    - Audit events
    - SHA256 content hash

    **Example Request:**
    ```json
    {
      "execution_result": { ... },
      "business_intent": { ... },
      "graph_spec": { ... }
    }
    ```
    """
    try:
        evidence_generator = get_evidence_generator()

        # Generate evidence pack
        evidence_pack = evidence_generator.generate_evidence_pack(
            execution_result=execution_result,
            business_intent=business_intent,
            graph_spec=graph_spec,
        )

        # Save to file
        evidence_path = evidence_generator.save_evidence_pack(evidence_pack)

        logger.info(
            f"Evidence pack generated and saved: {evidence_pack.pack_id} "
            f"(path={evidence_path})"
        )

        return evidence_pack

    except Exception as e:
        logger.error(f"Evidence pack generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Evidence pack generation failed: {str(e)}"
        )


@router.post("/evidence/verify")
async def verify_evidence_pack(
    evidence_pack: PipelineEvidencePack
) -> Dict[str, Any]:
    """
    Verify evidence pack integrity.

    Recomputes SHA256 hash and compares with stored hash.

    **Returns:**
    - valid: bool (hash matches)
    - expected_hash: str (original hash)
    - computed_hash: str (recomputed hash)
    """
    try:
        evidence_generator = get_evidence_generator()

        # Verify evidence pack
        is_valid = evidence_generator.verify_evidence_pack(evidence_pack)

        # Recompute hash for comparison
        original_hash = evidence_pack.content_hash
        evidence_pack.content_hash = ""
        computed_hash = evidence_generator._compute_content_hash(evidence_pack)

        return {
            "valid": is_valid,
            "pack_id": evidence_pack.pack_id,
            "expected_hash": original_hash,
            "computed_hash": computed_hash,
            "message": "Evidence pack is valid" if is_valid else "Evidence pack verification FAILED",
        }

    except Exception as e:
        logger.error(f"Evidence pack verification failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Evidence pack verification failed: {str(e)}"
        )
