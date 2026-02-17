"""
Governor Schemas.

Defines governance decision models:
- Mode decision (direct vs. rail)
- Manifest specifications
- Shadow evaluation
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# ============================================================================
# Mode Decision
# ============================================================================

class ModeDecision(BaseModel):
    """
    Decision on execution mode: direct or rail.

    Direct: Execute without NeuroRail observation (fast path)
    Rail: Execute with full NeuroRail observation (governed path)
    """
    decision_id: str = Field(
        default_factory=lambda: f"dec_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:14]}",
        description="Unique decision identifier"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Decision
    mode: str = Field(..., description="Execution mode: direct or rail")
    reason: str = Field(..., description="Reason for mode selection")

    # Context
    mission_id: Optional[str] = None
    job_id: Optional[str] = None
    job_type: Optional[str] = None

    # Evidence
    matched_rules: List[str] = Field(default_factory=list, description="Rule IDs that matched")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Evidence for decision")

    # Shadow Mode (Phase 1)
    shadow_mode: bool = Field(default=False, description="If True, decision was for shadow evaluation only")

    class Config:
        json_schema_extra = {
            "example": {
                "decision_id": "dec_20251230140000",
                "timestamp": "2025-12-30T14:00:00Z",
                "mode": "rail",
                "reason": "Job type requires governance (llm_call with personal_data)",
                "mission_id": "m_a1b2c3d4e5f6",
                "job_id": "j_123456789abc",
                "job_type": "llm_call",
                "matched_rules": ["rule_001", "rule_002"],
                "evidence": {"uses_personal_data": True},
                "shadow_mode": False
            }
        }


# ============================================================================
# Manifest (Phase 2 - minimal interface for Phase 1)
# ============================================================================

class ManifestSpec(BaseModel):
    """
    Minimal manifest specification.

    Phase 1: Only rules for mode decision
    Phase 2: Full budget constraints, execution plan, policies
    """
    version: str = Field(default="1.0", description="Manifest version")
    name: str = Field(..., description="Manifest name")
    description: str = Field(default="", description="Manifest description")

    # Mode selection rules (Phase 1)
    mode_rules: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Rules for selecting mode: [{condition: {...}, mode: 'rail/direct'}]"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "version": "1.0",
                "name": "default_manifest",
                "description": "Default mode selection rules",
                "mode_rules": [
                    {
                        "condition": {"job_type": "llm_call", "uses_personal_data": True},
                        "mode": "rail",
                        "reason": "Personal data processing requires governance"
                    },
                    {
                        "condition": {"job_type": "tool_execution"},
                        "mode": "direct",
                        "reason": "Tool execution is low-risk"
                    }
                ]
            }
        }


# ============================================================================
# Shadow Evaluation
# ============================================================================

class ShadowEvaluation(BaseModel):
    """
    Shadow evaluation result.

    Compares what would have happened with a different manifest version.
    """
    evaluation_id: str = Field(
        default_factory=lambda: f"shad_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:14]}",
        description="Unique evaluation identifier"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Manifest versions
    active_version: str = Field(..., description="Active manifest version")
    shadow_version: str = Field(..., description="Shadow manifest version")

    # Decisions
    active_mode: str = Field(..., description="Mode selected by active manifest")
    shadow_mode: str = Field(..., description="Mode selected by shadow manifest")
    delta: bool = Field(..., description="True if decisions differ")

    # Context
    mission_id: Optional[str] = None
    job_id: Optional[str] = None
    job_type: Optional[str] = None

    # Analysis
    impact_assessment: str = Field(
        default="",
        description="Assessment of impact if shadow version were active"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "evaluation_id": "shad_20251230140000",
                "timestamp": "2025-12-30T14:00:00Z",
                "active_version": "1.0",
                "shadow_version": "1.1",
                "active_mode": "direct",
                "shadow_mode": "rail",
                "delta": True,
                "mission_id": "m_a1b2c3d4e5f6",
                "job_id": "j_123456789abc",
                "job_type": "llm_call",
                "impact_assessment": "Would have enforced governance on 15% more jobs"
            }
        }


# ============================================================================
# Decision Request
# ============================================================================

class DecisionRequest(BaseModel):
    """Request for governance decision."""
    mission_id: Optional[str] = None
    job_id: Optional[str] = None
    job_type: str
    context: Dict[str, Any] = Field(default_factory=dict)
    shadow_evaluate: bool = Field(default=False, description="If True, also evaluate shadow manifest")
