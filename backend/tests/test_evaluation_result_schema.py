from uuid import uuid4

from app.modules.skill_evaluator.schemas import EvaluationResultResponse


def test_evaluation_result_response_serializes_pass_alias() -> None:
    result = EvaluationResultResponse.model_validate(
        {
            "id": uuid4(),
            "tenant_id": "tenant-a",
            "skill_run_id": uuid4(),
            "skill_key": "demo.skill",
            "skill_version": 1,
            "evaluator_type": "rule",
            "status": "completed",
            "overall_score": 1.0,
            "dimension_scores": {"quality": 1.0},
            "passed": True,
            "criteria_snapshot": {},
            "findings": {},
            "recommendations": {},
            "metrics_summary": {},
            "provider_selection_snapshot": {},
            "policy_compliance": "compliant",
            "policy_violations": [],
            "evaluation_revision": 1,
            "created_at": "2026-03-22T00:00:00Z",
            "created_by": "skill_evaluator",
        }
    )

    dumped = result.model_dump(mode="json", by_alias=True)
    assert dumped["pass"] is True
    assert "passed" not in dumped
