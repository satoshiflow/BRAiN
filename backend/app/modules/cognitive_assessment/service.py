from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.modules.cognitive_assessment.schemas import (
    AssociationCase,
    AssociationTrace,
    CognitiveAssessmentRequest,
    CognitiveAssessmentResult,
    CognitiveAssessmentResponse,
    CognitiveLearningFeedbackResponse,
    CognitiveSkillCandidate,
    EvaluationSignal,
    PerceptionSnapshot,
)
from app.modules.knowledge_engine.service import get_knowledge_engine_service
from app.modules.memory.schemas import MemoryQuery
from app.modules.memory.service import get_memory_service
from app.modules.skills_registry.schemas import SkillSortBy
from app.modules.skills_registry.service import get_skill_registry_service

try:
    from mission_control_core.core import Event, EventStream
except ImportError:  # pragma: no cover - optional in some envs
    Event = None
    EventStream = None


def _tokenize(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(token) >= 3]


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


class CognitiveAssessmentService:
    async def _emit_event_safe(self, event_type: str, payload: dict[str, Any]) -> None:
        if EventStream is None or Event is None:
            return
        try:
            stream = EventStream.get_instance()
            await stream.publish(
                Event(
                    type=event_type,
                    source="brain.cognitive_assessment",
                    payload=payload,
                )
            )
        except Exception as exc:  # pragma: no cover - best effort only
            logger.debug("Cognitive assessment event emit skipped: {}", exc)

    def _normalize_intent(self, payload: CognitiveAssessmentRequest) -> str:
        parts = [payload.intent_text or "", payload.problem_statement or "", payload.source_url or ""]
        normalized = "\n".join(part.strip() for part in parts if part and part.strip())
        if not normalized:
            raise ValueError("At least one of intent_text, problem_statement, source_url is required")
        return normalized

    def _derive_perception(self, normalized_intent: str) -> PerceptionSnapshot:
        tokens = _tokenize(normalized_intent)

        modes: list[str] = []
        if any(token in tokens for token in {"search", "find", "query", "lookup", "knowledge"}):
            modes.append("lookup")
        if any(token in tokens for token in {"create", "write", "generate", "draft", "build"}):
            modes.append("creation")
        if any(token in tokens for token in {"run", "execute", "deploy", "restart", "fix"}):
            modes.append("execution")
        if not modes:
            modes.append("general")

        risk_hints: list[str] = []
        if any(token in tokens for token in {"delete", "payment", "invoice", "billing", "admin", "prod", "production", "security", "shutdown"}):
            risk_hints.append("sensitive_operation")
        if any(token in tokens for token in {"customer", "tenant", "personal", "pii", "user"}):
            risk_hints.append("data_handling")

        impact_hints: list[str] = []
        if any(token in tokens for token in {"incident", "outage", "downtime", "failure"}):
            impact_hints.append("service_stability")
        if any(token in tokens for token in {"deploy", "release", "migration", "upgrade"}):
            impact_hints.append("release_path")

        novelty_hints: list[str] = []
        if len(tokens) >= 8:
            novelty_hints.append("broad_intent_surface")
        if any(token in tokens for token in {"custom", "novel", "new", "unknown"}):
            novelty_hints.append("potentially_novel_request")

        return PerceptionSnapshot(
            normalized_intent=normalized_intent,
            intent_keywords=tokens[:12],
            intent_modes=modes,
            risk_hints=risk_hints,
            impact_hints=impact_hints,
            novelty_hints=novelty_hints,
        )

    async def _associate_memory(self, principal: Principal, normalized_intent: str, mission_id: str | None) -> list[AssociationCase]:
        if not principal.tenant_id:
            return []
        query = MemoryQuery(
            query=normalized_intent[:1000],
            tenant_id=principal.tenant_id,
            mission_id=mission_id,
            limit=5,
        )
        result = await get_memory_service().recall_memories(query)
        cases: list[AssociationCase] = []
        for memory in result.memories[:5]:
            cases.append(
                AssociationCase(
                    source_type="memory",
                    source_id=memory.memory_id,
                    title=memory.memory_type,
                    score=_clamp((memory.importance / 100.0 * 0.6) + (memory.karma_score / 100.0 * 0.4)),
                    summary=memory.summary or memory.content[:240],
                    metadata={
                        "layer": memory.layer,
                        "mission_id": memory.mission_id,
                        "skill_run_id": memory.skill_run_id,
                    },
                )
            )
        return cases

    async def _associate_knowledge(self, db: AsyncSession, principal: Principal, normalized_intent: str) -> list[AssociationCase]:
        knowledge = await get_knowledge_engine_service().list_items(
            db,
            principal,
            query=normalized_intent[:500],
            limit=5,
        )
        cases: list[AssociationCase] = []
        for item in knowledge[:5]:
            cases.append(
                AssociationCase(
                    source_type="knowledge",
                    source_id=str(item["id"]),
                    title=str(item["title"]),
                    score=0.6,
                    summary=str(item["content"])[:240],
                    metadata={
                        "type": item.get("type"),
                        "tags": item.get("tags") or [],
                    },
                )
            )
        return cases

    def _definition_corpus(self, definition: Any) -> str:
        required_caps = [
            str(cap.get("capability_key", ""))
            for cap in (getattr(definition, "required_capabilities", []) or [])
            if isinstance(cap, dict)
        ]
        optional_caps = [
            str(cap.get("capability_key", ""))
            for cap in (getattr(definition, "optional_capabilities", []) or [])
            if isinstance(cap, dict)
        ]
        return " ".join(
            [
                str(getattr(definition, "skill_key", "")),
                str(getattr(definition, "purpose", "")),
                str(getattr(definition, "description", "")),
                " ".join(required_caps),
                " ".join(optional_caps),
            ]
        )

    def _score_definition(self, definition: Any, tokens: list[str], association: AssociationTrace, perception: PerceptionSnapshot) -> CognitiveSkillCandidate | None:
        corpus_tokens = set(_tokenize(self._definition_corpus(definition)))
        if not corpus_tokens:
            return None
        token_set = set(tokens)
        overlap = len(token_set.intersection(corpus_tokens))
        base = overlap / max(1, len(token_set))
        skill_key = str(getattr(definition, "skill_key", "")).lower()
        if any(token in skill_key for token in token_set):
            base += 0.12
        if association.total_cases > 0:
            base += min(0.15, association.total_cases * 0.025)
        if perception.risk_hints and str(getattr(definition, "risk_tier", "low")).lower() == "low":
            base -= 0.05
        if "lookup" in perception.intent_modes and "knowledge" in skill_key:
            base += 0.08
        value_boost = min(0.1, float(getattr(definition, "value_score", 0.0) or 0.0) * 0.1)
        score = _clamp(base + value_boost)
        if score <= 0.0:
            return None
        return CognitiveSkillCandidate(
            skill_key=str(definition.skill_key),
            version=int(definition.version),
            score=score,
            reason=f"overlap={overlap}, risk={definition.risk_tier}, association_cases={association.total_cases}",
        )

    def _derive_evaluation(
        self,
        *,
        perception: PerceptionSnapshot,
        association: AssociationTrace,
        recommended_skill_candidates: list[CognitiveSkillCandidate],
    ) -> EvaluationSignal:
        top_score = recommended_skill_candidates[0].score if recommended_skill_candidates else 0.0
        association_strength = min(1.0, association.total_cases / 6.0)
        novelty_score = _clamp(1.0 - association_strength + (0.1 if perception.novelty_hints else 0.0))
        impact_score = _clamp((0.25 * len(perception.impact_hints)) + (0.2 * len(perception.risk_hints)) + (0.35 * top_score))
        confidence = _clamp((top_score * 0.65) + (association_strength * 0.25) + (0.1 if not perception.novelty_hints else 0.0))

        governance_hints: list[str] = []
        if perception.risk_hints:
            governance_hints.append("pre_policy_sensitive_review")
        if novelty_score >= 0.7:
            governance_hints.append("novel_request_check")
        if confidence < 0.4:
            governance_hints.append("low_confidence_resolution")

        risk_hints = list(dict.fromkeys([*perception.risk_hints, *(governance_hints if perception.risk_hints else [])]))
        return EvaluationSignal(
            confidence=confidence,
            novelty_score=novelty_score,
            impact_score=impact_score,
            governance_hints=governance_hints,
            risk_hints=risk_hints,
        )

    def _build_result(self, evaluation: EvaluationSignal) -> CognitiveAssessmentResult:
        return CognitiveAssessmentResult(
            confidence=evaluation.confidence,
            risk=evaluation.risk_hints,
            impact=evaluation.impact_score,
            novelty=evaluation.novelty_score,
            governance_flags=evaluation.governance_hints,
            routing_hint=None,
        )

    async def assess(
        self,
        db: AsyncSession,
        payload: CognitiveAssessmentRequest,
        principal: Principal,
    ) -> CognitiveAssessmentResponse:
        normalized_intent = self._normalize_intent(payload)
        perception = self._derive_perception(normalized_intent)
        memory_cases = await self._associate_memory(principal, normalized_intent, payload.mission_id)
        knowledge_cases = await self._associate_knowledge(db, principal, normalized_intent)
        association = AssociationTrace(
            memory_cases=memory_cases,
            knowledge_cases=knowledge_cases,
            total_cases=len(memory_cases) + len(knowledge_cases),
        )

        definitions = await get_skill_registry_service().list_definitions(
            db,
            tenant_id=principal.tenant_id,
            include_system=True,
            status="active",
            sort_by=SkillSortBy.VALUE_SCORE,
        )
        latest_by_key: dict[str, Any] = {}
        for item in definitions:
            existing = latest_by_key.get(item.skill_key)
            if existing is None or item.version > existing.version:
                latest_by_key[item.skill_key] = item
            elif (
                existing is not None
                and item.version == existing.version
                and principal.tenant_id
                and item.tenant_id == principal.tenant_id
                and existing.tenant_id != principal.tenant_id
            ):
                latest_by_key[item.skill_key] = item

        tokens = perception.intent_keywords
        candidates = [
            candidate
            for candidate in (
                self._score_definition(item, tokens, association, perception)
                for item in latest_by_key.values()
            )
            if candidate is not None
        ]
        candidates.sort(key=lambda item: item.score, reverse=True)
        candidates = candidates[:5]

        evaluation = self._derive_evaluation(
            perception=perception,
            association=association,
            recommended_skill_candidates=candidates,
        )
        result_payload = self._build_result(evaluation)

        result = await db.execute(
            text(
                """
                INSERT INTO cognitive_assessments (
                    tenant_id,
                    mission_id,
                    normalized_intent,
                    perception,
                    association_trace,
                    evaluation_signal,
                    recommended_skill_candidates,
                    created_by
                ) VALUES (
                    :tenant_id,
                    :mission_id,
                    :normalized_intent,
                    CAST(:perception AS jsonb),
                    CAST(:association_trace AS jsonb),
                    CAST(:evaluation_signal AS jsonb),
                    CAST(:recommended_skill_candidates AS jsonb),
                    :created_by
                )
                RETURNING id, tenant_id, mission_id, normalized_intent, perception, association_trace, evaluation_signal, recommended_skill_candidates, created_at
                """
            ),
            {
                "tenant_id": principal.tenant_id,
                "mission_id": payload.mission_id,
                "normalized_intent": normalized_intent,
                "perception": perception.model_dump_json(),
                "association_trace": association.model_dump_json(),
                "evaluation_signal": evaluation.model_dump_json(),
                "recommended_skill_candidates": json.dumps([item.model_dump() for item in candidates]),
                "created_by": principal.principal_id,
            },
        )
        row = result.mappings().one()
        await db.commit()

        await self._emit_event_safe(
            "cognitive.assessment.created",
            {
                "assessment_id": str(row["id"]),
                "tenant_id": principal.tenant_id,
                "mission_id": payload.mission_id,
                "confidence": evaluation.confidence,
                "novelty_score": evaluation.novelty_score,
                "impact_score": evaluation.impact_score,
            },
        )

        return CognitiveAssessmentResponse(
            assessment_id=row["id"],
            tenant_id=row.get("tenant_id"),
            mission_id=row.get("mission_id"),
            perception=perception,
            association=association,
            evaluation=evaluation,
            result=result_payload,
            recommended_skill_candidates=candidates,
            created_at=row["created_at"],
        )

    async def get_assessment(self, db: AsyncSession, assessment_id: UUID, principal: Principal) -> CognitiveAssessmentResponse | None:
        result = await db.execute(
            text(
                """
                SELECT id, tenant_id, mission_id, normalized_intent, perception, association_trace, evaluation_signal, recommended_skill_candidates, created_at
                FROM cognitive_assessments
                WHERE id = :assessment_id
                  AND (CAST(:tenant_id AS text) IS NULL OR tenant_id = :tenant_id)
                """
            ),
            {"assessment_id": str(assessment_id), "tenant_id": principal.tenant_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        return CognitiveAssessmentResponse(
            assessment_id=row["id"],
            tenant_id=row.get("tenant_id"),
            mission_id=row.get("mission_id"),
            perception=PerceptionSnapshot.model_validate(row["perception"] or {}),
            association=AssociationTrace.model_validate(row["association_trace"] or {}),
            evaluation=EvaluationSignal.model_validate(row["evaluation_signal"] or {}),
            result=self._build_result(EvaluationSignal.model_validate(row["evaluation_signal"] or {})),
            recommended_skill_candidates=[
                CognitiveSkillCandidate.model_validate(item)
                for item in (row["recommended_skill_candidates"] or [])
            ],
            created_at=row["created_at"],
        )

    async def write_learning_feedback(
        self,
        db: AsyncSession,
        *,
        assessment_id: UUID,
        skill_run_id: UUID,
        outcome_state: str,
        overall_score: float | None,
        success: bool,
        metadata: dict[str, Any],
        evaluation_result_id: UUID | None = None,
        experience_record_id: UUID | None = None,
    ) -> CognitiveLearningFeedbackResponse:
        result = await db.execute(
            text(
                """
                INSERT INTO cognitive_learning_feedback (
                    assessment_id,
                    skill_run_id,
                    evaluation_result_id,
                    experience_record_id,
                    outcome_state,
                    overall_score,
                    success,
                    metadata
                ) VALUES (
                    :assessment_id,
                    :skill_run_id,
                    :evaluation_result_id,
                    :experience_record_id,
                    :outcome_state,
                    :overall_score,
                    :success,
                    CAST(:metadata AS jsonb)
                )
                RETURNING id, assessment_id, skill_run_id, evaluation_result_id, experience_record_id, outcome_state, overall_score, success, metadata, created_at
                """
            ),
            {
                "assessment_id": str(assessment_id),
                "skill_run_id": str(skill_run_id),
                "evaluation_result_id": str(evaluation_result_id) if evaluation_result_id else None,
                "experience_record_id": str(experience_record_id) if experience_record_id else None,
                "outcome_state": outcome_state,
                "overall_score": overall_score,
                "success": success,
                "metadata": json.dumps(metadata),
            },
        )
        row = result.mappings().one()

        await db.execute(
            text(
                """
                UPDATE cognitive_assessments
                SET latest_skill_run_id = :skill_run_id,
                    latest_feedback_at = NOW(),
                    latest_feedback_score = :overall_score,
                    latest_feedback_success = :success
                WHERE id = :assessment_id
                """
            ),
            {
                "assessment_id": str(assessment_id),
                "skill_run_id": str(skill_run_id),
                "overall_score": overall_score,
                "success": success,
            },
        )
        await db.commit()

        logger.info(
            "Cognitive assessment feedback stored: assessment={} run={} success={} score={}",
            assessment_id,
            skill_run_id,
            success,
            overall_score,
        )

        await self._emit_event_safe(
            "cognitive.learning.updated",
            {
                "assessment_id": str(assessment_id),
                "skill_run_id": str(skill_run_id),
                "success": success,
                "overall_score": overall_score,
                "outcome_state": outcome_state,
            },
        )

        return CognitiveLearningFeedbackResponse.model_validate(dict(row))


_service: CognitiveAssessmentService | None = None


def get_cognitive_assessment_service() -> CognitiveAssessmentService:
    global _service
    if _service is None:
        _service = CognitiveAssessmentService()
    return _service
