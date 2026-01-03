"""
Pipeline Evidence Generator (Sprint 8.6)

Generates evidence packs for pipeline execution (dry-run and live).
Similar to Sprint 7 evidence export but tailored for autonomous pipeline.
"""

from typing import Dict, Any, Optional
import json
import hashlib
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
from loguru import logger

from app.modules.autonomous_pipeline.schemas import (
    ExecutionGraphResult,
    ResolvedBusinessIntent,
    ExecutionGraphSpec,
)

# Sprint 9-B: Run Contracts
try:
    from app.modules.autonomous_pipeline.run_contract import RunContract
    RUN_CONTRACT_AVAILABLE = True
except ImportError:
    RUN_CONTRACT_AVAILABLE = False
    RunContract = None


class PipelineEvidencePack(BaseModel):
    """Evidence pack for pipeline execution."""

    pack_id: str = Field(..., description="Unique evidence pack ID")
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Business intent
    business_intent_id: str = Field(..., description="Business intent ID")
    business_intent: Optional[ResolvedBusinessIntent] = Field(None, description="Resolved intent")

    # Graph specification
    graph_id: str = Field(..., description="Execution graph ID")
    graph_spec: Optional[ExecutionGraphSpec] = Field(None, description="Graph specification")

    # Execution result
    execution_result: ExecutionGraphResult = Field(..., description="Execution result")

    # Sprint 9-B: Run Contract
    run_contract: Optional[Any] = Field(None, description="Run contract (Sprint 9-B)")
    contract_id: Optional[str] = Field(None, description="Contract ID if available")

    # Summary
    summary: Dict[str, Any] = Field(..., description="Execution summary")

    # Governance decisions
    governance_decisions: list[Dict[str, Any]] = Field(
        default_factory=list,
        description="All governance checks performed"
    )

    # Artifacts
    artifacts: list[str] = Field(default_factory=list, description="Generated artifacts")

    # Audit events
    audit_events: list[Dict[str, Any]] = Field(default_factory=list, description="All audit events")

    # Verification
    content_hash: str = Field(..., description="SHA256 hash of pack content")
    is_dry_run: bool = Field(..., description="Whether this was a dry-run")

    class Config:
        json_schema_extra = {
            "example": {
                "pack_id": "evidence_pack_1234567890",
                "generated_at": "2025-12-26T12:00:00Z",
                "business_intent_id": "intent_abc123",
                "graph_id": "graph_xyz789",
                "execution_result": {"status": "completed", "success": True},
                "summary": {
                    "total_nodes": 5,
                    "completed_nodes": 5,
                    "failed_nodes": 0,
                    "duration_seconds": 123.45,
                },
                "content_hash": "abc123def456...",
                "is_dry_run": True,
            }
        }


