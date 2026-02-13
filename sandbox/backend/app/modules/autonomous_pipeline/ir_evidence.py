"""
IR Evidence Pack Extension (Sprint 10)

Extends evidence pack with IR governance metadata.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from loguru import logger

from app.modules.ir_governance import IR, IRValidationResult, ir_hash
from app.modules.ir_governance.diff_audit import DiffAuditResult
from app.modules.autonomous_pipeline.evidence_generator import PipelineEvidencePack


class IREvidencePack(BaseModel):
    """
    IR-extended evidence pack for WebGenesis pipeline executions.

    Contains all Sprint 8 evidence PLUS IR governance metadata.

    No secrets (no raw approval tokens).
    Deterministic (hashes reproducible).
    """

    # Base evidence pack
    base_evidence: PipelineEvidencePack = Field(..., description="Base evidence from Sprint 8")

    # IR metadata
    ir_enabled: bool = Field(..., description="Whether IR was enabled for this execution")
    ir: Optional[IR] = Field(None, description="Canonical IR (if IR enabled)")
    ir_hash: Optional[str] = Field(None, description="IR hash (SHA256)")

    # Validation
    ir_validation: Optional[IRValidationResult] = Field(None, description="IR validation result")

    # Approval (NO raw token, only metadata)
    approval_used: bool = Field(default=False, description="Whether approval was required and consumed")
    approval_id: Optional[str] = Field(None, description="Approval ID (if used)")

    # Diff-audit
    diff_audit_result: Optional[DiffAuditResult] = Field(None, description="IR ↔ DAG diff-audit result")

    # Summary
    ir_summary: Dict[str, Any] = Field(default_factory=dict, description="IR execution summary")

    class Config:
        json_schema_extra = {
            "example": {
                "base_evidence": {"pack_id": "evidence_pack_123", "...": "..."},
                "ir_enabled": True,
                "ir_hash": "abc123def456...",
                "ir_validation": {"status": "PASS", "risk_tier": 1},
                "approval_used": False,
                "diff_audit_result": {"success": True},
                "ir_summary": {
                    "total_steps": 3,
                    "risk_tier": 1,
                    "approval_required": False,
                },
            }
        }


class IREvidenceGenerator:
    """
    Generate IR-extended evidence packs.

    Extends Sprint 8 evidence with IR governance metadata.
    """

    def generate_ir_evidence_pack(
        self,
        base_evidence: PipelineEvidencePack,
        ir: Optional[IR] = None,
        ir_validation: Optional[IRValidationResult] = None,
        approval_id: Optional[str] = None,
        diff_audit_result: Optional[DiffAuditResult] = None,
    ) -> IREvidencePack:
        """
        Generate IR-extended evidence pack.

        Args:
            base_evidence: Base evidence pack from Sprint 8
            ir: IR (if IR was used)
            ir_validation: IR validation result
            approval_id: Approval ID (if approval was consumed), NO TOKEN
            diff_audit_result: Diff-audit result

        Returns:
            IREvidencePack
        """
        logger.info(
            f"Generating IR evidence pack for {base_evidence.pack_id} "
            f"(ir_enabled={ir is not None})"
        )

        # Determine if IR was enabled
        ir_enabled = ir is not None

        # Compute IR hash
        computed_ir_hash = None
        if ir:
            computed_ir_hash = ir_hash(ir)

        # Determine if approval was used
        approval_used = approval_id is not None

        # Generate IR summary
        ir_summary = {}
        if ir:
            ir_summary = {
                "total_steps": len(ir.steps),
                "tenant_id": ir.tenant_id,
                "request_id": ir.request_id,
                "risk_tier": ir_validation.risk_tier if ir_validation else None,
                "approval_required": ir_validation.requires_approval if ir_validation else False,
                "validation_status": ir_validation.status if ir_validation else None,
                "diff_audit_passed": diff_audit_result.success if diff_audit_result else None,
            }

        # Create IR evidence pack
        ir_evidence = IREvidencePack(
            base_evidence=base_evidence,
            ir_enabled=ir_enabled,
            ir=ir,
            ir_hash=computed_ir_hash,
            ir_validation=ir_validation,
            approval_used=approval_used,
            approval_id=approval_id,
            diff_audit_result=diff_audit_result,
            ir_summary=ir_summary,
        )

        logger.info(
            f"IR evidence pack generated: ir_enabled={ir_enabled}, "
            f"approval_used={approval_used}, hash={computed_ir_hash[:16] if computed_ir_hash else 'N/A'}..."
        )

        return ir_evidence

    def save_ir_evidence_pack(self, ir_evidence: IREvidencePack) -> str:
        """
        Save IR evidence pack to storage.

        Args:
            ir_evidence: IR evidence pack

        Returns:
            Path to saved file
        """
        from pathlib import Path
        import json

        # Create storage directory
        evidence_dir = Path("storage/pipeline_evidence_ir")
        evidence_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        pack_id = ir_evidence.base_evidence.pack_id
        timestamp = int(datetime.utcnow().timestamp())
        filename = f"{pack_id}_ir_{timestamp}.json"
        filepath = evidence_dir / filename

        # Save to file
        with open(filepath, "w") as f:
            json.dump(ir_evidence.model_dump(), f, indent=2, default=str)

        logger.info(f"IR evidence pack saved: {filepath}")

        return str(filepath)


# Singleton
_ir_evidence_generator: Optional[IREvidenceGenerator] = None


def get_ir_evidence_generator() -> IREvidenceGenerator:
    """Get IR evidence generator singleton."""
    global _ir_evidence_generator
    if _ir_evidence_generator is None:
        _ir_evidence_generator = IREvidenceGenerator()
    return _ir_evidence_generator