class PipelineEvidenceGenerator:
    """
    Generate evidence packs for pipeline executions.

    Features:
    - Comprehensive evidence collection
    - Deterministic hash generation
    - JSON export
    - Dry-run and live execution support
    """

    # Storage directory
    EVIDENCE_DIR = Path("storage/pipeline_evidence")

    def __init__(self):
        """Initialize evidence generator."""
        self.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    def generate_evidence_pack(
        self,
        execution_result: ExecutionGraphResult,
        business_intent: Optional[ResolvedBusinessIntent] = None,
        graph_spec: Optional[ExecutionGraphSpec] = None,
        governance_decisions: Optional[list[Dict[str, Any]]] = None,
        run_contract: Optional[Any] = None,  # Sprint 9-B: RunContract
    ) -> PipelineEvidencePack:
        """
        Generate evidence pack from execution result.

        Args:
            execution_result: Execution graph result
            business_intent: Resolved business intent (optional)
            graph_spec: Graph specification (optional)
            governance_decisions: Governance check results (optional)
            run_contract: Run contract (Sprint 9-B, optional)

        Returns:
            PipelineEvidencePack
        """
        logger.info(
            f"Generating evidence pack for graph {execution_result.graph_id} "
            f"(dry_run={execution_result.was_dry_run})"
        )

        # Generate pack ID
        pack_id = f"evidence_pack_{execution_result.graph_id}_{int(datetime.utcnow().timestamp())}"

        # Generate summary
        summary = self._generate_summary(execution_result)

        # Extract artifacts
        artifacts = execution_result.artifacts or []

        # Extract audit events
        audit_events = execution_result.audit_events or []

        # Sprint 9-B: Extract contract ID if available
        contract_id = None
        if run_contract:
            contract_id = getattr(run_contract, 'contract_id', None)
            logger.info(f"Evidence pack includes run contract: {contract_id}")

        # Build evidence pack (without hash first)
        pack = PipelineEvidencePack(
            pack_id=pack_id,
            business_intent_id=execution_result.business_intent_id,
            business_intent=business_intent,
            graph_id=execution_result.graph_id,
            graph_spec=graph_spec,
            execution_result=execution_result,
            run_contract=run_contract,  # Sprint 9-B
            contract_id=contract_id,  # Sprint 9-B
            summary=summary,
            governance_decisions=governance_decisions or [],
            artifacts=artifacts,
            audit_events=audit_events,
            content_hash="",  # Will be computed below
            is_dry_run=execution_result.was_dry_run,
        )

        # Compute deterministic hash
        content_hash = self._compute_content_hash(pack)
        pack.content_hash = content_hash

        logger.info(f"Evidence pack generated: {pack_id} (hash={content_hash[:16]}...)")

        return pack

    def save_evidence_pack(self, pack: PipelineEvidencePack) -> Path:
        """
        Save evidence pack to JSON file.

        Args:
            pack: Evidence pack to save

        Returns:
            Path to saved file
        """
        # Create filename
        filename = f"{pack.pack_id}.json"
        file_path = self.EVIDENCE_DIR / filename

        # Save as JSON
        with open(file_path, "w") as f:
            json.dump(pack.model_dump(), f, indent=2, default=str)

        logger.info(f"Evidence pack saved: {file_path}")

        return file_path

    def verify_evidence_pack(self, pack: PipelineEvidencePack) -> bool:
        """
        Verify evidence pack integrity by recomputing hash.

        Args:
            pack: Evidence pack to verify

        Returns:
            True if hash matches, False otherwise
        """
        # Temporarily store original hash
        original_hash = pack.content_hash

        # Recompute hash
        pack.content_hash = ""
        computed_hash = self._compute_content_hash(pack)

        # Restore original hash
        pack.content_hash = original_hash

        # Verify
        is_valid = original_hash == computed_hash

        if is_valid:
            logger.info(f"Evidence pack verified: {pack.pack_id}")
        else:
            logger.warning(
                f"Evidence pack verification FAILED: {pack.pack_id} "
                f"(expected={original_hash[:16]}..., actual={computed_hash[:16]}...)"
            )

        return is_valid

    def _generate_summary(self, result: ExecutionGraphResult) -> Dict[str, Any]:
        """
        Generate execution summary.

        Args:
            result: Execution result

        Returns:
            Summary dict
        """
        return {
            "total_nodes": len(result.execution_order),
            "completed_nodes": len(result.completed_nodes),
            "failed_nodes": len(result.failed_nodes),
            "duration_seconds": result.duration_seconds,
            "success": result.success,
            "status": result.status.value,
            "was_dry_run": result.was_dry_run,
            "artifacts_count": len(result.artifacts),
            "audit_events_count": len(result.audit_events),
            "execution_order": result.execution_order,
        }

    def save_contract_separately(self, pack: PipelineEvidencePack) -> Optional[Path]:
        """
        Save run contract separately as contract.json (Sprint 9-B).

        Args:
            pack: Evidence pack containing run contract

        Returns:
            Path to saved contract file, or None if no contract
        """
        if not pack.run_contract or not pack.contract_id:
            return None

        # Create filename based on contract ID
        filename = f"{pack.contract_id}.json"
        file_path = self.EVIDENCE_DIR / filename

        # Save contract as JSON
        try:
            contract_dict = pack.run_contract.model_dump() if hasattr(pack.run_contract, 'model_dump') else pack.run_contract
            with open(file_path, "w") as f:
                json.dump(contract_dict, f, indent=2, default=str)

            logger.info(f"Run contract saved separately: {file_path}")
            return file_path
        except Exception as e:
            logger.warning(f"Failed to save contract separately: {e}")
            return None

    def _compute_content_hash(self, pack: PipelineEvidencePack) -> str:
        """
        Compute deterministic SHA256 hash of evidence pack.

        Args:
            pack: Evidence pack

        Returns:
            SHA256 hash (hex string)
        """
        # Build hashable content dict (sorted keys for determinism)
        hash_content = {
            "business_intent_id": pack.business_intent_id,
            "graph_id": pack.graph_id,
            "is_dry_run": pack.is_dry_run,
            "summary": pack.summary,
            "execution_order": pack.execution_result.execution_order,
            "completed_nodes": sorted(pack.execution_result.completed_nodes),
            "failed_nodes": sorted(pack.execution_result.failed_nodes),
            "artifacts": sorted(pack.artifacts),
            "contract_id": pack.contract_id,  # Sprint 9-B: Include contract ID
            # Note: Exclude timestamps and generated_at for determinism
        }

        # Convert to sorted JSON
        hash_json = json.dumps(hash_content, sort_keys=True)

        # Compute SHA256
        return hashlib.sha256(hash_json.encode("utf-8")).hexdigest()


# Singleton
_evidence_generator: Optional[PipelineEvidenceGenerator] = None


def get_evidence_generator() -> PipelineEvidenceGenerator:
    """Get singleton evidence generator."""
    global _evidence_generator
    if _evidence_generator is None:
        _evidence_generator = PipelineEvidenceGenerator()
    return _evidence_generator
